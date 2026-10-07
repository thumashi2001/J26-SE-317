from dataclasses import dataclass
import re


_TOKEN_PATTERN = re.compile(r"[^\W_]+(?:[-'’][^\W_]+)*", re.UNICODE)
_SENTENCE_BOUNDARY_PATTERN = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class ProcessedText:
    normalized_text: str
    sentences: list[str]
    tokens: list[str]


def normalize_text(text: str) -> str:
    """Normalize whitespace without removing meaningful words or punctuation."""
    whitespace_normalized = re.sub(r"\s+", " ", text)
    return whitespace_normalized.strip()


def extract_sentences(normalized_text: str) -> list[str]:
    """Split normalized text at punctuation followed by whitespace."""
    if not normalized_text:
        return []
    return [
        sentence.strip()
        for sentence in _SENTENCE_BOUNDARY_PATTERN.split(normalized_text)
        if sentence.strip()
    ]


def tokenize(text: str) -> list[str]:
    """Return lowercase word-like tokens using only the standard library."""
    return [match.casefold() for match in _TOKEN_PATTERN.findall(text)]


def process_text(text: str) -> ProcessedText:
    """Produce deterministic normalized text, sentences, and tokens."""
    normalized_text = normalize_text(text)
    sentences = extract_sentences(normalized_text)
    tokens = tokenize(normalized_text)
    return ProcessedText(
        normalized_text=normalized_text,
        sentences=sentences,
        tokens=tokens,
    )
