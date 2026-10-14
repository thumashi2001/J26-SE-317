import { getDb } from '../../config/db.js';

/**
 * C3 -> C1 Live Component Integration Bridge
 *
 * Emits evaluated and finalized C3 assessment evidence directly to C1 (Cognitive Digital Twin).
 * Logs learning events to MongoDB 'learning_events' and links weak/missing concepts
 * to the student's learner model for knowledge state updates.
 *
 * @param {Object} params
 * @param {string} params.studentId - Student identifier
 * @param {string} params.submissionId - C3 submission ID
 * @param {string} params.questionId - Question identifier
 * @param {string} [params.questionText] - Question description
 * @param {number} params.score - Awarded mark
 * @param {number} params.totalPossible - Maximum mark
 * @param {number} params.percentage - Percentage score
 * @param {Array} [params.conceptMatches] - Concept matches from F1
 * @param {boolean} [params.finalized] - Whether this is the finalized lecturer mark
 * @returns {Promise<{ synced: boolean, eventId?: string, topic?: string, reason?: string }>}
 */
export async function syncC3AssessmentToC1({
  studentId,
  submissionId,
  questionId,
  questionText = '',
  score,
  totalPossible,
  percentage,
  conceptMatches = [],
  finalized = false,
}) {
  try {
    const db = getDb();
    if (!db) return { synced: false, reason: 'Database connection unavailable' };

    // Resolve domain topic for C1 learner modelling based on question context
    let topic = 'sa_patterns_styles';
    const qLower = `${questionId || ''} ${questionText || ''}`.toLowerCase();
    if (qLower.includes('db') || qLower.includes('normaliz') || qLower.includes('sql') || qLower.includes('relation')) {
      topic = 'ds_components_formats';
    } else if (qLower.includes('micro') || qLower.includes('cloud') || qLower.includes('service')) {
      topic = 'ds_cloud_microservices';
    } else if (qLower.includes('testing') || qLower.includes('quality') || qLower.includes('metric')) {
      topic = 'qm_testing_basics';
    }

    const demonstrated = conceptMatches
      .filter((c) => c.status === 'demonstrated')
      .map((c) => c.concept);
    const partial = conceptMatches
      .filter((c) => c.status === 'partial')
      .map((c) => c.concept);
    const missing = conceptMatches
      .filter((c) => c.status === 'not_demonstrated' || c.status === 'missing')
      .map((c) => c.concept);

    const isPassing = (percentage ?? 0) >= 50;

    const eventDoc = {
      student_id: studentId,
      timestamp: new Date(),
      type: finalized ? 'c3_finalized_assessment' : 'c3_automated_assessment',
      submission_id: String(submissionId),
      question_id: questionId || 'C3-ASSESSMENT',
      topic,
      score: Number(score) || 0,
      total_possible: Number(totalPossible) || 0,
      percentage: Number(percentage) || 0,
      correct: isPassing,
      answered: true,
      time_sec: 60, // standardized assessment response interval
      demonstrated_concepts: demonstrated,
      partial_concepts: partial,
      missing_concepts: missing,
      source_component: 'Component 3 (Automated Marking & Answer Analysis)',
    };

    const col = db.collection('learning_events');
    if (!col || typeof col.insertOne !== 'function') {
      return { synced: false, reason: 'learning_events collection not available in current database' };
    }

    const res = await col.insertOne(eventDoc);

    return {
      synced: true,
      eventId: String(res.insertedId),
      topic,
      type: eventDoc.type,
    };
  } catch (err) {
    console.warn('[C3->C1 Integration] Warning: Could not sync assessment event to C1:', err.message);
    return { synced: false, reason: err.message };
  }
}
