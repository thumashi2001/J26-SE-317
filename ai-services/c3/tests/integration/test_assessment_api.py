from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def base_rubric() -> dict:
    concepts = ["high-level structure", "components", "relationships"]
    return {
        "rubric_id": "R-ASSESS-01",
        "title": "Software Architecture Rubric",
        "criteria": [
            {
                "criterion_id": "C1",
                "description": "Demonstrate knowledge of software architecture structure.",
                "max_marks": 4.0,
                "required_concepts": concepts,
                "scoring_levels": [
                    {
                        "level_id": "L0",
                        "label": "Unsatisfactory",
                        "mark": 0.0,
                        "descriptor": "No relevant concepts demonstrated.",
                    },
                    {
                        "level_id": "L2",
                        "label": "Developing",
                        "mark": 2.0,
                        "descriptor": "At least one structural concept demonstrated.",
                        "required_concepts": concepts,
                        "evidence_rule": {
                            "type": "required_concept_count",
                            "minimum_demonstrated": 1,
                        },
                    },
                    {
                        "level_id": "L4",
                        "label": "Proficient",
                        "mark": 4.0,
                        "descriptor": "All three core concepts demonstrated.",
                        "required_concepts": concepts,
                        "evidence_rule": {
                            "type": "required_concept_count",
                            "minimum_demonstrated": 3,
                        },
                    },
                ],
            }
        ],
    }


def multi_criteria_rubric() -> dict:
    return {
        "rubric_id": "R-MULTI-01",
        "title": "System Quality Rubric",
        "criteria": [
            {
                "criterion_id": "C1",
                "description": "Security access control.",
                "max_marks": 2.0,
                "required_concepts": ["access control"],
                "scoring_levels": [
                    {
                        "level_id": "L0",
                        "label": "None",
                        "mark": 0.0,
                        "descriptor": "No security evidence.",
                    },
                    {
                        "level_id": "L2",
                        "label": "Full",
                        "mark": 2.0,
                        "descriptor": "Access control demonstrated.",
                        "required_concepts": ["access control"],
                        "evidence_rule": {
                            "type": "required_concept_count",
                            "minimum_demonstrated": 1,
                        },
                    },
                ],
            },
            {
                "criterion_id": "C2",
                "description": "System reliability and fault tolerance.",
                "max_marks": 2.0,
                "required_concepts": ["fault tolerance"],
                "scoring_levels": [
                    {
                        "level_id": "L0",
                        "label": "None",
                        "mark": 0.0,
                        "descriptor": "No reliability evidence.",
                    },
                    {
                        "level_id": "L2",
                        "label": "Full",
                        "mark": 2.0,
                        "descriptor": "Fault tolerance demonstrated.",
                        "required_concepts": ["fault tolerance"],
                        "evidence_rule": {
                            "type": "required_concept_count",
                            "minimum_demonstrated": 1,
                        },
                    },
                ],
            },
        ],
    }


def tiered_progression_rubric() -> dict:
    return {
        "rubric_id": "R-TIER-01",
        "title": "OOP Progression Rubric",
        "criteria": [
            {
                "criterion_id": "C1",
                "description": "Demonstrate understanding of OOP principles.",
                "max_marks": 3.0,
                "scoring_levels": [
                    {
                        "level_id": "L0",
                        "label": "None",
                        "mark": 0.0,
                        "descriptor": "No OOP evidence.",
                    },
                    {
                        "level_id": "L1",
                        "label": "Basic",
                        "mark": 1.0,
                        "descriptor": "Demonstrates encapsulation.",
                        "required_concepts": ["encapsulation"],
                    },
                    {
                        "level_id": "L2",
                        "label": "Intermediate",
                        "mark": 2.0,
                        "descriptor": "Demonstrates polymorphism.",
                        "required_concepts": ["polymorphism"],
                    },
                    {
                        "level_id": "L3",
                        "label": "Advanced",
                        "mark": 3.0,
                        "descriptor": "Demonstrates polymorphism and runtime dispatch.",
                        "required_concepts": ["polymorphism", "runtime dispatch"],
                    },
                ],
            }
        ],
    }


