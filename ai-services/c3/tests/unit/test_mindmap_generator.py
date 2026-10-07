from app.schemas.analysis import AnswerAnalysisRequest
from app.schemas.mindmap import MindMapRequest
from services.mindmap.generator import generate_mindmap

def test_mindmap_generation_baseline():
    request = MindMapRequest(
        analysis_request=AnswerAnalysisRequest(
            question_id="Q1",
            question_text="Explain authentication and encryption.",
            student_answer="I use authentication, but I forgot the other one.",
            expected_concepts=["authentication", "encryption"],
            answer_type="short"
        )
    )
    
    response = generate_mindmap(request)
    
    assert response.question_id == "Q1"
    assert response.root_node_id == "root_q1"
    
    # 3 nodes expected: root, authentication, encryption
    assert len(response.nodes) == 3
    assert response.summary.total_nodes == 3
    
    # One demonstrated (auth), one missing (enc)
    assert response.summary.demonstrated_count == 1
    assert response.summary.missing_count == 1
    assert response.summary.partial_count == 0
    
    # Check relationships
    assert len(response.relationships) == 2
    for rel in response.relationships:
        assert rel.source_node_id == "root_q1"
        assert rel.relationship_type == "child"
        
    # Check node identities and traceability
    auth_node = next(n for n in response.nodes if n.concept == "authentication")
    assert auth_node.node_id == "concept_authentication"
    assert auth_node.status == "demonstrated"
    assert len(auth_node.evidence_sentence_ids) > 0  # Should be mapped by existing analyzer
    
    enc_node = next(n for n in response.nodes if n.concept == "encryption")
    assert enc_node.node_id == "concept_encryption"
    assert enc_node.status == "not_demonstrated"
    assert len(enc_node.evidence_sentence_ids) == 0

def test_mindmap_without_evidence_returns_warning():
    request = MindMapRequest(
        analysis_request=AnswerAnalysisRequest(
            question_id="Q2",
            question_text="Unrelated?",
            student_answer="Banana.",
            expected_concepts=["apple"],
            answer_type="short"
        )
    )
    response = generate_mindmap(request)
    assert any("No student evidence was detected" in w for w in response.warnings)

def test_deterministic_repeatability():
    request = MindMapRequest(
        analysis_request=AnswerAnalysisRequest(
            question_id="Q-REP",
            question_text="Repeatability test.",
            student_answer="This is a test of repeatability.",
            expected_concepts=["repeatability", "consistency"],
            answer_type="short"
        )
    )
    
    result_1 = generate_mindmap(request)
    result_2 = generate_mindmap(request)
    
    assert result_1 == result_2

def test_student_vs_expected_concept_regression():
    request = MindMapRequest(
        analysis_request=AnswerAnalysisRequest(
            question_id="Q-REG",
            question_text="Explain authentication and encryption.",
            student_answer="I use authentication.",
            expected_concepts=["authentication", "encryption"],
            answer_type="short"
        )
    )
    response = generate_mindmap(request)
    
    auth_node = next(n for n in response.nodes if n.concept == "authentication")
    assert auth_node.source == "student_answer"
    assert auth_node.status == "demonstrated"
    assert len(auth_node.evidence_sentence_ids) > 0
    
    enc_node = next(n for n in response.nodes if n.concept == "encryption")
    assert enc_node.source == "expected_concept"
    assert enc_node.status == "not_demonstrated"
    assert len(enc_node.evidence_sentence_ids) == 0

