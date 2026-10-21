/**
 * C4-owned mock-exam attempts (practice-bank sourced).
 * Persists only in C4 collections. Snapshots questions + keys at create time.
 * C2 past-paper source is checked via adapter and reported honestly when unavailable.
 */

import { randomUUID } from 'crypto';
import { PRACTICE_QUESTIONS } from '../../c1/data/practiceQuestions.js';
import { TOPICS } from '../../c1/data/content/index.js';
import { isSupportedPracticeTopic } from '../data/supportedTopics.js';
import { fetchC2ExamPaper } from './c2ExamAdapter.js';
import {
  assessSupervisedModelInputs,
  estimatePracticeQuizFromBlueprint,
  PRACTICE_QUIZ_SCORE_TARGET,
} from './liveModelAdapter.js';
import { predictLiveExamEstimates } from './liveInference.js';
import { readLearnerSnapshot, snapshotMeta } from './c1Reader.js';
import { attachQuizOutcome } from './policyDecisionLog.js';

export const EXAMS_COLLECTION = 'c4_exam_attempts';
export const EXAM_FEEDBACK_NOTE =
  'Scores are from C4 practice-bank mock quizzes (objective MCQ). Not a university module exam.';

function httpError(status, message, code) {
  const err = new Error(message);
  err.status = status;
  if (code) err.code = code;
  return err;
}

function assertOwner(doc, studentId) {
  if (!doc) throw httpError(404, 'Exam attempt not found');
  if (doc.student_id !== studentId) throw httpError(403, 'You do not have access to this exam attempt');
}

/** Public question — never includes correct indexes or why until review after submit. */
function publicQuestion(q) {
  return {
    questionId: q.question_id,
    topic: q.topic,
    text: q.text,
    options: q.options,
    multi: Array.isArray(q.correct) && q.correct.length > 1,
  };
}

function pickQuestions(topics, count) {
  const byTopic = [];
  for (const topic of topics) {
    if (!isSupportedPracticeTopic(topic)) continue;
    const bank = PRACTICE_QUESTIONS[topic] || [];
    const rows = [];
    bank.forEach((q, i) => {
      if (!q || !Array.isArray(q.options) || !Array.isArray(q.correct)) return;
      rows.push({
        question_id: `${topic}::${i}`,
        topic,
        text: q.text,
        options: [...q.options],
        correct: [...q.correct],
        why: q.why || null,
        tip: q.tip || null,
        difficulty: null,
      });
    });
    rows.sort((a, b) => (a.question_id < b.question_id ? -1 : 1));
    if (rows.length) byTopic.push(rows);
  }
  const selected = [];
  let round = 0;
  while (selected.length < count && byTopic.some((rows) => rows.length > round)) {
    for (const rows of byTopic) {
      if (selected.length >= count) break;
      if (rows[round]) selected.push(rows[round]);
    }
    round += 1;
  }
  return {
    questions: selected,
    blueprint: {
      strategy: 'weak_topic_round_robin_v1',
      topic_order: topics,
      question_count: selected.length,
      difficulty_adaptation: 'unavailable',
      difficulty_note:
        'Practice-bank items have no numeric difficulty metadata. Coverage adapts by weak-topic order and round-robin balance only.',
    },
  };
}

export async function getExamSources() {
  const c2 = await fetchC2ExamPaper({});
  return {
    sources: [
      {
        id: 'c1_practice_bank',
        available: true,
        label: 'C4 practice-based mock quiz',
        description:
          'Uses C1 practice-bank MCQs snapshotted into a C4 attempt. Not a C2 past paper.',
      },
      {
        id: 'c2_past_paper',
        available: c2.available,
        label: 'C2 past-paper exam',
        description: c2.reason,
        required_dependency: c2.required_dependency,
      },
    ],
  };
}

/**
 * Create a C4 mock-exam attempt from practice-bank content.
 */
