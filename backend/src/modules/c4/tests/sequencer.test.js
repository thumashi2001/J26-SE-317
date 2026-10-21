import test from 'node:test';
import assert from 'node:assert/strict';
import { PRACTICE_QUESTIONS } from '../../c1/data/practiceQuestions.js';
import { SUPPORTED_PRACTICE_TOPICS } from '../data/supportedTopics.js';
import { buildActivitySequence, STRATEGY_ID } from '../services/sequencer.js';

/** Current C1 practice keys used as realistic twin coverage in these unit tests. */
const T = {
  heuristics: 'ux_testing_heuristics',
  indexing: 'file_organization_indexing',
  relational: 'object_relational_db',
  risk: 'project_risk_management',
};

test('SUPPORTED_PRACTICE_TOPICS mirrors C1 PRACTICE_QUESTIONS keys', () => {
  assert.deepEqual([...SUPPORTED_PRACTICE_TOPICS], Object.keys(PRACTICE_QUESTIONS));
  assert.ok(SUPPORTED_PRACTICE_TOPICS.includes(T.indexing));
  assert.ok(!SUPPORTED_PRACTICE_TOPICS.includes('indexing'));
});

test('ranks by ascending mastery with topic-id tie-break', () => {
  const twinMastery = {
    [T.indexing]: { score: 40 },
    [T.relational]: { score: 40 },
    [T.heuristics]: { score: 20 },
    [T.risk]: { score: 90 },
  };
  const { activities, strategy } = buildActivitySequence({
    twinMastery,
    insightsTopics: null,
    horizon: null,
  });
  assert.equal(strategy, STRATEGY_ID);
  const pending = activities.filter((a) => a.status === 'pending' && a.kind === 'c1_practice');
  // score 20 first; then tied 40s sorted by topic id; then 90
  assert.deepEqual(pending.map((a) => a.topic), [
    T.heuristics,
    T.indexing,
    T.relational,
    T.risk,
  ]);
  assert.equal(pending[0].launch_path, `/c1/practice/${T.heuristics}`);
  assert.match(pending[0].recommendation_reason, /lowest/i);
});

test('prefers estimatedNow when finite; skips missing twin topics', () => {
  const twinMastery = {
    [T.indexing]: { score: 50 },
    [T.relational]: { score: 10 },
  };
  const insightsTopics = {
    [T.indexing]: { estimatedNow: 5, storedScore: 50 },
    [T.relational]: { estimatedNow: null, storedScore: 10 },
  };
  const { activities, unavailable } = buildActivitySequence({
    twinMastery,
    insightsTopics,
    horizon: 2,
  });
  assert.equal(activities[0].topic, T.indexing);
  assert.equal(activities[0].score_source, 'estimatedNow');
  assert.ok(unavailable.some((u) => u.topic === T.heuristics));
});

test('preserves completed activities and does not re-queue them as pending', () => {
  const twinMastery = {
    [T.indexing]: { score: 10 },
    [T.relational]: { score: 20 },
  };
  const { activities } = buildActivitySequence({
    twinMastery,
    insightsTopics: null,
    preserveCompleted: [
      {
        activity_id: `c1_practice:${T.indexing}`,
        topic: T.indexing,
        completion_kind: 'self_reported',
        completed_at: '2026-01-01T00:00:00.000Z',
        recommendation_reason: 'earlier',
      },
    ],
  });
  assert.equal(activities[0].status, 'self_reported_complete');
  assert.equal(activities[0].activity_id, `c1_practice:${T.indexing}`);
  assert.equal(
    activities.filter((a) => a.activity_id === `c1_practice:${T.indexing}` && a.status === 'pending')
      .length,
    0
  );
  assert.equal(activities.find((a) => a.activity_id === `c1_practice:${T.relational}`).status, 'pending');
});

test('does not invent ASSISTments skill IDs', () => {
  const { activities, unavailable } = buildActivitySequence({
    twinMastery: { '311': { score: 1 }, [T.indexing]: { score: 2 } },
    insightsTopics: null,
  });
  assert.ok(activities.every((a) => a.topic !== '311'));
  assert.ok(activities.some((a) => a.topic === T.indexing));
  assert.ok(unavailable.some((u) => u.topic === '311'));
});

