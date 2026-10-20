# Flagged questions from the first pilot: what to check

Pilot of 17 October 2026 (Google Form, 30 questions, 33 submissions, 28 after copy screening).
Percentages are the share of the 28 respondents who chose each option. `*` marks the answer key.

## Read this first: who answered
- 15 of the 28 respondents scored below 10 out of 30. Random guessing gives about 5 out of 30, so about half of the group answered at chance level. They probably had not studied these topics or did not try.
- Without them (13 respondents) the average share correct is 64%, against 40% for all 28. Most "very hard" flags therefore come from who answered, not only from the questions.
- Conclusion for the next round: send the form only to students who have studied the modules, add a first question "Have you studied this topic?", and aim for at least 20 serious respondents.
- `node scripts/itemAnalysis.js --csv responses.csv --min-score 10` leaves out chance-level respondents (with fewer than 15 left, the numbers are indicative only).

## The 12 flagged questions

| Question | What the answers show | Verdict | Action |
|---|---|---|---|
| PQ-project_risk_management-04 (EMV, 60% x 8M and 40% x -3M) | 64% correct (3.6M). The key is right: 4.8M - 1.2M = 3.6M. | Fine. Flagged only because the expected band was Hard. | None. The rule "calculation questions are Hard" is too strict for simple sums, so lower the prior to Medium. |
| PQ-unit_integration_testing-06 (top-down and bottom-up) | Only 10% correct. 39% chose the swapped pair (top-down needs drivers, bottom-up needs stubs). | The key is right (top-down uses stubs, bottom-up uses drivers). A real misconception, and a good distractor. | Check the slide with the lecturer and keep. Teach the pair explicitly. |
| PQ-unit_integration_testing-07 (what unit tests check, select all) | Boundary 42%, invalid 64%, equivalence class 32%, "only happy path" 28% (wrong). | Hard because all three correct options must be chosen. Not wrong. | Keep. Report partial credit for select-all questions. |
| PQ-unit_integration_testing-08 (TDD benefits, select all) | "Avoids over-engineering" chosen by only 17%. "Feedback is delayed" chosen by 35% (wrong). | Check the key. | Confirm on the slide that "avoids over-engineering" is listed as a TDD benefit. If it is not, replace that option. |
| PQ-unit_integration_testing-09 (bottom-up, select all) | "Stubs replace lower-level modules" chosen by 35% (wrong), matches the pair confusion in question 06. | Key matches the explanation. | Keep. Same misconception as question 06. |
| PQ-unit_integration_testing-10 (why integration testing, select all) | "Off-the-shelf components cannot be unit tested" chosen by 39%. | Check the key. | Confirm the slide gives this as a reason. If not, replace it. |
| PQ-ux_testing_heuristics-02 (go or no-go evaluation) | Summative 35%, diagnostic 35%. | "Diagnostic evaluation" may be confusing, because another question describes formative evaluation as "mainly diagnostic". | Check whether the lecture treats "diagnostic" as a type. If not, replace that distractor with a clearly different type. |
| PQ-ux_testing_heuristics-03 (number of evaluators) | Three to five 46%, six to eight 42%. | Key follows the lecture explanation. | Keep. The split suggests students are unsure. |
| PQ-ux_testing_heuristics-05 (RITE) | 39% correct, wrong options spread evenly. | Normal. | None. |
| PQ-ux_testing_heuristics-06 (NOT a heuristic) | 35% correct. 32% chose "Visibility of system status", which is a real heuristic. | Looks like guessing by many respondents. | None. Recheck with serious respondents only. |
| PQ-ux_testing_heuristics-07 (objective UX data, select all) | "A user's opinion" chosen by 35% (wrong). | Hard but fair. | Keep. |
| PQ-ux_testing_heuristics-09 (analytics tools, select all) | "Card sorting boards" chosen by 21% (wrong). | Hard but fair. | Keep. |

## Summary for the supervisor
- No question was found to have a clearly wrong key. Three need a quick check on the lecture slide (08, 10 and UX 02).
- The most useful finding is about the pilot: half of the respondents answered at chance level, and one group of 6 answer sheets was nearly identical. The next round needs a better sample.
