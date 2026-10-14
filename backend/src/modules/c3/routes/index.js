import { Router } from 'express';
import { requireAuth, requireRole } from '../../../middleware/auth.js';
import * as controller from '../controllers/c3Controller.js';

const router = Router();

router.use(requireAuth);

// Raw proxy & assessment pipeline endpoints
router.post('/analysis', controller.analyzeAnswer);
router.post('/marking', controller.markAnswer);
router.post('/feedback', controller.generateFeedback);
router.post('/mindmap', controller.generateMindmap);
router.post('/assess', controller.assessAnswer);

// Submissions and human-in-the-loop lecturer review workflow
router.get('/submissions', controller.listSubmissions);
router.get('/submissions/:id', controller.getSubmission);
router.post('/submissions/:id/review', requireRole('lecturer', 'admin'), controller.reviewSubmission);
router.post('/submissions/:id/finalize', requireRole('lecturer', 'admin'), controller.finalizeSubmission);

export default router;
