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

// Batch marking workflow (Lecturer configure once, submit multiple answers, automated grading)
router.post('/batch/setup', requireRole('lecturer', 'admin'), controller.createBatchSetup);
router.get('/batch/setup', requireRole('lecturer', 'admin'), controller.listBatchSetups);
router.get('/batch/setup/:id', requireRole('lecturer', 'admin'), controller.getBatchSetup);
router.post('/batch/validate', requireRole('lecturer', 'admin'), controller.validateBatchAnswers);
router.post('/batch/mark', requireRole('lecturer', 'admin'), controller.processBatchMarking);
router.post('/batch/:batchId/finalize-all', requireRole('lecturer', 'admin'), controller.finalizeBatchSubmissions);

// Scanned document / OCR endpoint boundary (explicit unsupported format handling)
router.post('/upload-scanned', controller.unsupportedOcrHandler);
router.post('/ocr', controller.unsupportedOcrHandler);

export default router;
