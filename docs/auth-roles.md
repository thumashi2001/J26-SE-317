# Roles and access (shared auth)

## Who can log in
| Role | ID format | How the account is made | Lands on |
|---|---|---|---|
| Student | `IT` + 8 numbers | Registers on the website, active at once | `/c1/diagnostic` first time, then `/c1/dashboard` |
| Lecturer | `SLIITLEC` + 3 numbers (11 characters) | Registers on the website, status **pending** until the admin approves | `/lecturer` |
| Admin | `SLIITADMIN` + 0 to 9 numbers | Created only by `node scripts/seedAdmin.js` from `backend/.env` (never registered on the site) | `/admin` |

Lecturers and the admin are stored in the `staff` collection. Students stay in `students`.
A lecturer whose status is `pending` or `rejected` cannot log in. Student tokens last 7 days, lecturer and admin tokens 12 hours.

## Admin account (one time)
1. In `backend/.env` set `ADMIN_ID`, `ADMIN_NAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` (10+ characters).
2. From the `backend` folder run `node scripts/seedAdmin.js`.
3. Log in on the normal login page. Running the script again resets the password to the one in `.env`.

## Adding your pages (teammates)
**Frontend**
1. Build your page under `frontend/src/pages/<your folder>/`.
2. Add a `<Route>` for it in `frontend/src/App.jsx` inside the area it belongs to (student, lecturer or admin).
3. Add one line to the matching list in `frontend/src/config/menus.js` so it shows in the side menu.
   Admin overview cards: `ADMIN_SECTIONS`. Lecturer overview cards: `LECTURER_SECTIONS`.

**Backend**
- Lecturer-only route: `router.get('/x', requireRole('lecturer'), handler)`
- Admin-only route: `router.get('/x', requireRole('admin'), handler)`
- Student data: use `resolveStudentId(req, req.params.studentId)`. Students get their own ID, lecturers must name a student, admins are refused.
- Admin-only APIs for your component can go in `backend/src/modules/admin/routes/index.js` (the router already requires an admin token).

## Architecture Decision Log entry
**Decision:** Three roles (student, lecturer, admin) share one login page and one JWT (HS256, `AUTH_SECRET`). Lecturers register and wait for admin approval. The admin account is created by a seed script from environment variables and cannot be registered through the website. Routes are protected on the server with `requireRole` and in the browser with `RoleRoute`. Each role has its own layout and menu (`config/menus.js`) so every component adds pages without changing the auth code.
**Why:** The master spec makes auth a shared responsibility. Approval keeps unknown people out of lecturer tools. Short staff tokens limit the time a removed lecturer keeps access.
