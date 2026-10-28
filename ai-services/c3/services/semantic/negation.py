"""Negation-cue check: does a sentence that names a concept also negate it? (possible contradiction, NOT a meaning
    check)

SIMPLE ENGLISH
    "Encapsulation does not hide anything" contains the word "encapsulation", so word matching alone would credit it.
    This module notices that a negation word ("not", "no", "never", "cannot", "doesn't", ...) sits right next to the
        concept's
    words and reports the sentence as NEGATED. It is a deliberately small, deterministic rule:
      * it can only see negation that is spelled with one of the cues below, close to the concept's words;
      * it cannot see a wrong statement that has no negation ("encapsulation exposes all data" is not detected);
      * a correct negated sentence ("encapsulation does not mean copying") is also reported, so the result is a
        POSSIBLE contradiction that the lecturer must check, never a verified error.
    The accuracy of this rule has NOT been measured (no human-labelled contradiction data exists). By default it only
        warns
    (C3_CONTRADICTION_POLICY=warn_only); marks are untouched unless withhold_credit is chosen explicitly.
"""

from __future__ import annotations

import os

from services.preprocessing.text_normalizer import tokenize
from services.semantic.baseline import token_overlap_score

# Verb negations negate the statement around them, so the concept may be just before or just after the cue
# ("encapsulation does not hide", "do not use encapsulation").
VERB_CUES = frozenset({
    "not", "never", "cannot",
    "isnt", "arent", "wasnt", "werent", "doesnt", "dont", "didnt", "wont", "wouldnt", "shouldnt", "cant", "couldnt",
    "hasnt", "havent",
})
# Determiner-style negations negate the noun phrase AFTER them ("no components", "without interfaces"). A concept that
# comes
# before them ("values with no repeating groups") is not negated.
DETERMINER_CUES = frozenset({"no", "none", "nothing", "nobody", "without", "neither", "nor"})
NEGATION_CUES = VERB_CUES | DETERMINER_CUES
ENV_POLICY = "C3_CONTRADICTION_POLICY"
# DEFAULT: flag and warn, but leave the concept's status (and so the mark) untouched
WARN_ONLY = "warn_only"
# opt-in: a concept that is only ever negated earns no credit (needs supervisor approval)
WITHHOLD_CREDIT = "withhold_credit"
DEFAULT_POLICY = WARN_ONLY


def contradiction_policy() -> str:
    """What a possible contradiction does: only warn (default) or withhold credit. Unset or unknown values use the
        default.

    Withholding credit changes marks, so it must be switched on explicitly until the supervisor approves that marking
        policy.
    """
    value = os.getenv(ENV_POLICY, DEFAULT_POLICY).strip().lower()
    return value if value in (WITHHOLD_CREDIT, WARN_ONLY) else DEFAULT_POLICY


# A cue only counts when it is within this many words of one of the concept's words.
WINDOW = 4
# "not only X but also Y" and "no longer" are not negations of X.
_NOT_NEGATING_NEXT = {"not": {"only"}, "no": {"longer"}}


def _plain(token: str) -> str:
    """Lower-case token without apostrophes, so "doesn't" and "doesn’t" both become "doesnt"."""
    return token.replace("'", "").replace("’", "")


def sentence_mentions(concept: str, sentence: str) -> bool:
    """True when the sentence contains every word of the concept (the same test the lexical analysis uses)."""
    return token_overlap_score(concept, tokenize(sentence)) == 1.0


def sentence_negates(concept: str, sentence: str) -> bool:
    """True when the sentence mentions the concept AND a negation cue is placed so that it can scope over a concept
        word."""
    tokens = tokenize(sentence)
    if token_overlap_score(concept, tokens) != 1.0:
        return False
    concept_words = set(tokenize(concept))
    positions = [i for i, t in enumerate(tokens) if t in concept_words]
    plain = [_plain(t) for t in tokens]
    for i, word in enumerate(plain):
        if word not in NEGATION_CUES or word in concept_words:
            continue
        following = plain[i + 1] if i + 1 < len(plain) else ""
        if following in _NOT_NEGATING_NEXT.get(word, set()):
            continue
        if word in DETERMINER_CUES:
            if any(0 < p - i <= WINDOW for p in positions):
                return True
        elif any(abs(i - p) <= WINDOW for p in positions):
            return True
    return False
