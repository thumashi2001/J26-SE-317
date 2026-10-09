# C1: Engagement index, confidence and estimated score

These three values explain the twin to the student. They are computed on the server from stored learning events,
and every value comes with a plain sentence that says why.

Code: `backend/src/modules/c1/services/insightsService.js`. Endpoint: `GET /api/v1/c1/insights/:studentId`.

## 1. Estimated score now

The stored topic score belongs to the day of the last answer. The estimate applies the forgetting rule from then until now.
The number comes from the Python AI service (`POST /twin/forecast` with 1 day ahead and no practice), so it uses the same
forgetting rule as the twin and the "What if I study?" forecast. If the AI service is down, the page shows the stored score.

## 2. Engagement index (0 to 100)

Looks at practice quizzes in the last 14 days.

| Part | Weight | Full marks when |
|---|---|---|
| Regularity | 35% | quiz answers on 5 or more different days |
| Recency | 30% | last answer 0 to 2 days ago, fading to 0 at 14 days |
| Volume | 20% | 30 or more answers |
| Finishing | 15% | every quiz that was started was finished |

Labels: below 30 Low, 30 to 64 Steady, 65 and above High. No quiz answer yet: Not started.

## 3. Answer reliability and confidence

Each answer has a reliability from 0 to 1.

- A normal answer counts 1.
- If the student left the quiz tab for 2 seconds or more during the question, it counts half.
- If a quiz answer took under 3 seconds, it counts 0.6 of its value (it may be a guess).
- Both together give 0.3.

Confidence in a topic score:

    evidence   = sum of reliability over the diagnostic and quiz answers on that topic
    confidence = (1 - e^(-evidence / 8)) x (0.6 + 0.4 x e^(-days since practice / 30))

Labels: below 40 Low, 40 to 69 Medium, 70 and above High.

Reliability does not change the score update yet. It only lowers the confidence label. Using it to weight the twin update
is planned for the behaviour analysis step.

## Honesty notes in the quiz

The quiz tells the student that leaving the tab is noted and that those answers count a little less. Copying and
right-click are switched off on the question area. These are light deterrents, not security: the aim is to detect
unreliable answers and show lower confidence, not to block students.
