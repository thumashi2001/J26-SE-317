"""Answer planning: labels are the sum of explicit rubric level marks, never a percentage formula."""

from __future__ import annotations

import hashlib
import math
import random
import re
from dataclasses import dataclass, field

from app.schemas.marking import Rubric, RubricCriterion, ScoringLevel

from .checks import in_range, tier_order_violations

MAX_PLAN_ATTEMPTS = 60


class TierCollapse(Exception):
    """The drafted rubric cannot realise the required tier ordering."""


def stable_int(*parts: object) -> int:
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()
    return int(digest[:12], 16)


@dataclass
class AnswerPlan:
    answer_id: str
    question_id: str
    tier: str
    slot: int
    sub_kind: str
    style: str
    register: str
    seed: int
    max_marks: float
    expected_mark: float
    criterion_levels: list[dict] = field(default_factory=list)  # {criterion_id, level_id, mark}
    target_concepts: list[str] = field(default_factory=list)
    omitted_concepts: list[str] = field(default_factory=list)
    misconception_criteria: list[str] = field(default_factory=list)

    @property
    def normalized(self) -> float:
        return self.expected_mark / self.max_marks


def _sorted_levels(c: RubricCriterion) -> list[ScoringLevel]:
    return sorted(c.scoring_levels, key=lambda lv: lv.mark)


