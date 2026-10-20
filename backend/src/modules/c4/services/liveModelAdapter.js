/**
 * Live-input adapters for SE v1 models (simulation-trained).
 *
 * Path + exam: usable when liveFeatureBuilders can construct verified inputs.
 * Response: remains unusable (item difficulty unavailable on C1).
 */

import { SIM_CATALOGUE_HASH } from '../data/simCatalogue.generated.js';
import {
  assessLiveResponseFeatures,
  buildExamFeaturesFromEvents,
  buildPathObservationPayload,
  countPathEpisodeSteps,
  countPracticeAttemptSteps,
  deriveAvailability,
  estimatePracticeQuizFromBlueprint,
  initialPathEpisodeState,
  LIVE_PATH_PROTOCOL,
  LIVE_PRACTICE_QUIZ_PROTOCOL,
  LIVE_PRIOR_STRENGTH_CONSTANT,
  PRACTICE_QUIZ_SCORE_TARGET,
  normalizeMasteryEntry,
} from './liveFeatureBuilders.js';

export {
  assessLiveResponseFeatures,
  buildExamFeaturesFromEvents,
  buildPathObservationPayload,
  countPathEpisodeSteps,
  countPracticeAttemptSteps,
  deriveAvailability,
  estimatePracticeQuizFromBlueprint,
  initialPathEpisodeState,
  LIVE_PATH_PROTOCOL,
  LIVE_PRACTICE_QUIZ_PROTOCOL,
  LIVE_PRIOR_STRENGTH_CONSTANT,
  PRACTICE_QUIZ_SCORE_TARGET,
  normalizeMasteryEntry,
};

/**
 * Path model input assessment (+ observation for inference when usable).
 */
export function assessPathModelInputs(opts) {
  const built = buildPathObservationPayload(opts || {});
  if (!built.usable) {
    return {
      usable: false,
      code: built.code,
      reason: built.reason,
      experimental: true,
      simulation_trained: true,
      real_student_validation: false,
      protocol: LIVE_PATH_PROTOCOL,
      catalogue_hash: SIM_CATALOGUE_HASH,
      fields: built.provenance || null,
    };
  }
  return {
    usable: true,
    code: built.code,
    experimental: true,
    simulation_trained: true,
    real_student_validation: false,
    protocol: built.protocol,
    model_protocol: built.model_protocol,
    catalogue_hash: built.catalogue_hash,
    semester: built.semester,
    observation: built.observation,
    action_mask: built.action_mask,
    input_timestamp: built.input_timestamp,
    provenance: built.provenance,
    label:
      'Experimental live serving of se-path-sim-v1. Simulation-trained; not real-exam validated. ' +
      'Operational scheduling still uses weakest_stored_mastery_v1 when inference fails.',
  };
}

/**
 * Supervised assessment — response blocked; exam features need events+cutoff.
 */
export function assessSupervisedModelInputs(opts = {}) {
  const response = assessLiveResponseFeatures();
  if (opts.mode === 'response') return response;
  if (opts.mode === 'exam' && opts.events && opts.cutoffIso) {
    return buildExamFeaturesFromEvents(opts.events, {
      cutoffIso: opts.cutoffIso,
      studentId: opts.studentId,
      practiceSessions: opts.practiceSessions,
    });
  }
  return {
    usable: false,
    code: 'supervised_inputs_need_context',
    reason:
      'Exam/pass live features require learning_events and a frozen prediction cutoff ' +
      '(C4 mock-attempt created_at). Response features remain blocked (no item difficulty).',
    experimental: true,
    simulation_trained: true,
    real_student_validation: false,
    real_exam_validation: false,
    response,
    field_status: {
      difficulty: 'unavailable',
      exam_features: 'available_when_cutoff_and_events_provided',
      topic_prior_streak: 'derivable_for_response_but_blocked_by_difficulty',
    },
  };
}
