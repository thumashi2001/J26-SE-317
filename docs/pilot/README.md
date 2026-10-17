# Pilot with Google Forms (no hosting needed)

## A. Make the form (about 10 minutes)
1. Open https://script.google.com and sign in with a Google account. Click New project.
2. Delete the code in the editor. Open `create-form.gs` from this folder, copy everything, and paste it into the editor.
3. Click the Run button (function `createPilotForm`). Google asks for permission the first time: Review permissions, choose your account, Advanced, Go to project (unsafe), Allow. The warning is normal for your own script.
4. Open View > Logs (or Execution log). Copy the line "SHARE THIS LINK WITH CLASSMATES". That is the form link for the message.
5. Open the form yourself, answer it once to test, then delete that test row from the response sheet before the real run.

## B. Collect answers
Send the message to classmates (see `docs/c1-review-and-pilot-messages.md`). Ask for about 20 or more answers.

## C. Run the analysis
1. Open the response sheet (link in the log: "Responses sheet"). File > Download > Comma Separated Values (.csv). Save it as `responses.csv` in `D:\J26-SE-317\backend`.
2. In a terminal:
   cd /d D:\J26-SE-317\backend
   node scripts\itemAnalysis.js --csv responses.csv
3. The result is `docs/pilot/c1-item-analysis-pilot.csv`: for each question the difficulty, discrimination and flags. Do not commit `responses.csv` if it has anything personal (the form collects nothing personal, but check).

## Change the topics
   node scripts\pilotForm.js topic_key_1 topic_key_2 topic_key_3
Topic keys are in `backend/src/modules/c1/data/content/<module>.js`. Run it again, and paste the new `create-form.gs`.
