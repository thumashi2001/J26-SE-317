import { Router } from 'express';
import { requireAuth } from '../../../middleware/auth.js';
import * as diagnostic from '../controllers/diagnosticController.js';
import * as events from '../controllers/eventController.js';
import * as history from '../controllers/historyController.js';
import * as forecast from '../controllers/forecastController.js';
import * as practice from '../controllers/practiceController.js';
import * as insights from '../controllers/insightsController.js';
import * as plan from '../controllers/planController.js';
import * as level from '../controllers/levelController.js';

const router = Router();

// Every C1 route needs a logged-in user.
router.use(requireAuth);

router.get('/diagnostic', diagnostic.getDiagnostic);
router.post('/diagnostic/submit', diagnostic.submitDiagnostic);
router.get('/twin/:studentId', diagnostic.getTwin);
router.post('/events', events.recordEvent);
router.get('/alerts/:studentId', events.getAlerts);
router.get('/history/:studentId/:topic', history.getHistory);
router.get('/forecast/:studentId/:topic', forecast.getForecast);
router.get('/insights/:studentId', insights.getInsights);
router.get('/behaviour/:studentId', insights.getBehaviour);
router.get('/plan/:studentId', plan.getPlan);
router.get('/level/:studentId', level.getLevel);
router.put('/exam-date', plan.setExamDate);
router.get('/practice/topics', practice.topics);
router.post('/practice/start', practice.start);
router.post('/practice/answer', practice.answer);
router.post('/practice/hint', practice.hint);

export default router;
