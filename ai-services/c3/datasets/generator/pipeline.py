# ruff: noqa: E501
"""End-to-end orchestration: scope -> rubric -> plan -> generate -> verify -> annotate -> split -> write."""

from __future__ import annotations

import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from . import DATASET_VERSION
from .checks import (
    answer_flags,
    derive_evidence_spans,
    derive_gold_mindmap,
    normalized_hash,
    split_sentences,
    tier_order_violations,
)
from .llm_tasks import DraftedRubric, GeneratedAnswer, LLMTaskError, LLMTasks, LLMValidationError
from .planning import AnswerPlan, TierCollapse, build_question_plans, deterministic_answer
from .prompts import prompt_hashes
from .source import SourceQuestion, normalize_ws, ocr_noise_ratio
from .splitting import SplitError, build_parent_docs, check_answer_leakage, split_parents
from .writer import ReleaseData

log = logging.getLogger("c3.generator")
LLM_EDGE_TIERS = ("CONTRADICTORY", "PARAPHRASE_FULL", "TYPO_FULL")


@dataclass
class PartCtx:
    question_id: str
    parent_id: str
    part_label: str
    module_code: str
    source_type: str
    marks: float
    raw: str
    text: str
    ocr_ratio: float
    answer_type: str
    draft: DraftedRubric
    structure_hash: str
    plans: list[AnswerPlan] = field(default_factory=list)


@dataclass
class Outcome:
    source_id: str
    parts: list[PartCtx] = field(default_factory=list)
    answers: list[dict] = field(default_factory=list)
    rejected: list[dict] = field(default_factory=list)
    excluded: dict | None = None
    failure: dict | None = None


def _concept_status_flags(plan: AnswerPlan, status: dict[str, str]) -> list[str]:
    flags = []
    if plan.tier in ("FULL", "PARAPHRASE_FULL", "TYPO_FULL") and "incorrect" in status.values():
        flags.append("full_answer_has_incorrect_concept")
    if plan.tier == "MISSING_CONCEPT":
        flags += [
            f"omitted_concept_marked_present:{c}"
            for c in plan.omitted_concepts
            if status.get(c) in ("demonstrated", "partial")
        ]
    return flags


def _paraphrase_extra(source_answer: str) -> str:
    return f"SOURCE ANSWER to paraphrase:\n<<<\n{source_answer}\n>>>"