export async function createExamAttempt(db, studentId, body, aiUrl) {
  const source = body?.source || 'c1_practice_bank';
  if (source === 'c2_past_paper') {
    const c2 = await fetchC2ExamPaper(body || {});
    throw httpError(503, c2.reason, 'c2_exam_unavailable');
  }
  if (source !== 'c1_practice_bank') {
    throw httpError(400, 'source must be c1_practice_bank or c2_past_paper');
  }

  const snap = await readLearnerSnapshot(db, studentId, aiUrl);
  const sem = snap.twin.semester;
  const twinKeys = new Set(Object.keys(snap.twin.mastery || {}));

  const requested = Array.isArray(body?.topics) ? body.topics.map(String) : null;
  let topics = requested || [];
  topics = topics.filter((t) => {
    if (!isSupportedPracticeTopic(t)) return false;
    if (!twinKeys.has(t)) return false;
    if (sem && TOPICS[t]?.semester && TOPICS[t].semester !== sem) return false;
    return true;
  });
  if (requested && requested.length && !topics.length) {
    throw httpError(
      400,
      'None of the requested topics are eligible for this student (semester, twin, or practice bank).',
      'topics_not_eligible'
    );
  }
  if (!topics.length) {
    // Default: student's semester topics that have practice + twin entry
    topics = Object.keys(TOPICS).filter(
      (t) =>
        isSupportedPracticeTopic(t) &&
        twinKeys.has(t) &&
        (!sem || TOPICS[t].semester === sem)
    );
  }
  if (!topics.length) {
    throw httpError(
      409,
      'No eligible practice topics for a mock quiz. Complete the C1 diagnostic first.',
      'no_eligible_topics'
    );
  }

  const mastery = snap.twin.mastery || {};
  topics.sort((a, b) => {
    const sa = Number(mastery[a]?.score);
    const sb = Number(mastery[b]?.score);
    const fa = Number.isFinite(sa) ? sa : 101;
    const fb = Number.isFinite(sb) ? sb : 101;
    if (fa !== fb) return fa - fb;
    return a < b ? -1 : a > b ? 1 : 0;
  });

  let count = body?.questionCount != null ? Number(body.questionCount) : 10;
  if (!Number.isFinite(count) || count < 3 || count > 40) {
    throw httpError(400, 'questionCount must be between 3 and 40');
  }

  const timeLimitSec = body?.timeLimitSec != null ? Number(body.timeLimitSec) : 20 * 60;
  if (!Number.isFinite(timeLimitSec) || timeLimitSec < 60 || timeLimitSec > 3 * 60 * 60) {
    throw httpError(400, 'timeLimitSec must be between 60 and 10800');
  }

  const clientRequestId =
    typeof body?.clientRequestId === 'string' && body.clientRequestId.trim()
      ? body.clientRequestId.trim()
      : null;
  if (clientRequestId) {
    const existing = await db.collection(EXAMS_COLLECTION).findOne({
      student_id: studentId,
      client_request_id: clientRequestId,
    });
    if (existing) return publicAttempt(existing, { includeQuestions: true });
  }

  const picked = pickQuestions(topics, count);
  const selected = picked.questions;
  if (selected.length < 3) {
    throw httpError(409, 'Not enough practice questions available for the selected topics');
  }

  const now = new Date();
  const cutoffIso = now.toISOString();
  // Pre-exam features from practice history only (timestamp <= attempt create).
  const [events, practiceSessions] = await Promise.all([
    db.collection('learning_events').find({ student_id: studentId }).toArray(),
    db.collection('practice_sessions').find({ student_id: studentId }).toArray(),
  ]);
  const blueprintEstimate = estimatePracticeQuizFromBlueprint({
    events,
    practiceSessions,
    cutoffIso,
    questionSnapshot: selected,
    scoreTarget: PRACTICE_QUIZ_SCORE_TARGET,
  });
  const liveEstimate = await predictLiveExamEstimates({
    studentId,
    events,
    practiceSessions,
    cutoffIso,
  });
  const responseBlocked = assessSupervisedModelInputs({ mode: 'response' });

  const doc = {
    attempt_id: randomUUID(),
    student_id: studentId,
    source: 'c1_practice_bank',
    status: 'in_progress',
    created_at: now,
    updated_at: now,
    started_at: now,
    time_limit_sec: timeLimitSec,
    expires_at: new Date(now.getTime() + timeLimitSec * 1000),
    topics,
    semester: sem || null,
    client_request_id: clientRequestId,
    question_snapshot: selected,
    exam_blueprint: picked.blueprint,
    answers: {}, // question_id -> number[] selected indexes
    submitted_at: null,
    result: null,
    prediction_outcome: null,
    pre_exam_model: {
      frozen_at: cutoffIso,
      prediction_cutoff_utc: cutoffIso,
      features_from_exam_answers: false,
      question_count: selected.length,
      practice_quiz_score_target: PRACTICE_QUIZ_SCORE_TARGET,
      assessment: {
        // Primary: estimate for THIS practice-bank quiz blueprint
        practice_quiz: blueprintEstimate.usable
          ? {
              usable: true,
              code: blueprintEstimate.code,
              method: blueprintEstimate.method,
              trained_model: false,
              predicted_score: blueprintEstimate.predicted_score,
              predicted_pass: blueprintEstimate.predicted_pass,
              practice_quiz_score_target: blueprintEstimate.practice_quiz_score_target,
              practice_quiz_score_target_note: blueprintEstimate.practice_quiz_score_target_note,
              question_count: blueprintEstimate.question_count,
              blueprint_topic_counts: blueprintEstimate.blueprint_topic_counts,
              cold_start: blueprintEstimate.cold_start,
              questions_using_default_prior: blueprintEstimate.questions_using_default_prior,
              default_prior_accuracy: blueprintEstimate.default_prior_accuracy,
              protocol: blueprintEstimate.protocol,
              experimental: false,
              simulation_trained: false,
              supported_meaning:
                'Heuristic (not a trained model): mean over this quiz’s snapshotted questions of ' +
                'each question’s topic prior accuracy from practice history ≤ cutoff. ' +
                'Topics with no prior attempts use an explicit 0.5 default. Product target ' +
                `${PRACTICE_QUIZ_SCORE_TARGET} is not an institutional pass rule.`,
              provenance: blueprintEstimate.provenance,
              note: blueprintEstimate.note,
            }
          : {
              usable: false,
              code: blueprintEstimate.code,
              reason: blueprintEstimate.reason,
            },
        // Secondary: simulation-trained readiness (different target — keep experimental label)
        exam: liveEstimate.ok
          ? {
              usable: true,
              predicted_score: liveEstimate.exam_score?.predicted_score,
              pass_probability: liveEstimate.pass?.pass_probability,
              predicted_pass: liveEstimate.pass?.predicted_pass,
              pass_label_threshold: liveEstimate.pass?.pass_label_threshold,
              classification_prob_threshold:
                liveEstimate.pass?.classification_prob_threshold,
              cold_start: liveEstimate.cold_start,
              protocol: liveEstimate.protocol,
              catalogue_hash: liveEstimate.catalogue_hash,
              provenance: liveEstimate.provenance,
              experimental: true,
              simulation_trained: true,
              supported_meaning:
                'Experimental estimate of synthetic-style overall practice readiness ' +
                '(fraction-correct scale from se-supervised-sim-v1 training). ' +
                'NOT the primary forecast for this quiz — use practice_quiz estimate above.',
              note: liveEstimate.note,
            }
          : {
              usable: false,
              code: liveEstimate.code,
              reason: liveEstimate.reason,
              experimental: true,
              simulation_trained: true,
            },
        response: responseBlocked,
      },
      note:
        'Primary frozen estimate = c4-practice-quiz-estimate-v1 heuristic formula (not trained). ' +
        'Secondary se-supervised-sim-v1 readiness remains experimental / different target. ' +
        'Neither uses current-attempt answers. Practice-quiz target 0.6 is a product rule, ' +
        'not institutional. Synthetic 0.55 pass label is training-only.',
    },
    source_snapshot: snapshotMeta(snap),
    content_note: EXAM_FEEDBACK_NOTE,
  };
  await db.collection(EXAMS_COLLECTION).insertOne(doc);
  return publicAttempt(doc, { includeQuestions: true });
}

