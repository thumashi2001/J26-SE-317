from app.schemas.mindmap import MindMapRequest, MindMapResponse, MindMapSummary
from services.semantic.analyzer import analyze_answer
from services.mindmap.node_builder import build_root_node, build_concept_nodes
from services.mindmap.relationship_builder import build_baseline_relationships

GENERATION_VERSION = "baseline-v1"

def generate_mindmap(request: MindMapRequest) -> MindMapResponse:
    """
    Generate a deterministic concept-based mind map from the student answer analysis.
    A single deterministic root is used to provide a stable contextual entry point for the generated concept structure and to simplify downstream visualization.
    """
    # 1. Run existing answer analysis
    analysis_request = request.analysis_request
    analysis = analyze_answer(analysis_request)
    
    # 2. Identify an explicit topic/root
    root_node = build_root_node(
        question_id=analysis_request.question_id, 
        question_text=analysis_request.question_text
    )
    
    # 3. Collect concept matches & create stable node IDs
    expected_concepts = analysis_request.expected_concepts or []
    concept_nodes = build_concept_nodes(analysis, expected_concepts)
    
    # 4. Attach unlinked concepts directly under the root using deterministic rules
    relationships = build_baseline_relationships(root_node, concept_nodes)
    
    all_nodes = [root_node] + concept_nodes
    
    # 5. Generate summary statistics
    demonstrated = sum(1 for n in concept_nodes if n.status == "demonstrated")
    partial = sum(1 for n in concept_nodes if n.status == "partial")
    missing = sum(1 for n in concept_nodes if n.status == "not_demonstrated")
    
    summary = MindMapSummary(
        total_nodes=len(all_nodes),
        demonstrated_count=demonstrated,
        partial_count=partial,
        missing_count=missing
    )
    
    warnings = []
    if missing > 0:
        warnings.append(f"Mind map contains {missing} missing expected concept(s).")
        
    # Check if we lack evidence
    if demonstrated == 0 and partial == 0:
        warnings.append("No student evidence was detected for expected concepts.")

    return MindMapResponse(
        question_id=analysis_request.question_id,
        root_node_id=root_node.node_id,
        title=f"Concept Map: {analysis_request.question_id}",
        nodes=all_nodes,
        relationships=relationships,
        summary=summary,
        warnings=warnings,
        generation_version=GENERATION_VERSION
    )
