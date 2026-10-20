"""Unit tests for services/mindmap node_builder and relationship_builder edge cases."""
import pytest

from app.schemas.analysis import AnswerAnalysisResponse, ConceptMatch
from app.schemas.mindmap import Node
from services.mindmap.node_builder import (
    build_concept_nodes,
    build_root_node,
    generate_node_id,
    generate_root_id,
)
from services.mindmap.relationship_builder import build_baseline_relationships


def make_analysis(matches: list[tuple[str, str, list[int]]]) -> AnswerAnalysisResponse:
    return AnswerAnalysisResponse(
        question_id="Q1",
        normalized_answer="t",
        sentence_count=1,
        token_count=1,
        sentences=[],
        reference_similarity=0.0,
        concept_matches=[
            ConceptMatch(concept=c, status=s, overlap_score=0.0, evidence_sentence_ids=ids)
            for c, s, ids in matches
        ],
        warnings=[],
        analysis_version="baseline-v1",
    )


def test_generate_node_id_is_deterministic_and_normalized() -> None:
    assert generate_node_id("  Access Control ") == "concept_access_control"
    assert generate_node_id("Access Control") == generate_node_id("access control")


def test_generate_root_id_normalized() -> None:
    assert generate_root_id(" Q 1 ") == "root_q_1"


@pytest.mark.xfail(
    strict=True,
    reason="AUDIT-MM1: generate_node_id maps 'a b' and 'a_b' to the same id 'concept_a_b' "
    "(node_builder.py:7-9); distinct concepts should get distinct node ids",
)
def test_generate_node_id_no_collision_between_space_and_underscore() -> None:
    assert generate_node_id("a b") != generate_node_id("a_b")


@pytest.mark.xfail(
    strict=True,
    reason="AUDIT-MM1: concept nodes for 'a b' and 'a_b' end up with duplicate node_id "
    "(node_builder.py:7-9); node ids in a mind map must be unique",
)
def test_concept_nodes_have_unique_ids_for_colliding_concepts() -> None:
    nodes = build_concept_nodes(make_analysis([]), ["a b", "a_b"])
    assert len({n.node_id for n in nodes}) == len(nodes)


@pytest.mark.xfail(
    strict=True,
    reason="AUDIT-MM2: label uses str.title() so 'REST' becomes 'Rest' (node_builder.py:57); "
    "acronyms should keep their casing",
)
def test_label_preserves_acronym_casing() -> None:
    nodes = build_concept_nodes(make_analysis([]), ["REST"])
    assert nodes[0].label == "REST"


@pytest.mark.xfail(
    strict=True,
    reason="AUDIT-MM2: str.title() turns \"don't\" into \"Don'T\" (node_builder.py:57); expected \"Don't\"",
)
def test_label_apostrophe_not_capitalised() -> None:
    nodes = build_concept_nodes(make_analysis([]), ["don't repeat"])
    assert nodes[0].label == "Don't Repeat"


def test_label_title_cases_plain_concepts() -> None:
    nodes = build_concept_nodes(make_analysis([]), ["access control", "high-level structure"])
    assert [n.label for n in nodes] == ["Access Control", "High-Level Structure"]
    assert nodes[0].concept == "access control"


def test_root_node_with_question_text() -> None:
    root = build_root_node("Q 1", "What is X?")
    assert root.node_id == "root_q_1"
    assert root.type == "root"
    assert root.label == "What is X?"
    assert root.concept == "Q 1"
    assert root.parent_node_id is None and root.children == []


@pytest.mark.parametrize("text", [None, ""])
def test_root_node_falls_back_to_main_topic(text) -> None:
    assert build_root_node("Q1", text).label == "Main Topic"


def test_concept_nodes_empty_inputs() -> None:
    assert build_concept_nodes(make_analysis([]), []) == []


def test_concept_nodes_status_source_and_evidence_preserved() -> None:
    analysis = make_analysis([("a", "demonstrated", [1, 2]), ("b", "partial", [3]), ("c", "not_demonstrated", [])])
    nodes = {n.concept: n for n in build_concept_nodes(analysis, [])}
    assert nodes["a"].source == "student_answer" and nodes["a"].evidence_sentence_ids == [1, 2]
    assert nodes["b"].source == "student_answer" and nodes["b"].status == "partial"
    assert nodes["c"].source == "expected_concept" and nodes["c"].status == "not_demonstrated"


def test_concept_nodes_dedupe_case_insensitively_and_add_unreturned_expected() -> None:
    analysis = make_analysis([("Alpha", "demonstrated", [1])])
    nodes = build_concept_nodes(analysis, ["alpha", "beta", "BETA"])
    assert [n.concept for n in nodes] == ["Alpha", "beta"]
    assert nodes[1].status == "not_demonstrated" and nodes[1].source == "expected_concept"


def _node(node_id: str) -> Node:
    return Node(node_id=node_id, type="concept", concept=node_id, label=node_id, source="s")


def test_relationship_builder_mutates_inputs_by_design() -> None:
    root = build_root_node("Q1", "t")
    children = [_node("c1"), _node("c2")]
    rels = build_baseline_relationships(root, children)
    assert root.children == ["c1", "c2"]
    assert all(c.parent_node_id == root.node_id and c.relationship_type == "child" for c in children)
    assert len(rels) == 2


def test_relationship_builder_empty_children() -> None:
    root = build_root_node("Q1", "t")
    assert build_baseline_relationships(root, []) == []
    assert root.children == []


def test_relationship_ids_are_unique_and_deterministic() -> None:
    def run() -> list[str]:
        root = build_root_node("Q1", "t")
        return [r.relationship_id for r in build_baseline_relationships(root, [_node("c1"), _node("c2")])]

    first = run()
    assert first == run()
    assert len(set(first)) == 2


@pytest.mark.xfail(
    strict=True,
    reason="AUDIT-MM3: build_baseline_relationships mutates root.children with append "
    "(relationship_builder.py:33), so calling it twice duplicates children ['c1','c1']; expected idempotent",
)
def test_relationship_builder_is_idempotent_for_same_inputs() -> None:
    root = build_root_node("Q1", "t")
    child = _node("c1")
    build_baseline_relationships(root, [child])
    build_baseline_relationships(root, [child])
    assert root.children == ["c1"]
