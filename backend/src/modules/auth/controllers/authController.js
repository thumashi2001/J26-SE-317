import { getDb } from '../../../config/db.js';
import * as service from '../services/authService.js';
import * as profile from '../services/profileService.js';

function handle(fn, status = 200) {
  return async (req, res) => {
    try {
      res.status(status).json(await fn(req));
    } catch (err) {
      res.status(err.status || 500).json({ error: err.message, ...(err.code ? { code: err.code } : {}) });
    }
  };
}

export const register = handle((req) => service.register(getDb(), req.body || {}), 201);
export const registerLecturer = handle((req) => service.registerLecturer(getDb(), req.body || {}), 201);
export const login = handle((req) => service.login(getDb(), req.body || {}));
export const me = handle((req) => service.me(getDb(), req.user));

// ---- my profile (any logged-in role)
export const getProfile = handle((req) => profile.getProfile(getDb(), req.user));
export const updateProfile = handle((req) => profile.updateProfile(getDb(), req.user, req.body || {}));
export const setAvatar = handle((req) => profile.setAvatar(getDb(), req.user, req.body ? req.body.image : null));
export const changePassword = handle((req) => profile.changePassword(getDb(), req.user, req.body || {}));
export const recordUsage = handle((req) => profile.recordUsage(getDb(), req.user, req.body ? req.body.seconds : 0));
export const getUsage = handle((req) => profile.getUsage(getDb(), req.user));
