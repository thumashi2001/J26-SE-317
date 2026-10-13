import { getDb } from '../../../config/db.js';
import * as service from '../services/adminSummaryService.js';

const AI_URL = () => process.env.C1_AI_URL || 'http://127.0.0.1:8001';

// GET /admin/c1/summary  (administrator only, see admin/routes) -> totals for the Component 1 card
export async function summary(req, res) {
  try {
    res.json(await service.getSummary(getDb(), AI_URL()));
  } catch (err) {
    res.status(err.status || 500).json({ error: err.message });
  }
}

// GET /admin/c1/active  (administrator only) -> students active in the last 7 days, with name and picture
export async function active(req, res) {
  try {
    res.json(await service.getActive(getDb()));
  } catch (err) {
    res.status(err.status || 500).json({ error: err.message });
  }
}
