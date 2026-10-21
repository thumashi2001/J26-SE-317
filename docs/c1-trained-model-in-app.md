# Trained model in the app (Component 1)

Where it is used: the topic page shows "Chance you answer the next question correctly".

Flow: topic page -> `GET /api/v1/c1/predict/:studentId` (Node, predictionService.js)
-> `POST /twin/predict-correct` (Python AI service, ml/service.py)
-> trained gradient boosting model (`ai-services/c1/ml/models/gbm_next_answer.joblib`).

1. Node reads the student's logged quiz answers and turns them into the model's input (day, topic, module, correct, time, hint, tab leaves).
2. Python builds the same 22 features used in training (`ml/features.py`) and asks the model for each practised topic.
3. Topics with no practice answers get no prediction (no history, no honest number).

Limits to state in the viva: trained on simulated students (AUC 0.657 against 0.60 for the rule-based twin); the number is a guide, not the score.

Setup: paste the two blocks of `ai-services/c1/ml_predict_append.py` into `app/main.py`, install `pandas scikit-learn joblib` for the AI service, restart both services.
Check: `node backend/scripts/checkPrediction.js`.
