"""Typed concept relationships in the mind map: cue-phrase rule, direction, negation, credit gating, consistent output.

The rule records what the student WROTE ("A depends on B"); these tests do not claim the statement is correct or that the
rule finds every relation.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.mindmap import MindMapRequest, Node
from services.mindmap.generator import generate_mindmap
from services.mindmap.relationship_builder import build_cooccurrence_relationships, typed_relation_between

client = TestClient(app)


@pytest.mark.parametrize("a,b,sentence,expected", [
    ("service", "database", "The service depends on the database.", ("service", "database", "depends_on")),
    ("service", "database", "The database is used by the service.", ("service", "database", "depends_on")),
    ("wheel", "car", "A wheel is part of a car.", ("wheel", "car", "part_of")),
    ("car", "wheel", "A car consists of a wheel and an engine.", ("wheel", "car", "part_of")),
    ("class", "object", "A class is a type of object.", ("class", "object", "is_a")),
    ("caching", "latency", "Poor caching leads to latency.", ("caching", "latency", "leads_to")),
    ("sql", "nosql", "SQL differs from NoSQL.", ("sql", "nosql", "contrasts_with")),
])
def test_cue_phrases_give_typed_directed_relations(a, b, sentence, expected):
    found = typed_relation_between(a, b, sentence)
    assert found is not None and found[:3] == expected


def test_direction_does_not_depend_on_the_argument_order():
    one = typed_relation_between("service", "database", "The service depends on the database.")
    two = typed_relation_between("database", "service", "The service depends on the database.")
    assert one[:3] == two[:3] == ("service", "database", "depends_on")


@pytest.mark.parametrize("sentence", [
    "The service does not depend on the database.",      # negation inside the cue
    "The service and the database are both important.",  # no cue phrase
    "The service, which is deployed on Tuesdays after a long review by the whole team, uses the database.",  # too far apart
    "The service uses.",                                  # second concept missing
])
def test_no_typed_relation_without_a_clean_cue(sentence):
    assert typed_relation_between("service", "database", sentence) is None


def test_concepts_must_appear_as_contiguous_phrases():
    assert typed_relation_between("load balancing", "server", "Balancing of load depends on the server.") is None
    assert typed_relation_between("load balancing", "server", "Load balancing depends on the server.") is not None


def _node(node_id, concept, status, sentences):
    return Node(node_id=node_id, type="concept", concept=concept, label=concept, source="student_answer",
                status=status, evidence_sentence_ids=sentences)


def test_typed_relation_replaces_co_mention_and_carries_evidence():
    nodes = [_node("n1", "service", "demonstrated", [1]), _node("n2", "database", "demonstrated", [1])]
    rels = build_cooccurrence_relationships(nodes, ["The service depends on the database."])
    assert len(rels) == 1
    rel = rels[0]
    assert (rel.source_node_id, rel.target_node_id, rel.relationship_type) == ("n1", "n2", "depends_on")
    assert "Sentence 1" in rel.evidence and "depends on" in rel.evidence and "not whether it is correct" in rel.evidence


def test_without_sentences_or_credit_the_line_stays_co_mentioned():
    text = ["The service depends on the database."]
    credited = [_node("n1", "service", "demonstrated", [1]), _node("n2", "database", "demonstrated", [1])]
    assert build_cooccurrence_relationships(credited)[0].relationship_type == "co_mentioned"
    uncredited = [_node("n1", "service", "demonstrated", [1]), _node("n2", "database", "not_demonstrated", [1])]
    assert build_cooccurrence_relationships(uncredited, text)[0].relationship_type == "co_mentioned"


def test_missing_relationships_and_out_of_range_sentences_are_safe():
    nodes = [_node("n1", "service", "demonstrated", [1]), _node("n2", "database", "demonstrated", [2])]
    assert build_cooccurrence_relationships(nodes, ["The service runs.", "The database stores."]) == []
    shared = [_node("n1", "service", "demonstrated", [5]), _node("n2", "database", "demonstrated", [5])]
    assert build_cooccurrence_relationships(shared, ["Only one sentence."])[0].relationship_type == "co_mentioned"


def _map(answer):
    request = {"analysis_request": {"question_id": "Q", "question_text": "Explain the design.", "student_answer": answer,
                                    "expected_concepts": ["service", "database", "cache"], "answer_type": "short"}}
    return generate_mindmap(MindMapRequest.model_validate(request))


def test_generated_map_is_consistent_with_typed_relationships():
    result = _map("The service depends on the database. The cache leads to lower load.")
    ids = {n.node_id for n in result.nodes}
    assert all(r.source_node_id in ids and r.target_node_id in ids for r in result.relationships)
    assert len({r.relationship_id for r in result.relationships}) == len(result.relationships)
    types = {(r.source_node_id.split("_")[-1], r.relationship_type) for r in result.relationships}
    assert any(t == "depends_on" for _, t in types)
    assert result == _map("The service depends on the database. The cache leads to lower load.")  # deterministic


def test_a_negated_dependency_is_not_typed_end_to_end():
    result = _map("The service does not depend on the database.")
    kinds = {r.relationship_type for r in result.relationships}
    assert "depends_on" not in kinds
    # the contradiction rule also withholds credit: 'not' sits next to both concept words
    statuses = {n.concept: n.status for n in result.nodes if n.type == "concept"}
    assert statuses["service"] == statuses["database"] == "not_demonstrated"


def test_assess_endpoint_returns_typed_relationships_in_the_stored_map():
    payload = {"question_id": "Q-ARCH-01", "question_text": "Explain.", "student_answer": "The service depends on the database.",
               "expected_concepts": ["service", "database"], "answer_type": "short",
               "rubric": {"rubric_id": "R", "title": "R", "criteria": [{"criterion_id": "C1", "description": "d", "max_marks": 2.0,
                          "required_concepts": ["service", "database"], "scoring_levels": [
                              {"level_id": "L0", "label": "none", "mark": 0.0, "descriptor": "none"},
                              {"level_id": "L2", "label": "all", "mark": 2.0, "descriptor": "both", "required_concepts": ["service", "database"],
                               "evidence_rule": {"type": "required_concept_count", "minimum_demonstrated": 2}}]}]}}
    data = client.post("/c3/assess", json=payload).json()
    assert data["total_awarded_marks"] == 2.0  # typing the relation did not change the rubric mark
    assert [r["relationship_type"] for r in data["mindmap"]["relationships"] if r["relationship_type"] != "child"] == ["depends_on"]