/** Drop answer keys from list/in-progress payloads. Review is returned only after submit. */
function publicResult(result, includeReview) {
  if (!result) return null;
  if (includeReview) return result;
  const { review, ...rest } = result;
  return rest;
}

function publicAttempt(doc, { includeQuestions = false, includeReview = false } = {}) {
  const expired =
    doc.status === 'in_progress' && doc.expires_at && new Date() > new Date(doc.expires_at);
  const out = {
    attemptId: doc.attempt_id,
    studentId: doc.student_id,
    source: doc.source,
    status: expired && doc.status === 'in_progress' ? 'expired' : doc.status,
    createdAt: doc.created_at,
    startedAt: doc.started_at,
    timeLimitSec: doc.time_limit_sec,
    expiresAt: doc.expires_at,
    topics: doc.topics,
    examBlueprint: doc.exam_blueprint || null,
    questionCount: (doc.question_snapshot || []).length,
    answeredCount: Object.keys(doc.answers || {}).length,
    contentNote: doc.content_note,
    preExamModel: doc.pre_exam_model,
    result: publicResult(doc.result, includeReview),
    predictionOutcome: doc.prediction_outcome || null,
    submittedAt: doc.submitted_at,
  };
  if (includeQuestions) {
    out.questions = (doc.question_snapshot || []).map(publicQuestion);
    out.answers = doc.answers || {};
  }
  if (includeReview && doc.result) {
    out.review = doc.result.review;
  }
  return out;
}

