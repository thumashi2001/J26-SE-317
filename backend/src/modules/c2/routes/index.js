import { Router } from 'express';
import { requireAuth, requireRole } from '../../../middleware/auth.js';
import * as controller from '../controllers/c2Controller.js';

const router = Router();

router.use(requireAuth);

router.get('/modules', controller.listModules);

router.get(
  '/reviews/:moduleKey/excluded',
  requireRole('lecturer', 'admin'),
  controller.listExcludedCandidates
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