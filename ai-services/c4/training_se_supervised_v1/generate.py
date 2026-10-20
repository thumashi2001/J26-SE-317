"""Generate reproducible synthetic SE learners, practice, questions, and mock exams.

Latent simulator variables are written to audit/ only and must never enter features.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .catalogue import (
    N_TOPICS,
    ORDERED_TOPICS,
    TOPIC_MODULE,
    TOPIC_SEMESTER,
    Y3S1_INDICES,
    Y3S2_INDICES,
    catalogue_hash,
    catalogue_payload,
)
from .contract import (
    DOMAIN_MARKERS,
    PRIMARY_SCENARIO,
    SCENARIOS,
    SizeConfig,
    ScenarioParams,
    sizes_for_mode,
)
from .paths import ensure_dir, write_json
from .protocol import GENERATOR_VERSION, PROTOCOL_VERSION
from .rng_streams import exam_rng, learner_rng, practice_rng, questions_rng


def _scenario_offset(name: str) -> int:
    """Stable per-scenario offset (do not use Python's randomized hash())."""
    import hashlib

    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 10_000


def _sigmoid(x: np.ndarray | float) -> np.ndarray | float:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30.0, 30.0)))


def generate_question_bank(
    sizes: SizeConfig,
    scenario: ScenarioParams,
    master_seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Public question metadata + audit difficulties (same values; audit keeps provenance)."""
    rng = questions_rng(master_seed + _scenario_offset(scenario.name))
    rows: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    qid = 0
    for t_idx, topic in enumerate(ORDERED_TOPICS):
        for j in range(sizes.n_questions_per_topic):
            difficulty = float(rng.normal(scenario.difficulty_mean, scenario.difficulty_sd))
            qid += 1
            q_id = f"q_{topic}_{j:03d}"
            rows.append(
                {
                    "question_id": q_id,
                    "topic": topic,
                    "topic_index": t_idx,
                    "module_code": TOPIC_MODULE[topic],
                    "difficulty": difficulty,  # declared item parameter (visible metadata)
                    "scenario": scenario.name,
                }
            )
            audit.append(
                {
                    "question_id": q_id,
                    "difficulty_assumed": difficulty,
                    "scenario": scenario.name,
                    "note": "Assumed parameter; not fitted from real SE items.",
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(audit)


def generate_learners(
    sizes: SizeConfig,
    scenario: ScenarioParams,
    master_seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = learner_rng(master_seed + _scenario_offset(scenario.name))
    public: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    for i in range(sizes.n_learners):
        learner_id = f"syn_L{i:05d}"
        # Explicit synthetic semester assignment (not live enrolment).
        semester = "Y3S1" if (i % 2 == 0) else "Y3S2"
        ability = float(rng.normal(scenario.ability_mean, scenario.ability_sd))
        affinities = rng.normal(0.0, scenario.topic_affinity_sd, size=N_TOPICS)
        public.append(
            {
                "learner_id": learner_id,
                "semester": semester,
                "scenario": scenario.name,
                "synthetic": True,
            }
        )
        audit.append(
            {
                "learner_id": learner_id,
                "semester": semester,
                "latent_ability": ability,
                **{f"topic_affinity_{ORDERED_TOPICS[k]}": float(affinities[k]) for k in range(N_TOPICS)},
                "scenario": scenario.name,
                "note": "Audit-only latents; excluded from all predictive features.",
            }
        )
    return pd.DataFrame(public), pd.DataFrame(audit)


def _effective_ability(
    latent_ability: float,
    affinities: np.ndarray,
    topic_practice_gain: np.ndarray,
) -> np.ndarray:
    return latent_ability + affinities + topic_practice_gain


def generate_practice_and_exams(
    sizes: SizeConfig,
    scenario: ScenarioParams,
    master_seed: int,
    questions: pd.DataFrame,
    learners_public: pd.DataFrame,
    learners_audit: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return practice attempts, exam summaries, exam items, practice-audit latents."""
    prng = practice_rng(master_seed + _scenario_offset(scenario.name))
    erng = exam_rng(master_seed + _scenario_offset(scenario.name))

    q_by_topic: dict[str, pd.DataFrame] = {
        t: questions[questions["topic"] == t].reset_index(drop=True) for t in ORDERED_TOPICS
    }
    audit_by_id = learners_audit.set_index("learner_id")

    practice_rows: list[dict[str, Any]] = []
    exam_rows: list[dict[str, Any]] = []
    exam_item_rows: list[dict[str, Any]] = []
    practice_audit: list[dict[str, Any]] = []

    base_ts = np.datetime64("2024-01-01T00:00:00")

    for _, learner in learners_public.iterrows():
        lid = str(learner["learner_id"])
        semester = str(learner["semester"])
        eligible_idx = np.asarray(
            Y3S1_INDICES if semester == "Y3S1" else Y3S2_INDICES, dtype=int
        )
        aud = audit_by_id.loc[lid]
        ability = float(aud["latent_ability"])
        affinities = np.array(
            [float(aud[f"topic_affinity_{t}"]) for t in ORDERED_TOPICS], dtype=np.float64
        )
        topic_gain = np.zeros(N_TOPICS, dtype=np.float64)

        n_attempts = int(
            prng.integers(sizes.practice_attempts_min, sizes.practice_attempts_max + 1)
        )
        gaps_h = prng.uniform(0.5, 18.0, size=n_attempts)
        times = base_ts + np.cumsum(gaps_h).astype("timedelta64[h]")

        for step in range(n_attempts):
            eff = _effective_ability(ability, affinities, topic_gain)
            # Topic choice restricted to semester-eligible indices.
            weakness = -eff[eligible_idx]
            logits = scenario.weak_topic_bias * weakness
            logits = logits - logits.max()
            probs = np.exp(logits)
            probs = probs / probs.sum()
            t_idx = int(eligible_idx[int(prng.choice(len(eligible_idx), p=probs))])
            topic = ORDERED_TOPICS[t_idx]
            assert TOPIC_SEMESTER[topic] == semester
            bank = q_by_topic[topic]
            qi = int(prng.integers(0, len(bank)))
            qrow = bank.iloc[qi]
            difficulty = float(qrow["difficulty"])
            noise = float(prng.normal(0.0, scenario.response_logit_noise_sd))
            logit = float(eff[t_idx] - difficulty + noise)
            p_correct = float(_sigmoid(logit))
            correct = int(prng.random() < p_correct)

            if correct:
                topic_gain[t_idx] += scenario.practice_gain_per_correct
            else:
                topic_gain[t_idx] += scenario.practice_gain_per_incorrect

            event_id = f"{lid}_p{step:04d}"
            practice_rows.append(
                {
                    "event_id": event_id,
                    "learner_id": lid,
                    "semester": semester,
                    "timestamp_utc": str(times[step]),
                    "step": step,
                    "topic": topic,
                    "topic_index": t_idx,
                    "module_code": TOPIC_MODULE[topic],
                    "question_id": str(qrow["question_id"]),
                    "difficulty": difficulty,
                    "correct": correct,
                    "activity_kind": "practice",
                    "scenario": scenario.name,
                    "synthetic": True,
                }
            )
            practice_audit.append(
                {
                    "event_id": event_id,
                    "learner_id": lid,
                    "true_p_correct": p_correct,
                    "generator_noise": noise,
                    "latent_ability": ability,
                    "effective_ability_topic": float(eff[t_idx]),
                    "topic_practice_gain": float(topic_gain[t_idx]),
                    "scenario": scenario.name,
                }
            )

        last_ts = times[-1]
        exam_start = last_ts + np.timedelta64(24, "h")
        eff_exam = _effective_ability(ability, affinities, topic_gain)

        # Mock exam covers only semester-eligible topics (explicit S1 coverage).
        n_exam = sizes.exam_items_per_topic * len(eligible_idx)
        exam_correct = 0
        for ei in range(n_exam):
            t_idx = int(eligible_idx[ei % len(eligible_idx)])
            topic = ORDERED_TOPICS[t_idx]
            bank = q_by_topic[topic]
            qi = int(erng.integers(0, len(bank)))
            qrow = bank.iloc[qi]
            difficulty = float(qrow["difficulty"])
            noise = float(erng.normal(0.0, scenario.response_logit_noise_sd))
            logit = float(eff_exam[t_idx] - difficulty + noise)
            p_correct = float(_sigmoid(logit))
            correct = int(erng.random() < p_correct)
            exam_correct += correct
            exam_item_rows.append(
                {
                    "learner_id": lid,
                    "semester": semester,
                    "exam_item_index": ei,
                    "timestamp_utc": str(exam_start + np.timedelta64(ei, "m")),
                    "topic": topic,
                    "topic_index": t_idx,
                    "question_id": str(qrow["question_id"]),
                    "difficulty": difficulty,
                    "correct": correct,
                    "scenario": scenario.name,
                    "synthetic": True,
                }
            )
            practice_audit.append(
                {
                    "event_id": f"{lid}_exam{ei:03d}",
                    "learner_id": lid,
                    "true_p_correct": p_correct,
                    "generator_noise": noise,
                    "latent_ability": ability,
                    "effective_ability_topic": float(eff_exam[t_idx]),
                    "topic_practice_gain": float(topic_gain[t_idx]),
                    "scenario": scenario.name,
                    "is_exam": True,
                }
            )

        score = exam_correct / float(n_exam)
        exam_rows.append(
            {
                "learner_id": lid,
                "semester": semester,
                "exam_eligible_topics": [ORDERED_TOPICS[i] for i in eligible_idx.tolist()],
                "exam_start_utc": str(exam_start),
                "prediction_cutoff_utc": str(last_ts),
                "exam_n_items": n_exam,
                "exam_n_correct": exam_correct,
                "y_exam_score": float(score),
                "scenario": scenario.name,
                "synthetic": True,
                "domain": "se_simulation",
            }
        )

    return (
        pd.DataFrame(practice_rows),
        pd.DataFrame(exam_rows),
        pd.DataFrame(exam_item_rows),
        pd.DataFrame(practice_audit),
    )


def generate_scenario_dataset(
    out_dir: Path,
    *,
    mode: str,
    scenario_name: str,
    master_seed: int,
) -> dict[str, Any]:
    if scenario_name not in SCENARIOS:
        raise KeyError(f"Unknown scenario {scenario_name!r}; declared={list(SCENARIOS)}")
    scenario = SCENARIOS[scenario_name]
    sizes = sizes_for_mode(mode)
    scen_dir = ensure_dir(out_dir / "scenarios" / scenario_name)
    audit_dir = ensure_dir(scen_dir / "audit")

    questions, q_audit = generate_question_bank(sizes, scenario, master_seed)
    learners, l_audit = generate_learners(sizes, scenario, master_seed)
    practice, exams, exam_items, p_audit = generate_practice_and_exams(
        sizes, scenario, master_seed, questions, learners, l_audit
    )

    questions.to_csv(scen_dir / "questions.csv", index=False)
    learners.to_csv(scen_dir / "learners.csv", index=False)
    practice.to_csv(scen_dir / "practice_attempts.csv", index=False)
    exams.to_csv(scen_dir / "mock_exams.csv", index=False)
    exam_items.to_csv(scen_dir / "mock_exam_items.csv", index=False)

    q_audit.to_csv(audit_dir / "question_latents.csv", index=False)
    l_audit.to_csv(audit_dir / "learner_latents.csv", index=False)
    p_audit.to_csv(audit_dir / "response_latents.csv", index=False)

    meta = {
        **DOMAIN_MARKERS,
        "scenario": asdict(scenario),
        "sizes": asdict(sizes),
        "mode": mode,
        "master_seed": master_seed,
        "n_practice_rows": int(len(practice)),
        "n_learners": int(len(learners)),
        "n_questions": int(len(questions)),
        "n_exam_rows": int(len(exams)),
        "exam_score_mean": float(exams["y_exam_score"].mean()),
        "practice_correct_rate": float(practice["correct"].mean()),
        "catalogue_sha256": catalogue_hash(),
        "catalogue": catalogue_payload(),
        "note": "Assumed parameters; not empirically fitted. Audit latents excluded from features.",
    }
    write_json(scen_dir / "generation_meta.json", meta)
    return meta


def generate_all_scenarios(
    out_dir: Path,
    *,
    mode: str,
    master_seed: int = 42,
) -> dict[str, Any]:
    """Generate every predeclared scenario. Always report all; never drop after metrics."""
    out_dir = ensure_dir(out_dir)
    summaries = {}
    for name in SCENARIOS:
        summaries[name] = generate_scenario_dataset(
            out_dir, mode=mode, scenario_name=name, master_seed=master_seed
        )
    index = {
        **DOMAIN_MARKERS,
        "protocol": PROTOCOL_VERSION,
        "generator_version": GENERATOR_VERSION,
        "mode": mode,
        "master_seed": master_seed,
        "primary_scenario": PRIMARY_SCENARIO,
        "scenarios_generated": list(SCENARIOS.keys()),
        "summaries": summaries,
        "reporting_rule": (
            "All scenarios generated and must be reported. "
            "Selection uses primary_scenario only."
        ),
    }
    write_json(out_dir / "generation_index.json", index)
    return index
