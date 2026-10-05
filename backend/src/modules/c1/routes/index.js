import { Router } from 'express';
import * as controller from '../controllers/diagnosticController.js';

const router = Router();

router.get('/diagnostic', controller.getDiagnostic);
router.post('/diagnostic/submit', controller.submitDiagnostic);
router.get('/twin/:studentId', controller.getTwin);

export default router;