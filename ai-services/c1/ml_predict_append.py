# --- paste: imports (top of app/main.py, with the other imports) ---
from typing import List
from ml.service import predict_correct


# --- paste: model + endpoint (bottom of app/main.py) ---
class PredictEvent(BaseModel):
    day: float                    # days since the student's first answer
    topic: str
    module: str = "OTHER"
    source: str = "quiz"
    session_id: str = ""
    q_in_session: int = 0
    question_type: str = "single"
    correct: int = 0
    time_sec: float = 30
    hint_used: int = 0
    tab_leaves: int = 0


class PredictRequest(BaseModel):
    as_of_day: float
    events: List[PredictEvent]


@app.post("/twin/predict-correct")
def twin_predict_correct(req: PredictRequest):
    """Trained gradient boosting model: chance of a correct answer on each topic the student has practised."""
    evs = [e.model_dump() if hasattr(e, "model_dump") else e.dict() for e in req.events]
    return {"model": "gradient_boosting", "topics": predict_correct(evs, req.as_of_day)}
