# C3 Research Decision Log

## C3 Research Context: Combined Evidence-Traceable Pipeline
C3 is evaluating an integrated workflow rather than standalone features:
Student Answer → Analysis → Evidence → Rubric Decision → Explanation → Concept Diagnosis → Feedback → Mind Map → Lecturer Verification.

This combined pipeline is a research artifact whose individual stages can be evaluated AND whose end-to-end consistency will be evaluated in future phases (e.g. marking quality, concept detection, explanation traceability, feedback quality, mind-map quality, and lecturer agreement).

## C3-DEC-001
**Date:** 2026-10-08  
**Component:** C3 — Automated Marking  
**Category:** A — Approved / inherited decision  
**Problem / Need:** Constrain the C3 input type to reduce uncontrolled variables (OCR noise).  
**Alternatives Considered:** A. Scanned PDFs B. Image uploads C. Typed answers  
**Decision:** Restrict C3 to processing TYPED ANSWERS ONLY for PP1.  
**Reason / Justification:** Removing OCR and image preprocessing isolates the semantic analysis research contribution, ensuring that errors in marking are purely due to semantic understanding rather than text-extraction failures.  
**Evidence Source:** Supervisor-approved C3 scope.  
**Implementation:** `StudentAssessment.jsx` provides only a text area. Backend strictly accepts text strings.  
**Validation:** Tested via E2E Node API and Browser payload parsing.  
**Outcome:** Clean text payloads are processed accurately.  
**Related Commit:** (Pending final push)  

## C3-DEC-002
**Date:** 2026-10-08  
**Component:** C3 — Automated Marking  
**Category:** C — New implementation/research decision  
**Problem / Need:** C3 needs to process answers through multiple specialized analytical steps.  
**Alternatives Considered:** A. Monolithic LLM prompt B. Modular architecture within the C3 FastAPI service  
**Decision:** C3 modular service architecture separating Analysis, Marking, Feedback, and Mindmap into distinct modules/routes within one FastAPI service.  
**Reason / Justification:** Separation of concerns allows independent experimental evaluation of each phase (e.g. testing RAG on Analysis vs Rubric).  
**Evidence Source:** Implementation / system requirement — pending research validation.  
**Implementation:** `ai-services/c3/app/api/` routing structure.  
**Validation:** Pytest coverage across isolated modules.  
**Outcome:** 100% test pass rate for isolated modular boundaries.  

## C3-DEC-003
**Date:** 2026-10-08  
**Component:** C3 — Automated Marking  
**Category:** C — New implementation/research decision  
**Problem / Need:** Need a measurable starting point for semantic analysis before introducing non-deterministic LLMs.  
**Alternatives Considered:** A. Direct LLM extraction B. Deterministic baseline (lexical/concept-overlap)  
**Decision:** Function 1 deterministic baseline using lexical/semantic concept-overlap matching rules. TF-IDF and advanced LLMs are proposed as future experimental comparisons.  
**Reason / Justification:** A deterministic baseline is required to measure if advanced techniques actually improve precision/recall.  
**Evidence Source:** Research methodology best practice.  
**Implementation:** `analysis_api.py` baseline matching logic mapping sentences.  
**Validation:** Outputs consistent concept-to-sentence mapping arrays.  
**Outcome:** Stable deterministic baseline achieved for comparison.  

## C3-DEC-004
**Date:** 2026-10-08  
**Component:** C3 — Automated Marking  
**Category:** A — Approved / inherited decision  
**Problem / Need:** Scoring must follow structured academic guidelines.  
**Alternatives Considered:** A. Holistic AI guessing B. Rubric-aware criterion-level marking  
**Decision:** Implement Rubric-aware criterion-level marking.  
**Reason / Justification:** The approved C3 research scope requires explainable, criterion-level evidence to mimic real lecturer rubrics.  
**Evidence Source:** Supervisor-approved C3 scope + research literature on rubric-based short-answer grading.  
**Implementation:** Function 2 marking engine (`marking.py`).  
**Validation:** Unit tests validate exact criteria mapping.  
**Outcome:** Accurate criterion scores derived from specific evidence arrays.  

## C3-DEC-005
**Date:** 2026-10-08  
**Component:** C3 — Automated Marking  
**Category:** C — New implementation/research decision  
**Problem / Need:** Calculating marks for partially correct answers.  
**Alternatives Considered:** A. `max_marks * 0.5` universal B. Exact rubric scoring rules  
**Decision:** Exact rubric scoring / partial-credit handling using strict Pydantic rules (`allow_partial`).  
**Reason / Justification:** Universal fractions distort rubrics. Marking must enforce explicit rules configured by the assessment owner.  
**Evidence Source:** Implementation / system requirement — pending research validation.  
**Implementation:** `ScoringLevel` and `EvidenceRule` Pydantic models.  
**Validation:** Pipeline triggers HTTP 422 if invalid rules are supplied; successful validation yields exact rubric integers/floats.  
**Outcome:** Strict rubric enforcement in marking.  

