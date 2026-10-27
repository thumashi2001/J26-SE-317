"""Builds the boxes (nodes) of the answer-specific mind map.

One root node (the question) and one node per concept. A concept node carries the status from Function 1
(demonstrated / partial / not_demonstrated) and the sentence numbers that contain evidence, so the map is derived from
the real analysis and not from hard-coded content.
"""

from app.schemas.analysis import AnswerAnalysisResponse
from app.schemas.mindmap import Node


def generate_node_id(concept: str) -> str:
    """Generate a stable, deterministic node ID based on the concept name."""
    normalized = concept.strip().lower().replace(" ", "_")
    return f"concept_{normalized}"

def generate_root_id(question_id: str) -> str:
    """Generate a stable root ID based on the question."""
    normalized = question_id.strip().lower().replace(" ", "_")
    return f"root_{normalized}"

def build_root_node(question_id: str, question_text: str) -> Node:
    """Create the root node representing the question/topic."""
    return Node(
        node_id=generate_root_id(question_id),
        type="root",
        concept=question_id,
        label=question_text or "Main Topic",
        source="system",
        status=None,
        evidence_sentence_ids=[],
        parent_node_id=None,
        children=[],
        relationship_type=None
    )

def build_concept_nodes(analysis: AnswerAnalysisResponse, expected_concepts: list[str]) -> list[Node]:
    """
    Build nodes for all concepts from the analysis and the expected list.
    Preserves status and evidence sentence IDs from Function 1.
    """
    nodes = []
    processed_concepts = set()

    # Process matched concepts from Function 1 analysis
    for match in analysis.concept_matches:
        concept_lower = match.concept.casefold()
        if concept_lower in processed_concepts:
            continue

        # "student_answer" = the student's words touched this concept; "expected_concept" = it only comes from the rubric.
        source = "student_answer" if match.status in ["demonstrated", "partial"] else "expected_concept"
        nodes.append(Node(
            node_id=generate_node_id(match.concept),
            type="concept",
            concept=match.concept,
            label=match.concept.title(),
            source=source,
            status=match.status,
            evidence_sentence_ids=match.evidence_sentence_ids
        ))
        processed_concepts.add(concept_lower)

    # Process any expected concepts that Function 1 did not explicitly return
    for expected in expected_concepts:
        concept_lower = expected.casefold()
        if concept_lower not in processed_concepts:
            nodes.append(Node(
                node_id=generate_node_id(expected),
                type="concept",
                concept=expected,
                label=expected.title(),
                source="expected_concept",
                status="not_demonstrated",
                evidence_sentence_ids=[]
            ))
            processed_concepts.add(concept_lower)

    return nodes
