# 01 Proposal, original research plan and decisions — traceability

Sources read (V): proposal PDF (75 pp., `Desktop\Reserach\Proposal\IT23227118_EDIRISINGHE T P V K.pdf`), Day 2/3/4/5/6/18 PDFs, NFR doc, TAF V2.2, logbook, two proposal decks, team execution doc v1.1, **Day 22, Day 23 (selection + experimental design), Day 25 docx**, repo `AGENTS.md`, `PROPOSAL_COMMENT_RESPONSE_MATRIX.md`, `CLAIM_EVIDENCE_DECISION_LOG.md`. Figures, WBS, Gantt and Table 7 tick marks are images and were not read (limit). Page numbers are PDF pages.

## 1. Proposal reconstruction
| Item | Proposal statement | Page |
|---|---|---|
| Title / ID / supervisor | AI-Powered Automated Marking and Answer Analysis System; J26-SE-317; T P V K Edirisinghe IT23227118; supervisor Ms Ishara Weerathunga (declaration signed 16/09/2026) | 1–2 |
| Problem | limited integration of rubric-aware semantic marking, concept diagnosis, explainable assessment and structured knowledge within one pipeline | 3 |
| Gap | "insufficiently integrated and experimentally validated research…" (exact wording) | 26 |
| Main objective | design, develop and experimentally evaluate the system with measurable agreement and reliable concept analysis | 27 |
| SO1–SO6 | semantic analysis; rubric-aware marking + evidence; concept-level analysis; explainable feedback; mind-map generation; experimental evaluation vs baselines | 27 |
| Method | Design Science Research + experimental evaluation; Agile development, 12 stages | 28, 34 |
| Baselines (Table 4) | deterministic MCQ; keyword/rule; semantic-model; LLM no RAG; LLM + RAG; multiple LLMs; proposed integrated | 30–31 |
| Fairness rule | same questions, answers, rubrics and conditions for all candidates "wherever technically feasible" | 33 |
| Metrics (Table 5) | QWK, MAE, RMSE, Accuracy, P/R/Macro-F1, agreement, feedback quality, concept coverage, relationship correctness, latency; **no numeric thresholds** | 31–33 |
| Datasets | Mohler, ASAP-SAS, SciEntsBank, ASAG2024; SLIIT data only with approval; synthetic "will not replace real student-answer benchmark evidence" | 29–30 |
| Requirements | 46 FR (FR-C3-01..46), 30 NFR (NFR-C3-01..30); Must/Should/Could | 40–50 |
| Must-have | answer processing, semantic analysis, rubric marking, partial credit, concept classes, explainable evidence, feedback, mind map, lecturer review, integration, experimental evaluation | 49 |
| Should-have | RAG, LLM comparison, RAG vs non-RAG, OCR, feedback-quality evaluation | 49 |
| Commercial | B2B institutional SaaS, subscription/usage/enterprise, tiers (no prices), IP, competitors | 51–59 |
| Risks | no risk section; threats to validity listed | 33–34 |
| AI-use disclosure | ChatGPT for research direction, drafting, requirements, architecture, experiment planning, formatting | 70 |

## 2. Original model plan (Day 22–23, recovered)
| Level | Candidate | Day 23 decision | Role |
|---|---|---|---|
| L0 | TF-IDF + classical ML | SELECT | transparent baseline |
| L1 | RoBERTa-base | SELECT | contextual encoder for marking |
| L2 | SBERT | SELECT | semantic comparison with reference |
| L3 | GPT- or Llama-family | CONDITIONAL SELECT | structured evidence + feedback |
| — | Cross-encoder | OPTIONAL | pair scoring |
| — | BERT | DEPRIORITISED | optional baseline |
| L4 | Integrated C3 pipeline | proposed system | — |
Experimental groups A lexical, B transformer, C semantic, D structured LLM, E hybrid; ablations A1–A6; RQ1–RQ6; H1–H5; EngSAF unseen-answer and unseen-question splits; reproducibility list; threats to validity. Day 25 lists "Candidate model comparison before final selection" and "RAG vs non-RAG under matched conditions" among evaluations.

