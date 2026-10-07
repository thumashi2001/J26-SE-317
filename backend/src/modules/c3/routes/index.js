import { Router } from 'express';
import { requireAuth } from '../../../middleware/auth.js';
import * as controller from '../controllers/c3Controller.js';

const router = Router();

router.use(requireAuth);

router.post('/analysis', controller.analyzeAnswer);
router.post('/marking', controller.markAnswer);
router.post('/feedback', controller.generateFeedback);
router.post('/mindmap', controller.generateMindmap);

export default router;
