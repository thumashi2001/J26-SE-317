import { getDb } from '../../../config/db.js';
import * as service from '../services/authService.js';

function handle(fn, status = 200) {
  return async (req, res) => {
    try {
      res.status(status).json(await fn(req));
    } catch (err) {
      res.status(err.status || 500).json({ error: err.message });
    }
  };
}

export const register = handle((req) => service.register(getDb(), req.body || {}), 201);
export const login = handle((req) => service.login(getDb(), req.body || {}));
export const me = handle((req) => service.me(getDb(), req.user.sub));
