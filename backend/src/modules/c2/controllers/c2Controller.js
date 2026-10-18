
import * as c2Service from '../services/c2Service.js';
import { getDb } from '../../../config/db.js';

import {
  generateC1PersonalizedMock,
  C1PersonalizationError,
} from '../services/c1PersonalizedMockService.js';

function handleError(res, error) {
  console.error('[C2 API]', error.message);

  const status =
    Number.isInteger(error.status) &&
    error.status >= 400 &&
    error.status < 600
      ? error.status
      : 500;

  const message =
    error instanceof c2Service.C2ServiceError
      ? error.message
      : 'Unexpected C2 server error';

  return res.status(status).json({ error: message });
}

// --------------------------------------------------
// List Supported Modules
// --------------------------------------------------

export async function listModules(req, res) {
  try {
    const result = await c2Service.getModules();

    return res.json(result);
  } catch (error) {
    return handleError(res, error);
  }
}

// --------------------------------------------------
// Get Syllabus Review Queue
// --------------------------------------------------

export async function listReviewQueue(req, res) {
  try {
    const { moduleKey } = req.params;

    const page = Number(req.query.page ?? 1);
    const pageSize = Number(req.query.pageSize ?? 25);

    if (
      !Number.isSafeInteger(page) ||
      page < 1 ||
      !Number.isSafeInteger(pageSize) ||
      pageSize < 1 ||
      pageSize > 100
    ) {
      return res.status(400).json({
        error: 'Invalid pagination parameters',
      });
    }

    const includeReviewed =
      req.query.includeReviewed === 'true';

    const result = await c2Service.getReviewQueue(
      moduleKey,
      { page, pageSize, includeReviewed }
    );

    return res.json(result);
  } catch (error) {
    return handleError(res, error);
  }
}

// --------------------------------------------------
// Get Excluded Syllabus Candidates
// --------------------------------------------------

export async function listExcludedCandidates(req, res) {
  try {
    const result = await c2Service.getExcludedCandidates(
      req.params.moduleKey
    );

    return res.json(result);
  } catch (error) {
    return handleError(res, error);
  }
}

// --------------------------------------------------
// M8 - Module-Wide Review Statistics
// --------------------------------------------------

export async function listReviewStatistics(req, res) {
  try {
    const { moduleKey } = req.params;

    const result = await c2Service.getReviewStatistics(
      moduleKey
    );

    return res.json(result);
  } catch (error) {
    return handleError(res, error);
  }
}

// --------------------------------------------------
// Lecturer Approval / Rejection
// --------------------------------------------------

export async function reviewCandidate(req, res) {
  try {
    const { moduleKey, candidateId } = req.params;

    const { decision, reviewNotes = '' } = req.body || {};

    // Validate the review decision.
    if (!['approved', 'rejected'].includes(decision)) {
      return res.status(400).json({
        error: 'Decision must be approved or rejected',
      });
    }

    // Validate review notes before calling trim().
    if (
      typeof reviewNotes !== 'string' ||
      reviewNotes.length > 2000
    ) {
      return res.status(400).json({
        error: 'Review notes must be at most 2000 characters',
      });
    }

    // Rejected topics require a reason.
    if (
      decision === 'rejected' &&
      !reviewNotes.trim()
    ) {
      return res.status(400).json({
        error: 'A rejection reason is required',
      });
    }

    // Reviewer identity comes from the authenticated JWT.
    const reviewerId = req.user.sub;

    const result = await c2Service.submitReviewDecision({
      moduleKey,
      candidateId,
      decision,
      reviewNotes: reviewNotes.trim(),
      reviewerId,
    });

    return res.json(result);
  } catch (error) {
    return handleError(res, error);
  }
}


