# C1 real question content (from lecture slides)

Status: DRAFT. Written from the lecture slide text only. The group and the lecturers should review it before the final demo.

## Size
| Semester | Modules | Topics | Practice questions | Diagnostic questions |
|---|---|---|---|---|
| Y3S1 | SE3070 CSSE, SE3080 SPM, SE3050 UEE, SE3060 DS | 22 | 220 | 66 |
| Y3S2 | SE3020 Distributed Systems, SE3030 Software Architecture, SEP&QM, SE3040 AF | 24 | 240 | 72 |

Each topic has 10 practice questions (6 single answer, 4 select all that apply) and 3 diagnostic questions.

## How many questions in each test
- Diagnostic test: 1 question per topic (22 for Y3S1, 24 for Y3S2). The 3 stored questions per topic give variety between students.
- Practice quiz: 7 questions per topic, 5 minutes.
- Change the diagnostic size with `QUESTIONS_PER_TOPIC` in `diagnosticService.js`.

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
- AF (SE3040) is filed under Y3S2. The source folder said Y3S1.
- Missing slide decks: SPM W01, W02, W08, W09 and SEP&QM Lecture 6. Those subjects have no questions yet.
- Slide mistakes found while writing (questions avoid them): DS L13 synchronous-system formula, DS L12 Byzantine replica count, AF L09 weighted score totals, SPM cost-per-point wording, DS (Database) MongoDB update example.
