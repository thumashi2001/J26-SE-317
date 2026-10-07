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
