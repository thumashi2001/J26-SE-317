"""HTTP endpoint for Function 2 (rubric-aware marking). Used by the lecturer-only raw Node endpoint
`POST /api/v1/c3/marking`; live student marking goes through /c3/assess instead."""
from fastapi import APIRouter, HTTPException

from app.schemas.marking import MarkingRequest, MarkingResponse
from services.marking.marking_engine import mark_answer
from services.marking.rubric_validator import RubricValidationError

# All routes in this file are served under /marking.
router = APIRouter(prefix="/marking", tags=["marking"])


@router.post("/evaluate", response_model=MarkingResponse)
def evaluate_marking(request: MarkingRequest) -> MarkingResponse:
    """Return a rubric-controlled deterministic proposed marking result."""
    try:
        return mark_answer(request)
    except RubricValidationError as error:
        # A rubric that contradicts itself (for example marks that do not add up) is a client error, not a crash.
        raise HTTPException(status_code=422, detail=error.errors) from error
