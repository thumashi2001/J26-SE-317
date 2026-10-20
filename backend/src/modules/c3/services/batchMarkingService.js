import { getDb } from '../../../config/db.js';
import { ObjectId } from 'mongodb';
import * as mcqSvc from './mcqMarkingService.js';
import * as aiClient from './aiClient.js';
import * as submissionSvc from './submissionService.js';
import { syncC3AssessmentToC1 } from '../../../integration/c3-c1/index.js';

function httpError(status, message) {
  const err = new Error(message);
  err.status = status;
  return err;
}

function parseId(id) {
  if (!id) return null;
  if (ObjectId.isValid(id) && typeof id === 'string' && id.length === 24) {
    return new ObjectId(id);
  }
  return id;
}

export function batchSetupsCol() {
  return getDb().collection('c3_batch_setups');
}

function submissionsCol() {
  return getDb().collection('c3_submissions');
}

function resultsCol() {
  return getDb().collection('c3_results');
}

/**
 * Validates and sanitizes assessment setup data.
 */
export function validateSetupData(setupData) {
  if (!setupData || typeof setupData !== 'object') {
    throw httpError(400, 'Assessment setup data is required');
  }

  const title = String(setupData.title || '').trim();
  if (!title || title.length < 3) {
    throw httpError(400, 'Assessment title must be at least 3 characters long');
  }

  const questionText = String(setupData.question_text || '').trim();
  if (!questionText || questionText.length < 5) {
    throw httpError(400, 'Question text must be at least 5 characters long');
  }

  const questionId = String(setupData.question_id || `Q-${Date.now()}`).trim();
  const moduleId = String(setupData.module_id || 'SE3010').trim();
  const answerType = String(setupData.answer_type || 'short').toLowerCase();

  if (!['short', 'essay', 'mcq', 'multiple-choice'].includes(answerType)) {
    throw httpError(400, "Answer type must be 'short', 'essay', or 'mcq'");
  }

  const maxMarks = Number(setupData.max_marks);
  if (isNaN(maxMarks) || maxMarks <= 0) {
    throw httpError(400, 'Maximum marks must be a positive number');
  }

  const isMcq = answerType === 'mcq' || answerType === 'multiple-choice';

  if (isMcq) {
    const rawOptions = setupData.options;
    if (!rawOptions || (Array.isArray(rawOptions) && rawOptions.length < 2)) {
      throw httpError(400, 'MCQ assessment requires at least 2 options');
    }
    const normalizedOptions = mcqSvc.normalizeOptions(rawOptions);
    if (normalizedOptions.length < 2) {
      throw httpError(400, 'MCQ assessment requires at least 2 valid options');
    }

    const correctAnswer = String(setupData.correct_answer || setupData.correct_option_id || '').trim();
    if (!correctAnswer) {
      throw httpError(400, 'MCQ assessment requires an authoritative correct answer key');
    }

    const matchingOption = normalizedOptions.find(
      (o) => o.option_id.toLowerCase() === correctAnswer.toLowerCase() ||
             o.label.toLowerCase() === correctAnswer.toLowerCase()
    );
    if (!matchingOption) {
      throw httpError(400, `Authoritative correct answer '${correctAnswer}' does not match any configured option`);
    }

    return {
      title,
      question_id: questionId,
      module_id: moduleId,
      question_text: questionText,
      answer_type: 'mcq',
      max_marks: maxMarks,
      options: normalizedOptions,
      correct_answer: matchingOption.option_id,
      expected_concepts: Array.isArray(setupData.expected_concepts) ? setupData.expected_concepts : [],
    };
  } else {
    // Subjective (short or essay)
    const rubric = setupData.rubric;
    if (!rubric || typeof rubric !== 'object') {
      throw httpError(400, 'Subjective assessment requires a rubric configuration');
    }
    const criteria = rubric.criteria;
    if (!Array.isArray(criteria) || criteria.length === 0) {
      throw httpError(400, 'Rubric must contain at least one evaluation criterion');
    }

    let criteriaSum = 0;
    const sanitizedCriteria = criteria.map((c, idx) => {
      const cId = String(c.criterion_id || `C${idx + 1}`).trim();
      const desc = String(c.description || '').trim();
      if (!desc) {
        throw httpError(400, `Criterion ${cId} is missing a description`);
      }
      const cMaxMarks = Number(c.max_marks);
      if (isNaN(cMaxMarks) || cMaxMarks <= 0) {
        throw httpError(400, `Criterion ${cId} must have positive max_marks`);
      }
      criteriaSum += cMaxMarks;

      const levels = Array.isArray(c.scoring_levels) && c.scoring_levels.length > 0
        ? c.scoring_levels
        : [
            { level_id: 'L0', label: 'None', mark: 0, descriptor: 'No evidence' },
            { level_id: 'L1', label: 'Proficient', mark: cMaxMarks, descriptor: 'Criteria satisfied' }
          ];

      return {
        criterion_id: cId,
        description: desc,
        max_marks: cMaxMarks,
        required_concepts: Array.isArray(c.required_concepts) ? c.required_concepts : [],
        scoring_levels: levels,
      };
    });

    if (Math.abs(criteriaSum - maxMarks) > 0.001) {
      throw httpError(
        400,
        `The sum of rubric criteria marks (${criteriaSum}) must equal the assessment max marks (${maxMarks})`
      );
    }

    return {
      title,
      question_id: questionId,
      module_id: moduleId,
      question_text: questionText,
      answer_type: answerType,
      max_marks: maxMarks,
      reference_answer: String(setupData.reference_answer || '').trim() || null,
      expected_concepts: Array.isArray(setupData.expected_concepts)
        ? setupData.expected_concepts.map((s) => String(s).trim()).filter(Boolean)
        : [],
      rubric: {
        rubric_id: String(rubric.rubric_id || `R-${questionId}`).trim(),
        title: String(rubric.title || `${title} Rubric`).trim(),
        criteria: sanitizedCriteria,
      },
    };
  }
}