class Pipeline:
    def __init__(
        self,
        tasks: LLMTasks,
        spec: dict,
        seed: int,
        n_per_tier: int,
        generator_model: str,
        verifier_model: str,
        workers: int = 1,
    ) -> None:
        self.tasks, self.spec, self.seed, self.n = tasks, spec, seed, n_per_tier
        self.generator_model, self.verifier_model, self.workers = generator_model, verifier_model, workers
        self.th = spec["thresholds"]
        self.failures: list[dict] = []

    # -- per source question -------------------------------------------------------------------------------
    def process_question(self, q: SourceQuestion) -> Outcome:
        out = Outcome(q.question_id)

        def exclude(stage: str, reason: str) -> Outcome:
            out.parts, out.answers, out.rejected = [], [], []
            out.excluded = {
                "question_id": q.question_id, "module_code": q.module_code, "source_type": q.source_type,
                "question_text_raw": q.question_text, "stage": stage, "reason": reason,
                "dataset_version": DATASET_VERSION,
            }  # fmt: skip
            return out

        try:
            text = normalize_ws(q.question_text)
            ratio = ocr_noise_ratio(q.question_text)
            if ratio > self.th["max_ocr_noise_ratio"]:
                try:
                    cleaned = self.tasks.clean_text(q.question_id, q.question_text)
                except LLMValidationError as exc:
                    return exclude("ocr", f"ocr_noise_unrepairable: {exc.message}")
                new_ratio = ocr_noise_ratio(cleaned)
                if new_ratio > self.th["max_ocr_noise_ratio"]:
                    return exclude("ocr", f"ocr_noise_ratio_{ratio:.3f}_remains_{new_ratio:.3f}_after_cleaning")
                text, ratio = cleaned, new_ratio
            work = SourceQuestion(
                q.question_id, q.module_code, q.source_type, q.legacy_replaced_question_id, text, q.marks
            )
            try:
                st = self.tasks.structure_question(work)
            except LLMValidationError as exc:
                return exclude("structure", f"structure_invalid: {exc.message}")
            if not st.answerable:
                return exclude("scope", st.exclusion_reason)
            multi = len(st.parts) > 1
            for p in st.parts:
                qid = f"{q.question_id}-{p.part_label}" if multi else q.question_id
                body = normalize_ws(f"{st.stem} {p.text}") if multi else text
                raw = body if multi else q.question_text
                if multi and text != normalize_ws(q.question_text):
                    raw = q.question_text
                try:
                    draft = self.tasks.draft_rubric(qid, q.module_code, p.marks, body)
                except LLMValidationError as exc:
                    return exclude("rubric", f"rubric_invalid_after_retries ({qid}): {exc.message}")
                out.parts.append(
                    PartCtx(qid, q.question_id, p.part_label, q.module_code, q.source_type, p.marks, raw, body,
                            ratio, st.answer_type, draft, st.prompt_hash)
                )  # fmt: skip
            for part in out.parts:
                misc = [m["criterion_index"] for m in part.draft.misconceptions]
                try:
                    part.plans = build_question_plans(
                        part.question_id, part.draft.rubric, self.spec, self.seed, self.n, misc
                    )
                except TierCollapse as exc:
                    return exclude("planning", f"tier_collapse ({part.question_id}): {exc}")
            for part in out.parts:
                self._answers_for_part(part, out)
            for part in out.parts:
                reason = self._missing_tier_reason(part, out)
                if reason:
                    return exclude("generation", reason)
            return out
        except LLMTaskError as exc:
            out.failure = {"question_id": q.question_id, "task": exc.task, "key": exc.key, "message": exc.message}
            return out

    def _missing_tier_reason(self, part: PartCtx, out: Outcome) -> str:
        mine = [a for a in out.answers if a["question_id"] == part.question_id]
        have = {a["tier"] for a in mine}
        gone = [t for t in self.spec["core_tiers"] if t not in have]
        if gone:
            return f"tier_missing_after_rejection ({part.question_id}): {gone}"
        means = {t: sum(a["normalized_mark"] for a in mine if a["tier"] == t) / sum(1 for a in mine if a["tier"] == t)
                 for t in self.spec["core_tiers"]}  # fmt: skip
        bad = tier_order_violations(means, self.spec)
        return f"tier_collapse_after_rejection ({part.question_id}): {bad[0]}" if bad else ""

    # -- generation -----------------------------------------------------------------------------------------
    def _answer_specs(self, part: PartCtx, tier: str, plans: list[AnswerPlan]) -> str:
        rubric = part.draft.rubric
        crit = {c.criterion_id: c for c in rubric.criteria}
        rng = self.spec["style_word_ranges"]
        lines = []
        for i, p in enumerate(plans, 1):
            head = f"Answer {i}: style={p.style} ({rng[p.style]['min']}-{rng[p.style]['max']} words), register={p.register}"
            if p.sub_kind != "standard":
                head += f", sub_kind={p.sub_kind}"
            lines.append(head)
            if tier == "IRRELEVANT":
                if p.sub_kind == "keyword_stuffed":
                    lines.append("  terms to stuff without explanation: " + "; ".join(part.draft.expected_concepts))
                continue
            for cl in p.criterion_levels:
                c = crit[cl["criterion_id"]]
                lv = next(lv for lv in c.scoring_levels if lv.level_id == cl["level_id"])
                lines.append(f"  - {c.description} -> must reach: {lv.label}: {lv.descriptor}")
            if p.omitted_concepts:
                lines.append("  never mention or allude to: " + "; ".join(p.omitted_concepts))
            if tier == "MISCONCEPTION":
                mine = [
                    m
                    for m in part.draft.misconceptions
                    if f"{part.question_id}-C{m['criterion_index'] + 1}" in p.misconception_criteria
                ]
                claims = (mine or part.draft.misconceptions)[:2]
                lines.append("  wrong claims to assert confidently: " + " | ".join(m["claim"] for m in claims))
        return "\n".join(lines)

    def _generate_tier(
        self, part: PartCtx, tier: str, plans: list[AnswerPlan], siblings: list[str], extra: str = "", start: int = 0
    ) -> tuple[dict[str, GeneratedAnswer], dict[str, list[str]]]:
        accepted: dict[str, GeneratedAnswer] = {}
        failed: dict[str, list[str]] = {}
        pending = list(plans)
        feedback = ""
        for attempt in range(start, start + self.th["max_regeneration_tries"]):
            if not pending:
                break
            gens = self.tasks.generate_answers(
                key=f"{part.question_id}:{tier}",
                question_text=part.text,
                marks=part.marks,
                reference=part.draft.reference_answer,
                concepts=part.draft.expected_concepts,
                tier=tier,
                answer_specs=self._answer_specs(part, tier, pending),
                count=len(pending),
                attempt=attempt,
                feedback=feedback,
                extra_rules=extra,
            )
            nxt, notes = [], []
            for i, (plan, g) in enumerate(zip(pending, gens, strict=True), 1):
                known = siblings + [a.text for a in accepted.values()]
                flags = answer_flags(
                    g.text, tier, plan.style, part.draft.reference_answer, plan.omitted_concepts, known, self.spec
                ) + _concept_status_flags(plan, g.concept_status)
                if flags:
                    nxt.append(plan)
                    failed[plan.answer_id] = flags
                    notes.append(f"answer {i}: {', '.join(flags)}")
                else:
                    accepted[plan.answer_id] = g
                    failed.pop(plan.answer_id, None)
            pending = nxt
            feedback = (
                ("\nThe previous attempt was rejected: " + " ; ".join(notes) + ". Rewrite those answers.")
                if notes
                else ""
            )
        return accepted, {p.answer_id: failed[p.answer_id] for p in pending}

    def _record(self, part: PartCtx, plan: AnswerPlan, text: str, status: dict[str, str], gen_hash: str) -> dict:
        concepts = part.draft.expected_concepts
        if plan.tier in ("EMPTY", "IRRELEVANT", "TOO_SHORT"):
            status = dict.fromkeys(concepts, "missing")
        status = {c: status[c] for c in concepts}
        return {
            "answer_id": plan.answer_id, "question_id": part.question_id, "parent_question_id": part.parent_id,
            "split": "", "tier": plan.tier, "sub_kind": plan.sub_kind, "style": plan.style, "register": plan.register,
            "student_answer": text, "word_count": len(text.split()), "expected_mark": plan.expected_mark,
            "max_marks": plan.max_marks, "normalized_mark": round(plan.normalized, 6),
            "criterion_marks": plan.criterion_levels, "concept_status": status,
            "incorrect_concepts": [c for c, s in status.items() if s == "incorrect"],
            "evidence_spans": derive_evidence_spans(text, status),
            "gold_mindmap": derive_gold_mindmap(status, part.draft.concept_graph, plan.tier),
            "generation_seed": plan.seed, "generator_model": self.generator_model,
            "prompt_hash": gen_hash or "deterministic_no_llm",
            "blind_grade_agreement": 1.0, "needs_review": False, "blind_grade_levels": {},
            "blind_grade_mark": plan.expected_mark, "verification": "deterministic", "check_flags": [],
            "dataset_version": DATASET_VERSION,
        }  # fmt: skip

    def _blind_grade(self, part: PartCtx, plan: AnswerPlan, rec: dict) -> None:
        bg = self.tasks.blind_grade(plan.answer_id, part.text, part.marks, part.draft.rubric, rec["student_answer"])
        n_match, mark, gap = 0, 0.0, 0
        for cl, crit in zip(plan.criterion_levels, part.draft.rubric.criteria, strict=True):
            order = [lv.level_id for lv in sorted(crit.scoring_levels, key=lambda lv: lv.mark)]
            chosen = bg.levels[crit.criterion_id]
            n_match += chosen == cl["level_id"]
            mark += next(lv.mark for lv in crit.scoring_levels if lv.level_id == chosen)
            gap = max(gap, abs(order.index(chosen) - order.index(cl["level_id"])))
        rec.update(
            blind_grade_agreement=round(n_match / len(plan.criterion_levels), 4),
            blind_grade_levels=bg.levels,
            blind_grade_mark=round(mark, 4),
            verification="blind_llm",
            needs_review=gap >= self.th["needs_review_level_gap"]
            or abs(mark - plan.expected_mark) > self.th["needs_review_total_deviation"] * plan.max_marks,
        )

    def _answers_for_part(self, part: PartCtx, out: Outcome) -> None:
        by_tier: dict[str, list[AnswerPlan]] = defaultdict(list)
        for p in part.plans:
            by_tier[p.tier].append(p)
        texts: list[str] = []
        recs: dict[str, tuple[AnswerPlan, dict]] = {}

        def reject(plan: AnswerPlan, text: str, reasons: list[str]) -> None:
            out.rejected.append({
                "answer_id": plan.answer_id, "question_id": part.question_id, "tier": plan.tier,
                "student_answer": text or "(none)", "reasons": reasons, "dataset_version": DATASET_VERSION,
            })  # fmt: skip

        for tier in ("EMPTY", "TOO_SHORT"):
            for plan in by_tier[tier]:
                for attempt in range(60):
                    t = deterministic_answer(plan, part.text, attempt)
                    if tier == "EMPTY" or normalized_hash(t) not in {normalized_hash(x) for x in texts}:
                        break
                if tier != "EMPTY":
                    texts.append(t)
                recs[plan.answer_id] = (plan, self._record(part, plan, t, {}, ""))
        full_text = ""
        for tier in [*self.spec["core_tiers"], *LLM_EDGE_TIERS]:
            plans = by_tier[tier]
            extra = ""
            if tier == "PARAPHRASE_FULL":
                full_text = next((r["student_answer"] for pl, r in recs.values() if pl.tier == "FULL"), "")
                if not full_text:
                    continue
                extra = _paraphrase_extra(full_text)
            accepted, failed = self._generate_tier(part, tier, plans, texts, extra)
            for plan in plans:
                if plan.answer_id in accepted:
                    g = accepted[plan.answer_id]
                    texts.append(g.text)
                    recs[plan.answer_id] = (plan, self._record(part, plan, g.text, g.concept_status, g.prompt_hash))
                else:
                    reject(plan, "", failed.get(plan.answer_id, ["not_generated"]))
        for plan, rec in recs.values():
            if rec["verification"] == "deterministic" and plan.tier not in ("EMPTY", "TOO_SHORT"):
                self._blind_grade(part, plan, rec)
        out.answers += [rec for _, rec in sorted(recs.values(), key=lambda pr: pr[0].answer_id)]

    # -- global stage ------------------------------------------------------------------------------------------
    def _regen_duplicates(self, outcomes: list[Outcome]) -> None:
        """Make answer text unique across the WHOLE dataset (exact normalised duplicates are regenerated or rejected)."""
        seen: set[str] = set()
        seen_texts: list[str] = []
        for oc in outcomes:
            ctx = {p.question_id: p for p in oc.parts}
            plans = {pl.answer_id: pl for p in oc.parts for pl in p.plans}
            for rec in list(oc.answers):
                text = rec["student_answer"]
                if not text.strip():
                    continue
                h = normalized_hash(text)
                if h not in seen:
                    seen.add(h)
                    seen_texts.append(text)
                    continue
                part, plan = ctx[rec["question_id"]], plans[rec["answer_id"]]
                new = None
                if plan.tier == "TOO_SHORT":
                    for attempt in range(1, 200):
                        t = deterministic_answer(plan, part.text, attempt)
                        if normalized_hash(t) not in seen:
                            new = (t, {}, "")
                            break
                else:
                    siblings = [r["student_answer"] for r in oc.answers if r is not rec] + [""]
                    extra = ""
                    if plan.tier == "PARAPHRASE_FULL":
                        src = next(
                            (
                                r["student_answer"]
                                for r in oc.answers
                                if r["tier"] == "FULL" and r["question_id"] == rec["question_id"]
                            ),
                            "",
                        )
                        extra = _paraphrase_extra(src)
                    acc, _ = self._generate_tier(part, plan.tier, [plan], siblings + seen_texts, extra, start=10)
                    g = acc.get(plan.answer_id)
                    if g and normalized_hash(g.text) not in seen:
                        new = (g.text, g.concept_status, g.prompt_hash)
                if new is None:
                    oc.answers.remove(rec)
                    oc.rejected.append({
                        "answer_id": rec["answer_id"], "question_id": rec["question_id"], "tier": rec["tier"],
                        "student_answer": text, "reasons": ["cross_question_exact_duplicate"],
                        "dataset_version": DATASET_VERSION,
                    })  # fmt: skip
                    continue
                fresh = self._record(part, plan, new[0], new[1], new[2])
                if rec["verification"] == "blind_llm":
                    self._blind_grade(part, plan, fresh)
                rec.clear()
                rec.update(fresh)
                seen.add(normalized_hash(new[0]))
                seen_texts.append(new[0])

    # -- full run --------------------------------------------------------------------------------------------------
    def run(self, questions: list[SourceQuestion]) -> tuple[ReleaseData | None, list[dict]]:
        if self.workers > 1:
            with ThreadPoolExecutor(max_workers=self.workers) as pool:
                outcomes = list(pool.map(self.process_question, questions))
        else:
            outcomes = []
            for i, q in enumerate(questions, 1):
                outcomes.append(self.process_question(q))
                log.info("[%d/%d] %s", i, len(questions), q.question_id)
        failures = [o.failure for o in outcomes if o.failure]
        if failures:
            return None, failures
        try:
            self._regen_duplicates(outcomes)
        except LLMTaskError as exc:
            return None, [{"question_id": "(dedupe)", "task": exc.task, "key": exc.key, "message": exc.message}]
        excluded = [o.excluded for o in outcomes if o.excluded]
        for o in outcomes:
            if o.excluded is None:
                for part in o.parts:
                    reason = self._missing_tier_reason(part, o)
                    if reason:
                        o.excluded = {
                            "question_id": o.source_id, "module_code": part.module_code, "source_type": part.source_type,
                            "question_text_raw": part.raw, "stage": "dedupe", "reason": reason,
                            "dataset_version": DATASET_VERSION,
                        }  # fmt: skip
                        excluded.append(o.excluded)
                        break
        kept = [o for o in outcomes if o.excluded is None]
        parts = [p for o in kept for p in o.parts]
        q_rows = [self._question_row(p) for p in parts]
        try:
            split_of = split_parents(build_parent_docs(q_rows), self.spec, self.seed)
        except SplitError as exc:
            return None, [{"question_id": "(split)", "task": "splitting", "key": "", "message": str(exc)}]
        for r in q_rows:
            r["split"] = split_of[r["parent_question_id"]]
        a_rows = [a for o in kept for a in o.answers]
        for a in a_rows:
            a["split"] = split_of[a["parent_question_id"]]
        try:
            by_split: dict[str, list[str]] = defaultdict(list)
            for a in a_rows:
                by_split[a["split"]].append(a["student_answer"])
            check_answer_leakage(by_split)
        except SplitError as exc:
            return None, [{"question_id": "(leakage)", "task": "splitting", "key": "", "message": str(exc)}]
        rubric_rows = [row for p in parts for row in self._rubric_rows(p)]
        for a in a_rows:  # sanity: spans stay within the sentence count
            n_sent = len(split_sentences(a["student_answer"]))
            assert all(i < n_sent for v in a["evidence_spans"].values() for i in v)
        meta = {
            "n_per_tier": self.n, "generator_model": self.generator_model, "verifier_model": self.verifier_model,
            "prompt_hashes": prompt_hashes(), "source_questions": len(questions),
            "llm_calls_this_run": dict(self.tasks.stats.calls),
        }  # fmt: skip
        rejected = [r for o in kept for r in o.rejected]
        return ReleaseData(q_rows, rubric_rows, a_rows, excluded, rejected, meta), []

    def _question_row(self, p: PartCtx) -> dict:
        return {
            "question_id": p.question_id, "parent_question_id": p.parent_id, "part_label": p.part_label,
            "module_code": p.module_code, "source_type": p.source_type, "split": "",
            "question_text_raw": p.raw, "question_text": p.text, "ocr_noise_ratio": p.ocr_ratio,
            "max_marks": p.marks, "answer_type": p.answer_type, "reference_answer": p.draft.reference_answer,
            "expected_concepts": p.draft.expected_concepts, "concept_graph": p.draft.concept_graph,
            "rubric_id": p.draft.rubric.rubric_id, "rubric_status": "llm_drafted_unverified",
            "scope_status": "in_scope_text_answerable", "generator_model": self.generator_model,
            "structure_prompt_hash": p.structure_hash, "rubric_prompt_hash": p.draft.prompt_hash,
            "dataset_version": DATASET_VERSION,
        }  # fmt: skip

    @staticmethod
    def _rubric_rows(p: PartCtx) -> list[dict]:
        rub = p.draft.rubric
        return [
            {
                "rubric_id": rub.rubric_id, "question_id": p.question_id, "rubric_title": rub.title,
                "criterion_id": c.criterion_id, "criterion_index": i, "description": c.description,
                "max_marks": c.max_marks, "required_concepts": c.required_concepts,
                "scoring_levels": [lv.model_dump(mode="json") for lv in c.scoring_levels],
                "rubric_status": "llm_drafted_unverified", "dataset_version": DATASET_VERSION,
            }
            for i, c in enumerate(rub.criteria)
        ]  # fmt: skip


def cache_dir(out_dir: Path) -> Path:
    return out_dir / "_llm_cache"
