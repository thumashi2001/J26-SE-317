/**
 * Auto-mounted at /api/v1/c4 by backend/src/app.js (do not edit app.js).
 */
import { Router } from 'express';
import { requireAuth } from '../../../middleware/auth.js';
import * as paths from '../controllers/pathController.js';
import * as sim from '../controllers/simDemoController.js';
import * as exams from '../controllers/examController.js';
import * as feedback from '../controllers/feedbackController.js';
import * as lecturer from '../controllers/lecturerController.js';

const router = Router();

router.use(requireAuth);

router.post('/paths', paths.create);
router.get('/paths', paths.list);
router.get('/paths/active', paths.active);
router.get('/paths/:pathId', paths.detail);
router.post('/paths/:pathId/progress', paths.progress);
router.post('/paths/:pathId/replan', paths.replan);
router.post('/paths/:pathId/refresh', paths.refresh);
router.get('/paths/:pathId/revisions', paths.revisions);

// C4 mock exams (practice-bank). C2 past-paper source reports unavailable honestly.
router.get('/exams/sources', exams.sources);
router.post('/exams', exams.create);
router.get('/exams', exams.list);
router.get('/exams/evaluation', exams.evaluation);
router.get('/exams/:attemptId', exams.detail);
router.post('/exams/:attemptId/answers', exams.saveAnswers);
router.post('/exams/:attemptId/submit', exams.submit);

router.post('/feedback', feedback.create);
router.get('/feedback', feedback.list);

// Read-only lecturer view. Live scope is fail-closed; studentId is not authorization.
router.get('/lecturer/scope', lecturer.scope);
router.get('/lecturer/students', lecturer.students);
router.get('/lecturer/students/:studentId/plan', lecturer.plan);

// Synthetic simulation demo (v1 Python APIs via server-side proxy). No Atlas writes.
router.get('/simulation/v1/ready', sim.demoReady);
router.get('/simulation/v1/scenarios', sim.scenarios);
router.get('/simulation/v1/path/ready', sim.pathReady);
router.get('/simulation/v1/path/catalogue', sim.pathCatalogue);
router.post('/simulation/v1/path/predict', sim.pathPredict);
router.get('/simulation/v1/supervised/ready', sim.supervisedReady);
router.post('/simulation/v1/supervised/response', sim.supervisedResponse);
router.post('/simulation/v1/supervised/exam-score', sim.supervisedExamScore);
router.post('/simulation/v1/supervised/pass', sim.supervisedPass);

export default router;
