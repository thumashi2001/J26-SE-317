import { Router } from 'express';
import { requireAuth, requireRole } from '../../../middleware/auth.js';
import * as controller from '../controllers/c3Controller.js';
import { rateLimit } from '../middleware/rateLimit.js';
import { c3NotFound, c3ErrorHandler } from '../middleware/errorHandling.js';

const router = Router();

router.use(requireAuth);

// Raw analysis endpoints return unredacted model output (including MCQ keys): lecturers only
// (the shared resolveStudentId helper already refuses admins for these calls).
const staff = requireRole('lecturer');
router.post('/analysis', staff, rateLimit('raw'), controller.analyzeAnswer);
router.post('/marking', staff, rateLimit('raw'), controller.markAnswer);
router.post('/feedback', staff, rateLimit('raw'), controller.generateFeedback);
router.post('/mindmap', staff, rateLimit('raw'), controller.generateMindmap);
router.post('/assess', rateLimit('assess'), controller.assessAnswer);

// Assessments a student may choose from (question and options only; no keys, rubrics or reference answers)
router.get('/assessments', controller.listAssessments);

// Example setups with keys and rubrics: staff only
router.get('/examples', requireRole('lecturer', 'admin'), controller.listExamples);

// Submissions and human-in-the-loop lecturer review workflow
router.get('/submissions', controller.listSubmissions);
router.get('/submissions/:id', controller.getSubmission);
router.post('/submissions/:id/review', requireRole('lecturer', 'admin'), controller.reviewSubmission);
router.post('/submissions/:id/finalize', requireRole('lecturer', 'admin'), controller.finalizeSubmission);

// Batch marking workflow (Lecturer configure once, submit multiple answers, automated grading)
router.post('/batch/setup', requireRole('lecturer', 'admin'), controller.createBatchSetup);
router.get('/batch/setup', requireRole('lecturer', 'admin'), controller.listBatchSetups);
router.get('/batch/setup/:id', requireRole('lecturer', 'admin'), controller.getBatchSetup);
router.post('/batch/validate', requireRole('lecturer', 'admin'), rateLimit('batch'), controller.validateBatchAnswers);
router.post('/batch/mark', requireRole('lecturer', 'admin'), rateLimit('batch'), controller.processBatchMarking);
router.post('/batch/:batchId/finalize-all', requireRole('lecturer', 'admin'), controller.finalizeBatchSubmissions);

// Scanned document / OCR endpoint boundary (explicit unsupported format handling)
router.post('/upload-scanned', controller.unsupportedOcrHandler);
router.post('/ocr', controller.unsupportedOcrHandler);

// Unknown C3 paths and errors thrown inside C3 handlers answer in JSON without internal details.
router.use(c3NotFound);
router.use(c3ErrorHandler);

export default router;
