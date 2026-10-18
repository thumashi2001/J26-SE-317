
import * as c2Service from '../services/c2Service.js';

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