export async function listStudentQuestions(req, res) {
  try {
    const { moduleKey } = req.query;

    const page = Number(req.query.page ?? 1);
    const pageSize = Number(req.query.pageSize ?? 10);

    if (
      !Number.isSafeInteger(page) ||
      page < 1 ||
      !Number.isSafeInteger(pageSize) ||
      pageSize < 1 ||
      pageSize > 100
    ) {
      return res.status(400).json({
        error: 'Invalid pagination parameters',
      });
    }

    if (
      moduleKey !== undefined &&
      (typeof moduleKey !== 'string' || !moduleKey.trim())
    ) {
      return res.status(400).json({
        error: 'Invalid module key',
      });
    }

    const result = await c2Service.getStudentQuestions({
      moduleKey,
      page,
      pageSize,
    });

    return res.json(result);
  } catch (error) {
    return handleError(res, error);
  }
}

// --------------------------------------------------
// M11.1 - Historical Exam Pattern Analysis
// --------------------------------------------------

export async function listExamPatterns(req, res) {
  try {
    const { moduleKey } = req.query;

    if (
      typeof moduleKey !== 'string' ||
      !moduleKey.trim()
    ) {
      return res.status(400).json({
        error: 'A valid moduleKey is required',
      });
    }

    const result = await c2Service.getExamPatterns(
      moduleKey.trim()
    );

    return res.json(result);
  } catch (error) {
    return handleError(res, error);
  }
}

// --------------------------------------------------
// M12.1 - Evidence-Aware Topic Predictions
// --------------------------------------------------

export async function listTopicPredictions(req, res) {
  try {
    const { moduleKey } = req.query;

    if (
      typeof moduleKey !== 'string' ||
      !moduleKey.trim()
    ) {
      return res.status(400).json({
        error: 'A valid moduleKey is required',
      });
    }

    const result = await c2Service.getTopicPredictions(
      moduleKey.trim()
    );

    return res.json(result);
  } catch (error) {
    return handleError(res, error);
  }
}

// --------------------------------------------------
// M12.2.1 - Personalized Practice Mock Examinations
// --------------------------------------------------

export async function generateMockExam(req, res) {
  try {
    const {
      moduleKey,
      targetMarks = 100,
      maxQuestions = 20,
      preferredTopics = [],
      difficulty = null,
      seed = 42,
    } = req.body || {};

    if (
      typeof moduleKey !== 'string' ||
      !moduleKey.trim()
    ) {
      return res.status(400).json({
        error: 'A valid moduleKey is required',
      });
    }

    if (
      !Number.isSafeInteger(targetMarks) ||
      targetMarks < 1 ||
      targetMarks > 200 ||
      !Number.isSafeInteger(maxQuestions) ||
      maxQuestions < 1 ||
      maxQuestions > 30 ||
      !Number.isSafeInteger(seed)
    ) {
      return res.status(400).json({
        error: 'Invalid mock examination parameters',
      });
    }

    if (
      !Array.isArray(preferredTopics) ||
      preferredTopics.length > 30 ||
      preferredTopics.some(
        (topic) =>
          typeof topic !== 'string' ||
          !topic.trim()
      ) ||
      (
        difficulty !== null &&
        (
          typeof difficulty !== 'string' ||
          !difficulty.trim()
        )
      )
    ) {
      return res.status(400).json({
        error: 'Invalid personalization preferences',
      });
    }

    const result = await c2Service.generateMockExam({
      module_key: moduleKey.trim(),
      target_marks: targetMarks,
      max_questions: maxQuestions,
      preferred_topics: preferredTopics,
      difficulty,
      seed,
    });

    return res.json(result);
  } catch (error) {
    return handleError(res, error);
  }
}

// --------------------------------------------------
// M12.4.2 - Staff-Only Synthetic Development Preview
// --------------------------------------------------

export async function generateSyntheticPracticePreview(req, res) {
  try {
    const {
      moduleKey,
      seed = 42,
    } = req.body || {};

    if (
      typeof moduleKey !== 'string' ||
      !moduleKey.trim()
    ) {
      return res.status(400).json({
        error: 'A valid moduleKey is required',
      });
    }

    if (!Number.isSafeInteger(seed)) {
      return res.status(400).json({
        error: 'seed must be a valid integer',
      });
    }

    const result =
      await c2Service.generateSyntheticPracticePreview({
        moduleKey: moduleKey.trim(),
        seed,
      });

    return res.json(result);
  } catch (error) {
    return handleError(res, error);
  }
}