function arraysEqualAsSets(a, b) {
  if (!Array.isArray(a) || !Array.isArray(b) || a.length !== b.length) return false;
  const sa = [...a].sort();
  const sb = [...b].sort();
  return sa.every((v, i) => v === sb[i]);
}

function isTimedOut(doc, now = new Date()) {
  return Boolean(doc.expires_at && now > new Date(doc.expires_at));
}

/** Grade saved answers in-place. Does not mutate pre_exam_model. */
function applyGrade(doc, { timedOut = false } = {}) {
  const review = [];
  let correctCount = 0;
  const byTopic = {};
  for (const q of doc.question_snapshot || []) {
    const selected = doc.answers[q.question_id] || [];
    const ok = arraysEqualAsSets(selected, q.correct);
    if (ok) correctCount += 1;
    if (!byTopic[q.topic]) byTopic[q.topic] = { topic: q.topic, correct: 0, total: 0 };
    byTopic[q.topic].total += 1;
    if (ok) byTopic[q.topic].correct += 1;
    review.push({
      questionId: q.question_id,
      topic: q.topic,
      text: q.text,
      options: q.options,
      selected,
      correctIndexes: q.correct,
      isCorrect: ok,
      explanation: q.why,
      assessment: 'objective_mcq',
    });
  }
  const total = (doc.question_snapshot || []).length;
  const scoreFraction = total ? correctCount / total : 0;
  const now = new Date();
  doc.status = 'submitted';
  doc.submitted_at = now;
  doc.updated_at = now;
  doc.timed_out_on_submit = !!timedOut;
  doc.result = {
    scoreFraction,
    scorePercent: Math.round(scoreFraction * 1000) / 10,
    correctCount,
    total,
    topicBreakdown: Object.values(byTopic).map((t) => ({
      ...t,
      accuracy: t.total ? t.correct / t.total : 0,
    })),
    review,
    note: EXAM_FEEDBACK_NOTE,
    grading: 'server_side_objective_mcq',
    finalizedReason: timedOut ? 'time_limit_exceeded' : 'student_submit',
  };
  attachPredictionOutcome(doc);
  return doc;
}