/**
 * Creates and persists a shared batch assessment setup.
 */
export async function createBatchSetup({ lecturerId, setupData }) {
  const sanitized = validateSetupData(setupData);
  const now = new Date();
  const batchId = `BATCH-${sanitized.question_id}-${Date.now().toString(36).toUpperCase()}`;

  const setupDoc = {
    ...sanitized,
    batch_id: batchId,
    created_by: lecturerId,
    status: 'active',
    created_at: now,
    updated_at: now,
  };

  const res = await batchSetupsCol().insertOne(setupDoc);
  return {
    ...setupDoc,
    _id: String(res.insertedId),
  };
}

/**
 * Lists all batch setups with submission summary statistics.
 */
export async function listBatchSetups({ lecturerId, role }) {
  const query = {};
  if (role !== 'admin') {
    query.created_by = lecturerId;
  }

  const setups = await batchSetupsCol()
    .find(query)
    .sort({ created_at: -1 })
    .limit(100)
    .toArray();

  if (setups.length === 0) return [];

  const batchIds = setups.map((s) => s.batch_id);

  // Group submissions by batch_id
  const submissions = await submissionsCol()
    .find({ batch_id: { $in: batchIds } })
    .toArray();

  const subStats = new Map();
  for (const s of submissions) {
    const bId = s.batch_id;
    if (!subStats.has(bId)) {
      subStats.set(bId, { total: 0, pending: 0, reviewed: 0, finalized: 0, failed: 0 });
    }
    const stat = subStats.get(bId);
    stat.total += 1;
    if (s.status === 'finalized') stat.finalized += 1;
    else if (s.status === 'reviewed') stat.reviewed += 1;
    else if (s.status === 'failed') stat.failed += 1;
    else stat.pending += 1;
  }

  return setups.map((s) => {
    const st = subStats.get(s.batch_id) || { total: 0, pending: 0, reviewed: 0, finalized: 0, failed: 0 };
    return {
      _id: String(s._id),
      batch_id: s.batch_id,
      title: s.title,
      question_id: s.question_id,
      module_id: s.module_id,
      answer_type: s.answer_type,
      max_marks: s.max_marks,
      created_by: s.created_by,
      created_at: s.created_at,
      stats: st,
    };
  });
}

