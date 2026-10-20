import { Router } from 'express';
import { requireAuth } from '../../../middleware/auth.js';
import * as controller from '../controllers/authController.js';

const router = Router();
router.post('/register', controller.register); // students
router.post('/register-lecturer', controller.registerLecturer); // lecturers, need admin approval
router.post('/login', controller.login); // students, lecturers and the admin
router.get('/me', requireAuth, controller.me);

// My profile: every role. The ID is never editable.
router.get('/profile', requireAuth, controller.getProfile);
router.patch('/profile', requireAuth, controller.updateProfile);
router.put('/profile/avatar', requireAuth, controller.setAvatar);
router.post('/change-password', requireAuth, controller.changePassword);
router.post('/usage', requireAuth, controller.recordUsage);
router.get('/usage', requireAuth, controller.getUsage);
export default router;
