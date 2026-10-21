import test from 'node:test';
import assert from 'node:assert/strict';
import {
  assessPathModelInputs,
  assessSupervisedModelInputs,
  normalizeMasteryEntry,
  deriveAvailability,
  buildExamFeaturesFromEvents,
  countPracticeAttemptSteps,
  estimatePracticeQuizFromBlueprint,
  LIVE_PRIOR_STRENGTH_CONSTANT,
  PRACTICE_QUIZ_SCORE_TARGET,
} from '../services/liveModelAdapter.js';
import { SIM_OBS_DIM, SIM_ORDERED_TOPICS } from '../data/simCatalogue.generated.js';

test('missing mastery is not observed zero', () => {
  const missing = normalizeMasteryEntry(null);
  assert.equal(missing.available, 0);
  assert.equal(missing.value, null);
  const zero = normalizeMasteryEntry({ score: 0 });
  assert.equal(zero.available, 1);
  assert.equal(zero.value, 0);
  const mid = normalizeMasteryEntry({ score: 50 });
  assert.equal(mid.value, 0.5);
});

test('availability requires semester ∩ bank ∩ twin', () => {
  const bad = deriveAvailability({ semester: 'Y2S1', twinMastery: { [SIM_ORDERED_TOPICS[0]]: { score: 40 } } });
  assert.equal(bad.ok, false);
  const ok = deriveAvailability({
    semester: 'Y3S1',
    twinMastery: { [SIM_ORDERED_TOPICS[0]]: { score: 40 } },
  });
  assert.equal(ok.ok, true);
  assert.equal(ok.available[0], 1);
});

test('path model builds usable live observation with protocol prior + episode steps', () => {
  const twin = {};
  for (const t of SIM_ORDERED_TOPICS) {
    if (t.startsWith('ds_') || t.startsWith('sa_') || t.startsWith('qm_')) continue;
    twin[t] = { score: 40 };
  }
  const out = assessPathModelInputs({
    semester: 'Y3S1',
    twinMastery: twin,
    elapsedEnvSteps: 2,
    priorStrength: LIVE_PRIOR_STRENGTH_CONSTANT,
  });
  assert.equal(out.usable, true);
  assert.equal(out.observation.length, SIM_OBS_DIM);
  assert.equal(out.action_mask.length, SIM_ORDERED_TOPICS.length);
  assert.ok(out.action_mask.some(Boolean));
  assert.equal(out.provenance.prior_strength.value, LIVE_PRIOR_STRENGTH_CONSTANT);
  assert.match(out.provenance.prior_strength.provenance, /protocol_constant/);
  assert.equal(out.provenance.elapsed_env_step_frac.steps, 2);
});

test('response supervised inputs remain blocked without inventing difficulty', () => {
  const out = assessSupervisedModelInputs({ mode: 'response' });
  assert.equal(out.usable, false);
  assert.equal(out.field_status.difficulty, 'unavailable');
  assert.equal(out.real_student_validation, false);
});

test('exam features usable from events with cutoff; no future leakage', () => {
  const topic = SIM_ORDERED_TOPICS[0];
  const cutoff = '2026-10-15T12:00:00.000Z';
  const events = [
    {
      type: 'quiz_answer',
      topic,
      correct: true,
      answered: true,
      timestamp: '2026-10-15T11:00:00.000Z',
      session_id: 's1',
      question_id: 'q1',
    },
    {
      type: 'quiz_answer',
      topic,
      correct: false,
      answered: true,
      timestamp: '2026-10-15T13:00:00.000Z', // after cutoff — must be ignored
      session_id: 's1',
      question_id: 'q2',
    },
  ];
  const out = buildExamFeaturesFromEvents(events, { cutoffIso: cutoff, studentId: 'IT1' });
  assert.equal(out.usable, true);
  assert.equal(out.features[`topic_attempts_${topic}`], 1);
  assert.equal(out.features[`topic_accuracy_${topic}`], 1);
  assert.equal(out.features.global_attempts, 1);
  assert.equal(out.features_from_exam_answers, undefined);
});