/**
 * Retrieves a single batch setup and its associated student results.
 */
export async function getBatchSetup(setupId, role) {
  const parsed = parseId(setupId);
  const setup = await batchSetupsCol().findOne({
    $or: [{ _id: parsed }, { batch_id: String(setupId) }, { _id: String(setupId) }],
  });

  if (!setup) {
    throw httpError(404, 'Assessment batch setup not found');
  }

  const batchId = setup.batch_id;

  // Retrieve all submissions in this batch
  const submissions = await submissionsCol()
    .find({ batch_id: batchId })
    .sort({ submitted_at: -1 })
    .toArray();

  const subIds = submissions.map((s) => String(s._id));
  const results = await resultsCol()
    .find({ submission_id: { $in: subIds } })
    .toArray();

  const resultMap = new Map();
  for (const r of results) {
    resultMap.set(String(r.submission_id), r);
  }

  let totalMarksSum = 0;
  let finalizedCount = 0;
  let reviewedCount = 0;
  let pendingCount = 0;
  let failedCount = 0;

  const items = submissions.map((s) => {
    const sId = String(s._id);
    const r = resultMap.get(sId);
    const automatedMark =
      r?.automated_mark ??
      r?.ai_evaluation?.total_awarded_marks ??
      r?.ai_result?.marking?.total_awarded_marks ??
      0;
    const finalMark = r?.final_mark ?? null;
    const currentMark = finalMark !== null ? finalMark : automatedMark;
    totalMarksSum += currentMark;

    const status = r?.status || s.status || 'pending_review';
    if (status === 'finalized') finalizedCount += 1;
    else if (status === 'reviewed') reviewedCount += 1;
    else if (status === 'failed') failedCount += 1;
    else pendingCount += 1;

    return {
      submission_id: sId,
      student_id: s.student_id,
      student_answer: s.student_answer,
      selected_options: s.selected_options,
      status,
      automated_mark: automatedMark,
      final_mark: finalMark,
      percentage: r?.percentage ?? (setup.max_marks > 0 ? Math.round((currentMark / setup.max_marks) * 1000) / 10 : 0),
      lecturer_decision: r?.lecturer_decision || null,
      override_reason: r?.override_reason || null,
      reviewed_by: r?.reviewed_by || null,
      submitted_at: s.submitted_at,
      evaluated_at: r?.created_at,
    };
  });

  const totalCount = items.length;
  const averageMark = totalCount > 0 ? Math.round((totalMarksSum / totalCount) * 10) / 10 : 0;

  return {
    setup: {
      ...setup,
      _id: String(setup._id),
    },
    items,
    stats: {
      total_count: totalCount,
      pending_count: pendingCount,
      reviewed_count: reviewedCount,
      finalized_count: finalizedCount,
      failed_count: failedCount,
      average_mark: averageMark,
      max_marks: setup.max_marks,
    },
  };
}

/**
 * Validates multiple student answers against a batch setup prior to marking.
 */
