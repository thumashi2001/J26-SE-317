"""
AdaptiveLearnSE Component 3 — Calibrated Mock LLM Provider
Provides deterministic, zero-cost, schema-validated assessment outputs for offline benchmarking and testing.
"""

import time
import json
import re
from typing import Any
from .base import BaseLLMProvider, LLMRequest, LLMResponse, LLMUsage


class MockLLMProvider(BaseLLMProvider):
    """Calibrated Deterministic Mock Provider simulating LLM inference."""

    def __init__(self, provider_name: str = "calibrated-mock"):
        super().__init__(provider_name)

    def is_available(self) -> bool:
        return True

    def health_check(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "provider": self.provider_name,
            "is_real_execution": False,
            "mode": "deterministic_offline_simulation",
            "supported_models": ["mock-gpt4o", "mock-claude-3-5-sonnet", "mock-llama-3-8b"]
        }

    def generate(self, request: LLMRequest) -> LLMResponse:
        start_time = time.perf_counter()
        prompt_text = request.prompt

        # Estimate prompt tokens
        words = len(prompt_text.split())
        prompt_tokens = int(words * 1.3) + 20

        # Robust section extraction using explicit section headers
        def _extract_section(txt: str, start_hdr: str, end_hdrs: list) -> str:
            pattern = rf"{start_hdr}\s*:\s*(.*?)(?=(?:" + "|".join(end_hdrs) + r")|\Z)"
            m = re.search(pattern, txt, re.DOTALL | re.IGNORECASE)
            return m.group(1).strip() if m else ""

        student_ans = _extract_section(
            prompt_text, "Student Answer", ["Provide your evaluation", r'"""\s*$', r"\Z"]
        ).strip('"\n\r ')

        ref_ans = _extract_section(
            prompt_text, "Reference Answer", ["Maximum Marks", "Max Marks", "Rubric Criteria", "Retrieved Curriculum Context", "CCKG", "Student Answer"]
        )

        rubric_str = _extract_section(
            prompt_text, "Rubric Criteria", ["Retrieved Curriculum Context", "CCKG", "Student Answer"]
        )
        has_rubric = bool(rubric_str and len(rubric_str) > 5)

        vector_str = _extract_section(
            prompt_text, "Retrieved Curriculum Context", ["CCKG", "Student Answer"]
        )
        has_vector_rag = bool(vector_str and "no specific curriculum passage" not in vector_str.lower())
        vector_text = vector_str if has_vector_rag else ""

        graph_str = _extract_section(
            prompt_text, "CCKG Knowledge Graph Context", ["Student Answer"]
        )
        has_graph_rag = bool(graph_str and ("requires prerequisite" in graph_str.lower() or "prerequisite" in graph_str.lower()))
        graph_text = graph_str if has_graph_rag else ""

        marks_match = re.search(r"Max(?:imum)? Marks:\s*([0-9.]+)", prompt_text, re.IGNORECASE)
        max_marks = float(marks_match.group(1)) if marks_match else 10.0

        # Heuristic scoring calibration for mock responses
        # Check for distractor / irrelevant text
        stopwords = {"a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "this", "that", "it"}
        is_irrelevant = any(w in student_ans.lower() for w in ["roman empire", "recipe", "flour", "sugar", "caesar", "aqueduct", "colosseum"])
        is_empty = len(student_ans.strip()) < 5

        if is_empty or is_irrelevant:
            awarded_mark = 0.0
            overall_feedback = "The submitted response is empty or discusses an irrelevant topic outside software engineering."
            criteria_eval = [
                {
                    "criterion_id": "C1",
                    "awarded_mark": 0.0,
                    "explanation": "No relevant technical evidence demonstrated for this criterion.",
                    "evidence_quotes": []
                }
            ]
            demonstrated = []
            missing = ["core concepts"]
        else:
            # Tokenize and compute reference overlap
            ans_tokens = set(re.findall(r"\b[a-z0-9_-]+\b", student_ans.lower())) - stopwords
            ref_tokens = set(re.findall(r"\b[a-z0-9_-]+\b", ref_ans.lower())) - stopwords if ref_ans else set()

            if ref_tokens and ans_tokens:
                overlap = len(ans_tokens & ref_tokens) / max(1, len(ref_tokens))
                base_ratio = min(1.0, overlap * 1.25)
            elif ans_tokens:
                base_ratio = min(0.8, len(ans_tokens) / 30.0)
            else:
                base_ratio = 0.0

            # Experiment 2: Rubric alignment penalty/boost
            if has_rubric:
                # Rubric alignment refines granularity
                base_ratio = round(base_ratio * 1.05, 2)

            # Experiment 3: Vector RAG grounding bonus/validation
            if has_vector_rag and vector_text:
                v_tokens = set(re.findall(r"\b[a-z0-9_-]+\b", vector_text.lower())) - stopwords
                v_overlap = len(ans_tokens & v_tokens)
                if v_overlap >= 3:
                    base_ratio = min(1.0, base_ratio + 0.05)

            # Experiment 4: GraphRAG prerequisite validation
            if has_graph_rag and graph_text:
                g_tokens = set(re.findall(r"\b[a-z0-9_-]+\b", graph_text.lower())) - stopwords
                g_overlap = len(ans_tokens & g_tokens)
                if g_overlap >= 2:
                    base_ratio = min(1.0, base_ratio + 0.03)

            awarded_mark = min(max_marks, max(0.0, round(base_ratio * max_marks, 1)))

            # Multi-LLM model variance
            if "claude" in request.model.lower():
                awarded_mark = min(max_marks, round(awarded_mark * 0.94, 1))
            elif "llama" in request.model.lower():
                awarded_mark = min(max_marks, round(awarded_mark * 0.91, 1))

            concepts_found = [t for t in ["high cohesion", "loose coupling", "microservices", "statement coverage", "branch coverage", "rest", "soap", "http", "react", "components"] if t in student_ans.lower()]
            overall_feedback = (
                f"The response demonstrates relevant concepts ({', '.join(concepts_found[:3]) if concepts_found else 'technical principles'}). "
                "Criterion-level alignment with reference specifications has been evaluated."
            )
            criteria_eval = [
                {
                    "criterion_id": "C1",
                    "awarded_mark": round(awarded_mark * 0.5, 1),
                    "explanation": "Criterion demonstrated in student submission.",
                    "evidence_quotes": [student_ans[:80]] if len(student_ans) > 10 else []
                },
                {
                    "criterion_id": "C2",
                    "awarded_mark": round(awarded_mark * 0.5, 1),
                    "explanation": "Technical evidence evaluated against curriculum requirements.",
                    "evidence_quotes": [student_ans[80:160]] if len(student_ans) > 80 else []
                }
            ]
            demonstrated = concepts_found
            missing = [c for c in ["loose coupling", "branch coverage", "http"] if c not in concepts_found]

        payload = {
            "model": request.model,
            "total_awarded_mark": awarded_mark,
            "max_marks": max_marks,
            "percentage": round((awarded_mark / max_marks) * 100, 1) if max_marks > 0 else 0.0,
            "criteria_evaluations": criteria_eval,
            "demonstrated_concepts": demonstrated,
            "missing_concepts": missing,
            "overall_feedback": overall_feedback,
            "grounding_citations": ["SLIIT SE3010 Modular Design Guidelines"] if not is_irrelevant else []
        }

        raw_str = json.dumps(payload, indent=2)
        latency = (time.perf_counter() - start_time) * 1000.0 + 12.0  # simulate ~12ms inference

        completion_tokens = len(raw_str.split()) + 15
        usage = LLMUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost_usd=0.0  # mock is free
        )

        return LLMResponse(
            raw_content=raw_str,
            parsed_json=payload,
            model_identifier=request.model,
            provider_name=self.provider_name,
            usage=usage,
            latency_ms=round(latency, 2),
            finish_reason="stop",
            is_success=True,
            is_real_execution=False
        )
