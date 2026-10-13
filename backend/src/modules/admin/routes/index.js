import { Router } from 'express';
import { requireAuth, requireRole } from '../../../middleware/auth.js';
import * as admin from '../controllers/adminController.js';
import * as c1 from '../../c1/controllers/adminSummaryController.js';

const router = Router();

// Everything here is for the administrator only.
router.use(requireAuth, requireRole('admin'));

router.get('/stats', admin.stats);
router.get('/lecturers', admin.lecturers); // ?status=pending|approved|rejected
router.post('/lecturers/:id/approve', admin.approve);
router.post('/lecturers/:id/reject', admin.reject);

router.get('/c1/summary', c1.summary); // Component 1 card: totals only

// Other members: add your admin-only routes below this line, for example
//   router.get('/c3/review-queue', c3.queue);

export default router;
