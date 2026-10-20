"""
AdaptiveLearnSE Component 3 — Model Diagnostic Suite & Robustness Audit
Evaluates 6 specific diagnostic test cases across:
1. Lexical Token Overlap Baseline
2. Condition E (Deterministic Rubric Engine)
3. Condition F Original (v1.0.0 Length-Biased GBR)
4. Condition F Corrected (v2.0.0 Gated Semantic Regressor)

Diagnostic Suite Test Cases:
- Case 1: Relevant Correct Answer
- Case 2: Partially Correct Answer
- Case 3: Completely Irrelevant Answer of Comparable Length
- Case 4: Long Irrelevant Distractor Answer (Roman Empire history)
- Case 5: Answer Containing Keywords with Inverted/Incorrect Reasoning
- Case 6: Empty Answer
"""

import os
import sys
import json
import joblib
import numpy as np
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
sys.path.append(BASE_DIR)
sys.path.append(SCRIPT_DIR)

from app.schemas.marking import Rubric, RubricCriterion, ScoringLevel
from app.schemas.assessment import AssessmentRequest
from services.assessment.orchestrator import assess_answer
from services.preprocessing.text_normalizer import tokenize

import train_semantic_model as tsm_v1
import train_semantic_model_corrected as tsm_v2

MODELS_DIR = os.path.join(BASE_DIR, "models")
RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")

# Question context
QUESTION_ID = "DIAG-SE3010-001"
QUESTION_TEXT = "Explain the difference between statement coverage and branch coverage in software testing, and explain why statement coverage alone may be insufficient."
REFERENCE_ANSWER = "Statement coverage measures the proportion of executable statements executed by tests. Branch coverage measures whether every decision branch (true and false outcomes) has been tested. Statement coverage is insufficient because a single path can execute all statements without testing alternative branch decisions."
EXPECTED_CONCEPTS = ["statement coverage", "branch coverage", "decision branch", "test adequacy"]
MAX_MARKS = 10.0

# Build synthetic rubric for Condition E
def get_diagnostic_rubric():
    c1 = RubricCriterion(
        criterion_id="DIAG-C01",
        description="Explains statement coverage and executed statements.",
        max_marks=3.0,
        required_concepts=["statement coverage"],
        scoring_levels=[
            ScoringLevel(level_id="L1", label="Full", mark=3.0, descriptor="Full explanation", required_concepts=["statement coverage"]),
            ScoringLevel(level_id="L0", label="None", mark=0.0, descriptor="Missing", required_concepts=[])
        ]
    )
    c2 = RubricCriterion(
        criterion_id="DIAG-C02",
        description="Explains branch coverage and decision branch outcomes.",
        max_marks=4.0,
        required_concepts=["branch coverage", "decision branch"],
        scoring_levels=[
            ScoringLevel(level_id="L2", label="Full", mark=4.0, descriptor="Full explanation", required_concepts=["branch coverage", "decision branch"]),
            ScoringLevel(level_id="L1", label="Partial", mark=2.0, descriptor="Partial explanation", required_concepts=["branch coverage"]),
            ScoringLevel(level_id="L0", label="None", mark=0.0, descriptor="Missing", required_concepts=[])
        ]
    )
    c3 = RubricCriterion(
        criterion_id="DIAG-C03",
        description="Explains why statement coverage is insufficient.",
        max_marks=3.0,
        required_concepts=["test adequacy"],
        scoring_levels=[
            ScoringLevel(level_id="L1", label="Full", mark=3.0, descriptor="Explains alternative branches", required_concepts=["test adequacy"]),
            ScoringLevel(level_id="L0", label="None", mark=0.0, descriptor="Missing", required_concepts=[])
        ]
    )
    return Rubric(rubric_id="R-DIAG-001", title="Diagnostic Rubric", criteria=[c1, c2, c3])

DIAGNOSTIC_CASES = [
    {
        "case_id": "CASE-1-CORRECT",
        "description": "Relevant Correct Answer",
        "expected_mark": 10.0,
        "student_answer": (
            "Statement coverage measures the percentage of executable statements exercised by test cases, "
            "whereas branch coverage verifies that every decision branch and outcome is tested. "
            "Statement coverage alone is insufficient for test adequacy because it fails to evaluate hidden alternative branches."
        )
    },
    {
        "case_id": "CASE-2-PARTIAL",
        "description": "Partially Correct Answer (Only Statement Coverage)",
        "expected_mark": 3.0,
        "student_answer": (
            "Statement coverage is a testing metric that measures the executable statements executed during test runs."
        )
    },
    {
        "case_id": "CASE-3-IRRELEVANT-SHORT",
        "description": "Completely Irrelevant Answer of Comparable Length",
        "expected_mark": 0.0,
        "student_answer": (
            "The recipe calls for two cups of flour, one cup of sugar, and fresh butter mixed thoroughly in a bowl before baking for thirty minutes."
        )
    },
    {
        "case_id": "CASE-4-IRRELEVANT-LONG",
        "description": "Long Irrelevant Distractor Answer (Roman Empire History)",
        "expected_mark": 0.0,
        "student_answer": (
            "The Roman Empire was a very large ancient empire that expanded across the Mediterranean Sea. "
            "Julius Caesar was a renowned general who led Roman legions across Gaul and later crossed the Rubicon to become dictator of Rome. "
            "Roman engineers constructed magnificent aqueducts, amphitheaters, and stone paved roads. "
            "Eventually the Western Roman Empire collapsed in 476 AD while the Eastern Roman Empire continued as Byzantium."
        )
    },
    {
        "case_id": "CASE-5-INCORRECT-REASONING",
        "description": "Answer Containing Keywords but Inverted / Incorrect Reasoning",
        "expected_mark": 0.0,
        "student_answer": (
            "Statement coverage is always superior to branch coverage because executing statements automatically guarantees "
            "that every decision branch and condition outcome is completely covered without needing branch tests."
        )
    },
    {
        "case_id": "CASE-6-EMPTY",
        "description": "Empty / Whitespace-Only Answer",
        "expected_mark": 0.0,
        "student_answer": "   "
    }
]

