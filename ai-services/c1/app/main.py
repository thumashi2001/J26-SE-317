"""FastAPI service for Component 1 (Cognitive Digital Twin).
Run from ai-services/c1:   uvicorn app.main:app --reload --port 8001
Interactive docs:           http://127.0.0.1:8001/docs
"""
from typing import List
from fastapi import FastAPI
from pydantic import BaseModel

from services.mastery.calculator import score_diagnostic, update_score
from services.forgetting.decay import apply_decay
from services.risk.predictor import predict_risk

app = FastAPI(title="C1 Cognitive Digital Twin - AI service")


class DiagnosticAnswer(BaseModel):
    topic: str
    correct: bool


class DiagnosticRequest(BaseModel):
    student_id: str
    answers: List[DiagnosticAnswer]


class EventRequest(BaseModel):
    current_score: float          # 0-100, the topic's stored score
    correct: bool
    hint_used: bool = False
    days_since_practice: float = 0
    practice_sessions: int = 0


class RiskEvent(BaseModel):
    day: int
    topic: str
    correct: bool
    hint_used: bool = False
    time_sec: float = 30


class RiskRequest(BaseModel):
    student_id: str
    as_of_day: int
    events: List[RiskEvent]


@app.get("/health")
def health():
    return {"status": "ok", "service": "c1-ai"}


@app.post("/diagnostic/score")
def diagnostic_score(req: DiagnosticRequest):
    return {"student_id": req.student_id, "mastery": score_diagnostic([a.model_dump() for a in req.answers])}


@app.post("/twin/apply-event")
def apply_event(req: EventRequest):
    decayed = apply_decay(req.current_score, req.days_since_practice, req.practice_sessions)
    updated = update_score(decayed, req.correct, req.hint_used)
    return {"score_before": req.current_score, "after_forgetting": decayed, "score_after": updated}


@app.post("/risk/predict")
def risk_predict(req: RiskRequest):
    out = predict_risk([e.model_dump() for e in req.events], req.as_of_day)
    return {"student_id": req.student_id, **out}# --- paste: imports (top of app/main.py, with the other imports) ---
from services.forecast.simulator import forecast


# --- paste: model + endpoint (bottom of app/main.py) ---
class ForecastRequest(BaseModel):
    current_score: float          # 0-100, the topic's stored score
    days_since_practice: float = 0
    practice_sessions: int = 0
    correct: int = 0              # answers correct so far on this topic
    answered: int = 0             # answers given so far on this topic
    days_ahead: int = 21          # how many days until the exam
    sessions_per_week: int = 3    # the "what if" plan


@app.post("/twin/forecast")
def twin_forecast(req: ForecastRequest):
    return forecast(
        req.current_score,
        req.days_since_practice,
        req.practice_sessions,
        req.correct,
        req.answered,
        req.days_ahead,
        req.sessions_per_week,
    )
