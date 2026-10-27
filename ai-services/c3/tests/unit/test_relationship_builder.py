from app.schemas.mindmap import Node
from services.mindmap.relationship_builder import build_baseline_relationships, generate_relationship_id


def test_baseline_relationships():
    root = Node(node_id="root_1", type="root", concept="q", label="q", source="system", status=None, evidence_sentence_ids=[])
    child1 = Node(node_id="c_1", type="concept", concept="c1", label="c1", source="student_answer", status="demonstrated", evidence_sentence_ids=[])

    rels = build_baseline_relationships(root, [child1])

    assert len(rels) == 1
    assert rels[0].source_node_id == "root_1"
    assert rels[0].target_node_id == "c_1"
    assert rels[0].relationship_type == "child"
    assert rels[0].relationship_id == generate_relationship_id("root_1", "c_1", "child")

    assert child1.parent_node_id == "root_1"
    assert child1.relationship_type == "child"
    assert "c_1" in root.children


def test_cooccurrence_links_only_concepts_sharing_a_sentence():
    from app.schemas.mindmap import Node
    from services.mindmap.relationship_builder import build_cooccurrence_relationships

    def node(i, sents):
        return Node(node_id=i, type="concept", concept=i, label=i, source="x", evidence_sentence_ids=sents)

    rels = build_cooccurrence_relationships([node("a", [1, 2]), node("b", [2]), node("c", [3]), node("m", [])])
    assert [(r.source_node_id, r.target_node_id) for r in rels] == [("a", "b")]
    assert rels[0].relationship_type == "co_mentioned" and "sentence 2" in rels[0].evidence
