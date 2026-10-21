# 02 Official PP1 marking criteria — assessment of C3 against the real mark sheet

Source (V): `C:\Users\M S I\Downloads\PP1 Assessment Criteria (1).pdf` — "RP (IT4010) – Progress Presentation 1 – Mark Sheet [Total contribution = 15%]". Bands: Excellent 100–75, Good 74–60, Average 59–40, Below 39–0. Examiner 1, Examiner 2, Moderator sign; there is also "Recommend for NBQSA (Yes/No)".
The lecture deck (`IT4010_Sem1_Lecture 7.pptx`) is *guidance*, not the rubric. SOLID is **not** in the rubric; it is evidence for "standards/best practices" (LO3).

**Labels:** V = verified by reading/executing; R = reported by you; I = inference. The "indicative band" is **my judgement of how the evidence reads against the descriptor, not a prediction of the examiners' mark**. No averaged percentage is given.

## 1. Weights (V)
| LO | Title | Weight | Sub-criteria (weight inside the LO) |
|---|---|---|---|
| LO1 | Proven gap / creative solution | 10 % | problem definition 30 · proof of concept 70 |
| LO2 | Applying knowledge in the stream | 25 % | application of key pillars 30 · application of technologies 70 |
| LO3 | Solution implementation | 40 % | design excellence 20 · completion 30 · standards/best practices 20 · user/functional requirements 20 · risk mitigation 10 |
| LO4 | Effective communication | 15 % | communication 60 · presentation 40 |
| LO5 | Commercialisation / entrepreneurship | 10 % | single criterion |

Effective marks out of 100: LO1 3.0 + 7.0; LO2 7.5 + 17.5; LO3 8 + 12 + 8 + 8 + 4; LO4 9 + 6; LO5 10. **Technology application (17.5), completion (12) and proof of concept (7) are the largest single items.**

## 2. The "100 % vs ~50 %" question
- The sheet's top band for completion says: *"Work completed is satisfactory (approximately 50% where applicable) and no identifiable delay as per the project plan"* (V). The sheet never asks for 100 %.
- You told me the panel expects 100 % of the approved individual component (R). I could not find that in any document (V by search). If the panel judges against the **full approved scope**, the exposed items are in 08 §3: LLM/RAG/semantic-model comparison not run, C2/C4/CCKG integration not built, real student data and human mind-map/feedback evaluation absent, concept relationships absent (star graph).
- Practical stance: present C3 as "the deterministic core of all five capabilities is working end to end; the experimental layer is the next phase", never as 100 % complete.

