# AdaptiveLearnSE Component 3 — Two-Minute Backup Demo Video Script & Storyboard

**Document Version:** 2.0.0 (Authoritative 2-Minute Video Backup Specification)  
**Target Milestone:** Project Performance 1 (PP1) / Viva Evaluation (22, 23, and 26 October 2026)  
**Component:** Component 3 (AI-Powered Automated Marking & Answer Analysis System)  
**Target Runtime:** Exactly 120 Seconds (2:00 Minutes)  
**Status:** **Authoritative Script, Storyboard & Recording Runbook Prepared for Video Capture**  

---

## 1. Video Production & Recording Setup

| Parameter | Recommended Specification |
| :--- | :--- |
| **Resolution & Aspect Ratio** | 1920 × 1080 (1080p, 16:9 Standard Full HD) |
| **Framerate** | 30 or 60 frames per second |
| **Recording Tool** | OBS Studio (free/open-source) OR Windows Game Bar (`Win + Alt + R`) |
| **Audio Configuration** | Clean USB condenser microphone; noise suppression enabled |
| **Browser Configuration** | Google Chrome full-screen (`F11`), 100% zoom, dark/light theme consistent |
| **Target Video Filename** | `ss/videos/c3_pp1_two_minute_demo.mp4` (or cloud presentation backup link) |

---

## 2. Minute-by-Minute Storyboard & Verbatim Voiceover

```
[0:00 - 0:15] Scene 1: Problem Definition & Title Card
[0:15 - 0:40] Scene 2: Assessment Setup & Multi-Criterion Rubric
[0:40 - 1:00] Scene 3: Cohort Ingestion & Pre-Marking Validation
[1:00 - 1:25] Scene 4: Automated Batch Marking & Irrelevant Rejection
[1:25 - 1:45] Scene 5: Explainable Evidence & Interactive SVG Mind Map
[1:45 - 2:00] Scene 6: Lecturer Override Governance, Finalization & C1 Sync
```

---

### Scene 1: Title Card & Educational Context (0:00 – 0:15 | 15s)
- **Visual On Screen:** Title slide showing *"AdaptiveLearnSE — Component 3: AI-Powered Automated Marking & Answer Analysis System"*. Transition smoothly to the web login page at `http://localhost:5173/login`.
- **Voiceover:**  
  *"Grading subjective software engineering answers is time-consuming, prone to marker fatigue, and lacks actionable feedback. AdaptiveLearnSE Component 3 provides an AI-powered, rubric-aware marking engine with concept diagnosis, explainable feedback, and strict lecturer governance."*

---

### Scene 2: Lecturer Batch Assessment Setup (0:15 – 0:40 | 25s)
- **Visual On Screen:** Log in as lecturer (`SLIITLEC101`). Open `/lecturer/c3/batch`. Highlight Question `SE3010-Q01` (4 marks) and expand the two rubric criteria cards (High Cohesion and Loose Coupling, each with Full, Partial, and None levels). Click **"Save & Continue to Answers ->"**.
- **Voiceover:**  
  *"Lecturers configure the assessment once. Here, Question SE3010-Q01 defines a 4-mark rubric partitioned into High Cohesion and Loose Coupling criteria. Clicking Save locks this rubric into MongoDB for the entire cohort."*

---

### Scene 3: Cohort Ingestion & Pre-Marking Validation (0:40 – 1:00 | 20s)
- **Visual On Screen:** In Step 2, click **"⚡ Fill Sample Cohort"**, showing 7 student answers. Click **"Validate Answers ->"**. Camera zooms into Step 3 summary cards showing 5 valid rows, 1 duplicate student ID flagged (`IT21001001`), and 1 empty row flagged (`IT21001005`).
- **Voiceover:**  
  *"Next, student answers are ingested via dynamic grid or CSV. Before running AI models, our defensive validation engine scans the cohort, flagging duplicate student submissions and empty rows to prevent corrupted grading."*

---

### Scene 4: Real-Time Batch Marking & Fluff Rejection (1:00 – 1:25 | 25s)
- **Visual On Screen:** Click **"Mark Valid Cohort (AI) ->"**. Table populates with scores within 1 second. Highlight student `IT21001001` with `4.0 / 4.0 (100%)` and hover over irrelevant student `IT21001006` showing `0.0 / 4.0 (0%)`.
- **Voiceover:**  
  *"Automated marking executes in milliseconds. Valid answers receive criterion-level marks. Notice that student IT21001006 submitted a verbose answer discussing database normalization—our rubric evaluator rejected the irrelevant response, awarding zero marks with zero hallucinations."*

---

### Scene 5: Traceable Evidence & Concept Mind Map DAG (1:25 – 1:45 | 20s)
- **Visual On Screen:** Click **"Inspect Evidence & Mind Map"** on student `IT21001001`. In modal, show highlighted sentence evidence, strengths feedback, and interactive SVG mind-map graph with green demonstrated concept nodes.
- **Voiceover:**  
  *"Every score is traceable. The inspector modal highlights the exact answer sentence fulfilling each rubric criterion, accompanied by formative feedback and a concept mind map visualizing demonstrated, partial, and missing knowledge in an interactive SVG graph."*

---

### Scene 6: Lecturer Override, Finalization & C1 Sync (1:45 – 2:00 | 15s)
- **Visual On Screen:** In modal, enter override score `3.5` with justification: `"Awarded 3.5 marks. Strong microservices justification with minor terminology gap."` Click **Apply Override**. Close modal, click **"⚡ Finalize All Submissions"**. Table reaches 100% Finalized audit state.
- **Voiceover:**  
  *"To guarantee academic governance, score adjustments mandate written justifications. Finalizing the cohort transitions submissions to the audit state and emits learning events to Component 1's cognitive digital twin. Thank you."*

---

## 3. Recording Instructions for Candidate

1. Launch local dev environment (Python port 8003, Express port 3000, Vite port 5173).
2. Open Chrome incognito at `http://localhost:5173/login`.
3. Press `Win + Alt + R` to start Windows Game Bar recording (or OBS Studio).
4. Perform the exact 6 scenes described above following the timestamps.
5. Save the output MP4 to `ss/videos/c3_pp1_two_minute_demo.mp4`.
6. Keep this MP4 on a local USB flash drive as a fail-safe backup for the viva panel.
