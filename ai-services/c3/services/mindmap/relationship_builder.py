import hashlib

from app.schemas.mindmap import Node, Relationship

def generate_relationship_id(source_id: str, target_id: str, rel_type: str) -> str:
    """Generate a deterministic relationship ID."""
    raw = f"{source_id}->{target_id}:{rel_type}"
    return hashlib.md5(raw.encode()).hexdigest()

def build_baseline_relationships(root_node: Node, concept_nodes: list[Node]) -> list[Relationship]:
    """
    Deterministic baseline relationship strategy:
    Attach all concept nodes as siblings under the root node.
    We do not invent semantic relationships based on word co-occurrence or unreliable LLM outputs.
    
    Relationship direction explicitly implies:
    source = parent
    target = child
    
    Example:
    root
      └── authentication
    """
    relationships = []
    
    for child in concept_nodes:
        # Update node hierarchy properties directly on the objects
        child.parent_node_id = root_node.node_id
        child.relationship_type = "child"
        root_node.children.append(child.node_id)
        
        rel = Relationship(
            relationship_id=generate_relationship_id(root_node.node_id, child.node_id, "child"),
            source_node_id=root_node.node_id,
            target_node_id=child.node_id,
            relationship_type="child",
            evidence="Deterministic baseline structural attachment."
        )
        relationships.append(rel)
        
    return relationships
