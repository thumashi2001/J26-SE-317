import { Router } from 'express';
import { requireAuth, requireRole } from '../../../middleware/auth.js';
import * as controller from '../controllers/c3Controller.js';
import * as app from '../controllers/c3AppController.js';

const router = Router();
router.use(requireAuth);

// ── Raw AI proxy routes (preserved for testing / direct use) ─────────────────
router.post('/analysis', controller.analyzeAnswer);
router.post('/marking', controller.markAnswer);
router.post('/feedback', controller.generateFeedback);
router.post('/mindmap', controller.generateMindmap);

// ── Student: Assessment API ───────────────────────────────────────────────────
router.get('/assessments', app.listAssessments);
router.get('/assessments/:id', app.getAssessment);

// ── Student: Submission API ───────────────────────────────────────────────────
router.post('/submissions', app.submitAnswer);
router.get('/submissions/me', app.listMySubmissions);
router.get('/submissions/:id', app.getMySubmission);
router.get('/results/:submissionId', app.getMyResult);

// ── Lecturer: Submission queue + review ──────────────────────────────────────
router.get('/lecturer/submissions', requireRole('lecturer'), app.lecturerListSubmissions);
router.get('/lecturer/submissions/:submissionId', requireRole('lecturer'), app.lecturerGetSubmission);
router.post('/lecturer/submissions/:submissionId/accept', requireRole('lecturer'), app.lecturerAccept);
router.post('/lecturer/submissions/:submissionId/override', requireRole('lecturer'), app.lecturerOverride);

// ── Admin: Stats ──────────────────────────────────────────────────────────────
router.get('/admin/stats', requireRole('admin'), app.adminStats);

export default router;
