/**
 * Component 3 — Automated MCQ / Objective Marking Service
 *
 * Implements deterministic, authoritative answer-key evaluation for Multiple-Choice Questions (MCQ).
 * Keeps objective evaluation strictly separate from subjective semantic NLP/rubric evaluation.
 */

function httpError(status, message) {
  const err = new Error(message);
  err.status = status;
  return err;
}

/**
 * Normalizes options into a standardized list of objects:
 * [{ option_id: 'opt_1', label: 'A', text: '...' }, ...]
 */
export function normalizeOptions(options) {
  if (!options) return [];

  // If already an array of objects
  if (Array.isArray(options)) {
    return options.map((opt, idx) => {
      const defaultLabel = String.fromCharCode(65 + idx); // A, B, C, D...
      if (typeof opt === 'string') {
        return {
          option_id: defaultLabel,
          label: defaultLabel,
          text: opt.trim(),
        };
      }
      if (typeof opt === 'object' && opt !== null) {
        const id = String(opt.option_id || opt.id || opt.key || defaultLabel).trim();
        const label = String(opt.label || opt.key || defaultLabel).trim();
        const text = String(opt.text || opt.option_text || opt.description || '').trim();
        return { option_id: id, label, text };
      }
      return { option_id: defaultLabel, label: defaultLabel, text: String(opt) };
    });
  }

  // If an object mapping keys to text, e.g. { A: 'Text A', B: 'Text B' }
  if (typeof options === 'object') {
    return Object.entries(options).map(([key, val], idx) => {
      const defaultLabel = String.fromCharCode(65 + idx);
      const label = String(key).trim();
      const text = typeof val === 'object' && val !== null ? String(val.text || val.description || '') : String(val);
      return {
        option_id: label,
        label: label,
        text: text.trim(),
      };
    });
  }

  return [];
}

/**
 * Resolves an option selector (ID, label, or text) to canonical option_id.
 */
function resolveOptionId(selector, normalizedOptions) {
  if (selector === null || selector === undefined) return null;
  const selStr = String(selector).trim();
  if (!selStr) return null;

  // 1. Direct match on option_id (case-insensitive)
  const byId = normalizedOptions.find((o) => o.option_id.toLowerCase() === selStr.toLowerCase());
  if (byId) return byId.option_id;

  // 2. Direct match on label (case-insensitive)
  const byLabel = normalizedOptions.find((o) => o.label.toLowerCase() === selStr.toLowerCase());
  if (byLabel) return byLabel.option_id;

  // 3. Match on option text
  const byText = normalizedOptions.find((o) => o.text.toLowerCase() === selStr.toLowerCase());
  if (byText) return byText.option_id;

  return null;
}

/**
 * Evaluates an MCQ answer against the authoritative question answer key.
 *
 * @param {Object} payload
 * @param {string} payload.question_id
 * @param {string} payload.question_text
 * @param {Array|Object} payload.options - Option list or dictionary
 * @param {string|Array} [payload.correct_answer] - Authoritative correct option ID(s)
 * @param {Array} [payload.correct_options] - Authoritative correct option ID(s)
 * @param {string|number} [payload.max_marks] - Maximum possible mark (default 1.0)
 * @param {string|Array} [payload.selected_option_id] - Student's chosen option ID
 * @param {Array} [payload.selected_options] - Student's chosen options for multi-select
 * @param {string} [payload.student_answer] - Fallback student response text or option ID
 * @returns {Object} Deterministic C3 marking and evaluation result
 */
