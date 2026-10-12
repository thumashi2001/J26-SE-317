# C1: hint button, celebration screen, landing page

## 50/50 hint (practice quiz)
- Only on single-answer questions, once per question. It removes two wrong options.
- The server picks the options (the browser never sees the answer key). Endpoint: `POST /api/v1/c1/practice/hint` with `sessionId` and `questionId`.
- The answer is saved with `hint_used: true`. The twin update gives a correct answer with a hint about half the normal gain.
- Topic insights now include `hintsUsed`, `quizAnswers`, `timeSpentSec` and `practiceSessions` per topic, and `totals` for the whole student.
- The topic page shows time spent answering and hints used.

## Celebration screen
- After a finished quiz with 5 of 7 or better (70 percent), fireworks play for about 5 seconds. A perfect score also gets confetti and a trophy banner.
- It does not block clicks, and it is skipped when the device asks for reduced motion.

## Landing page (before login)
- `/` shows the landing page to visitors. After login, `/` sends each person to their own home page as before.
- Top bar: logo, links, Log in, Register. Sections: hero, how it works, modules (real modules and topics from the question content), features, call to action, footer.
- The cards marked Example in the hero are illustrations, not real student data.
- SLIIT logo: put the official file at `frontend/public/sliit-logo.png`. Until then the page shows the text SLIIT.
- The footer says this is a student research project and not an official SLIIT service.
