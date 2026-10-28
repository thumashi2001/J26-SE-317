"""Function 4: assemble the answer-specific concept mind map from the answer analysis.

Lines: structural root->concept links plus "co_mentioned" links between concepts written in the same sentence.

In the live flow the orchestrator calls build_mindmap_from_analysis() with the analysis it already computed;
generate_mindmap() is the version behind the stand-alone /mindmap/generate endpoint (it analyses the answer itself).
Node/Express stores the resulting map inside the submission result in MongoDB; it is not stored in Neo4j.
"""
from app.schemas.analysis import AnswerAnalysisResponse
from app.schemas.mindmap import MindMapRequest, MindMapResponse, MindMapSummary
from services.mindmap.node_builder import build_concept_nodes, build_root_node
from services.mindmap.relationship_builder import build_baseline_relationships, build_cooccurrence_relationships
from services.semantic.analyzer import analyze_answer

GENERATION_VERSION = "baseline-v1"


def build_mindmap_from_analysis(
    question_id: str,
    question_text: str | None,
    analysis: AnswerAnalysisResponse,
    expected_concepts: list[str],
) -> MindMapResponse:
    """Root node + one node per concept + structural root->concept links + a small summary."""
    root_node = build_root_node(
        question_id=question_id,
        question_text=question_text,
    )
    concept_nodes = build_concept_nodes(analysis, expected_concepts)
    relationships = build_baseline_relationships(root_node, concept_nodes)
    # Evidence-based concept-to-concept lines (same-sentence co-occurrence); never invented semantic relations.
    relationships += build_cooccurrence_relationships(concept_nodes, [item.text for item in analysis.sentences])
    all_nodes = [root_node] + concept_nodes

    # Counts shown in the summary and used for the warnings below.
    demonstrated = sum(1 for n in concept_nodes if n.status == "demonstrated")
    partial = sum(1 for n in concept_nodes if n.status == "partial")
    missing = sum(1 for n in concept_nodes if n.status == "not_demonstrated")

    summary = MindMapSummary(
        total_nodes=len(all_nodes),
        demonstrated_count=demonstrated,
        partial_count=partial,
        missing_count=missing,
    )

    warnings = []
    if missing > 0:
        warnings.append(f"Mind map contains {missing} missing expected concept(s).")
    if demonstrated == 0 and partial == 0:
        warnings.append("No student evidence was detected for expected concepts.")

    return MindMapResponse(
        question_id=question_id,
        root_node_id=root_node.node_id,
        title=f"Concept Map: {question_id}",
        nodes=all_nodes,
        relationships=relationships,
        summary=summary,
        warnings=warnings,
        generation_version=GENERATION_VERSION,
    )


def generate_mindmap(request: MindMapRequest) -> MindMapResponse:
    """
    Generate a deterministic concept-based mind map from the student answer analysis.
    A single deterministic root is used to provide a stable contextual entry point for the generated concept structure
        and to simplify downstream visualization.
    """
    analysis_request = request.analysis_request
    analysis = analyze_answer(analysis_request)
    expected_concepts = analysis_request.expected_concepts or []
    return build_mindmap_from_analysis(
        question_id=analysis_request.question_id,
        question_text=analysis_request.question_text,
        analysis=analysis,
        expected_concepts=expected_concepts,
    )