/** Pair frozen pre-exam estimates with observed score (no feature leakage). */
function attachPredictionOutcome(doc) {
  const pq = doc.pre_exam_model?.assessment?.practice_quiz;
  const sim = doc.pre_exam_model?.assessment?.exam;
  doc.prediction_outcome = {
    frozen_at: doc.pre_exam_model?.frozen_at || null,
    prediction_cutoff_utc: doc.pre_exam_model?.prediction_cutoff_utc || null,
    observed_score_fraction: doc.result?.scoreFraction ?? null,
    observed_score_percent: doc.result?.scorePercent ?? null,
    practice_quiz_prediction: pq?.usable
      ? {
          predicted_score: pq.predicted_score,
          predicted_pass: pq.predicted_pass,
          practice_quiz_score_target: pq.practice_quiz_score_target,
          protocol: pq.protocol,
        }
      : { usable: false, code: pq?.code || 'unavailable' },
    experimental_readiness_prediction: sim?.usable
      ? {
          predicted_score: sim.predicted_score,
          pass_probability: sim.pass_probability,
          protocol: sim.protocol,
          note: 'Different target from this quiz; experimental only.',
        }
      : { usable: false, code: sim?.code || 'unavailable' },
    features_from_exam_answers: false,
  };
}

function mergeAnswers(doc, answers) {
  if (!answers || typeof answers !== 'object' || Array.isArray(answers)) {
    throw httpError(400, 'answers must be an object keyed by questionId');
  }
  const validIds = new Set((doc.question_snapshot || []).map((q) => q.question_id));
  for (const [qid, sel] of Object.entries(answers)) {
    if (!validIds.has(qid)) throw httpError(400, `Unknown questionId: ${qid}`);
    if (!Array.isArray(sel) || sel.some((x) => !Number.isInteger(x) || x < 0)) {
      throw httpError(400, `answers[${qid}] must be an array of non-negative integers`);
    }
    doc.answers[qid] = sel;
  }
}

/** If still in_progress past expires_at, grade saved answers and persist. */
async function finalizeIfExpired(db, doc) {
  if (doc.status !== 'in_progress' || !isTimedOut(doc)) return doc;
  applyGrade(doc, { timedOut: true });
  await db.collection(EXAMS_COLLECTION).replaceOne({ attempt_id: doc.attempt_id }, doc);
  return doc;
}

export async function getAttempt(db, studentId, attemptId) {
  let doc = await db.collection(EXAMS_COLLECTION).findOne({ attempt_id: attemptId });
  assertOwner(doc, studentId);
  doc = await finalizeIfExpired(db, doc);
  const includeReview = doc.status === 'submitted';
  return publicAttempt(doc, { includeQuestions: true, includeReview });
}

export async function listAttempts(db, studentId) {
  const rows = await db.collection(EXAMS_COLLECTION).find({ student_id: studentId }).toArray();
  for (const row of rows) {
    if (row.status === 'in_progress' && isTimedOut(row)) {
      await finalizeIfExpired(db, row);
    }
  }
  const fresh = await db.collection(EXAMS_COLLECTION).find({ student_id: studentId }).toArray();
  fresh.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  return { studentId, attempts: fresh.map((d) => publicAttempt(d)) };
}

export async function saveAnswers(db, studentId, attemptId, body) {
  let doc = await db.collection(EXAMS_COLLECTION).findOne({ attempt_id: attemptId });
  assertOwner(doc, studentId);

  if (doc.status === 'submitted' && doc.result) {
    return {
      ...publicAttempt(doc, { includeQuestions: true, includeReview: true }),
      duplicate: true,
      note: 'Attempt already submitted; answers not changed.',
    };
  }
  if (doc.status !== 'in_progress') throw httpError(409, 'Attempt is not in progress');

  if (isTimedOut(doc)) {
    // Accept last payload then finalize with grade (timeout finalization).
    if (body?.answers) mergeAnswers(doc, body.answers);
    applyGrade(doc, { timedOut: true });
    await db.collection(EXAMS_COLLECTION).replaceOne({ attempt_id: attemptId }, doc);
    return {
      ...publicAttempt(doc, { includeQuestions: true, includeReview: true }),
      timedOut: true,
      code: 'exam_timeout',
    };
  }

  mergeAnswers(doc, body?.answers);
  doc.updated_at = new Date();
  await db.collection(EXAMS_COLLECTION).replaceOne({ attempt_id: attemptId }, doc);
  return publicAttempt(doc, { includeQuestions: true });
}

