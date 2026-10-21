/**
 * C4 consumer for coding exercises. Development now mounts C3 marking,
 * feedback, mind-map and submission review routes. Those are not a published
 * coding-exercise catalogue, launch path, or completion contract.
 * Coding actions stay masked. This is not a C3 grader.
 */

export async function fetchCodingExercises() {
  return {
    available: false,
    content_ids: [],
    reason:
      'No authorized coding-exercise catalogue or launch API was found. ' +
      'C4 will not invent exercises or treat an MCQ as a coding task.',
    required_provider: {
      owner: 'C3',
      list: 'GET /api/v1/c3/exercises?published=true → [{ exerciseId, topicId, title, launchPath }]',
      completion:
        'POST /api/v1/c3/exercises/:id/completion read by C4, or a C4-visible completion record the student owns',
      grading: 'Remains in C3. C4 records completion evidence only.',
    },
  };
}
