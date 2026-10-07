import { Router } from 'express';
import { requireAuth } from '../../../middleware/auth.js';
import * as controller from '../controllers/authController.js';

const router = Router();
router.post('/register', controller.register); // students
router.post('/register-lecturer', controller.registerLecturer); // lecturers, need admin approval
router.post('/login', controller.login); // students, lecturers and the admin
router.get('/me', requireAuth, controller.me);
export default router;