export function evaluateMcqAnswer(payload = {}) {
  // 1. Validate Question Identification
  const qId = String(payload.question_id || '').trim();
  if (!qId) {
    throw httpError(400, 'question_id is required for MCQ marking');
  }

  const qText = String(payload.question_text || '').trim();
  if (!qText) {
    throw httpError(400, 'question_text is required for MCQ marking');
  }

  // 2. Validate Options
  const normalizedOptions = normalizeOptions(payload.options);
  if (normalizedOptions.length < 2) {
    throw httpError(400, 'MCQ question must have at least 2 options');
  }

  // Check for duplicate option IDs
  const seenIds = new Set();
  for (const opt of normalizedOptions) {
    const lower = opt.option_id.toLowerCase();
    if (seenIds.has(lower)) {
      throw httpError(400, `Duplicate option ID '${opt.option_id}' detected in options`);
    }
    seenIds.add(lower);
  }

  // 3. Validate Authoritative Answer Key
  let correctKeyRaw = payload.correct_options || payload.correct_answer || payload.answer_key;
  if (!correctKeyRaw && payload.rubric?.criteria?.[0]?.scoring_levels) {
    // If answer key is defined in rubric descriptor or level
    const topLevel = payload.rubric.criteria[0].scoring_levels.find((l) => l.mark > 0);
    correctKeyRaw = topLevel?.required_concepts?.[0] || topLevel?.correct_answer;
  }

  if (correctKeyRaw === undefined || correctKeyRaw === null || (Array.isArray(correctKeyRaw) && correctKeyRaw.length === 0)) {
    throw httpError(400, 'Authoritative answer key is missing for MCQ marking');
  }

  const correctKeys = Array.isArray(correctKeyRaw) ? correctKeyRaw : [correctKeyRaw];
  const canonicalCorrectIds = [];

  for (const rawKey of correctKeys) {
    const resolved = resolveOptionId(rawKey, normalizedOptions);
    if (!resolved) {
      throw httpError(400, `Authoritative answer key '${rawKey}' does not match any valid option ID in the question`);
    }
    if (!canonicalCorrectIds.includes(resolved)) {
      canonicalCorrectIds.push(resolved);
    }
  }

  // 4. Validate Permitted Mark Range
  const rawMaxMarks = payload.max_marks ?? payload.total_possible_marks ?? 1.0;
  const maxMarks = Number(rawMaxMarks);
  if (isNaN(maxMarks) || maxMarks <= 0) {
    throw httpError(400, 'max_marks must be a positive number greater than 0');
  }

  // 5. Extract and Validate Student Submission
  let studentSelectionsRaw = payload.selected_options ?? payload.selected_option_id ?? payload.student_answer;
  let isUnanswered = false;

  if (studentSelectionsRaw === null || studentSelectionsRaw === undefined) {
    isUnanswered = true;
    studentSelectionsRaw = [];
  } else if (Array.isArray(studentSelectionsRaw)) {
    if (studentSelectionsRaw.length === 0) {
      isUnanswered = true;
    }
  } else {
    const str = String(studentSelectionsRaw).trim();
    if (!str) {
      isUnanswered = true;
      studentSelectionsRaw = [];
    } else {
      studentSelectionsRaw = [str];
    }
  }

  const canonicalSelectedIds = [];
  if (!isUnanswered) {
    for (const rawSel of studentSelectionsRaw) {
      const resolved = resolveOptionId(rawSel, normalizedOptions);
      if (!resolved) {
        throw httpError(400, `Selected option '${rawSel}' is not a valid option for question '${qId}'`);
      }
      if (!canonicalSelectedIds.includes(resolved)) {
        canonicalSelectedIds.push(resolved);
      }
    }
  }

  // 6. Answer-Key Comparison & Mark Calculation
  let awardedMark = 0.0;
  let isCorrect = false;

  if (isUnanswered) {
    awardedMark = 0.0;
    isCorrect = false;
  } else {
    // Multi-select vs Single-choice comparison
    const sameCount = canonicalSelectedIds.length === canonicalCorrectIds.length;
    const allMatch = canonicalSelectedIds.every((id) => canonicalCorrectIds.includes(id));
    if (sameCount && allMatch) {
      isCorrect = true;
      awardedMark = maxMarks;
    } else {
      isCorrect = false;
      awardedMark = 0.0;
    }
  }

  // Validate bounds
  awardedMark = Math.max(0.0, Math.min(maxMarks, awardedMark));
  const percentage = Math.round((awardedMark / maxMarks) * 1000) / 10;

  // Labels for reporting
  const selectedLabels = canonicalSelectedIds.map((id) => {
    const opt = normalizedOptions.find((o) => o.option_id === id);
    return opt ? opt.label : id;
  });
  const correctLabels = canonicalCorrectIds.map((id) => {
    const opt = normalizedOptions.find((o) => o.option_id === id);
    return opt ? opt.label : id;
  });

  const levelId = isCorrect ? 'MCQ-CORRECT' : isUnanswered ? 'MCQ-UNANSWERED' : 'MCQ-INCORRECT';
  const levelLabel = isCorrect ? 'Correct' : isUnanswered ? 'Unanswered' : 'Incorrect';
  const descriptor = isCorrect
    ? `Authoritative key matched: Option ${correctLabels.join(', ')}.`
    : isUnanswered
    ? 'No option was selected by the student.'
    : `Incorrect selection. Selected: Option ${selectedLabels.join(', ')}; Correct: Option ${correctLabels.join(', ')}.`;

  const explanation = isCorrect
    ? `Awarded full marks (${awardedMark}/${maxMarks}) for selecting the authoritative correct option (${correctLabels.join(', ')}).`
    : isUnanswered
    ? `Awarded 0/${maxMarks} marks because the question was left unanswered.`
    : `Awarded 0/${maxMarks} marks because selected option (${selectedLabels.join(', ')}) does not match the authoritative answer key (${correctLabels.join(', ')}).`;

  // 7. Assemble Standardized Response Structure
  return {
    question_id: qId,
    answer_type: 'mcq',
    is_correct: isCorrect,
    is_unanswered: isUnanswered,
    total_awarded_marks: awardedMark,
    total_possible_marks: maxMarks,
    percentage: percentage,
    selected_option_ids: canonicalSelectedIds,
    selected_labels: selectedLabels,
    correct_option_ids: canonicalCorrectIds,
    correct_labels: correctLabels,
    options: normalizedOptions,
    marking: {
      question_id: qId,
      total_awarded_marks: awardedMark,
      total_possible_marks: maxMarks,
      percentage: percentage,
      marking_version: 'mcq-deterministic-v1',
      overall_explanation: explanation,
      warnings: [],
      criteria_results: [
        {
          criterion_id: 'C1-MCQ',
          criterion_description: 'Authoritative Multiple-Choice Option Key Match',
          selected_level_id: levelId,
          selected_level_label: levelLabel,
          rubric_descriptor: descriptor,
          awarded_mark: awardedMark,
          max_marks: maxMarks,
          evidence_sentence_ids: isCorrect ? [1] : [],
          supporting_concepts: isCorrect ? canonicalCorrectIds : [],
          explanation: explanation,
          warnings: [],
        },
      ],
    },
    analysis: {
      question_id: qId,
      answer_type: 'mcq',
      sentences: [
        {
          sentence_id: 1,
          text: isUnanswered ? '[Unanswered]' : `Selected Option: ${selectedLabels.join(', ')}`,
        },
      ],
      concept_matches: canonicalCorrectIds.map((id) => ({
        concept: id,
        status: canonicalSelectedIds.includes(id) ? 'demonstrated' : 'missing',
        overlap_score: canonicalSelectedIds.includes(id) ? 1.0 : 0.0,
      })),
      demonstrated_concepts: isCorrect ? canonicalCorrectIds : [],
      missing_concepts: isCorrect ? [] : canonicalCorrectIds,
      preprocessed_answer: isUnanswered ? '' : selectedLabels.join(', '),
      warnings: [],
    },
    feedback: {
      question_id: qId,
      summary: isCorrect
        ? 'Excellent! You selected the correct answer.'
        : isUnanswered
        ? 'This question was left unanswered. Make sure to attempt all questions.'
        : 'Your selected option was incorrect. Review the core concept and explanation.',
      strengths: isCorrect ? [`Correctly identified option ${correctLabels.join(', ')}.`] : [],
      missing_concepts: isCorrect ? [] : [`Authoritative key: Option ${correctLabels.join(', ')}`],
      misconceptions: !isCorrect && !isUnanswered ? [`Selected option ${selectedLabels.join(', ')} instead of ${correctLabels.join(', ')}.`] : [],
      actionable_guidance: isCorrect
        ? 'Consolidate this knowledge by practicing related application-level questions.'
        : 'Review the lecture notes on this topic before re-attempting.',
      rubric_alignment: `Mark: ${awardedMark}/${maxMarks} (${percentage}%) based on authoritative answer key.`,
      warnings: [],
    },
    mindmap: {
      nodes: [
        { id: qId, label: qText.slice(0, 30) + '...', type: 'root' },
        ...canonicalCorrectIds.map((cid) => ({
          id: `opt-${cid}`,
          label: `Key: ${cid}`,
          type: isCorrect ? 'demonstrated' : 'missing',
        })),
      ],
      edges: canonicalCorrectIds.map((cid) => ({
        source: qId,
        target: `opt-${cid}`,
        relationship: 'requires_key',
      })),
    },
  };
}