# =========================================================================
# Scenario 1: Full-credit answer
# =========================================================================
def test_assess_full_credit_answer() -> None:
    payload = {
        "question_id": "Q-ARCH-01",
        "question_text": "Explain software architecture and its components.",
        "student_answer": (
            "Software architecture defines the high-level structure of a system. "
            "It organizes components and specifies their relationships clearly."
        ),
        "expected_concepts": ["high-level structure", "components", "relationships"],
        "answer_type": "short",
        "rubric": base_rubric(),
    }
    response = client.post("/c3/assess", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Mark Authority Check
    assert data["total_awarded_marks"] == 4.0
    assert data["total_possible_marks"] == 4.0
    assert data["percentage"] == 100.0
    assert data["marking"]["total_awarded_marks"] == 4.0
    assert data["marking"]["percentage"] == 100.0
    assert data["marking"]["criteria_results"][0]["selected_level_id"] == "L4"
    assert data["marking"]["criteria_results"][0]["awarded_mark"] == 4.0

    # F1 Traceability
    assert data["analysis"]["sentence_count"] == 2
    matched_concepts = [c["concept"] for c in data["analysis"]["concept_matches"] if c["status"] == "demonstrated"]
    assert "high-level structure" in matched_concepts
    assert "components" in matched_concepts
    assert "relationships" in matched_concepts

    # F3 Feedback Traceability
    assert data["feedback"]["overall_feedback"]["total_mark"] == 4.0
    assert data["feedback"]["criteria_feedback"][0]["awarded_mark"] == 4.0
    assert len(data["feedback"]["criteria_feedback"][0]["strengths"]) > 0
    assert len(data["feedback"]["criteria_feedback"][0]["missing_concepts"]) == 0

    # F4 Mind Map Traceability
    assert data["mindmap"]["summary"]["demonstrated_count"] == 3
    assert data["mindmap"]["summary"]["missing_count"] == 0
    assert len(data["mindmap"]["nodes"]) == 4  # Root + 3 concepts


# =========================================================================
# Scenario 2: Partial-credit answer
# =========================================================================
def test_assess_partial_credit_answer() -> None:
    payload = {
        "question_id": "Q-ARCH-01",
        "question_text": "Explain software architecture.",
        "student_answer": "Software architecture provides a high-level structure.",
        "expected_concepts": ["high-level structure", "components", "relationships"],
        "answer_type": "short",
        "rubric": base_rubric(),
    }
    response = client.post("/c3/assess", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Mark Authority Check
    assert data["total_awarded_marks"] == 2.0
    assert data["total_possible_marks"] == 4.0
    assert data["percentage"] == 50.0
    assert data["marking"]["total_awarded_marks"] == 2.0
    assert data["marking"]["criteria_results"][0]["selected_level_id"] == "L2"
    assert data["marking"]["criteria_results"][0]["awarded_mark"] == 2.0

    # F3 Feedback contains missing concept guidance
    missing = data["feedback"]["criteria_feedback"][0]["missing_concepts"]
    assert "components" in missing
    assert "relationships" in missing
    assert len(data["feedback"]["criteria_feedback"][0]["improvement_suggestions"]) > 0

    # F4 Mind map reflects partial demonstrated status
    assert data["mindmap"]["summary"]["demonstrated_count"] == 1
    assert data["mindmap"]["summary"]["missing_count"] == 2


# =========================================================================
# Scenario 3: Zero / irrelevant answer
# =========================================================================
def test_assess_zero_irrelevant_answer() -> None:
    payload = {
        "question_id": "Q-ARCH-01",
        "question_text": "Explain software architecture.",
        "student_answer": "I prefer cooking delicious dinner tonight.",
        "expected_concepts": ["high-level structure", "components", "relationships"],
        "answer_type": "short",
        "rubric": base_rubric(),
    }
    response = client.post("/c3/assess", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Mark Authority Check
    assert data["total_awarded_marks"] == 0.0
    assert data["percentage"] == 0.0
    assert data["marking"]["total_awarded_marks"] == 0.0
    assert data["marking"]["criteria_results"][0]["selected_level_id"] == "L0"

    # F4 Mind Map reflects no student evidence
    assert data["mindmap"]["summary"]["demonstrated_count"] == 0
    assert data["mindmap"]["summary"]["missing_count"] == 3
    assert any("No student evidence" in w for w in data["mindmap"]["warnings"])


# =========================================================================
# Scenario 4: Higher-level concept
# =========================================================================
def test_assess_higher_level_concept() -> None:
    payload = {
        "question_id": "Q-OOP-01",
        "question_text": "Explain advanced polymorphism in OOP.",
        "student_answer": (
            "Polymorphism enables interchangeable behavior. "
            "It relies on dynamic runtime dispatch to invoke correct methods."
        ),
        "expected_concepts": ["polymorphism", "runtime dispatch"],
        "answer_type": "short",
        "rubric": tiered_progression_rubric(),
    }
    response = client.post("/c3/assess", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["marking"]["criteria_results"][0]["selected_level_id"] == "L3"
    assert data["total_awarded_marks"] == 3.0
    assert data["marking"]["criteria_results"][0]["awarded_mark"] == 3.0
    assert data["percentage"] == 100.0


# =========================================================================
# Scenario 5: Criterion-level required concepts
# =========================================================================
def test_assess_criterion_level_required_concepts() -> None:
    payload = {
        "question_id": "Q-QUALITY-01",
        "question_text": "Discuss security and reliability measures.",
        "student_answer": "We strictly enforce access control across all microservices.",
        "answer_type": "short",
        "rubric": multi_criteria_rubric(),
    }
    response = client.post("/c3/assess", json=payload)
    assert response.status_code == 200
    data = response.json()

    # C1 awarded 2 marks, C2 awarded 0 marks
    c1_res = next(c for c in data["marking"]["criteria_results"] if c["criterion_id"] == "C1")
    c2_res = next(c for c in data["marking"]["criteria_results"] if c["criterion_id"] == "C2")
    assert c1_res["awarded_mark"] == 2.0
    assert c1_res["selected_level_id"] == "L2"
    assert c2_res["awarded_mark"] == 0.0
    assert c2_res["selected_level_id"] == "L0"

    assert data["total_awarded_marks"] == 2.0
    assert data["total_possible_marks"] == 4.0
    assert data["percentage"] == 50.0

    # Feedback criterion alignment
    c1_fb = next(c for c in data["feedback"]["criteria_feedback"] if c["criterion_id"] == "C1")
    c2_fb = next(c for c in data["feedback"]["criteria_feedback"] if c["criterion_id"] == "C2")
    assert c1_fb["awarded_mark"] == 2.0
    assert len(c1_fb["strengths"]) > 0
    assert c2_fb["awarded_mark"] == 0.0
    assert "fault tolerance" in c2_fb["next_level_improvements"]



# =========================================================================
# Scenario 6: Invalid request
# =========================================================================
def test_assess_invalid_request_missing_answer() -> None:
    payload = {
        "question_id": "Q-INVALID",
        "question_text": "A question text.",
        "answer_type": "short",
        "rubric": base_rubric(),
    }
    response = client.post("/c3/assess", json=payload)
    assert response.status_code == 422


# =========================================================================
# Scenario 7: Controlled downstream/service failure (invalid rubric)
# =========================================================================
def test_assess_invalid_rubric_rejected_cleanly() -> None:
    invalid_rubric = base_rubric()
    # Violate rubric constraints: max_marks <= 0
    invalid_rubric["criteria"][0]["max_marks"] = -1.0
    payload = {
        "question_id": "Q-INVALID-RUBRIC",
        "question_text": "A question text.",
        "student_answer": "Any answer text.",
        "answer_type": "short",
        "rubric": invalid_rubric,
    }
    response = client.post("/c3/assess", json=payload)
    assert response.status_code == 422

