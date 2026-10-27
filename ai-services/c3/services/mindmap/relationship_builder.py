"""Builds the lines (relationships) of the mind map.

LIMITATION TO STATE HONESTLY IN THE VIVA
    Root -> concept lines are purely structural "child" links. The only concept-to-concept lines are "co_mentioned":
    two concepts the student wrote about in the SAME sentence. That is observable evidence (the sentence number is on
    the line), but it is co-occurrence, not a typed relation such as "A is part of B"; the system does not infer those.
"""
import hashlib

from app.schemas.mindmap import Node, Relationship


def generate_relationship_id(source_id: str, target_id: str, rel_type: str) -> str:
    """Generate a deterministic relationship ID."""
    # md5 is used only to make a short stable identifier (not for security).
    raw = f"{source_id}->{target_id}:{rel_type}"
    return hashlib.md5(raw.encode()).hexdigest()

def build_cooccurrence_relationships(concept_nodes: list[Node]) -> list[Relationship]:
    """Link two concepts that share an evidence sentence (FR-C3-33: relationships "where evidence exists").

    Only concepts with student evidence can be linked (missing concepts have no sentence). Direction is by node order,
    which is arbitrary, so the relationship type is symmetric ("co_mentioned") and carries the shared sentence numbers.
    """
    relationships = []
    for i, a in enumerate(concept_nodes):
        for b in concept_nodes[i + 1:]:
            shared = sorted(set(a.evidence_sentence_ids) & set(b.evidence_sentence_ids))
            if not shared:
                continue
            where = ", ".join(str(n) for n in shared)
            relationships.append(Relationship(
                relationship_id=generate_relationship_id(a.node_id, b.node_id, "co_mentioned"),
                source_node_id=a.node_id,
                target_node_id=b.node_id,
                relationship_type="co_mentioned",
                evidence=f"Both concepts appear in sentence {where} of the student's answer (co-occurrence only).",
            ))
    return relationships


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