def choose_level_indices(kind: str, rubric: Rubric, rng: random.Random, rule: dict, misc_idx: list[int]) -> list[int]:
    """Index into each criterion's mark-sorted levels (0 = zero level, last = top)."""
    k = len(rubric.criteria)
    sizes = [len(c.scoring_levels) for c in rubric.criteria]
    if kind == "all_top":
        return [n - 1 for n in sizes]
    if kind == "all_zero":
        return [0] * k
    if kind == "all_top_except_one_lower":
        idx = [n - 1 for n in sizes]
        j = rng.randrange(k)
        idx[j] = sizes[j] - 2
        return idx
    if kind == "middle":
        out = []
        for n in sizes:
            cands = sorted({c for c in ((n - 1) // 2, n // 2) if 1 <= c <= n - 2})
            if rule.get(
                "relaxed"
            ):  # late attempts: allow the upper non-top levels so PARTIAL can clear MISSING_CONCEPT
                cands = list(range(max(1, n - 3), n - 1))
            out.append(rng.choice(cands))
        return out
    if kind == "half_top_half_zero":
        # top level on about half of the criteria, preferring the lighter-weighted ones so the tier stays below PARTIAL
        n_top = max(1, min(k - 1, round(k * rule.get("top_fraction", 0.5) - 0.01)))
        lightest = sorted(range(k), key=lambda i: rubric.criteria[i].max_marks)[: min(k, n_top + 1)]
        top = set(rng.sample(lightest, n_top))
        return [sizes[i] - 1 if i in top else 0 for i in range(k)]
    if kind == "misconception":
        n_rel = max(1, math.ceil(k * rule.get("related_fraction", 0.6)))
        related = [i for i in dict.fromkeys(misc_idx) if 0 <= i < k][:n_rel]
        pool = [i for i in range(k) if i not in related]
        rng.shuffle(pool)
        related += pool[: n_rel - len(related)]
        others = [i for i in range(k) if i not in related]
        idx = [0] * k
        if others and rng.random() < 0.5:
            for i in others[: rule.get("max_lowest_nonzero_criteria", 1)]:
                idx[i] = 1
        return idx
    if kind == "lowest_nonzero_on_half":
        chosen = set(rng.sample(range(k), math.ceil(k / 2)))
        return [1 if i in chosen else 0 for i in range(k)]
    raise ValueError(f"unknown plan rule kind: {kind}")


def _make_plan(
    question_id: str, tier: str, slot: int, rubric: Rubric, idx: list[int], seed: int, sub_kind: str
) -> AnswerPlan:
    levels, targets, omitted_pool, kept_pool = [], [], [], []
    for c, i in zip(rubric.criteria, idx, strict=True):
        lv = _sorted_levels(c)[i]
        levels.append({"criterion_id": c.criterion_id, "level_id": lv.level_id, "mark": lv.mark})
        if lv.mark > 0:
            targets += lv.required_concepts or c.required_concepts
            kept_pool += c.required_concepts + lv.required_concepts
        else:
            omitted_pool += c.required_concepts
    kept = {x.casefold() for x in kept_pool}
    omitted = [c for c in dict.fromkeys(omitted_pool) if c.casefold() not in kept]
    max_marks = sum(c.max_marks for c in rubric.criteria)
    return AnswerPlan(
        answer_id=f"{question_id}-{tier}-{slot + 1}",
        question_id=question_id,
        tier=tier,
        slot=slot,
        sub_kind=sub_kind,
        style="standard",
        register="formal",
        seed=seed,
        max_marks=max_marks,
        expected_mark=round(sum(lv["mark"] for lv in levels), 4),
        criterion_levels=levels,
        target_concepts=list(dict.fromkeys(targets)),
        omitted_concepts=omitted if tier == "MISSING_CONCEPT" else [],
    )


def _sub_kinds(rule: dict, n: int, rng: random.Random) -> list[str]:
    kinds = rule.get("sub_kinds") or ["standard"]
    order = kinds[:]
    rng.shuffle(order)
    return [order[i % len(order)] for i in range(n)]


def _imbalance(assign: list[int], tiers: list[str], n_values: int) -> float:
    by_tier: dict[str, list[int]] = {}
    for v, t in zip(assign, tiers, strict=True):
        by_tier.setdefault(t, []).append(v)
    overall = sum(assign) / len(assign)
    return max(abs(sum(v) / len(v) - overall) for v in by_tier.values()) / max(1, n_values - 1)


def balanced_assignment(tiers: list[str], values: list[str], rng: random.Random, tries: int = 40) -> list[str]:
    """Spread `values` evenly over plans so every tier sees the same mix (tier-independent attribute)."""
    n = len(tiers)
    best, best_score = None, 1e9
    for _ in range(tries):
        pool = [i % len(values) for i in range(n)]
        rng.shuffle(pool)
        score = _imbalance(pool, tiers, len(values))
        if score < best_score:
            best, best_score = pool, score
    assert best is not None
    return [values[i] for i in best]


def build_question_plans(
    question_id: str,
    rubric: Rubric,
    spec: dict,
    seed: int,
    n_per_tier: int = 2,
    misconception_criteria: list[int] | None = None,
) -> list[AnswerPlan]:
    """Plans for all tiers of one question. Raises TierCollapse if the ordering cannot be realised."""
    rules = spec["plan_rules"]
    core, edge = spec["core_tiers"], spec["edge_tiers"]
    misc_idx = misconception_criteria or []
    problems: list[str] = []
    for attempt in range(MAX_PLAN_ATTEMPTS):
        rng = random.Random(stable_int(seed, question_id, "plan", attempt))
        plans: list[AnswerPlan] = []
        for tier in core + edge:
            rule = {**rules[tier], "relaxed": attempt >= MAX_PLAN_ATTEMPTS // 3}
            n = 1 if tier in edge else n_per_tier
            subs = _sub_kinds(rule, n, rng)
            seen: set[tuple[int, ...]] = set()
            for slot in range(n):
                for _ in range(6):  # prefer distinct level choices between slots of one tier
                    idx = choose_level_indices(rule["kind"], rubric, rng, rule, misc_idx)
                    if tuple(idx) not in seen:
                        break
                seen.add(tuple(idx))
                plan = _make_plan(
                    question_id, tier, slot, rubric, idx, stable_int(seed, question_id, tier, slot), subs[slot]
                )
                if tier == "MISCONCEPTION":
                    plan.misconception_criteria = [
                        c.criterion_id for c, i in zip(rubric.criteria, idx, strict=True) if i == 0
                    ]
                plans.append(plan)
        means = {
            t: sum(p.normalized for p in plans if p.tier == t) / max(1, sum(1 for p in plans if p.tier == t))
            for t in core
        }
        problems = tier_order_violations(means, spec)
        for p in plans:
            if p.tier == "MISSING_CONCEPT" and not p.omitted_concepts:
                problems.append(f"{p.answer_id} omits no concept that is exclusive to a zeroed criterion")
            if not in_range(p.normalized, spec["normalized_mark_ranges"][p.tier]):
                problems.append(f"{p.answer_id} normalized {p.normalized:.3f} outside tier range")
        if not problems:
            _assign_style_register(plans, rng, spec)
            return plans
    raise TierCollapse("; ".join(problems[:4]))


def _assign_style_register(plans: list[AnswerPlan], rng: random.Random, spec: dict) -> None:
    llm_core = [p for p in plans if p.tier in spec["core_tiers"]]
    styles = balanced_assignment([p.tier for p in llm_core], spec["styles"], rng)
    regs = balanced_assignment([p.tier for p in llm_core], spec["registers"], rng)
    for p, s, r in zip(llm_core, styles, regs, strict=True):
        p.style, p.register = s, r
    for p in plans:
        if p.tier in spec["core_tiers"]:
            continue
        if p.tier == "EMPTY":
            p.style, p.register = "not_applicable", "not_applicable"
        elif p.tier == "TOO_SHORT":
            p.style, p.register = "concise", rng.choice(spec["registers"])
        elif p.tier == "TYPO_FULL":
            p.style, p.register = rng.choice(spec["styles"]), "minor_typos"
        else:
            p.style, p.register = rng.choice(spec["styles"]), rng.choice(spec["registers"][:2])


# -- deterministic (no-LLM) answers ----------------------------------------------------------------------
_TEMPLATES = (
    "Not sure, something about {a} and {b}.",
    "I think it is related to {a}?",
    "{a} and {b}, I guess.",
    "No idea, maybe {a}.",
    "Only remember {a} came up in class.",
    "Probably to do with {a}.",
    "Honestly I cannot recall, {a} maybe.",
    "Is it {a} or {b}? Not certain.",
)
_STOP = frozenset(
    "which would could should explain describe discuss identify there their these those about what when where why "
    "how".split()
)


def deterministic_answer(plan: AnswerPlan, question_text: str, attempt: int = 0) -> str:
    """EMPTY / TOO_SHORT answers need no LLM. `attempt` varies the draw when a collision must be avoided."""
    rng = random.Random(stable_int(plan.seed, "det", attempt))
    if plan.tier == "EMPTY":
        return "" if plan.sub_kind == "empty" else rng.choice(["   ", " \n ", "\t "])
    words = [w for w in dict.fromkeys(re.findall(r"[A-Za-z]{5,}", question_text.lower())) if w not in _STOP]
    if len(words) < 2:
        words += ["this", "topic"]
    a, b = rng.sample(words, 2)
    text = rng.choice(_TEMPLATES).format(a=a, b=b)
    assert len(text.split()) < 8
    return text
