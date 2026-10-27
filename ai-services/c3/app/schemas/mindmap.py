"""Data shapes for Function 4: the answer-specific concept mind map.

A mind map here is a small graph: one root node (the question) and one node per concept, joined by relationships.
In the current implementation every relationship is a structural root -> concept link ("child"); no semantic
concept-to-concept relationship is generated.
"""

from pydantic import BaseModel

from app.schemas.analysis import AnswerAnalysisRequest


class MindMapRequest(BaseModel):
    """Input for the mind map: the same analysis request used by Function 1."""
    analysis_request: AnswerAnalysisRequest


class Node(BaseModel):
    """A box in the map: the question (root) or one concept with its status and evidence sentences."""

    node_id: str
    type: str
    concept: str
    label: str
    source: str
    status: str | None = None                       # demonstrated / partial / missing (concept nodes only)
    evidence_sentence_ids: list[int] = []
    parent_node_id: str | None = None
    children: list[str] = []
    relationship_type: str | None = None


class Relationship(BaseModel):
    """A line between two nodes. `evidence` explains why the line exists."""

    relationship_id: str
    source_node_id: str
    target_node_id: str
    relationship_type: str
    evidence: str | None = None


class MindMapSummary(BaseModel):
    """Counts shown above the map: total nodes and how many concepts are demonstrated, partial or missing."""
    total_nodes: int
    demonstrated_count: int
    partial_count: int
    missing_count: int


class MindMapResponse(BaseModel):
    """Function 4 output: a root node, concept nodes, the links between them, and the summary counts."""
    question_id: str
    root_node_id: str
    title: str
    nodes: list[Node]
    relationships: list[Relationship]
    summary: MindMapSummary
    warnings: list[str]
    generation_version: str
