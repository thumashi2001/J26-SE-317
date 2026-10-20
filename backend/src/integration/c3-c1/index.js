import { getDb } from '../../config/db.js';

/**
 * C3 -> C1 Live Component Integration Bridge
 *
 * Emits evaluated and finalized C3 assessment evidence directly to C1 (Cognitive Digital Twin).
 * Synchronizes learning events idempotently to MongoDB 'learning_events' by stable submission_id.
 *
 * Lifecycle:
 * 1. At submission: records one provisional learning event (lifecycle_stage: 'provisional',
 *    provisional_score, type: 'c3_automated_assessment').
 * 2. At finalization: updates the existing record in-place (lifecycle_stage: 'finalized',
 *    final_score, lecturer_decision, override_reason, type: 'c3_finalized_assessment').
 * 3. Idempotent: repeated calls for the same submission_id update in-place without duplicating events.
 *
 * @param {Object} params
 * @param {string} params.studentId - Student identifier
 * @param {string} params.submissionId - C3 submission ID
 * @param {string} params.questionId - Question identifier
 * @param {string} [params.questionText] - Question description
 * @param {number} params.score - Awarded mark
 * @param {number} params.totalPossible - Maximum mark
 * @param {number} [params.percentage] - Percentage score
 * @param {Array} [params.conceptMatches] - Concept matches from F1
 * @param {boolean} [params.finalized] - Whether this is the finalized lecturer mark
 * @param {string} [params.lecturerDecision] - 'accepted' | 'overridden'
 * @param {string} [params.overrideReason] - Lecturer justification for override
 * @param {string} [params.reviewedBy] - Lecturer/staff identifier
 * @returns {Promise<{ synced: boolean, eventId?: string, topic?: string, type?: string, lifecycle_stage?: string, reason?: string, note?: string }>}
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
  lecturerDecision = null,
  overrideReason = null,
  reviewedBy = null,
}) {
  try {
    const db = getDb();
    if (!db) return { synced: false, reason: 'Database connection unavailable' };

    const col = db.collection('learning_events');
    if (!col || typeof col.findOne !== 'function') {
      return { synced: false, reason: 'learning_events collection not available in current database' };
    }

    const subIdStr = String(submissionId || '').trim();
    if (!subIdStr) {
      return { synced: false, reason: 'submissionId is required for C3 event synchronization' };
    }

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
      .filter((c) => c && c.status === 'demonstrated')
      .map((c) => c.concept);
    const partial = conceptMatches
      .filter((c) => c && c.status === 'partial')
      .map((c) => c.concept);
    const missing = conceptMatches
      .filter((c) => c && (c.status === 'not_demonstrated' || c.status === 'missing'))
      .map((c) => c.concept);

    const numericScore = Number(score) || 0;
    const numericTotal = Number(totalPossible) || 0;
    const numericPct = Number(percentage) || (numericTotal > 0 ? Math.round((numericScore / numericTotal) * 1000) / 10 : 0);
    const isPassing = numericPct >= 50;

    const existing = await col.findOne({ submission_id: subIdStr });

    if (!finalized) {
      // Provisional assessment event at submission time
      // If the event was already finalized, do not revert it to provisional
      if (existing && existing.lifecycle_stage === 'finalized') {
        return {
          synced: true,
          eventId: String(existing._id),
          topic: existing.topic,
          type: existing.type,
          lifecycle_stage: existing.lifecycle_stage,
          note: 'Event already finalized; provisional sync skipped',
        };
      }

      const updateResult = await col.findOneAndUpdate(
        { submission_id: subIdStr },
        {
          $set: {
            student_id: studentId,
            type: 'c3_automated_assessment',
            lifecycle_stage: 'provisional',
            question_id: questionId || 'C3-ASSESSMENT',
            topic,
            score: numericScore,
            provisional_score: numericScore,
            final_score: null,
            total_possible: numericTotal,
            percentage: numericPct,
            correct: isPassing,
            answered: true,
            time_sec: 60,
            demonstrated_concepts: demonstrated,
            partial_concepts: partial,
            missing_concepts: missing,
            source_component: 'Component 3 (Automated Marking & Answer Analysis)',
            lecturer_decision: null,
            override_reason: null,
            reviewed_by: null,
            updated_at: new Date(),
          },
          $setOnInsert: {
            submission_id: subIdStr,
            timestamp: new Date(),
          },
        },
        { upsert: true, returnDocument: 'after' }
      );

      const doc = updateResult?.value || updateResult;
      return {
        synced: true,
        eventId: doc?._id ? String(doc._id) : 'upserted',
        topic,
        type: 'c3_automated_assessment',
        lifecycle_stage: 'provisional',
      };
    } else {
      // Finalized assessment event at lecturer review/finalization time
      const updateResult = await col.findOneAndUpdate(
        { submission_id: subIdStr },
        {
          $set: {
            student_id: studentId,
            type: 'c3_finalized_assessment',
            lifecycle_stage: 'finalized',
            question_id: questionId || 'C3-ASSESSMENT',
            topic,
            score: numericScore,
            final_score: numericScore,
            total_possible: numericTotal,
            percentage: numericPct,
            correct: isPassing,
            answered: true,
            time_sec: 60,
            demonstrated_concepts: demonstrated,
            partial_concepts: partial,
            missing_concepts: missing,
            source_component: 'Component 3 (Automated Marking & Answer Analysis)',
            lecturer_decision: lecturerDecision,
            override_reason: overrideReason,
            reviewed_by: reviewedBy,
            finalized_at: new Date(),
            updated_at: new Date(),
          },
          $setOnInsert: {
            submission_id: subIdStr,
            provisional_score: numericScore,
            timestamp: new Date(),
          },
        },
        { upsert: true, returnDocument: 'after' }
      );

      const doc = updateResult?.value || updateResult;
      return {
        synced: true,
        eventId: doc?._id ? String(doc._id) : 'upserted',
        topic,
        type: 'c3_finalized_assessment',
        lifecycle_stage: 'finalized',
      };
    }
  } catch (err) {
    console.warn('[C3->C1 Integration] Warning: Could not sync assessment event to C1:', err.message);
    return { synced: false, reason: err.message };
  }
}
