"""
AdaptiveLearnSE Component 3 — Synthetic Dataset Loader Utility
==============================================================
Provides high-level programmatic access to the canonical C3-Phase3-v5-FINAL
synthetic benchmark dataset located in ai-services/c3/datasets/synthetic/.

This loader operates strictly offline for research evaluations, benchmarking,
and model comparison (Conditions A-F). It DOES NOT load data into MongoDB or
expose records as student submissions.
"""

import csv
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Base path resolution
DATASETS_DIR = Path(__file__).resolve().parent
SYNTHETIC_DIR = DATASETS_DIR / "synthetic"


def get_synthetic_dataset_dir() -> Path:
    """Return the absolute path to the synthetic dataset directory."""
    return SYNTHETIC_DIR


def parse_concepts(val: Any) -> List[str]:
    """
    Parse concept list from string.
    Supports both JSON arrays ('["concept1", "concept2"]')
    and semicolon-delimited strings ('concept1; concept2').
    """
    if not val or str(val).strip().lower() in ("nan", "none", "", "null"):
        return []
    val = str(val).strip()
    if val.startswith("["):
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                return [str(c).strip() for c in parsed if str(c).strip()]
        except Exception:
            pass
    return [c.strip() for c in val.split(";") if c.strip()]


def parse_marks(val: Any) -> List[Dict[str, Any]]:
    """
    Parse criterion marks.
    Supports JSON criterion structures ('[{"criterion_id": "...", "mark": ...}]')
    and comma-separated numbers ('5,5').
    """
    if not val or str(val).strip().lower() in ("nan", "none", "", "null"):
        return []
    val = str(val).strip()
    if val.startswith("["):
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
    if "," in val:
        try:
            return [{"mark": float(m.strip())} for m in val.split(",") if m.strip()]
        except Exception:
            pass
    try:
        return [{"mark": float(val)}]
    except Exception:
        return []


def parse_evidence_spans(val: Any) -> Union[Dict[str, Any], List[str]]:
    """
    Parse evidence spans.
    Supports JSON mapping ('{"C01": ["S1"]}') and semicolon-delimited sentences.
    """
    if not val or str(val).strip().lower() in ("nan", "none", "", "null"):
        return {}
    val = str(val).strip()
    if val.startswith("{"):
        try:
            return json.loads(val)
        except Exception:
            pass
    return [s.strip() for s in val.split(";") if s.strip()]


