
import os
import re
import secrets
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

from services.syllabus_topic_review_queue import (
    SyllabusTopicReviewQueue,
)
from services.syllabus_topic_review_repository import (
    SyllabusTopicReviewRepository,
)


app = FastAPI(
    title="C2 Exam Intelligence API",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


# Supported Year 3 Software Engineering modules
MODULE_KEYS = [
    "application_frameworks",
    "case_studies_software_engineering",
    "database_systems",
    "distributed_systems",
    "software_architecture",
    "software_engineering_process_quality_management",
    "software_project_management",
    "user_experience_engineering",
]


# Existing syllabus review repository and queue
repository = SyllabusTopicReviewRepository()
queue = SyllabusTopicReviewQueue(repository=repository)


class ReviewDecisionRequest(BaseModel):
    module_key: str
    candidate_id: str
    decision: str
    review_notes: str = Field(default="", max_length=2000)
    reviewer_id: str


def require_internal_token(x_c2_internal_token: str | None):
    expected = os.environ.get("C2_INTERNAL_TOKEN")

    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Internal API token is not configured",
        )

    if not x_c2_internal_token or not secrets.compare_digest(
        x_c2_internal_token,
        expected,
    ):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
        )


def validate_module(module_key):
    if module_key not in MODULE_KEYS:
        raise HTTPException(
            status_code=400,
            detail="Invalid module",
        )


# --------------------------------------------------
# Health Check
# --------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "c2",
    }


# --------------------------------------------------
# List Supported Modules
# --------------------------------------------------

@app.get("/modules")
def list_modules(
    x_c2_internal_token: str | None = Header(default=None),
):
    require_internal_token(x_c2_internal_token)

    return {
        "modules": MODULE_KEYS,
    }


# --------------------------------------------------
# Get Syllabus Review Queue
# --------------------------------------------------

@app.get("/reviews/{module_key}")
def get_reviews(
    module_key: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    include_reviewed: bool = False,
    x_c2_internal_token: str | None = Header(default=None),
):
    require_internal_token(x_c2_internal_token)
    validate_module(module_key)

    try:
        return queue.get_queue(
            module_key,
            page=page,
            page_size=page_size,
            include_reviewed=include_reviewed,
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Review report not found",
        )

    except ValueError:
        raise HTTPException(
            status_code=409,
            detail="Review data is invalid or inconsistent",
        )


# --------------------------------------------------
# Get Excluded Syllabus Candidates
# --------------------------------------------------

@app.get("/reviews/{module_key}/excluded")
def get_excluded(
    module_key: str,
    x_c2_internal_token: str | None = Header(default=None),
):
    require_internal_token(x_c2_internal_token)
    validate_module(module_key)

    try:
        return queue.get_excluded_candidates(module_key)

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Review report not found",
        )


# --------------------------------------------------
# Lecturer Approval / Rejection
# --------------------------------------------------

@app.post("/reviews/decision")
def save_decision(
    request: ReviewDecisionRequest,
    x_c2_internal_token: str | None = Header(default=None),
):
    # Internal service authentication
    require_internal_token(x_c2_internal_token)

    # Validate selected module
    validate_module(request.module_key)

    # Validate review decision
    if request.decision not in ("approved", "rejected"):
        raise HTTPException(
            status_code=400,
            detail="Decision must be approved or rejected",
        )

    # Rejected topics must include a meaningful reason
    if (
        request.decision == "rejected"
        and not request.review_notes.strip()
    ):
        raise HTTPException(
            status_code=400,
            detail="A rejection reason is required",
        )

    # Validate reviewer identity
    if not request.reviewer_id.strip():
        raise HTTPException(
            status_code=400,
            detail="Reviewer ID is required",
        )

    if not re.fullmatch(
        r"[a-zA-Z0-9:_-]+",
        request.reviewer_id,
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid reviewer ID",
        )

    # Load the original extracted syllabus report
    try:
        report = queue._load_report(request.module_key)

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Review report not found",
        )

    # Find the candidate in the original report
    matched = None

    for candidate in report["review_candidates"]:
        candidate_id = queue.candidate_id(
            request.module_key,
            candidate["candidate_name"],
        )

        if candidate_id == request.candidate_id:
            matched = candidate
            break

    if matched is None:
        raise HTTPException(
            status_code=404,
            detail="Candidate not found",
        )

    # Construct the review record
    record = {
        "candidate_id": request.candidate_id,
        "module_key": request.module_key,
        "candidate_name": matched["candidate_name"],
        "review_decision": request.decision,
        "verification_status": (
            "verified"
            if request.decision == "approved"
            else "rejected"
        ),
        "reviewer_id": request.reviewer_id,
        "reviewed_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "review_notes": request.review_notes.strip(),
        "sources": matched["sources"],
    }

    # Persist validated review decision
    try:
        saved = repository.save_review(record)

    except ValueError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        )

    return {
        "success": True,
        "review": saved,
    }
