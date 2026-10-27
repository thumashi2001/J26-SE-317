# Annotation guidelines — semantic paraphrase benchmark v1

Status: **ready for human annotation. No human has labelled any item yet.** The item texts were drafted by an AI assistant
(Claude, 2026-10-27); the `draft.proposed_label` field is that drafter's intent and is **not ground truth**. Annotators never see it.

## The question you answer
For each row you get a question, **one concept**, and a student answer. Decide whether *this answer* shows an understanding of
*that concept*. Judge meaning, not wording: an answer can show the concept without using its name, and can use the name
without showing the concept. Ignore spelling and grammar. Judge only the concept given, not the whole answer.

## Labels (choose exactly one)
| Label | Use when |
|---|---|
| `demonstrated` | The answer clearly expresses the concept's core meaning, in any wording or terminology, with no conflicting statement about it. |
| `partial` | The answer touches the concept but is incomplete or too vague to show the core idea (for example names the area but not what makes it the concept). |
| `missing` | The answer does not address the concept (off topic, only generic, or the concept's words appear in an unrelated sense). |
| `contradicted` | The answer states something about the concept that is wrong or opposite (including negating it), whether or not it uses the concept's words. |

Tie-breaks: wrong beats incomplete (`contradicted` over `partial`); if the core idea is present but with one minor slip, use `partial`.
Do not use your own opinion about how good the answer is overall. Do not use outside tools or models to decide.

## Rationale (required)
One sentence saying which words or claim in the answer led to your label, e.g. "says each fact is stored once = removes
repetition". A label without a rationale is rejected.

## Process
1. The custodian generates **blind sheets** (`sheets.blind_rows` then `sheets.write_sheet`, kept outside the dataset folder): they hold only
   item id, question, concept, answer, and empty `label` / `rationale` columns. Category, split, group and the draft label are removed.
2. **At least two** annotators label every item **independently** (pseudonyms `ANN01`, `ANN02`, ...). They do not see each other's
   sheets or any model output.
3. Where labels differ, an **adjudicator** (`ADJ01`, who is not one of the two annotators for that item) decides and writes a rationale.
4. Returns are ingested with `sheets.ingest_returns` / `sheets.ingest_adjudication`. Status is then derived automatically
   (`human_labelled`, `adjudicated`, `needs_adjudication`).
5. Record in the manifest: who annotated (pseudonyms only, no real names in the repo), when, the guidelines version, and agreement
   (exact agreement; kappa if enough items). Choose any agreement threshold *before* looking at model results.

## Rules that protect the evaluation
- Annotators and the adjudicator must not have seen model outputs or the draft labels.
- Do not edit item text after annotation starts (the content hash would change and the frozen configuration is then refused).
- The **dev** split is used to choose the semantic threshold; the **heldout** split is scored once.
- Dev and held-out items come from different groups (different questions/concepts); do not move items between splits.
- Item authors must not annotate their own items where avoidable; if the drafter is also an annotator, record it.