export async function validateBatchAnswers({ setupId, items }) {
  const parsed = parseId(setupId);
  const setup = await batchSetupsCol().findOne({
    $or: [{ _id: parsed }, { batch_id: String(setupId) }, { _id: String(setupId) }],
  });

  if (!setup) {
    throw httpError(404, 'Assessment batch setup not found');
  }

  if (!Array.isArray(items) || items.length === 0) {
    throw httpError(400, 'A non-empty list of student answers is required');
  }

  const isMcq = setup.answer_type === 'mcq' || setup.answer_type === 'multiple-choice';
  const validItems = [];
  const invalidItems = [];
  const seenStudentIds = new Set();

  items.forEach((item, index) => {
    const rowNum = index + 1;
    const studentId = String(item.student_id || '').trim().toUpperCase();

    if (!studentId) {
      invalidItems.push({
        row: rowNum,
        student_id: '',
        reason: 'Student ID is missing or empty',
      });
      return;
    }

    if (seenStudentIds.has(studentId)) {
      invalidItems.push({
        row: rowNum,
        student_id: studentId,
        reason: `Duplicate student ID '${studentId}' in the same batch submission`,
      });
      return;
    }
    seenStudentIds.add(studentId);

    if (isMcq) {
      const selectedOption = String(
        item.selected_option_id || item.selected_option || item.student_answer || ''
      ).trim();

      if (!selectedOption) {
        // Flagged as unanswered, but still a valid row for grading (will receive 0 marks)
        validItems.push({
          row: rowNum,
          student_id: studentId,
          selected_option_id: null,
          student_answer: '',
          is_unanswered: true,
        });
        return;
      }

      // Check if selected option is valid
      const matchingOpt = setup.options.find(
        (o) => o.option_id.toLowerCase() === selectedOption.toLowerCase() ||
               o.label.toLowerCase() === selectedOption.toLowerCase()
      );

      if (!matchingOpt) {
        invalidItems.push({
          row: rowNum,
          student_id: studentId,
          reason: `Invalid option '${selectedOption}'. Valid options are: ${setup.options.map((o) => o.label).join(', ')}`,
        });
        return;
      }

      validItems.push({
        row: rowNum,
        student_id: studentId,
        selected_option_id: matchingOpt.option_id,
        student_answer: matchingOpt.label,
        is_unanswered: false,
      });
    } else {
      // Subjective
      const answerText = String(item.student_answer || item.answer || '').trim();
      if (!answerText) {
        invalidItems.push({
          row: rowNum,
          student_id: studentId,
          reason: 'Student answer text is empty',
        });
        return;
      }

      validItems.push({
        row: rowNum,
        student_id: studentId,
        student_answer: answerText,
      });
    }
  });

  return {
    batch_id: setup.batch_id,
    setup_title: setup.title,
    question_id: setup.question_id,
    answer_type: setup.answer_type,
    total_rows: items.length,
    valid_count: validItems.length,
    invalid_count: invalidItems.length,
    valid_items: validItems,
    invalid_items: invalidItems,
  };
}

/**
 * Executes automated batch marking for all valid student answers against the shared setup.
 */
export async function processBatchMarking({ lecturerId, setupId, items, aiUrl }) {
  const parsed = parseId(setupId);
  const setup = await batchSetupsCol().findOne({
    $or: [{ _id: parsed }, { batch_id: String(setupId) }, { _id: String(setupId) }],
  });

  if (!setup) {
    throw httpError(404, 'Assessment batch setup not found');
  }

  const isMcq = setup.answer_type === 'mcq' || setup.answer_type === 'multiple-choice';
  const validation = await validateBatchAnswers({ setupId: setup.batch_id, items });

  if (validation.valid_count === 0) {
    throw httpError(400, 'No valid student answers found in the submitted batch');
  }

  const results = [];
  let successCount = 0;
  let failCount = 0;

  for (const item of validation.valid_items) {
    try {
      let aiResult;
      const payload = {
        question_id: setup.question_id,
        question_text: setup.question_text,
        answer_type: setup.answer_type,
        max_marks: setup.max_marks,
        batch_id: setup.batch_id,
        student_id: item.student_id,
      };

      if (isMcq) {
        payload.options = setup.options;
        payload.correct_answer = setup.correct_answer;
        payload.selected_option_id = item.selected_option_id;
        payload.student_answer = item.student_answer;
        payload.expected_concepts = setup.expected_concepts || [];

        aiResult = mcqSvc.evaluateMcqAnswer(payload);
      } else {
        payload.rubric = setup.rubric;
        payload.reference_answer = setup.reference_answer;
        payload.expected_concepts = setup.expected_concepts || [];
        payload.student_answer = item.student_answer;

        aiResult = await aiClient.assessAnswer(aiUrl, payload);
      }

      // Persist submission and result idempotently
      const { submissionId, resultId } = await submissionSvc.createSubmissionWithResult({
        studentId: item.student_id,
        payload,
        aiResult,
      });

      const awardedMark = aiResult?.total_awarded_marks ?? aiResult?.marking?.total_awarded_marks ?? 0;
      results.push({
        student_id: item.student_id,
        submission_id: submissionId,
        result_id: resultId,
        awarded_mark: awardedMark,
        max_marks: setup.max_marks,
        percentage: setup.max_marks > 0 ? Math.round((awardedMark / setup.max_marks) * 1000) / 10 : 0,
        status: 'pending_review',
      });
      successCount += 1;
    } catch (err) {
      failCount += 1;
      results.push({
        student_id: item.student_id,
        status: 'failed',
        error: err.message || 'Evaluation failed for this student',
      });
    }
  }

  return {
    batch_id: setup.batch_id,
    setup_title: setup.title,
    question_id: setup.question_id,
    total_processed: validation.valid_items.length,
    successful_count: successCount,
    failed_count: failCount,
    invalid_rows_ignored: validation.invalid_count,
    results,
  };
}