def load_manifest() -> Dict[str, Any]:
    """Load dataset manifest file (00_MANIFEST.json)."""
    manifest_path = SYNTHETIC_DIR / "00_MANIFEST.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found at {manifest_path}")
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_question_bank(
    split: Optional[str] = None,
    parse_structured_fields: bool = True
) -> List[Dict[str, Any]]:
    """
    Load question bank records (01_FINAL_question_bank.csv).
    
    Args:
        split: Optional filter by 'train', 'validation', or 'test'.
        parse_structured_fields: If True, parses JSON/delimited columns.
        
    Returns:
        List of question dictionaries.
    """
    qb_path = SYNTHETIC_DIR / "01_FINAL_question_bank.csv"
    if not qb_path.exists():
        raise FileNotFoundError(f"Question bank not found at {qb_path}")

    records = []
    with open(qb_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if split and row.get("split", "").lower() != split.lower():
                continue
            item = dict(row)
            if parse_structured_fields:
                item["expected_concepts_parsed"] = parse_concepts(item.get("expected_concepts"))
                item["expected_relationships_parsed"] = parse_concepts(item.get("expected_relationships"))
                item["evidence_requirements_parsed"] = parse_concepts(item.get("evidence_requirements"))
                try:
                    item["marks"] = float(item["marks"]) if item.get("marks") else 0.0
                except ValueError:
                    pass
            records.append(item)
    return records


def load_controlled_answers(
    split: Optional[str] = None,
    quality: Optional[str] = None,
    question_id: Optional[str] = None,
    parse_structured_fields: bool = True
) -> List[Dict[str, Any]]:
    """
    Load controlled synthetic answers (02_FINAL_controlled_answers.csv).
    
    Args:
        split: Optional filter by 'train', 'validation', or 'test'.
        quality: Optional filter by 'FULL', 'MOSTLY_CORRECT', 'PARTIAL',
                 'MISSING_CONCEPT', 'MISCONCEPTION', or 'IRRELEVANT'.
        question_id: Optional filter for a specific question ID.
        parse_structured_fields: If True, parses structured concept and mark fields.
        
    Returns:
        List of answer dictionaries.
    """
    ca_path = SYNTHETIC_DIR / "02_FINAL_controlled_answers.csv"
    if not ca_path.exists():
        raise FileNotFoundError(f"Controlled answers not found at {ca_path}")

    records = []
    with open(ca_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if split and row.get("split", "").lower() != split.lower():
                continue
            if quality and row.get("answer_quality", "").upper() != quality.upper():
                continue
            if question_id and row.get("question_id", "") != question_id:
                continue

            item = dict(row)
            if parse_structured_fields:
                item["demonstrated_concepts_parsed"] = parse_concepts(item.get("demonstrated_concepts"))
                item["missing_concepts_parsed"] = parse_concepts(item.get("missing_concepts"))
                item["incorrect_concepts_parsed"] = parse_concepts(item.get("incorrect_concepts"))
                item["criterion_marks_parsed"] = parse_marks(item.get("criterion_marks"))
                item["evidence_spans_parsed"] = parse_evidence_spans(item.get("evidence_spans"))
                try:
                    item["expected_mark"] = float(item["expected_mark"]) if item.get("expected_mark") else 0.0
                except ValueError:
                    pass
                try:
                    item["marks"] = float(item["marks"]) if item.get("marks") else 0.0
                except ValueError:
                    pass
            records.append(item)
    return records


def load_rubric_criteria(question_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load rubric criteria records (03_FINAL_rubric_criteria.csv)."""
    rc_path = SYNTHETIC_DIR / "03_FINAL_rubric_criteria.csv"
    if not rc_path.exists():
        raise FileNotFoundError(f"Rubric criteria not found at {rc_path}")

    records = []
    with open(rc_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if question_id and row.get("question_id", "") != question_id:
                continue
            item = dict(row)
            try:
                item["criterion_marks"] = float(item["criterion_marks"]) if item.get("criterion_marks") else 0.0
            except ValueError:
                pass
            records.append(item)
    return records


def load_replacement_audit() -> List[Dict[str, Any]]:
    """Load question replacement audit records (04_ORIGINAL_63_REPLACEMENT_AUDIT.csv)."""
    ra_path = SYNTHETIC_DIR / "04_ORIGINAL_63_REPLACEMENT_AUDIT.csv"
    if not ra_path.exists():
        raise FileNotFoundError(f"Replacement audit not found at {ra_path}")

    records = []
    with open(ra_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(dict(row))
    return records


def get_dataset_summary() -> Dict[str, Any]:
    """Return summary metrics of the synthetic dataset package."""
    manifest = load_manifest()
    qb = load_question_bank(parse_structured_fields=False)
    ca = load_controlled_answers(parse_structured_fields=False)

    split_counts_qb = {}
    for r in qb:
        s = r.get("split", "unknown")
        split_counts_qb[s] = split_counts_qb.get(s, 0) + 1

    split_counts_ca = {}
    quality_counts = {}
    for r in ca:
        s = r.get("split", "unknown")
        split_counts_ca[s] = split_counts_ca.get(s, 0) + 1
        q = r.get("answer_quality", "unknown")
        quality_counts[q] = quality_counts.get(q, 0) + 1

    return {
        "dataset_version": manifest.get("dataset_version", "unknown"),
        "total_questions": len(qb),
        "total_answers": len(ca),
        "question_splits": split_counts_qb,
        "answer_splits": split_counts_ca,
        "quality_distribution": quality_counts,
        "expert_validation_claimed": manifest.get("expert_validation", False),
    }


def get_question_bundle(question_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a question, its rubric criteria, and its 6 controlled answers bundled together.
    """
    questions = [q for q in load_question_bank() if q.get("question_id") == question_id]
    if not questions:
        return None
    question = questions[0]
    rubrics = load_rubric_criteria(question_id=question_id)
    answers = load_controlled_answers(question_id=question_id)
    return {
        "question": question,
        "rubric_criteria": rubrics,
        "controlled_answers": answers,
    }
