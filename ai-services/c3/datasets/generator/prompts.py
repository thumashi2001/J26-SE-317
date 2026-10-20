"""Prompt templates. Placeholders look like <<NAME>>; templates are hashed into the manifest."""

from __future__ import annotations

import hashlib

SYSTEM_GENERATOR = (
    "You are a meticulous university software-engineering examiner and dataset author. "
    "Reply with a single valid JSON object only, no markdown."
)
SYSTEM_STUDENT = (
    "You role-play university software-engineering students answering exam questions at a controlled quality "
    "level, for building a marking benchmark. Reply with a single valid JSON object only, no markdown."
)
SYSTEM_GRADER = (
    "You are a strict, independent exam marker. Judge only the student answer against the rubric. "
    "Reply with a single valid JSON object only, no markdown."
)

STRUCTURE_QUESTION = """Analyse this exam question taken from a university software-engineering module.

QUESTION_ID: <<QUESTION_ID>>
TOTAL_MARKS: <<MARKS>>
QUESTION_TEXT (verbatim from the source, may contain OCR noise):
<<<
<<QUESTION_TEXT>>
>>>

Decide:
1. answerable_as_written_text: true only if a student can answer fully in written prose WITHOUT writing source
   code, drawing/producing a diagram, or interpreting a figure/table/code listing that is not reproduced in the text.
   If the question mixes answerable and unanswerable parts, set false (we do not partially keep it).
2. If false, give exclusion_reason (one of: requires_code, requires_diagram, requires_unavailable_figure,
   other) plus a short detail.
3. If true, split into parts. A multi-part question has explicit sub-questions (a), (b), (c) / (i), (ii). For each
   part return part_label ("a","b",...; use "" for a single-part question), text = the part's wording copied
   VERBATIM from QUESTION_TEXT (never paraphrase, never fix typos), marks. Put any shared scenario text that all
   parts need into "stem", also copied verbatim ("" if none). For a single-part question return exactly one part
   with the full text, an empty stem and marks = TOTAL_MARKS.
   If part marks are stated in the text use them and set marks_stated true; otherwise assign sensible marks that
   SUM EXACTLY to TOTAL_MARKS and set marks_stated false.
4. answer_type: one of explanation, discussion, comparison, definition, justification, analysis, other.

Return JSON:
{"answerable_as_written_text": true, "exclusion_reason": "", "stem": "", "marks_stated": false,
 "answer_type": "explanation", "parts": [{"part_label": "", "text": "...", "marks": 10}]}
<<FEEDBACK>>"""

CLEAN_TEXT = """The exam question below was scanned and has whitespace or hyphenation damage (words split across
lines, stray double spaces, soft hyphens). Repair ONLY whitespace and hyphenation. Do not change, add, remove or
re-spell any word, number or symbol, and do not rewrite sentences.

TEXT:
<<<
<<QUESTION_TEXT>>
>>>

Return JSON: {"clean_text": "..."}"""

DRAFT_RUBRIC = """Draft a marking reference and analytic rubric for this software-engineering exam question.

QUESTION_ID: <<QUESTION_ID>>
MODULE: <<MODULE>>
TOTAL_MARKS: <<MARKS>>
QUESTION:
<<<
<<QUESTION_TEXT>>
>>>

Return JSON with exactly these keys:
- reference_answer: a genuine model answer a strong student could write, <<REF_WORDS>> words, specific to the
  question (name concrete techniques, trade-offs, examples).
- expected_concepts: 3 to 8 concrete technical terms/phrases (each 1-5 words) that a correct answer must use. No
  placeholders such as "conceptual understanding" or "supporting evidence".
- concept_graph: list of {"source","target","type"} edges between expected_concepts only; type is one of
  prerequisite_of, part_of, depends_on, contrasts_with, causes, example_of.
- common_misconceptions: 2 to 4 objects {"claim": a plausible but WRONG technical statement students make about this
  topic, "correct": the correct statement, "criterion_index": 0-based index of the criterion it undermines}.
- criteria: 3 to 5 rubric criteria preferred (2 to 6 allowed; fewer than 3 makes the tiers hard to separate).
  Each: {"description","max_marks","required_concepts","scoring_levels"}.
  * sum of max_marks over criteria == <<MARKS>> exactly. Use unequal weights where the question's emphasis differs
    (do not make all criteria equal when there are 3 or more).
  * scoring_levels: 3 to 5 levels in increasing order, each {"label","mark","descriptor","required_concepts",
    "min_demonstrated"}. The first level MUST have mark 0 (nothing creditable). Marks strictly increase; the last
    (top) level mark == the criterion's max_marks. Intermediate marks should be non-round where natural (e.g. 1.5,
    2.5, 3.5) and level steps must differ between criteria.
  * descriptors must describe observable answer content for that level (what is stated, how accurately), and must
    be specific to this question.
  * required_concepts (criterion and levels) must be copied exactly from expected_concepts; mark-0 level has [].
  * min_demonstrated: integer 1..len(level.required_concepts) (the number of that level's concepts that must be
    shown); omit or use 0 for the mark-0 level.
<<FEEDBACK>>"""