## C3-DEC-006
**Date:** 2026-10-08  
**Component:** C3 — Automated Marking  
**Category:** B — Supervisor-directed decision  
**Problem / Need:** Explainability requires pointing to exact text in the student's answer.  
**Alternatives Considered:** A. General summary explanation B. Evidence traceability through sentence IDs  
**Decision:** Evidence traceability through sentence IDs.  
**Reason / Justification:** True explainable AI in education must highlight exact phrases/sentences contributing to a decision.  
**Evidence Source:** Supervisor-directed explainable AI requirement.  
**Implementation:** Analysis engine tags sentences; Marking engine assigns `evidence_sentence_ids`.  
**Validation:** API-level evidence verified; manual/static UI verification confirms highlighting.  
**Outcome:** Traceability from mark back to student input established in API and UI components.  

## C3-DEC-007
**Date:** 2026-10-08  
**Component:** C3 — Automated Marking  
**Category:** C — New implementation/research decision  
**Problem / Need:** Displaying concept mastery accurately.  
**Alternatives Considered:** A. Binary (Yes/No) B. Selected-level-aware concept classification  
**Decision:** Selected-level-aware concept classification (Demonstrated, Partial, Missing).  
**Reason / Justification:** Better reflects the granular nature of academic assessment where students may partially mention concepts.  
**Evidence Source:** Implementation / system requirement — pending research validation.  
**Implementation:** Frontend `ConceptStatus` component dynamically mapping state.  
**Validation:** E2E payload successfully populates multi-state concepts.  
**Outcome:** Clear concept visualization in UI.  

## C3-DEC-008
**Date:** 2026-10-08  
**Component:** C3 — Automated Marking  
**Category:** B — Supervisor-directed decision  
**Problem / Need:** Feedback must be actionable and grounded.  
**Alternatives Considered:** A. Generative text wall B. Explainable feedback based on structured evidence  
**Decision:** Explainable feedback based on structured evidence.  
**Reason / Justification:** The baseline was designed so feedback is constructed from structured upstream evidence, ensuring comments are derived strictly from criterion performance without introducing an additional generative dependency.  
**Evidence Source:** Supervisor-approved scope.  
**Implementation:** Function 3 feedback generator separating strengths and missing concepts.  
**Validation:** Generates arrays of specific strengths and weaknesses tied to concepts.  
**Outcome:** Predictable, safe, formatted feedback for students.  

## C3-DEC-009
**Date:** 2026-10-08  
**Component:** C3 — Automated Marking  
**Category:** C — New implementation/research decision  
**Problem / Need:** Generating mind maps from text efficiently.  
**Alternatives Considered:** A. LLM drawing generation B. Deterministic concept-based mind-map baseline  
**Decision:** Deterministic concept-based mind-map baseline mapping structured concepts into nodes.  
**Reason / Justification:** Graph construction is safer when parsed from deterministic concept arrays rather than direct generative inference.  
**Evidence Source:** Implementation / system requirement — pending research validation.  
**Implementation:** Function 4 mind map mapping logic.  
**Validation:** JSON yields perfectly structured `nodes` and `relationships`.  
**Outcome:** Consistently rendered mind maps in React.  

## C3-DEC-010
**Date:** 2026-10-08  
**Component:** C3 — Automated Marking  
**Category:** C — New implementation/research decision  
**Problem / Need:** Distinguishing what a student wrote vs what the rubric wanted.  
**Alternatives Considered:** A. Merge all concepts B. Student-derived vs expected concept distinction  
**Decision:** Maintain strict distinction between student-derived and expected concepts.  
**Reason / Justification:** "Missing" concepts must be visible on the mind map without implying the student provided them.  
**Evidence Source:** Implementation / system requirement — pending research validation.  
**Implementation:** Mind map schema explicitly tracks `status: missing`.  
**Validation:** Visualized as grey/ghost nodes in the UI mind map.  
**Outcome:** Graph clearly illustrates knowledge gaps.  

## C3-DEC-011
**Date:** 2026-10-08  
**Component:** C3 — Automated Marking  
**Category:** C — New implementation/research decision  
**Problem / Need:** Mind maps require a central anchoring point.  
**Alternatives Considered:** A. Anchor on primary concept B. Anchor on question context  
**Decision:** Mind-map root anchored to the Question/Assessment context.  
**Reason / Justification:** Provides structural consistency regardless of answer content.  
**Evidence Source:** Implementation / system requirement — pending research validation.  
**Implementation:** Root node assigned `SE-DB-001` or similar ID.  
**Validation:** Verified root generation in DB payload.  
**Outcome:** Predictable radial layout origin.  

