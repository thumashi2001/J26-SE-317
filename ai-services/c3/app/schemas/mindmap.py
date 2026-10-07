from pydantic import BaseModel
from typing import Optional

from app.schemas.analysis import AnswerAnalysisRequest

class MindMapRequest(BaseModel):
    analysis_request: AnswerAnalysisRequest


class Node(BaseModel):
    node_id: str
    type: str
    concept: str
    label: str
    source: str
    status: Optional[str] = None
    evidence_sentence_ids: list[int] = []
    parent_node_id: Optional[str] = None
    children: list[str] = []
    relationship_type: Optional[str] = None


class Relationship(BaseModel):
    relationship_id: str
    source_node_id: str
    target_node_id: str
    relationship_type: str
    evidence: Optional[str] = None


class MindMapSummary(BaseModel):
    total_nodes: int
    demonstrated_count: int
    partial_count: int
    missing_count: int


class MindMapResponse(BaseModel):
    question_id: str
    root_node_id: str
    title: str
    nodes: list[Node]
    relationships: list[Relationship]
    summary: MindMapSummary
    warnings: list[str]
    generation_version: str