/**
 * Finalizes all eligible submissions in a batch in one confirmed operation.
 */
export async function finalizeBatchSubmissions({ lecturerId, batchId }) {
  const setup = await batchSetupsCol().findOne({ batch_id: String(batchId) });
  if (!setup) {
    throw httpError(404, 'Assessment batch setup not found');
  }

  const submissions = await submissionsCol()
    .find({ batch_id: setup.batch_id })
    .toArray();

  if (submissions.length === 0) {
    return { batch_id: setup.batch_id, finalized_count: 0, message: 'No submissions found in this batch' };
  }

  const subIds = submissions.map((s) => String(s._id));
  const results = await resultsCol()
    .find({ submission_id: { $in: subIds } })
    .toArray();

  let finalizedCount = 0;
  const now = new Date();

  for (const r of results) {
    if (r.status === 'finalized') {
      finalizedCount += 1;
      continue;
    }

    const sub = submissions.find((s) => String(s._id) === String(r.submission_id));
    const effectiveMark = r.final_mark !== null && r.final_mark !== undefined
      ? r.final_mark
      : (r.automated_mark ?? r.ai_evaluation?.total_awarded_marks ?? 0);
    const decision = r.lecturer_decision || 'accepted';

    await resultsCol().updateOne(
      { _id: r._id },
      {
        $set: {
          status: 'finalized',
          lecturer_decision: decision,
          final_mark: effectiveMark,
          reviewed_by: r.reviewed_by || lecturerId,
          finalized_at: now,
          updated_at: now,
        },
      }
    );

    await submissionsCol().updateOne(
      { _id: r.submission_id ? parseId(r.submission_id) : parseId(sub?._id) },
      {
        $set: {
          status: 'finalized',
          updated_at: now,
        },
      }
    );

    // Sync to C1 idempotently
    const finalPct = setup.max_marks > 0 ? Math.round((effectiveMark / setup.max_marks) * 1000) / 10 : 0;
    syncC3AssessmentToC1({
      studentId: sub ? sub.student_id : r.student_id,
      submissionId: String(r.submission_id),
      questionId: setup.question_id,
      questionText: setup.question_text,
      score: effectiveMark,
      totalPossible: setup.max_marks,
      percentage: finalPct,
      conceptMatches: r.ai_evaluation?.analysis?.concept_matches || [],
      finalized: true,
      lecturerDecision: decision,
      overrideReason: r.override_reason || null,
      reviewedBy: r.reviewed_by || lecturerId,
    }).catch(() => {});

    finalizedCount += 1;
  }

  return {
    batch_id: setup.batch_id,
    finalized_count: finalizedCount,
    total_submissions: submissions.length,
    status: 'finalized',
  };
}
