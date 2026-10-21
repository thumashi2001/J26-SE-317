/**
 * C4 → C2 exam content adapter (C4-owned; does not modify C2).
 *
 * Inspected C2 surfaces (ai-services/c2):
 * - Offline PDF → paper parse → question_repository JSON builders
 *   (paper_parser, question_repository.build_question_repository, json_repository)
 * - Dataset/taxonomy/coverage validators and classification pipelines
 * - Config: modules.json, exam_structures.json (mostly unverified / empty topics)
 * - No Node module under backend/src/modules/c2
 * - No FastAPI student attempt API
 * - Question records have question_text/marks/topic placeholders — not MCQ options
 *   or server-held answer keys suitable for timed student delivery
 *
 * Therefore there is no reusable authorized delivery contract C4 can call without
 * inventing keys or bypassing publication rules. Direct Mongo access is forbidden.
 *
 * Practice-bank mock quizzes remain a separate C4 source and must not be labelled
 * as C2 past-paper integration.
 */

export const C2_ADAPTER_STATUS = 'unavailable_no_delivery_contract';

/**
 * Attempt to load an authorized past-paper style exam from C2.
 */
export async function fetchC2ExamPaper(_opts = {}) {
  return {
    available: false,
    source: 'c2',
    status: C2_ADAPTER_STATUS,
    reason:
      'C2 exposes offline dataset builders (e.g. build_question_repository) without an ' +
      'authorized HTTP/service contract for student exam attempts, answer-key isolation, ' +
      'or publication checks. C4 will not import offline paper JSON as live exams.',
    inspected: {
      python_builders: [
        'ai-services/c2/services/paper_parser.py',
        'ai-services/c2/services/question_repository.py',
        'ai-services/c2/services/json_repository.py',
      ],
      node_api: null,
      student_attempt_api: null,
      answer_key_api: null,
    },
    required_dependency:
      'C2-owned authenticated APIs that (1) list published papers for a student/module, ' +
      '(2) issue an attempt with public questions only (no keys/rubrics), ' +
      '(3) accept answers under ownership + timing rules, ' +
      '(4) return server-side grading or deferred marking without exposing keys early.',
    required_payload_sketch: {
      list: 'GET /api/v1/c2/papers?module=&published=true → [{ paperId, module, title }]',
      start:
        'POST /api/v1/c2/attempts { paperId } → { attemptId, expiresAt, questions:[{id,text,options?}] }',
      save: 'POST /api/v1/c2/attempts/:id/answers { answers }',
      submit: 'POST /api/v1/c2/attempts/:id/submit → { score?, pendingManual?, reviewAfterSubmit }',
    },
  };
}