// --------------------------------------------------
// M14.2.2 - C1 Digital Twin Personalized Mock
// --------------------------------------------------

export async function generateC1MockExam(req, res) {
  try {
    const {
      moduleKey,
      targetMarks = 100,
      maxQuestions = 20,
      seed = 42,
    } = req.body || {};

    if (
      typeof moduleKey !== 'string' ||
      !moduleKey.trim()
    ) {
      return res.status(400).json({
        error: 'A valid moduleKey is required',
      });
    }

    if (
      !Number.isSafeInteger(targetMarks) ||
      targetMarks < 1 ||
      targetMarks > 200 ||
      !Number.isSafeInteger(maxQuestions) ||
      maxQuestions < 1 ||
      maxQuestions > 30 ||
      !Number.isSafeInteger(seed)
    ) {
      return res.status(400).json({
        error: 'Invalid mock examination parameters',
      });
    }

    // Student ID is taken only from the verified JWT.
    const studentId = req.user.sub;

    const result = await generateC1PersonalizedMock({
      db: getDb(),
      studentId,
      moduleKey: moduleKey.trim(),
      targetMarks,
      maxQuestions,
      seed,
    });

    return res.json(result);
  } catch (error) {
    if (error instanceof C1PersonalizationError) {
      return res.status(error.status).json({
        error: error.message,
      });
    }

    // Reuse the existing C2 error handler.
    return handleError(res, error);
  }
}

// M14.3.3.2 - Lecturer Question Classification Review
export async function reviewQuestionClassification(req, res) {
  try {
    const { questionId } = req.params;

    const {
      moduleKey,
      topicId,
      decision,
      reviewNotes = '',
    } = req.body || {};

    if (
      typeof questionId !== 'string' ||
      !questionId.trim() ||
      typeof moduleKey !== 'string' ||
      !moduleKey.trim() ||
      typeof topicId !== 'string' ||
      !topicId.trim()
    ) {
      return res.status(400).json({
        error: 'Valid questionId, moduleKey and topicId are required',
      });
    }

    if (!['approved', 'rejected'].includes(decision)) {
      return res.status(400).json({
        error: 'Decision must be approved or rejected',
      });
    }

    if (
      typeof reviewNotes !== 'string' ||
      reviewNotes.length > 2000
    ) {
      return res.status(400).json({
        error: 'Invalid review notes',
      });
    }

    if (
      decision === 'rejected' &&
      !reviewNotes.trim()
    ) {
      return res.status(400).json({
        error: 'Rejection requires review notes',
      });
    }

    const result =
      await c2Service.submitQuestionClassificationReview({
        questionId: questionId.trim(),
        moduleKey: moduleKey.trim(),
        topicId: topicId.trim(),
        decision,
        reviewNotes: reviewNotes.trim(),
        reviewerId: req.user.sub,
      });

    return res.json(result);
  } catch (error) {
    return handleError(res, error);
  }
}

// M15.3 - Lecturer Question Classification Review List
export async function listQuestionClassificationReviews(req, res) {
  try {
    const { moduleKey } = req.query;
    const page = Number(req.query.page ?? 1);
    const pageSize = Number(req.query.pageSize ?? 10);
    const includeReviewed = req.query.includeReviewed === 'true';

    if (
      !Number.isSafeInteger(page) ||
      page < 1 ||
      !Number.isSafeInteger(pageSize) ||
      pageSize < 1 ||
      pageSize > 100
    ) {
      return res.status(400).json({
        error: 'Invalid pagination parameters',
      });
    }

    if (
      moduleKey !== undefined &&
      (typeof moduleKey !== 'string' || !moduleKey.trim())
    ) {
      return res.status(400).json({
        error: 'Invalid module key',
      });
    }

    const result =
      await c2Service.getQuestionClassificationReviews({
        moduleKey: moduleKey ? moduleKey.trim() : undefined,
        page,
        pageSize,
        includeReviewed,
      });

    return res.json(result);
  } catch (error) {
    return handleError(res, error);
  }
}