## C3-DEC-012
**Date:** 2026-10-08  
**Component:** C3 — Automated Marking  
**Category:** A — Approved / inherited decision  
**Problem / Need:** Connecting C3 with the wider LMS shell.  
**Alternatives Considered:** A. Standalone Django B. Shared Node/Express orchestration  
**Decision:** Shared Node/Express orchestration bridging UI to Python backend.  
**Reason / Justification:** Adheres to AdaptiveLearnSE monolithic Node boundary rules, ensuring unified Auth and Routing (C1, C2).  
**Evidence Source:** System Architecture requirement.  
**Implementation:** `c3AppController.js` coordinates async calls to the FastAPI instance.  
**Validation:** Node integration tests passed.  
**Outcome:** Seamless UI to AI pipeline transit.  

## C3-DEC-013
**Date:** 2026-10-08  
**Component:** C3 — Automated Marking  
**Category:** A — Approved / inherited decision  
**Problem / Need:** Persistent data storage.  
**Alternatives Considered:** A. PostgreSQL B. Shared MongoDB architecture  
**Decision:** Shared MongoDB architecture (`c3_submissions`, `c3_results`).  
**Reason / Justification:** Adheres to AdaptiveLearnSE DB rules.  
**Evidence Source:** System Architecture requirement.  
**Implementation:** Mongoose models/drivers in Node.js.  
**Validation:** Verified database insertion via Node scripts.  
**Outcome:** High-availability JSON document persistence.  

## C3-DEC-014
**Date:** 2026-10-08  
**Component:** C3 — Automated Marking  
**Category:** B — Supervisor-directed decision  
**Problem / Need:** AI marking reliability and academic safety.  
**Alternatives Considered:** A. Auto-publish marks B. Lecturer human-in-the-loop verification  
**Decision:** Lecturer human-in-the-loop verification.  
**Reason / Justification:** C3 is a support system. AI cannot finalize academic marks without lecturer validation.  
**Evidence Source:** Supervisor-directed requirement for AI safety.  
**Implementation:** Submissions enter `awaiting_review` state explicitly.  
**Validation:** Tested Review queue population and UI finalization guards.  
**Outcome:** Safe, ethical AI rollout.  

## C3-DEC-015
**Date:** 2026-10-08  
**Component:** C3 — Automated Marking  
**Category:** B — Supervisor-directed decision  
**Problem / Need:** Handling AI errors or disagreements.  
**Alternatives Considered:** A. Blind override B. Accept vs Override with reason  
**Decision:** Accept vs Override with explicit reason persistence.  
**Reason / Justification:** Capturing the override reason provides auditable lecturer disagreement data that can later support error analysis, disagreement analysis, model improvement research, and future learning experiments.  
**Evidence Source:** System requirement for AI optimization research.  
**Implementation:** Override action requires `overrideMark` and `overrideReason` payloads.  
**Validation:** DB inspection confirms original mark and lecturer mark are safely separated.  
**Outcome:** High-quality audit trails for future analysis.  

## C3-DEC-016
**Date:** 2026-10-08  
**Component:** C3 — Automated Marking  
**Category:** B — Supervisor-directed decision  
**Problem / Need:** Evaluating the system without real student privacy risks.  
**Alternatives Considered:** A. Live classroom deployment B. Purpose-built synthetic dataset  
**Decision:** The MAIN research dataset will be purpose-built and synthetic (to be created in a later phase). Current seed/test data is purely for development/integration.  
**Reason / Justification:** Prevents PII leaks and allows controlled edge-case generation.  
**Evidence Source:** Supervisor-directed decision on dataset methodology.  
**Implementation:** `seed_users.js` and `assessmentService.js` utilize fake `IT` IDs and seeded rubric structures for integration data.  
**Validation:** End-to-end tests function over the development bounds.  
**Outcome:** Safe experimental sandbox established for future research dataset application.  

## C3-DEC-017
**Date:** 2026-10-08  
**Component:** C3 — Automated Marking  
**Category:** C — New implementation/research decision  
**Problem / Need:** Role of LLM/RAG in the architecture.  
**Alternatives Considered:** A. Assumed core architecture B. LLM/RAG as experimental comparison  
**Decision:** LLM/RAG is strictly an experimental comparison methodology, not the assumed core architecture.  
**Reason / Justification:** We must not claim LLM/RAG is superior until experiments demonstrate it. The research compares deterministic baselines against generative models.  
**Evidence Source:** Research methodology best practice.  
**Implementation:** Pluggable AI engine via `ai-services` modularity.  
**Validation:** NOT YET EVALUATED.  
**Outcome:** Architecturally prepared for rigorous comparative evaluation.  
