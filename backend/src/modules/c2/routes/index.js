
import { Router } from 'express';
import { requireAuth, requireRole } from '../../../middleware/auth.js';
import * as controller from '../controllers/c2Controller.js';

const router = Router();

// All C2 routes require authentication.
router.use(requireAuth);

// --------------------------------------------------
// C2 - Shared module information
// --------------------------------------------------

router.get(
  '/modules',
  controller.listModules
);

// --------------------------------------------------
// M9.1 - Student Question Bank
// Available to authenticated students.
// --------------------------------------------------

router.get(
  '/questions',
  controller.listStudentQuestions
);

// --------------------------------------------------
// M11.1 - Historical Exam Pattern Analysis
// Available to authenticated users.
// --------------------------------------------------

router.get(
  '/exam-patterns',
  controller.listExamPatterns
);

// --------------------------------------------------
// M8 - Lecturer Syllabus Review
// Restricted to lecturers and administrators.
// --------------------------------------------------

router.get(
  '/reviews/:moduleKey/excluded',
  requireRole('lecturer', 'admin'),
  controller.listExcludedCandidates
);

router.get(
  '/reviews/:moduleKey/stats',
  requireRole('lecturer', 'admin'),
  controller.listReviewStatistics
);

router.get(
  '/reviews/:moduleKey',
  requireRole('lecturer', 'admin'),
  controller.listReviewQueue
);

router.post(
  '/reviews/:moduleKey/:candidateId/decision',
  requireRole('lecturer', 'admin'),
  controller.reviewCandidate
);

export default router;
