# How the Component 1 questions were made, checked and improved

Status: DRAFT for the supervisor meeting. Reviewer sign-off and the pilot results are still to be added (sections 5 and 6).

This page answers the panel comment: "In the individual component, when generating the questions there should be a research method involved."
The questions are written from the lecture slides, then described, reviewed and tested with a fixed method. Each step has a script or a file in the repository, so it can be repeated.

## 1. Source and plan (blueprint)
- Source: the lecture slide text of 8 modules (SE3070, SE3080, SE3050, SE3060, SE3040, SE3020, SE3030, SEP&QM). Files: `backend/src/modules/c1/data/content/<module>.js`.
- Size: 46 topics. Every topic has 10 practice questions (6 single answer, 4 select all that apply) and 3 diagnostic questions. Total 598.
- Every question is tagged with a type by its author: concept, scenario, compare, not, order, calc or multi.
- Plan: `node scripts/questionBlueprint.js` builds the blueprint `docs/c1-question-blueprint.csv` (topic, type, thinking level, expected difficulty for every question) and checks that each topic offers a mix of levels.

## 2. Thinking level and expected difficulty (rules)
Thinking level follows the revised Bloom taxonomy (Anderson and Krathwohl, 2001), using the four levels that suit multiple-choice questions.

| Question type tag | Thinking level |
|---|---|
| concept, multi | Remember, or Understand if the stem asks why, purpose, role, how, benefit |
| order | Understand |
| scenario, calc | Apply |
| compare, not | Analyse |

"Select all that apply" is a format, not a thinking level, so it is classified by what the stem asks.

Expected difficulty before any student answers (a prior): Easy for Remember, Medium for Understand, Apply and Analyse, Hard for select all that apply and for calculation questions.
The rules are in `backend/src/modules/c1/data/questionMeta.js`. They are a starting point, and sections 5 and 6 test them.

Current spread (598 questions): Remember 51%, Understand 9%, Apply 25%, Analyse 16%. Difficulty: Easy 124, Medium 248, Hard 226.
Finding: the bank leans towards recall, and "Understand" questions are few. This is listed as an improvement for the next version (add more why and how questions).

## 3. Writing rules
Based on the item writing guidelines of Haladyna, Downing and Rodriguez (2002).
- One idea per question, four options, one clearly best answer (or a clear set for select all).
- No "all of the above" or "none of the above". No Roman numeral combination options.
- Options are all different, and the correct answer is spread across the four positions.
- Every question has an explanation of why the answer is right.
`node scripts/checkContent.js` checks these rules automatically for every question.

Finding from this check: in some modules the correct option was the longest one more often than chance (25%), which is a hint students can use without knowing the topic.
Fix applied: 26 questions had their options reworded (the correct option shortened, or the wrong options made as detailed). No question text, correct answer or explanation was changed.

| Module | Correct option was the longest (before) | After |
|---|---|---|
| SE3020 | 48% | 26% |
| SE3050 | 46% | 31% |
| SE3080 | 38% | 24% |

(SE3030 is the opposite case at 6%, and the other modules were already between 20% and 31%.)

## 4. Diagnostic design
- One question per topic, the question is picked from 3 stored versions.
- Time per question, tab leaves and very fast wrong answers are recorded. A very fast correct answer or a tab leave counts for less, and a very fast wrong answer is marked as a likely guess.
- Details: `docs/c1-real-content.md`.

## 5. Expert review
- `node scripts/questionBlueprint.js` also writes `docs/c1-review-sheet.csv`: 40 questions (5 per module, spread across thinking levels).
- A lecturer or a senior student answers four checks for each: matches the slides, exactly the right answer, believable wrong options, fair difficulty.
- Results and the changes made go here: **to be filled in** (reviewer, date, number reviewed, number changed).

## 6. Testing the questions on real answers (item analysis)
Method from classical test theory (Ebel and Frisbie, 1991). Code: `services/itemAnalysis.js`, run with `node scripts/itemAnalysis.js`.
For each question the script reports:
- difficulty index p: the share of students who answered correctly (first attempt only, no hint),
- discrimination: how well the question separates strong students from weak ones (correlation with the score on the other questions),
- calibrated difficulty: p pulled towards the expected value of the question's prior band when there are few answers (weight 10),
- flags: too easy (p above 0.90), very hard (p below 0.20), weak or negative discrimination (negative usually means the answer key is wrong), expected band differs from observed band.
A question is only judged with at least 15 first-attempt answers.

Pilot plan (Google Form): 30 questions from 3 topics (the 10 practice questions of each) are put into one Google Form, and about 20 classmates answer it once, on their own, in about 30 minutes. The form has no name or email, so the data is anonymous.
`node scripts/pilotForm.js` writes `docs/pilot/create-form.gs`, which builds the form automatically in Google Forms, and `docs/pilot/pilot-key.json`, the answer key.
After the responses are in, download the response sheet as CSV and run `node scripts/itemAnalysis.js --csv responses.csv`. This needs no database. The question numbers match the app's question ids, so the result is comparable.
With about 20 respondents every pilot question has about 20 answers, above the minimum of 15. Because every student answers all 30 questions, discrimination is calculated on a full set of answers.
Data quality screening: the analysis compares the chosen options of every pair of respondents. If two answer sheets are identical on at least 90% of the questions (wrong answers included), they are treated as copies of one another, and only the earliest sheet of each group is kept (`--no-screen` turns this off). The excluded sheets are reported by sheet row number, never by name.

Preliminary results (pilot of 17 October 2026, Google Form, 30 questions on Project Risk Management, Unit, API and Integration Testing, and Testing and Analysis of UX):
- 33 submissions. 6 of them formed one group of near-identical sheets, so 5 copies were left out and 28 respondents were analysed.
- Without screening, 3 questions were flagged and the mean discrimination was 0.65. With screening, 13 questions were flagged and the mean discrimination was 0.55. The copied sheets made the questions look easier than they are, which is why the screening step matters.
- 80% of the expected difficulty bands matched the observed ones.
- Several select-all questions in the testing topics were very hard (only 7% to 18% answered them fully right) but separated strong from weak students well (discrimination 0.45 to 0.73). They are hard, not wrong, and are candidates for review and, for the twin, partial credit.
- Next: review the 13 flagged questions with the lecturer, fix them, and repeat with a second group.

Final results: **to be filled in** after the review.

The script was tested on a small hand-made class with known answers (`node scripts/checkItemAnalysis.js`) and run end to end on simulated answers (`--demo`, a pipeline test, not evidence).

## 7. How this connects to the twin
The calibrated difficulty will be used as an input to the prediction model (a harder question lowers the chance of a correct answer). This is the next step after the pilot.

## References
- Anderson, L. W. and Krathwohl, D. R. (eds.) (2001). A Taxonomy for Learning, Teaching, and Assessing: A Revision of Bloom's Taxonomy of Educational Objectives. Longman.
- Haladyna, T. M., Downing, S. M. and Rodriguez, M. C. (2002). A review of multiple-choice item-writing guidelines for classroom assessment. Applied Measurement in Education, 15(3), 309-334.
- Ebel, R. L. and Frisbie, D. A. (1991). Essentials of Educational Measurement (5th ed.). Prentice Hall.
