import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import {
  buildMultiMask,
  buildMultiObservation,
  maskCompletedActivities,
  MULTI_N_ACTIONS,
  MULTI_PROTOCOL_V2,
  resolveMultiAction,
} from '../services/multiActionContract.js';

const here = dirname(fileURLToPath(import.meta.url));
const fixturePath = join(
  here,
  '../../../../../ai-services/c4/training_se_v2/multi_action/fixtures/obs_case.json'
);

test('node multi-action observation matches the Python fixture', () => {
  const fixture = JSON.parse(readFileSync(fixturePath, 'utf8'));
  const built = buildMultiObservation({
    mastery: fixture.mastery,
    available: fixture.available,
    elapsedEnvSteps: fixture.elapsed_env_steps,
    recentAccuracy: null,
    engagementCompletionRate: null,
    examUrgency: null,
  });
  assert.equal(built.usable, true);
  assert.equal(built.protocol, fixture.protocol);
  assert.equal(built.observation.length, fixture.observation.length);
  built.observation.forEach((v, i) => {
    assert.ok(Math.abs(v - fixture.observation[i]) < 1e-5, `index ${i}`);
  });
  const mask = buildMultiMask({
    semester: 'Y3S1',
    available: fixture.available,
    mastery: fixture.mastery,
  });
  assert.equal(mask.mask.length, MULTI_N_ACTIONS);
  assert.equal(mask.coding_scheduled, false);
  assert.equal(mask.mask.slice(-46).some(Boolean), false);
  const unknown = buildMultiMask({
    semester: 'Y9',
    available: fixture.available,
    mastery: fixture.mastery,
  });
  assert.equal(unknown.mask.some(Boolean), false);
});

test('practice, revision and quiz resolve to launch paths; coding and ineligible actions do not', () => {
  const fixture = JSON.parse(readFileSync(fixturePath, 'utf8'));
  const topic = 'interaction_functional_design';
  for (const actionType of ['practice', 'revision', 'quiz']) {
    const resolved = resolveMultiAction({
      actionType,
      topicId: topic,
      semester: 'Y3S1',
      available: fixture.available,
      mastery: fixture.mastery,
    });
    assert.equal(resolved.usable, true, actionType);
    assert.ok(resolved.launchPath.includes(topic));
    assert.ok(resolved.activityId.endsWith(`:${topic}`));
  }
  const coding = resolveMultiAction({
    actionType: 'coding',
    topicId: topic,
    semester: 'Y3S1',
    available: fixture.available,
    mastery: fixture.mastery,
  });
  assert.equal(coding.usable, false);
  assert.equal(coding.code, 'coding_unavailable');
  const otherSemester = resolveMultiAction({
    actionType: 'quiz',
    topicId: 'ds_architectures_sockets',
    semester: 'Y3S1',
    available: fixture.available.map(() => 1),
    mastery: fixture.mastery,
  });
  assert.equal(otherSemester.usable, false);
  assert.equal(otherSemester.code, 'ineligible');
});

test('completed practice is masked; Y3S2 keeps coding masked and excludes a Y3S1 topic', () => {
  const fixture = JSON.parse(readFileSync(fixturePath, 'utf8'));
  const y3s1 = buildMultiMask({
    semester: 'Y3S1',
    available: fixture.available,
    mastery: fixture.mastery,
  });
  const masked = maskCompletedActivities(y3s1.mask, ['c1_practice:interaction_functional_design']);
  assert.equal(y3s1.mask[0], true);
  assert.equal(masked[0], false);
  assert.equal(masked[46], y3s1.mask[46]);
  const y3s2 = buildMultiMask({
    semester: 'Y3S2',
    available: fixture.available.map(() => 1),
    mastery: fixture.mastery,
  });
  assert.equal(y3s2.mask[0], false);
  assert.ok(y3s2.mask.slice(46 * 3).every((bit) => bit === false));
  assert.equal(y3s2.mask.length, MULTI_N_ACTIONS);
});

test('node features match the se-path-multi-v2 fixture', () => {
  const fixturePathV2 = join(
    here,
    '../../../../../ai-services/c4/training_se_v2/multi_action_v2/fixtures/obs_case.json'
  );
  const fixture = JSON.parse(readFileSync(fixturePathV2, 'utf8'));
  assert.equal(fixture.protocol, MULTI_PROTOCOL_V2);
  const built = buildMultiObservation({
    mastery: fixture.mastery,
    available: fixture.available,
    elapsedEnvSteps: fixture.elapsed_env_steps,
    recentAccuracy: null,
    engagementCompletionRate: null,
    examUrgency: null,
  });
  assert.equal(built.usable, true);
  assert.equal(built.observation.length, fixture.obs_dim);
  built.observation.forEach((value, index) => {
    assert.ok(Math.abs(value - fixture.observation[index]) < 1e-5, `index ${index}`);
  });
});
