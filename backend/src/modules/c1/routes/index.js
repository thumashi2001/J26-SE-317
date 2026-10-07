import { Router } from 'express';
import { requireAuth } from '../../../middleware/auth.js';
import * as diagnostic from '../controllers/diagnosticController.js';
import * as events from '../controllers/eventController.js';

const router = Router();

// Every C1 route needs a logged-in user.
router.use(requireAuth);

router.get('/diagnostic', diagnostic.getDiagnostic);
router.post('/diagnostic/submit', diagnostic.submitDiagnostic);
router.get('/twin/:studentId', diagnostic.getTwin);
router.post('/events', events.recordEvent);
router.get('/alerts/:studentId', events.getAlerts);

export default router;
