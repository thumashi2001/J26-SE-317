"""Keywords and key phrases of an answer (FR-C3-017): plain word counting, no model.

SIMPLE ENGLISH
    Drop everyday filler words ("the", "is", "of"...), count the words that are left, and report the most frequent ones.
    Two content words that stand next to each other (for example "load balancer") and appear at least twice are
    reported as a phrase. The same answer always gives the same list. This lists what the student WROTE about; it does
    not judge whether the words are correct or important to the question.
"""
from collections import Counter

from app.schemas.analysis import Keyword
from services.preprocessing.text_normalizer import tokenize

MAX_KEYWORDS = 10
MIN_WORD_LENGTH = 3
MIN_PHRASE_COUNT = 2  # an adjacent pair is reported as a phrase only when it is repeated

STOPWORDS = frozenset(
    "a about above after again all also am an and any are as at be because been before being below between both but by "
    "can could did do does doing down during each few for from further had has have having he her here hers him his "
    "how "
    "i if in into is it its itself just me more most my no nor not now of off on once only or other our out over own "
    "same she should so some such than that the their theirs them then there these they this those through to too "
    "under until up very was we were what when where which while who whom why will with would you your".split()
)


def is_content_word(token: str) -> bool:
    """A content word: long enough, not a filler word (numbers and hyphenated terms count)."""
    return token not in STOPWORDS and (len(token) >= MIN_WORD_LENGTH or any(ch.isdigit() for ch in token))


def extract_keywords(sentences: list[str], limit: int = MAX_KEYWORDS) -> list[Keyword]:
    """Most frequent content words and repeated adjacent content-word pairs, ranked by count then first appearance."""
    word_count: Counter[str] = Counter()
    phrase_count: Counter[str] = Counter()
    first_seen: dict[str, int] = {}
    where: dict[str, set[int]] = {}
    position = 0
    for sentence_id, sentence in enumerate(sentences, start=1):
        tokens = tokenize(sentence)
        for index, token in enumerate(tokens):
            if not is_content_word(token):
                continue
            word_count[token] += 1
            where.setdefault(token, set()).add(sentence_id)
            first_seen.setdefault(token, position)
            position += 1
            nxt = tokens[index + 1] if index + 1 < len(tokens) else None
            if nxt is not None and is_content_word(nxt):
                phrase = f"{token} {nxt}"
                phrase_count[phrase] += 1
                where.setdefault(phrase, set()).add(sentence_id)
                first_seen.setdefault(phrase, position)

    candidates = [(term, count, "word") for term, count in word_count.items()]
    candidates += [(term, count, "phrase") for term, count in phrase_count.items() if count >= MIN_PHRASE_COUNT]
    # Higher count first; a phrase before a word on a tie (it is the more specific); then order of first appearance.
    candidates.sort(key=lambda item: (-item[1], item[2] != "phrase", first_seen[item[0]]))
    return [
        Keyword(term=term, count=count, kind=kind, sentence_ids=sorted(where[term]))
        for term, count, kind in candidates[:limit]
    ]
