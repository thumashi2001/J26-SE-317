# Shared UI for all four components

Everything here is common to the whole web app. Reuse it, do not copy it.

## Colours
Change colours only through the tokens in `frontend/src/index.css` (`--primary`, `--weak`, `--fair`, `--strong`, `--paper`, `--panel`, `--line`, `--text`, `--muted` and the soft/ink pairs). Dark mode is the `:root[data-theme='dark']` block. Never hard-code a hex colour in a component CSS file.

## Layout and header
- `components/Layout.jsx` is the page frame: sidebar (logo, student card, menu, theme, log out) and the `Topbar`.
- `components/Topbar.jsx` is the header on every page: area name, today's usage chip and the profile icon that opens `/profile`. Pages only render inside `<Outlet />`, so a new page gets the header for free.
- To add a page for your component, add a route under the existing role area in `App.jsx` and a menu item. Do not build your own header.

## My profile (`/profile`, student, lecturer and admin)
`pages/ProfilePage.jsx`. Name and email can be edited, the ID and semester cannot. Picture upload (shrunk to 192x192 in the browser), change password, daily usage ring with countdown to the 30 minute goal, 7 day bars, and for students the knowledge level in stars.

## Small components (`components/ui/`)
- `<Avatar name src size ring />` round picture with the animated ring. Falls back to initials.
- `<StarRating value={3.5} size={28} label="..." />` 0 to 5 in half steps, read only.
- `useUsage(enabled)` from `hooks/useUsage.js` sends a ping every 30 seconds while the tab is visible and returns `{ usage, todaySeconds }`.
- Use `const { profile } = useAuth()` to get the picture and name anywhere.

## API
Auth routes (all need a token): `GET/PATCH /auth/profile`, `PUT /auth/profile/avatar {image}`, `POST /auth/change-password`, `POST/GET /auth/usage`.
Component 1: `GET /c1/level/:studentId` returns `{score, stars, label, topics, practised, strongest, weakest, nextLevelAt}`. Stars are the average decayed topic score / 20, rounded to half stars. If your component changes mastery, the stars follow automatically.

## Auth pages
`components/AuthShell.jsx` plus `pages/auth.css` frame the login and register pages. Keep them as they are.