## 3. Plan vs actual matrix
| Planned element | Actual | Status | Evidence |
|---|---|---|---|
| L0 TF-IDF + classical ML on benchmark data | TF-IDF + Ridge/GBR trained on synthetic data; scripts deleted from HEAD | PARTIAL | git `f21dba4`, `c57e553`; `trainable_model_summary_corrected.json` (MAE 5.994, r 0.282) |
| L1 RoBERTa-base | none | NOT IMPLEMENTED | `git grep` roberta/transformers/torch: none; not in requirements |
| L2 SBERT | none (remote embeddings only for unused RAG path) | NOT IMPLEMENTED | `services/rag/embeddings.py` |
| L3 GPT/Llama | provider code, cache, preflight; never run on dataset | PARTIAL / BLOCKED (quota) | `services/llm/*`; Gemini ≈20 req/day |
| L4 integrated pipeline | deterministic core + lecturer flow | IMPLEMENTED (lexical core) | 09 Part C |
| Benchmark datasets EngSAF/ASAP-SAS/Mohler/ASAG2024 | present locally, unused; synthetic set primary | NOT USED | `Desktop\Reserach\Data sets\`; DEC-06 |
| RAG vs non-RAG | code only | NOT RUN | `experiments/conditions.py` |
| Candidate comparison and best-model selection | none valid beyond baseline vs E | NOT DEMONSTRATED | 06 |
| QWK | not implemented | MISSING | grep |
| Concept-level + feedback + map | implemented in baseline form | PARTIAL | 03 |
| Gold standard by experts | none | MISSING | dataset card |

## 4. Decisions and their provenance
| Decision | Source | Provenance | Concern |
|---|---|---|---|
| COM-07 "Do not present uncalibrated zero-shot LLM numbers during PP1"; Condition E authoritative; A–D, F post-PP1 | repo matrix | internal, undated; no minutes | cannot be shown as supervisor-signed (R) |
| DEC-05 / COM-05 OCR excluded | repo | internal | COM-05 attributed to "TAF Review" but TAF has no such comment; proposal p.49 lists OCR Should-Have |
| DEC-06 synthetic dataset primary | repo | self-recorded | contradicts proposal p.30 and Day 23/18 tier order |
| DEC-07 PP1 boundary: E primary, F = gradient-boosted regressor | repo | internal | F defined three ways (GBR; multi-LLM ensemble; E + embeddings + LLM fusion) |
| "Strict panel verdicts" (Day 18, NFR) | team documents | self-authored simulation | not signed panel records |
| Proposal Appendix 4 decision log (Jun–Aug 2026) | proposal pp.68–69 | in proposal, no COM/DEC ids | — |
| TAF supervisor evaluation boxes | TAF p.15 | blank / unsigned | do not claim TAF approval beyond the proposal declaration |
| Supervisor meeting sheet | Downloads PDF | all decision fields blank | question bank only |
| "Train/configure 2–3 candidate models and select the best" | your report (R); written basis Day 22/23/25, proposal §3.3 | number "2–3" not in any document | ask supervisor to confirm in writing |

## 5. Contradictions to resolve or pre-empt
1. **Conditions:** proposal has seven approaches; Day 18 has A–F (GraphRAG, concept-evidence E); Day 23 has A–E (TF-IDF…hybrid); repo has E/F redefined. 2. **Data:** proposal/Day 23 benchmarks vs DEC-06 synthetic. 3. **OCR:** Should-Have vs excluded. 4. **Counts:** 46 FR/30 NFR vs 96 FR/56 stories; 5. **Objectives:** 1+6 (proposal) vs 5 (deck) vs 3 (AGENTS.md). 6. **RQs:** none in proposal vs RQ1–6 (Day 2) vs main RQ + H1–H6 (Day 18) vs RQ1–6 + H1–H5 (Day 23). 7. **Key functions:** defined only in team doc. 8. **Dates:** proposal decision log starts June; logbook starts 21 Jul. 9. **Proposal defects:** Table 1 citation numbers mismatch reference list; ToC omissions; technologies justified only by licence cost (p.61).
10. **Repo docs vs reality:** ~29 documents/evidence pages still show pre-repair numbers or the mock provider; E "17.3 % better" and baseline 5.609 do not reproduce.

## 6. Recommended wording for the viva
"My proposal commits to a controlled comparison under equal conditions. The decisions that deferred LLM/RAG conditions are recorded in my project log; I do not have signed minutes, so I am not presenting them as supervisor approvals."