test('countPracticeAttemptSteps dedupes, skips abandoned, ignores Mark done timestamps', () => {
  const since = '2026-10-15T08:00:00.000Z';
  const events = [
    {
      type: 'quiz_answer',
      answered: true,
      timestamp: '2026-10-15T09:00:00.000Z',
      session_id: 's1',
      question_id: 'q1',
    },
    {
      type: 'quiz_answer',
      answered: true,
      timestamp: '2026-10-15T09:01:00.000Z',
      session_id: 's1',
      question_id: 'q1', // retry / duplicate
    },
    {
      type: 'quiz_answer',
      answered: true,
      timestamp: '2026-10-15T09:02:00.000Z',
      session_id: 's1',
      question_id: 'q2',
    },
    {
      type: 'quiz_answer',
      answered: true,
      timestamp: '2026-10-15T07:00:00.000Z', // before episode
      session_id: 's0',
      question_id: 'q0',
    },
    {
      type: 'quiz_answer',
      answered: true,
      timestamp: '2026-10-15T09:03:00.000Z',
      session_id: 'abandoned',
      question_id: 'q9',
    },
    {
      type: 'self_report', // Mark done must never count
      timestamp: '2026-10-15T09:04:00.000Z',
      session_id: 's1',
    },
  ];
  const steps = countPracticeAttemptSteps({
    events,
    practiceSessions: [
      { session_id: 's1', abandoned: false },
      { session_id: 'abandoned', abandoned: true },
    ],
    sinceIso: since,
  });
  assert.equal(steps, 2);
});

test('estimatePracticeQuizFromBlueprint uses topic priors for THIS quiz only', () => {
  const topic = SIM_ORDERED_TOPICS[0];
  const cutoff = '2026-10-15T12:00:00.000Z';
  const events = [
    {
      type: 'quiz_answer',
      topic,
      correct: true,
      answered: true,
      timestamp: '2026-10-15T11:00:00.000Z',
      session_id: 's1',
      question_id: 'q1',
    },
    {
      type: 'quiz_answer',
      topic,
      correct: false,
      answered: true,
      timestamp: '2026-10-15T11:05:00.000Z',
      session_id: 's1',
      question_id: 'q2',
    },
  ];
  const out = estimatePracticeQuizFromBlueprint({
    events,
    cutoffIso: cutoff,
    questionSnapshot: [
      { topic, question_id: 'snap1' },
      { topic, question_id: 'snap2' },
      { topic: 'unknown_topic_xyz', question_id: 'snap3' },
    ],
  });
  assert.equal(out.usable, true);
  assert.equal(out.protocol, 'c4-practice-quiz-estimate-v1');
  assert.equal(out.trained_model, false);
  assert.equal(JSON.stringify(out.provenance).includes('Simulation-trained model'), false);
  assert.match(out.provenance.not_the_simulation_model, /c4-practice-quiz-estimate-v1/);
  assert.equal(out.method, 'heuristic_mean_topic_prior_accuracy');
  assert.equal(out.question_count, 3);
  assert.equal(out.practice_quiz_score_target, PRACTICE_QUIZ_SCORE_TARGET);
  // topic prior accuracy = 0.5; unknown topic uses 0.5 → mean 0.5
  assert.equal(out.predicted_score, 0.5);
  assert.equal(out.predicted_pass, false); // 0.5 < 0.6
  assert.equal(out.simulation_trained, false);
  assert.equal(out.cold_start, false);
  assert.ok(out.questions_using_default_prior >= 1);
});

test('exam features skip abandoned sessions and duplicate session+question rows', () => {
  const topic = SIM_ORDERED_TOPICS[0];
  const cutoff = '2026-10-15T12:00:00.000Z';
  const events = [
    {
      type: 'quiz_answer',
      topic,
      correct: true,
      answered: true,
      timestamp: '2026-10-15T10:00:00.000Z',
      session_id: 'good',
      question_id: 'q1',
    },
    {
      type: 'quiz_answer',
      topic,
      correct: false,
      answered: true,
      timestamp: '2026-10-15T10:05:00.000Z',
      session_id: 'good',
      question_id: 'q1', // duplicate
    },
    {
      type: 'quiz_answer',
      topic,
      correct: true,
      answered: true,
      timestamp: '2026-10-15T10:10:00.000Z',
      session_id: 'bad',
      question_id: 'q9',
    },
  ];
  const out = buildExamFeaturesFromEvents(events, {
    cutoffIso: cutoff,
    studentId: 'IT1',
    practiceSessions: [
      { session_id: 'good', abandoned: false },
      { session_id: 'bad', abandoned: true },
    ],
  });
  assert.equal(out.usable, true);
  assert.equal(out.features.global_attempts, 1);
  assert.equal(out.provenance.skipped_abandoned_events, 1);
  assert.equal(out.provenance.skipped_duplicate_events, 1);
});
