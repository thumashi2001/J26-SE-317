from fastapi import APIRouter, HTTPException

from app.schemas.marking import MarkingRequest, MarkingResponse
from services.marking.marking_engine import mark_answer
from services.marking.rubric_validator import RubricValidationError


router = APIRouter(prefix="/marking", tags=["marking"])


@router.post("/evaluate", response_model=MarkingResponse)
def evaluate_marking(request: MarkingRequest) -> MarkingResponse:
    """Return a rubric-controlled deterministic proposed marking result."""
    try:
        return mark_answer(request)
    except RubricValidationError as error:
        raise HTTPException(status_code=422, detail=error.errors) from error
