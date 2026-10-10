# C1 behaviour analysis (day 5)

Answer behaviour is read from quiz answers only (answers with a question id and a measured time).

## Personal baseline
Median answer time of the student's older quiz answers (the newest 7 are left out so a new habit cannot hide itself). It needs 10 answers. Before that, only the fixed limits are used.

## Answer types
| Type | Rule |
|---|---|
| fast | under 8 s, or under 35% of the baseline |
| slow | over 120 s, or over 2.5 x the baseline |
| likely guess | a fast answer that is also wrong |

## Overall pattern (latest 10 quiz answers in the last 14 days, at least 5 answers)
| Pattern | Rule |
|---|---|
| Guessing | 25% or more are likely guesses |
| Rushing | 40% or more are fast |
| Struggling | 40% or more are slow and accuracy is under 50% |
| Careful | 40% or more are slow and accuracy is 50% or more |
| Steady | none of the above |

## Knowledge read per topic (speed and correctness together)
Uses the latest 10 answers on a topic (at least 4). The student's typical time is the median of all quiz answers, never below 15 s.
quick = under 8 s or under 60% of typical. slow = over 150% of typical.

| | Quick | Slower than your average |
|---|---|---|
| Mostly right (75% or more) | Strong and quick | Knows it, needs speed |
| Mostly wrong (under 50%) | Guessing or careless | Needs revision |

"Quick" or "slow" means 40% or more of the answers. Anything in between is "Getting there".

## Twin weight
A correct answer raises the topic score by `normal gain x weight`.
weight = 1, x0.5 if the student left the tab, x0.6 if the answer was fast (minimum 0.3).
Wrong answers are never reduced. The weight is stored on the learning event and shown to the student.
The same 8 s limit lowers answer reliability in the score reliability (confidence) calculation.

## Alerts
- `sudden_drop` (Medium): the topic score is 15 or more points below the highest of its last 3 history points in 14 days.
- `guessing` (Medium): 4 or more of the latest 7 quiz answers are likely guesses.
- The same alert type is not raised again within 3 days (per topic for sudden drops).

## API
`GET /api/v1/c1/behaviour/:studentId` returns pattern, headline, why, advice, median seconds, fast, slow, guesses, accuracy and `topics` (the knowledge read per topic).
