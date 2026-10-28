"""Builds the lines (relationships) of the mind map.

LIMITATION TO STATE HONESTLY IN THE VIVA
    Root -> concept lines are purely structural "child" links. Concept-to-concept lines come in two kinds:
      * typed (is_a, part_of, depends_on, leads_to, contrasts_with): only when BOTH concepts are demonstrated or
          partial,
        sit in the same sentence, and a fixed cue phrase ("part of", "depends on", "leads to", ...) stands between them
        with no negation word. The cue phrase and sentence number are written on the line as evidence. Direction follows
        the wording (source -> target), e.g. "A depends on B" gives A --depends_on--> B.
      * "co_mentioned": the concepts share a sentence but no cue phrase links them (co-occurrence only).
    The cue list is small and hand-written. It misses relations phrased in other ways and can not tell a true statement
        from
    a false one ("a database is part of a cat" is typed part_of); typing records what the student WROTE, not whether it
        is
    correct. No relation is inferred from similarity or from an LLM.
"""
import hashlib
import re

from app.schemas.mindmap import Node, Relationship
from services.preprocessing.text_normalizer import tokenize
from services.semantic.negation import NEGATION_CUES

# (cue pattern, relationship type, True when the EARLIER concept in the sentence is the source). First match wins.
CUE_RULES: tuple[tuple[re.Pattern, str, bool], ...] = tuple(
    (re.compile(f"^(?:{pattern})$"), rel_type, forward)
    for pattern, rel_type, forward in (
        (r"(?:is|are) (?:a |an )?(?:type|kind|form|subtype|example) of", "is_a", True),
        (r"(?:is|are) (?:a |an |the )?(?:part|component|element|member|subset) of", "part_of", True),
        (
            r"consists? of|consisting of|(?:is|are) (?:made up|composed) of|contains?|includes?|comprises?",
            "part_of",
            False,
        ),
        (r"(?:is|are) (?:used|required|needed) by", "depends_on", False),
        (r"depends? on|relies on|rely on|requires?|needs?|uses?|calls?", "depends_on", True),
        (r"causes?|leads? to|results? in|enables?|produces?", "leads_to", True),
        (r"unlike|differs? from|(?:is|are) different from|in contrast to|as opposed to", "contrasts_with", True),
    )
)
MAX_CUE_WORDS = 5  # the phrase between the two concepts may be at most this long
# ignored just before the second concept ("depends on THE database")
ARTICLES = {"the", "a", "an", "its", "their", "this", "that"}


def generate_relationship_id(source_id: str, target_id: str, rel_type: str) -> str:
    """Generate a deterministic relationship ID."""
    # md5 is used only to make a short stable identifier (not for security).
    raw = f"{source_id}->{target_id}:{rel_type}"
    return hashlib.md5(raw.encode()).hexdigest()


def _find(sequence: list[str], tokens: list[str]) -> int:
    """Start index of the contiguous token sequence inside the sentence, or -1."""
    n = len(sequence)
    return next((i for i in range(len(tokens) - n + 1) if tokens[i:i + n] == sequence), -1)


def _plain(word: str) -> str:
    """Token without apostrophes so "doesn't" matches the negation list."""
    return word.replace("'", "").replace("’", "")


def typed_relation_between(concept_a: str, concept_b: str, sentence: str):
    """(source concept, target concept, type, cue phrase) if a fixed cue phrase links the two concepts, else None.

    The two concepts must each appear as a contiguous phrase, the words between them must match a cue rule exactly, and
        no
    negation word may be among them ("A does not depend on B" is not typed).
    """
    tokens = tokenize(sentence)
    seq_a, seq_b = tokenize(concept_a), tokenize(concept_b)
    if not seq_a or not seq_b:
        return None
    start_a, start_b = _find(seq_a, tokens), _find(seq_b, tokens)
    if start_a < 0 or start_b < 0 or start_a == start_b:
        return None
    first, second = ((concept_a, seq_a, start_a), (concept_b, seq_b, start_b))
    if start_b < start_a:
        first, second = second, first
    between = tokens[first[2] + len(first[1]):second[2]]
    while between and between[-1] in ARTICLES:
        between = between[:-1]
    if not between or len(between) > MAX_CUE_WORDS or any(_plain(w) in NEGATION_CUES for w in between):
        return None
    phrase = " ".join(between)
    for pattern, rel_type, forward in CUE_RULES:
        if pattern.match(phrase):
            source, target = (first[0], second[0]) if forward else (second[0], first[0])
            return source, target, rel_type, phrase
    return None


def _typed_for(a: Node, b: Node, shared: list[int], sentences: list[str] | None):
    """First typed relation for the pair over their shared sentences; both concepts must be credited by the analysis."""
    if not sentences or a.status not in ("demonstrated", "partial") or b.status not in ("demonstrated", "partial"):
        return None
    nodes = {a.concept: a, b.concept: b}
    for number in shared:
        if 1 <= number <= len(sentences):
            found = typed_relation_between(a.concept, b.concept, sentences[number - 1])
            if found:
                source, target, rel_type, phrase = found
                return nodes[source], nodes[target], rel_type, phrase, number
    return None


def build_cooccurrence_relationships(
    concept_nodes: list[Node], sentences: list[str] | None = None
) -> list[Relationship]:
    """Link two concepts that share an evidence sentence (FR-C3-33: relationships "where evidence exists").

    Only concepts with student evidence can be linked (missing concepts have no sentence). Without a cue phrase the type
        is
    symmetric ("co_mentioned") and the line carries the shared sentence numbers.

    When the sentence texts are given and both concepts are demonstrated/partial, a cue phrase between them upgrades the
        line
    to a typed relationship (see the module docstring); the first shared sentence with a cue decides the type.
    """
    relationships = []
    for i, a in enumerate(concept_nodes):
        for b in concept_nodes[i + 1:]:
            shared = sorted(set(a.evidence_sentence_ids) & set(b.evidence_sentence_ids))
            if not shared:
                continue
            typed = _typed_for(a, b, shared, sentences)
            if typed is not None:
                src, tgt, rel_type, phrase, sentence_no = typed
                relationships.append(Relationship(
                    relationship_id=generate_relationship_id(src.node_id, tgt.node_id, rel_type),
                    source_node_id=src.node_id,
                    target_node_id=tgt.node_id,
                    relationship_type=rel_type,
                    evidence=(f"Sentence {sentence_no} says '{src.concept} {phrase} {tgt.concept}' "
                              f"(cue phrase '{phrase}'); "
                              "this records what the student wrote, not whether it is correct."),
                ))
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
