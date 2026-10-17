# Messages to send: lecturer review and classmate pilot

Copy and paste. Change the names and dates.

## 1. Message to a lecturer or senior student (expert review)

Hi [name],

I am building the practice and diagnostic questions for our IT4010 research project (an adaptive learning app). The panel asked us to show a research method for how the questions are made, so I would like your help to check a small sample.

I attached a sheet with 40 multiple-choice questions taken from our lecture slides, about 5 per module. For each question please answer four things: (1) does it match the lecture content, (2) is the marked answer exactly right, (3) are the wrong options believable, (4) is the difficulty fair (Easy, Medium or Hard). Short comments are enough.

It should take about 30 to 40 minutes. If you can send it back by [date], I can include your feedback in my supervisor meeting on [date]. Thank you very much.

[your name]

Attach: Question-review-sheet.xlsx (the Excel version of docs/c1-review-sheet.csv).

## 2. Message to classmates (pilot)

Hi everyone,

I need 30 minutes of your help to test the questions of my research component. It is a Google Form with 30 multiple-choice questions on 3 topics: Project Risk Management, Unit, API and Integration Testing, and Testing and Analysis of UX.

Link: [form link]

Please answer on your own, without notes or searching, because the answers are only useful if they show what you really know. There is no name or email in the form, and the results are used only to improve the questions. Please submit only once, and by [date and time]. Thank you!

## Notes for you
- How to make the form: see docs/pilot/README.md (10 minutes, no coding).
- After the deadline: download the responses as CSV and run `node scripts\itemAnalysis.js --csv responses.csv`.
- A question needs at least 15 answers before its numbers count, so aim for 20 or more classmates.
