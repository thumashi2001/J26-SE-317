# AdaptiveLearnSE Component 3 — Verifiable Git Work Diary & Task Traceability

**Document Version:** 2.0.0 (Authoritative Governance & Work Diary)  
**Target Milestone:** Project Performance 1 (PP1) / Viva Evaluation (22, 23, and 26 October 2026)  
**Component:** Component 3 (AI-Powered Automated Marking & Answer Analysis System)  
**Candidate / Contributor:** Vk-Viman (Component 3 Engineer)  

---

## 1. Verifiable Git Commit Diary (Direct Repository Evidence)

The following diary is extracted directly from verifiable Git commit records in `feature/c3-system-integration` and `feature/c3-pp1-final-integration-20261020`. No commits or timestamps have been simulated or altered.

| Commit Hash | Commit Date | Author | Work Area / Module | Direct Git Commit Subject | Associated Deliverable / Requirement | Verifiable Tests & Artifacts Produced |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `950bf99` | 2026-09-15 | Vk-Viman | Monorepo Root | `chore: scaffold AdaptiveLearnSE monorepo` | Project Initialization | Repository layout & Docker configuration. |
| `5cdf37b` | 2026-09-15 | Vk-Viman | `ai-services/c3/` | `feat: initialize C3 AI service` | Service Skeleton | FastAPI app initialization and schemas. |
| `34c2638` | 2026-10-06 | Vk-Viman | `.agents/skills/` | `chore: add C3 development agent instructions` | Engineering Governance | `c3-development` skill instructions. |
| `6c91ca6` | 2026-10-06 | Vk-Viman | `ai-services/c3/` | `feat: implement C3 answer processing and semantic baseline` | Function 1 (F1) | `test_preprocessing.py`, `test_semantic_baseline.py` (8 passed). |
| `dbf6dc7` | 2026-10-07 | Vk-Viman | `ai-services/c3/` | `feat: implement rubric-aware marking engine` | Function 2 (F2) | `test_rubric_validator.py`, `test_criterion_evaluator.py` (30 passed). |
| `9de7e54` | 2026-10-07 | Vk-Viman | `ai-services/c3/` | `feat: implement explainable marking feedback` | Function 3 (F3) | `test_feedback_generator.py` (10 passed). |
| `ce4796b` | 2026-10-07 | Vk-Viman | `ai-services/c3/` | `feat: implement concept-based mind map generator` | Function 4 (F4) | `test_mindmap_generator.py`, `test_relationship_builder.py` (5 passed). |
| `6ffea98` | 2026-10-07 | Vk-Viman | `backend/src/modules/c3/` | `feat: integrate C3 AI service with shared backend` | Backend Gateway | `c3Controller.js`, `aiClient.js`, initial Node tests. |
| `1024cdd` | 2026-10-11 | Vk-Viman | `ai-services/c3/` | `feat: integrate end-to-end assessment pipeline` | Composite Assessment | `test_assessment_api.py` (7 passed). |
| `7d44e19` | 2026-10-11 | Vk-Viman | `frontend/src/pages/c3/` | `feat: integrate assessment workflow with frontend` | Frontend UI | `AssessmentPage.jsx`, `MindMapGraph.jsx`, `CriterionCard.jsx`. |
| `fb29391` | 2026-10-14 | Vk-Viman | Backend & UI | `feat: complete lecturer review and finalization workflow` | Governance & Overrides | `LecturerQueuePage.jsx`, `LecturerReviewPage.jsx`, override reason check. |
| `3fc28ef` | 2026-10-14 | Vk-Viman | Integration | `feat: integrate c3-c1 learner modeling bridge and robust input handling` | C3-to-C1 Bridge | `backend/src/integration/c3-c1/index.js`, idempotency tests. |
| `af7d0cb` | 2026-10-14 | Vk-Viman | Monorepo Root | `merge: integrate Development into C3 system integration` | Team Sync | Merged C1 and C2 PRs #19–#26 cleanly. |
| `4ae6e0e` | 2026-10-14 | Vk-Viman | Datasets | `feat: integrate synthetic dataset package and verified programmatic loader` | Benchmark Dataset | `test_dataset_loader.py` (12 passed), 1,002 synthetic answers. |
| `6688876` | 2026-10-14 | Vk-Viman | Backend & Services | `fix: implement authoritative MCQ marking engine and comprehensive test suite` | Deterministic MCQ | `mcqMarkingService.js`, 12 dedicated MCQ unit tests. |
| `b1b148b` | 2026-10-14 | Vk-Viman | Frontend & UI | `fix: enhance table responsiveness, UI scrolling, and provenance tracking` | Usability Polish | CSS grid responsiveness, sticky review headers, provenance tags. |
| Working Tree | 2026-10-20 | Vk-Viman | Backend & UI | Lecturer Batch Marking Studio & Evaluation Verification | Cohort Batch Marking | `batchMarkingService.js`, `LecturerBatchMarkingPage.jsx`, 41 backend tests, 12 screenshots. |

---

## 2. Microsoft Planner Audit & Access Status

- **Repository Audit Finding:** No Microsoft Planner `.xlsx` export, `.json` task dump, or API access token is stored in the Git repository.
- **Academic Disclosure:** In compliance with anti-fabrication guidelines, no fictional Planner completion dates or task IDs have been fabricated.
- **Candidate Instructions for Viva Day:**
  1. Open your SLIIT Microsoft 365 account at `https://tasks.office.com/`.
  2. Navigate to the **AdaptiveLearnSE** Project Board.
  3. Filter by bucket **Component 3: Automated Marking & Answer Analysis**.
  4. Click the three dots `...` in the top menu and select **"Export plan to Excel"**.
  5. Save the resulting file as `docs/pp1/planner_export_component3.xlsx` and keep it open in Excel during the viva defense as complementary proof of task management.

---

## 3. Work Regularity Summary for the Panel

When examiners inspect project management and task regularity:
- Work commenced in mid-September 2026 with architectural scaffolding and AI service initialization.
- Core algorithmic functions (F1 Preprocessing, F2 Rubric Scoring, F3 Feedback, F4 Mind Map DAGs) were developed and tested between 6 October and 7 October 2026.
- Full-stack UI integration and end-to-end composite pipeline were completed between 11 October and 14 October 2026.
- Advanced lecturer cohort batch marking, empirical held-out benchmark evaluation (N=150), and comprehensive documentation verification were completed on 20 October 2026.
- All code progress is accompanied by automated regression tests and verifiable Git commits.
