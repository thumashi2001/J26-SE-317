# C1 real question content (from lecture slides)

Status: DRAFT. Written from the lecture slide text only. The group and the lecturers should review it before the final demo.

## Size
| Semester | Modules | Topics | Practice questions | Diagnostic questions stored |
|---|---|---|---|---|
| Y3S1 | SE3070 CSSE, SE3080 SPM, SE3050 UEE, SE3060 Database Systems, SE3040 Application Frameworks | 28 | 280 | 84 |
| Y3S2 | SE3020 Distributed Systems, SE3030 Software Architecture, SEP&QM | 18 | 180 | 54 |

Each topic has 10 practice questions (6 single answer, 4 select all that apply) and 3 diagnostic questions.

## How many questions in each test
- Diagnostic test: 1 question per topic (28 for Y3S1, 18 for Y3S2). The 3 stored questions per topic give variety between students.
- Diagnostic timer: about 43 seconds per question, rounded to half a minute (Y3S1 20:00, Y3S2 13:00). It starts when the student presses Start my test. When it reaches zero the answers given so far are sent, and unanswered questions count as wrong.
- Time per question and tab leaves are saved for every diagnostic answer. A very fast correct answer, or one given after leaving the tab, counts for less of the gain above the start score (start score is 40, a correct answer normally gives 60, a fast one 52, a tab-leave one 50). A very fast wrong answer is marked as a likely guess and lowers the topic's score reliability.
- Practice quiz: 7 questions per topic, 5 minutes.
- Change the diagnostic size with `QUESTIONS_PER_TOPIC` and the pace with `SECONDS_PER_QUESTION` in `diagnosticService.js`.

## Where things are
- `backend/src/modules/c1/data/content/<module>.js`: one file per module (topic key, label, lectures, questions).
- `content/index.js`: joins all modules. `content/helpers.js`: S, M, D helpers. `content/tips.js`: tip texts.
- `scripts/checkContent.js`: checks every question (4 options, no dashes, no Roman numerals, answer position balance, duplicates).
- `scripts/seedContent.js`: loads question_bank and practice_bank. Asks before removing anything.
- `scripts/exportTopicLabels.js`: writes `frontend/src/utils/topicLabels.js` (real topic names on screen).

## Topic keys are shared names
Topic keys are the canonical identifiers other components (C2 to C4) must use. Do not rename a key after teammates start using it.

## Things for the lecturer or group to confirm
- SEP&QM has no official module code on its slides. `SEPQM` is a placeholder.
- AF (SE3040) is filed under Y3S1 (confirmed).
- Missing slide decks: SPM W01, W02, W08, W09 and SEP&QM Lecture 6. Those subjects have no questions yet.
- Slide mistakes found while writing (questions avoid them): DS L13 synchronous-system formula, DS L12 Byzantine replica count, AF L09 weighted score totals, SPM cost-per-point wording, DS (Database) MongoDB update example.