def run_diagnostics():
    print("=" * 80)
    print("  ADAPTIVELEARNSE COMPONENT 3 — DIAGNOSTIC ROBUSTNESS SUITE AUDIT")
    print("=" * 80)
    
    # Load Condition F Original
    v1_path = os.path.join(MODELS_DIR, "c3_scoring_regressor.joblib")
    v1_data = joblib.load(v1_path)
    gbr_v1 = v1_data["gbr"]
    tfidf_v1 = v1_data["tfidf"]
    
    # Load Condition F Corrected
    v2_path = os.path.join(MODELS_DIR, "c3_scoring_regressor_corrected.joblib")
    v2_data = joblib.load(v2_path)
    gbr_v2 = v2_data["gbr"]
    tfidf_v2 = v2_data["tfidf"]
    
    rubric = get_diagnostic_rubric()
    results = []
    
    for case in DIAGNOSTIC_CASES:
        ans_text = case["student_answer"]
        gt_mark = case["expected_mark"]
        
        # 1. Lexical Token Overlap Baseline
        ans_tokens = set(tokenize(ans_text))
        ref_tokens = set(tokenize(REFERENCE_ANSWER))
        if ref_tokens and ans_tokens:
            overlap = len(ans_tokens & ref_tokens) / len(ref_tokens)
            base_score = round(overlap * MAX_MARKS, 2)
        else:
            base_score = 0.0
            
        # 2. Condition E (Deterministic Rubric Engine)
        req = AssessmentRequest(
            question_id=QUESTION_ID,
            question_text=QUESTION_TEXT,
            student_answer=ans_text,
            reference_answer=REFERENCE_ANSWER,
            expected_concepts=EXPECTED_CONCEPTS,
            answer_type="short",
            rubric=rubric
        )
        cond_e_res = assess_answer(req)
        cond_e_score = float(cond_e_res.total_awarded_marks)
        
        # 3. Condition F Original (v1.0.0 with length bias)
        df_single = pd.DataFrame([{
            "question_text": QUESTION_TEXT,
            "student_answer": ans_text,
            "expected_concepts": json.dumps(EXPECTED_CONCEPTS)
        }])
        feats_v1 = tsm_v1.extract_dense_features(df_single, tfidf_v1, is_train=False)
        cond_f_v1_score = round(float(np.clip(gbr_v1.predict(feats_v1)[0], 0.0, 1.0) * MAX_MARKS), 2)
        
        # 4. Condition F Corrected (v2.0.0 Gated Semantic Regressor)
        df_single_v2 = pd.DataFrame([{
            "question_text": QUESTION_TEXT,
            "student_answer": ans_text,
            "reference_answer": REFERENCE_ANSWER,
            "expected_concepts": json.dumps(EXPECTED_CONCEPTS),
            "marks": MAX_MARKS
        }])
        feats_v2, rel_mask = tsm_v2.extract_semantic_features(df_single_v2, tfidf_v2, is_train=False)
        raw_pred_v2 = gbr_v2.predict(feats_v2)[0]
        cond_f_v2_score = round(float(np.clip(raw_pred_v2 * rel_mask[0], 0.0, 1.0) * MAX_MARKS), 2)
        
        case_result = {
            "case_id": case["case_id"],
            "description": case["description"],
            "expected_ground_truth": gt_mark,
            "scores": {
                "token_overlap_baseline": base_score,
                "condition_e_rubric_engine": cond_e_score,
                "condition_f_v1_length_biased": cond_f_v1_score,
                "condition_f_v2_corrected": cond_f_v2_score
            },
            "evaluation_verdict": {
                "condition_e_passed": abs(cond_e_score - gt_mark) <= 2.0,
                "condition_f_v1_passed": abs(cond_f_v1_score - gt_mark) <= 2.0,
                "condition_f_v2_passed": abs(cond_f_v2_score - gt_mark) <= 2.0
            }
        }
        results.append(case_result)
        
        print(f"\n[{case['case_id']}] {case['description']}")
        print(f"  Target Ground Truth:           {gt_mark:.1f} / 10.0")
        print(f"  1. Token Overlap Baseline:     {base_score:.2f} / 10.0")
        print(f"  2. Condition E (Rubric Engine):{cond_e_score:.2f} / 10.0  {'[PASS]' if abs(cond_e_score - gt_mark) <= 2.0 else '[FAIL]'}")
        print(f"  3. Condition F v1.0.0 (GBR):   {cond_f_v1_score:.2f} / 10.0  {'[PASS]' if abs(cond_f_v1_score - gt_mark) <= 2.0 else '[FAIL]'}")
        print(f"  4. Condition F v2.0.0 (Gated): {cond_f_v2_score:.2f} / 10.0  {'[PASS]' if abs(cond_f_v2_score - gt_mark) <= 2.0 else '[FAIL]'}")

    out_path = os.path.join(RESULTS_DIR, "diagnostic_suite_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("\n" + "=" * 80)
    print(f"Diagnostic results saved to: {out_path}")
    print("=" * 80)
    return results

if __name__ == "__main__":
    run_diagnostics()