## 3. Criterion-by-criterion assessment
| Criterion (weight) | What the descriptor needs | Evidence for | Evidence against / gaps | Indicative band (judgement) |
|---|---|---|---|---|
| **LO1 problem definition (3.0)** | Problem clearly presented *referring to the current implementation* | Proposal gap p.26; abstract p.3; manual-marking motivation p.13; running pipeline shows the gap (score + concept evidence + feedback + map) | Survey (Appendix 7) is about learning progress, not marking; no marking-time data | Excellent–Good (I) |
| **LO1 proof of concept (7.0)** | Implementation clearly demonstrates the proposed solution | Verified end-to-end results: 4/4, 2/4, 0/4 (arch presets), 3/3, 2/4; lecturer review/override/finalise; 324+75 tests | Matching is lexical (paraphrase 0/4, negation and stuffing 4/4); no model comparison; synthetic data | Good (I); Excellent only if you present honestly as a *baseline* proof of concept |
| **LO2 key pillars (7.5)** | Most appropriate research areas identified and applied | Day 22/23 selection of TF-IDF, SBERT, RoBERTa, GPT/Llama; rubric-aware marking, concept diagnosis, XAI evidence, mind map; DSR + experiment design | Implementation applies *none* of the transformer/LLM pillars yet; XAI is rule-based transparency, not learned-model explainability | Average–Good (I) |
| **LO2 technologies (17.5)** | Well-presented, in-depth knowledge of technologies | Real FastAPI/Express/React/Mongo/Neo4j stack; provider abstraction (Gemini/OpenAI/Ollama), cache/retry/rate limiting; sklearn TF-IDF history | Proposal justifies technologies only by licence cost (p.61); no BERT/RoBERTa/SBERT code; you must be able to explain every layer (heavy AI-assisted development) | Average–Good, depends on viva answers (I) |
| **LO3 design (8)** | Excellent design features | Pure core packages, DIP-clean, thin routes, provider ABC, hermetic tests (04) | Duplicated helpers, 95-line `assess_answer`, second marking engine in Node, god components, singletons | Good (I) |
| **LO3 completion (12)** | ≈50 % satisfactory and no identifiable delay | Five capabilities exist in baseline form; lecturer flow; evidence pack | Delay vs plan not evidenced (WBS/Gantt are images); experimental layer not started; integration contracts unbuilt | Good–Excellent against the sheet's own ≈50 %; Average against 100 % (I) |
| **LO3 standards/best practices (8)** | Appropriate standards well demonstrated | 324 py + 75 node tests, strict xfail "known bug" convention, ruff/eslint, CLAUDE/AGENTS rules, dataset audit, SHA-verified repair, git history | 111 ruff and 13 ESLint findings unfixed; security todos; 29 commits with AI co-author trailer (disclose) | Good (I) |
| **LO3 user/functional requirements (8)** | Comprehensive, realistic, well described | 46 FR + 30 NFR (proposal), 96 FR + 56 stories + 20 personas (Day 3–6), traceability Table 24 | Two FR numbering systems; PP1 "two key functions" defined only in team doc; no numeric NFR targets; requirement→test map is partial (03) | Good (I) |
| **LO3 risk mitigation (4)** | Risks identified, measures executing | Demo-day risk register RSK-01..07; threats to validity p.33–34; known-bug tests | Proposal has no risk section; research risks (data validity, quota, leakage) not in a register | Average–Good (I) |
| **LO4 communication (9) / presentation (6)** | Structure, Q&A, visuals, time | 09–12 provide scripts and Q&A | Entirely depends on you; Q&A on code you did not hand-write is the main risk | N/A — not assessable from the repo |
| **LO5 commercialisation (10)** | Sound evidence of business potential, user benefits | Proposal pp.51–59: B2B institutional SaaS, tiers, revenue, costs, IP, competitor comparison | **No market evidence**: no interviews, prices, competitor price data, projections (V absent) | Average (I); improve by a one-slide pitch (see 12/09) — claims must stay descriptive |

## 4. What raises the marks most before the viva (ordered by weight × feasibility)
1. LO2 technologies (17.5): be able to explain, file by file, how the pipeline works and *why* TF-IDF/SBERT/RoBERTa/LLM were chosen (09 Part D, 10 groups 3–4).
2. LO1 proof of concept + LO3 completion (19): a clean live demo of the verified presets and lecturer flow; state limits first.
3. LO4 (15): rehearse the 60 s / 2 min / 5 min versions (12).
4. LO5 (10): a short, honest commercial slide using proposal pp.51–59 only.
5. LO3 standards/risk (12): show test counts, the dataset audit and the known-bug convention; show the research-risk list (08 §7).

## 5. Lecture-level evidence pack (slide 19) — status
| Item | Status |
|---|---|
| Working demo | Available (reliability order in 11) |
| Two key functions | Defined only in team execution doc §7.3: (1) Answer Processing + Semantic Analysis, (2) Rubric-Aware Marking + Evidence — both demonstrable |
| Architecture diagram | Day 24 docs/PNG exist (not audited visually) |
| User/supervisor feedback | Not found as signed records (supervisor sheet has blank decision fields; V) — do not claim approvals |
| GitHub commit history | Present; AI co-author trailer on 29 commits |
| MS Planner, RP diary | Logbook docx exists (21 Jul–22 Aug entries); Planner not seen |
| **AI-use record** | Proposal Table 33 discloses ChatGPT for planning/drafting; **code-level AI assistance (Claude Code) must be added** — prepare a truthful statement |
| Testing evidence | Strong (324/75/5) |
| Risk register | Demo-day only (RSK-01..07) |
