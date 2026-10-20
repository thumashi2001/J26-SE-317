import { getDb } from '../../../config/db.js';
import * as service from '../services/classInsightsService.js';

// GET /c1/class  (lecturers only, see routes) -> how the class is learning and who may need help
export async function classInsights(req, res) {
  try {
    res.json(await service.getClass(getDb()));
  } catch (err) {
    res.status(err.status || 500).json({ error: err.message });
  }
}