export async function submitAttempt(db, studentId, attemptId, body = {}) {
  let doc = await db.collection(EXAMS_COLLECTION).findOne({ attempt_id: attemptId });
  assertOwner(doc, studentId);

  if (doc.status === 'submitted' && doc.result) {
    return {
      ...publicAttempt(doc, { includeQuestions: true, includeReview: true }),
      duplicate: true,
    };
  }
  if (doc.status !== 'in_progress') throw httpError(409, 'Attempt cannot be submitted');

  const timedOut = isTimedOut(doc);
  if (body?.answers) mergeAnswers(doc, body.answers);

  applyGrade(doc, { timedOut });
  // pre_exam_model untouched; prediction_outcome attached inside applyGrade
  for (const topic of doc.topics || []) {
    const attached = await attachQuizOutcome(db, {
      studentId,
      topic,
      attemptId: doc.attempt_id,
      scoreFraction: doc.result?.scoreFraction,
    });
    if (attached) break;
  }
  await db.collection(EXAMS_COLLECTION).replaceOne({ attempt_id: attemptId }, doc);
  return {
    ...publicAttempt(doc, { includeQuestions: true, includeReview: true }),
    duplicate: false,
    timedOut,
  };
}

/** Weak topics from latest submitted attempt for planning hints (read-only). */
export async function latestWeakTopics(db, studentId) {
  const rows = await db.collection(EXAMS_COLLECTION).find({ student_id: studentId }).toArray();
  const submitted = rows
    .filter((r) => r.status === 'submitted' && r.result)
    .sort((a, b) => new Date(b.submitted_at) - new Date(a.submitted_at));
  if (!submitted.length) return { topics: [], attemptId: null };
  const latest = submitted[0];
  const weak = (latest.result.topicBreakdown || [])
    .filter((t) => t.accuracy < 0.6)
    .map((t) => t.topic);
  return { topics: weak, attemptId: latest.attempt_id, scorePercent: latest.result.scorePercent };
}

/** Paired frozen estimates vs observed scores already stored on attempts. No fabricated rows. */
export async function evaluateStoredPredictions(db, studentId) {
  const rows = await db.collection(EXAMS_COLLECTION).find({ student_id: studentId }).toArray();
  const pairs = rows.filter((r) => r.status === 'submitted' && r.prediction_outcome && r.result);
  const errors = [];
  for (const r of pairs) {
    const pred = r.prediction_outcome.practice_quiz_prediction?.predicted_score;
    const obs = r.prediction_outcome.observed_score_fraction;
    if (Number.isFinite(pred) && Number.isFinite(obs)) errors.push(Math.abs(pred - obs));
  }
  const mae = errors.length ? errors.reduce((s, e) => s + e, 0) / errors.length : null;
  return {
    studentId,
    pairCount: pairs.length,
    heuristicMae: mae,
    passProbabilityForThisQuiz: {
      available: false,
      reason:
        'Insufficient evidence: no model is trained to output P(pass) for this practice-bank quiz. ' +
        'The 0.6 rule is a product decision threshold, not a probability. ' +
        'Simulation pass probability predicts a different synthetic target.',
    },
    note:
      pairs.length
        ? 'MAE is over stored heuristic predicted_score vs observed fraction on this student only. Not a validated accuracy claim.'
        : 'No submitted attempts with a frozen prediction/outcome pair yet.',
  };
}
