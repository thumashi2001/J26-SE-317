"""Step 0 of every analysis: turn the student's raw text into clean, comparable pieces.

SIMPLE ENGLISH
    The student's answer is just text. Before the system can look for concepts it needs (1) the text with tidy spacing,
    (2) the text split into sentences (so evidence can point at "sentence 2"), and (3) a list of lowercase words.
    Nothing here understands meaning; it only cleans and splits, and it always gives the same output for the same input.
"""
import re
from dataclasses import dataclass

# A "word" = letters/digits, optionally joined by a hyphen or apostrophe (so "high-level" stays one word).
_TOKEN_PATTERN = re.compile(r"[^\W_]+(?:[-'’][^\W_]+)*", re.UNICODE)
# A sentence ends at . ! or ? followed by whitespace.
_SENTENCE_BOUNDARY_PATTERN = re.compile(r"(?<=[.!?])\s+")
# Markup is not answer content (FR-C3-05): drop <script>/<style> blocks entirely, then any remaining HTML-like tag.
# The tag pattern requires a letter or "/" after "<", so plain maths such as "a < b" or "x <= 3" is left alone.
_SCRIPT_STYLE_PATTERN = re.compile(r"<(script|style)\b[^>]*>.*?</\1\s*>", re.IGNORECASE | re.DOTALL)
_TAG_PATTERN = re.compile(r"</?[A-Za-z][^<>]*>")


@dataclass(frozen=True)
class ProcessedText:
    """The three views of one answer used by later steps."""

    normalized_text: str
    sentences: list[str]
    tokens: list[str]


def normalize_text(text: str) -> str:
    """Strip HTML-like markup and normalize whitespace, keeping all meaningful words and punctuation."""
    # Remove markup first (replaced by a space so words either side of a tag do not fuse), then collapse whitespace.
    without_markup = _TAG_PATTERN.sub(" ", _SCRIPT_STYLE_PATTERN.sub(" ", text))
    # Collapse runs of spaces/newlines/tabs into one space, then trim the ends.
    whitespace_normalized = re.sub(r"\s+", " ", without_markup)
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
    # casefold() = a stronger lowercase, so "Components" and "components" are the same token.
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
