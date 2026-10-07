import { Router } from 'express';
import { requireAuth } from '../../../middleware/auth.js';
import * as controller from '../controllers/authController.js';

const router = Router();
router.post('/register', controller.register);
router.post('/login', controller.login);
router.get('/me', requireAuth, controller.me);
export default router;