GENERATE_ANSWERS = """You will write <<COUNT>> distinct exam answers to the question below, each as a different
university student. Each answer has a TARGET quality fixed by the marking rubric. Hit the target exactly: neither
better nor worse.

QUESTION (<<MARKS>> marks):
<<<
<<QUESTION_TEXT>>
>>>

REFERENCE ANSWER (for your understanding only; do NOT copy or closely paraphrase it unless told):
<<<
<<REFERENCE>>
>>>

EXPECTED CONCEPTS: <<CONCEPTS>>

TIER MEANING: <<TIER_INSTRUCTION>>

RUBRIC CRITERIA AND THE LEVEL EACH ANSWER MUST REACH:
<<ANSWER_SPECS>>

Hard rules:
- Write as a student would. Do NOT echo rubric wording, do NOT mention marks, rubrics, "this answer", or
  meta-comments such as "the answer does not cover". Never describe what is missing; just omit it.
- Vary sentence openings and structure between answers; no shared boilerplate.
- Follow each answer's style (word range) and register exactly. Length must reflect STYLE only, never quality: a
  verbose weak answer is padded with on-topic but non-credit-worthy material (background, restating the
  question, examples that do not satisfy the descriptors); a concise strong answer is dense.
- register: formal = academic prose; informal = casual first-person student voice; minor_typos = a few natural
  spelling slips.
<<EXTRA_RULES>>
Return JSON:
{"answers": [{"student_answer": "...", "concept_status": {"<concept>": "demonstrated|partial|missing|incorrect"}}]}
with exactly <<COUNT>> answers in the order given, and concept_status covering ALL expected concepts exactly as
spelled above (demonstrated = correctly and clearly explained; partial = mentioned/vague/incomplete; missing = not
present; incorrect = stated wrongly).
<<FEEDBACK>>"""

BLIND_GRADE = """Mark the student answer using the rubric. For EACH criterion choose the single scoring level whose
descriptor best matches the answer. Judge strictly on content; ignore length and style.

QUESTION (<<MARKS>> marks):
<<<
<<QUESTION_TEXT>>
>>>

RUBRIC:
<<RUBRIC>>

STUDENT ANSWER:
<<<
<<ANSWER>>
>>>

Return JSON: {"criteria": [{"criterion_id": "...", "level_id": "..."}]} with one entry per criterion."""

TEMPLATES = {
    "structure_question": STRUCTURE_QUESTION,
    "clean_text": CLEAN_TEXT,
    "draft_rubric": DRAFT_RUBRIC,
    "generate_answers": GENERATE_ANSWERS,
    "blind_grade": BLIND_GRADE,
}

TIER_INSTRUCTIONS = {
    "FULL": "complete, accurate, well-explained answer reaching the top level on every criterion.",
    "MOSTLY_CORRECT": "mostly complete and accurate; one criterion is handled slightly less well than the top level.",
    "PARTIAL": "covers each area but only to a middling level: some points vague, shallow or incomplete.",
    "MISSING_CONCEPT": "good on the criteria marked as top level, and silent on the others. NEVER mention the "
    "omitted concepts (listed per answer) or hint at them.",
    "MISCONCEPTION": "confident and fluent but asserts specific WRONG technical claims (use the supplied "
    "misconceptions or invent similar ones). Do not hedge; state the wrong claims as fact.",
    "IRRELEVANT": "earns no credit. Follow each answer's sub_kind: same_domain_wrong_topic = accurate material about "
    "a different software-engineering topic; generic_padding = vague waffle about software or studying with no "
    "technical content; unrelated_essay = an essay on an entirely different (non-technical) subject; "
    "keyword_stuffed = a list/jumble of the rubric's technical terms with no explanation or relationships.",
    "CONTRADICTORY": "states a correct key claim and then negates or reverses it in the same answer, so the net "
    "position is incoherent.",
    "PARAPHRASE_FULL": "re-express the SOURCE ANSWER given below with completely different wording and sentence "
    "structure, keeping exactly the same technical content and accuracy.",
    "TYPO_FULL": "full-credit content (as FULL) but written with many natural spelling mistakes, missing letters and "
    "swapped characters, as typed quickly.",
}


def render(template: str, **values: str) -> str:
    out = template
    for key, value in values.items():
        out = out.replace(f"<<{key.upper()}>>", str(value))
    return out


def prompt_hashes() -> dict[str, str]:
    return {name: hashlib.sha256(text.encode("utf-8")).hexdigest() for name, text in sorted(TEMPLATES.items())}