test('pinFirstTopic moves eligible topic to next actionable pending activity', () => {
  const twinMastery = {
    [T.indexing]: { score: 40 },
    [T.relational]: { score: 40 },
    [T.heuristics]: { score: 20 },
    [T.risk]: { score: 90 },
  };
  const { activities, strategy, next_activity_topic, next_activity_source } =
    buildActivitySequence({
      twinMastery,
      insightsTopics: null,
      horizon: null,
      pinFirstTopic: T.risk,
      pinReason: 'Pinned by se-path-sim-v1 for test',
    });
  const pending = activities.filter((a) => a.status === 'pending' && a.kind === 'c1_practice');
  assert.equal(pending[0].topic, T.risk);
  assert.equal(pending[0].next_activity, true);
  assert.equal(pending[0].next_activity_source, 'se-path-sim-v1');
  assert.match(pending[0].recommendation_reason, /se-path-sim-v1|Pinned/);
  assert.equal(next_activity_topic, T.risk);
  assert.equal(next_activity_source, 'se-path-sim-v1');
  assert.match(strategy, /se-path-sim-v1_next/);
});

test('pinNextActivity places an eligible revision or quiz ahead of the heuristic order', () => {
  const twinMastery = {
    [T.indexing]: { score: 10 },
    [T.relational]: { score: 20 },
    [T.heuristics]: { score: 30 },
    [T.risk]: { score: 90 },
  };
  const revision = buildActivitySequence({
    twinMastery,
    insightsTopics: null,
    pinNextActivity: { topic: T.risk, kind: 'revision', reason: 'multi revision' },
  });
  const pending = revision.activities.filter((a) => a.status === 'pending');
  assert.equal(pending[0].kind, 'c1_revision');
  assert.equal(pending[0].topic, T.risk);
  assert.equal(pending[0].next_activity, true);
  assert.match(pending[0].launch_path, /^\/c1\/topic\//);
  assert.match(revision.strategy, /se-path-multi-v1_next/);

  const quiz = buildActivitySequence({
    twinMastery,
    insightsTopics: null,
    pinNextActivity: { topic: T.risk, kind: 'quiz', reason: 'multi quiz' },
  });
  const quizPending = quiz.activities.filter((a) => a.status === 'pending');
  assert.equal(quizPending[0].kind, 'c4_quiz');
  assert.match(quizPending[0].launch_path, /tab=exams/);

  const v2 = buildActivitySequence({
    twinMastery,
    insightsTopics: null,
    pinNextActivity: {
      topic: T.risk,
      kind: 'practice',
      reason: 'v2 practice',
      source: 'se-path-multi-v2',
    },
  });
  const v2Pending = v2.activities.filter((a) => a.status === 'pending');
  assert.equal(v2Pending[0].kind, 'c1_practice');
  assert.equal(v2Pending[0].next_activity_source, 'se-path-multi-v2');
  assert.equal(v2Pending[0].recommendation_source, 'se-path-multi-v2');
  assert.match(v2Pending[0].launch_path, /^\/c1\/practice\//);
  assert.match(v2.strategy, /se-path-multi-v2_next/);
  assert.equal(quiz.activity_type_limits.coding_exercise.scheduled, false);
});

test('adds revision and quiz for top weak topics and does not invent coding tasks', () => {
  const twinMastery = {
    [T.indexing]: { score: 40 },
    [T.heuristics]: { score: 20 },
  };
  const { activities, activity_type_limits: limits } = buildActivitySequence({
    twinMastery,
    insightsTopics: null,
  });
  assert.ok(activities.some((a) => a.kind === 'c1_revision' && a.launch_path.startsWith('/c1/topic/')));
  assert.ok(activities.some((a) => a.kind === 'c4_quiz' && a.launch_path.includes('tab=exams')));
  assert.equal(limits.coding_exercise.scheduled, false);
  assert.ok(!activities.some((a) => a.kind === 'coding'));
});

test('obsolete pre-catalogue topic ids are not sequenced as practice', () => {
  // Regression: Development renamed C1 practice keys; stale twin ids must not
  // produce pending activities or invented launch paths.
  const { activities, unavailable } = buildActivitySequence({
    twinMastery: {
      indexing: { score: 10 },
      usability_heuristics: { score: 5 },
      normalization: { score: 20 },
      risk_management: { score: 30 },
    },
    insightsTopics: null,
  });
  assert.equal(activities.filter((a) => a.status === 'pending' && a.kind === 'c1_practice').length, 0);
  for (const obsolete of ['indexing', 'usability_heuristics', 'normalization', 'risk_management']) {
    assert.ok(
      unavailable.some((u) => u.topic === obsolete),
      `expected ${obsolete} marked unavailable`
    );
  }
});
