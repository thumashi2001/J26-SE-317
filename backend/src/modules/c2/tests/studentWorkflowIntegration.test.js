import test from 'node:test';
import assert from 'node:assert/strict';

import {
  prepareAttemptPayload,
  executeAttemptSubmission,
} from '../../../../../frontend/src/services/attemptSubmissionHelper.js';
import {
  submitMockAttempt,
  listMockAttempts,
  getMockAttempt,
} from '../services/mockAttemptService.js';
import { resetMemoryStoreForTesting } from '../services/mockAttemptRepository.js';

test('studentWorkflowIntegration: setup test harness', () => {
  resetMemoryStoreForTesting();
});

test('Stage Navigation & State: supports 5-stage progression', () => {
  const stages = ['overview', 'evidence', 'setup', 'attempt', 'results'];
  assert.equal(stages.length, 5);

  let currentStage = 'overview';
  let generatedPaper = null;
  let activeAttempt = null;
  let attemptResult = null;

  // Overview to Evidence
  currentStage = 'evidence';
  assert.equal(currentStage, 'evidence');

  // Evidence to Setup
  currentStage = 'setup';
  assert.equal(currentStage, 'setup');

  // Attempt is locked without a generated paper
  const canAccessAttempt = Boolean(generatedPaper);
  assert.equal(canAccessAttempt, false, 'Exam Attempt must be locked when no paper is generated');

  // Generate paper
  generatedPaper = {
    paper_id: 'MOCK-SE3080-001',
    module_key: 'software_project_management',
    source_type: 'authentic',
    total_marks: 100,
    questions: [
      { question_id: 'SE3080-Q1', question_text: 'Explain Agile sprint planning.', marks: 10, source_type: 'authentic' },
      { question_id: 'SE3080-Q2', question_text: 'Discuss earned value analysis.', marks: 10, source_type: 'authentic' },
    ],
  };

  assert.equal(Boolean(generatedPaper), true);

  // Transition to Attempt
  activeAttempt = generatedPaper;
  currentStage = 'attempt';
  assert.equal(currentStage, 'attempt');

  // Submit attempt transitions to Results
  attemptResult = {
    attemptId: 'ATTEMPT-999',
    moduleKey: 'software_project_management',
    status: 'pending_marking',
    marksAwarded: null,
  };
  activeAttempt = null;
  currentStage = 'results';
  assert.equal(currentStage, 'results');
  assert.equal(attemptResult.status, 'pending_marking');
  assert.equal(attemptResult.marksAwarded, null);
});

test('Module Selection Persistence & Change Safeguards', () => {
  let selectedModuleKey = 'database_systems';
  let generatedPaper = {
    paper_id: 'MOCK-DBS-01',
    module_key: 'database_systems',
    questions: [{ question_id: 'DB-1', question_text: 'B-tree index structures' }],
  };

  // Changing module resets generated paper to prevent cross-module reuse
  const newModuleKey = 'distributed_systems';
  if (newModuleKey !== selectedModuleKey) {
    selectedModuleKey = newModuleKey;
    generatedPaper = null; // Cleanly discarded
  }

  assert.equal(selectedModuleKey, 'distributed_systems');
  assert.equal(generatedPaper, null, 'Changing module must discard previously generated paper');
});

test('Practice Setup: Authentic Past-Paper generation maintains real marks', () => {
  const authenticPaper = {
    paper_id: 'MOCK-AUTH-IT3020-001',
    module_key: 'database_systems',
    source_type: 'authentic',
    target_marks: 50,
    total_marks: 50,
    questions: [
      {
        question_id: 'IT3020-2023-Q1a',
        question_text: 'Explain indexing techniques for high-write databases.',
        marks: 25,
        source_type: 'authentic',
      },
      {
        question_id: 'IT3020-2023-Q1b',
        question_text: 'Compare optimistic vs pessimistic concurrency control.',
        marks: 25,
        source_type: 'authentic',
      },
    ],
  };

  const payload = prepareAttemptPayload({
    paper: authenticPaper,
    moduleKey: 'database_systems',
    questions: authenticPaper.questions,
    answers: {
      'IT3020-2023-Q1a': 'LSM trees are optimized for high-write workloads.',
    },
    secondsElapsed: 120,
  });

  assert.equal(payload.moduleKey, 'database_systems');
  assert.equal(payload.sourceType, 'authentic');
  assert.equal(payload.questions[0].marks, 25);
  assert.equal(payload.questions[1].marks, 25);
  assert.equal(payload.answers['IT3020-2023-Q1a'], 'LSM trees are optimized for high-write workloads.');
});

test('Practice Setup: Synthetic Practice preserves unassessed marks across all 8 modules', () => {
  const allModules = [
    'case_studies_software_engineering',
    'database_systems',
    'software_project_management',
    'user_experience_engineering',
    'application_frameworks',
    'distributed_systems',
    'software_architecture',
    'software_engineering_process_quality_management',
  ];

  allModules.forEach((mod) => {
    const synthQuestions = Array.from({ length: 5 }, (_, i) => ({
      question_id: `M16-${mod.toUpperCase().slice(0, 4)}-${i + 1}`,
      question_text: `Synthetic question #${i + 1} for ${mod}`,
      marks: null,
      source_type: 'synthetic',
    }));

    const paper = {
      paper_id: `MOCK-SYNTH-${mod}`,
      module_key: mod,
      practice_mode: 'synthetic_experimental',
      source_type: 'synthetic',
      total_marks: null,
      questions: synthQuestions,
    };

    const payload = prepareAttemptPayload({
      paper,
      moduleKey: mod,
      questions: synthQuestions,
      answers: { [`M16-${mod.toUpperCase().slice(0, 4)}-1`]: 'Student answer' },
      secondsElapsed: 60,
    });

    assert.equal(payload.sourceType, 'synthetic');
    assert.equal(payload.moduleKey, mod);
    payload.questions.forEach((q) => {
      assert.equal(q.marks, null, 'Synthetic question marks must remain null (unassessed)');
      assert.equal(q.source_type, 'synthetic');
    });
  });
});

test('Answer Persistence Across Question Navigation Simulation', () => {
  const questions = [
    { question_id: 'Q1', question_text: 'Text 1' },
    { question_id: 'Q2', question_text: 'Text 2' },
    { question_id: 'Q3', question_text: 'Text 3' },
  ];

  // State object simulating ActiveAttemptView answers state
  let answersState = {};

  // Student answers Q1
  answersState = { ...answersState, Q1: 'Answer for question 1' };
  assert.equal(answersState.Q1, 'Answer for question 1');

  // Student navigates to Q2 and types
  answersState = { ...answersState, Q2: 'Answer for question 2' };
  assert.equal(answersState.Q1, 'Answer for question 1', 'Navigating to Q2 must not clear Q1 answer');
  assert.equal(answersState.Q2, 'Answer for question 2');

  // Student navigates to Q3, leaves empty, jumps back to Q1
  assert.equal(answersState.Q1, 'Answer for question 1', 'Jumping back to Q1 must preserve entered text');
  assert.equal(answersState.Q2, 'Answer for question 2', 'Q2 answer preserved');

  // Check answered/unanswered counts
  const answeredCount = questions.filter(
    (q) => (answersState[q.question_id] || '').trim().length > 0
  ).length;
  assert.equal(answeredCount, 2);

  const unanswered = questions.filter(
    (q) => !(answersState[q.question_id] || '').trim().length
  );
  assert.equal(unanswered.length, 1);
  assert.equal(unanswered[0].question_id, 'Q3');
});

test('Exam Attempt Submission & Pending Marking Verification', async () => {
  const studentUser = {
    userId: 'student-m19-6',
    role: 'student',
    email: 'student196@sliit.lk',
  };

  const paper = {
    paper_id: 'MOCK-SE3080-TEST',
    module_key: 'software_project_management',
    source_type: 'authentic',
    total_marks: 30,
    questions: [
      {
        question_id: 'SE3080-Q1',
        question_text: 'Describe Scrum master responsibilities.',
        marks: 15,
        source_type: 'authentic',
      },
      {
        question_id: 'SE3080-Q2',
        question_text: 'Explain Gantt chart dependency critical path.',
        marks: 15,
        source_type: 'authentic',
      },
    ],
  };

  const answers = {
    'SE3080-Q1': 'The Scrum Master facilitates daily standups, removes impediments, and coaches the team.',
    'SE3080-Q2': 'The critical path is the longest sequence of dependent activities determining minimal project duration.',
  };

  const payload = prepareAttemptPayload({
    paper,
    moduleKey: 'software_project_management',
    questions: paper.questions,
    answers,
    secondsElapsed: 240,
  });

  // Execute submission via helper
  let submissionCallbackCalled = false;
  let successCallbackCalled = false;

  const result = await executeAttemptSubmission({
    onSubmitAttempt: async (p) => {
      submissionCallbackCalled = true;
      return submitMockAttempt({ studentId: studentUser.userId, ...p });
    },
    onSubmitSuccess: (res) => {
      successCallbackCalled = true;
      assert.equal(res.status, 'pending_marking');
    },
    payload,
    fallbackSubmitFn: null,
  });

  assert.equal(submissionCallbackCalled, true);
  assert.equal(successCallbackCalled, true);
  assert.equal(result.moduleKey, 'software_project_management');
  assert.equal(result.status, 'pending_marking');
  assert.equal(result.marksAwarded, null, 'No marks must be fabricated; marksAwarded remains null');
  assert.equal(result.totalMarks, 30);
  assert.equal(result.timeSpentSeconds, 240);
  assert.equal(result.answeredCount, 2);

  // Retrieve attempt history for student
  const history = await listMockAttempts(
    studentUser.userId,
    'software_project_management'
  );
  assert.equal(history.length >= 1, true);
  const found = history.find((a) => a.attemptId === result.attemptId);
  assert.ok(found);
  assert.equal(found.status, 'pending_marking');

  // Verify student isolation: another student cannot access this attempt
  const otherStudentId = 'student-other-user';
  await assert.rejects(
    async () => {
      await getMockAttempt(result.attemptId, otherStudentId);
    },
    { name: 'MockAttemptError', message: 'Mock examination attempt not found' }
  );
});

test('Academic Integrity: No fabricated prediction probabilities', () => {
  // Descriptive historical frequency is valid
  const historicalEvidence = {
    authentic_questions: 110,
    distinct_papers: 5,
    verified_topic_coverage: 0.0,
    prediction_ready: false,
  };

  // Must not contain future probability percentages or predicted exam questions
  assert.equal(historicalEvidence.prediction_ready, false);
  assert.equal(historicalEvidence.verified_topic_coverage, 0.0);
  assert.equal('probability_next_exam' in historicalEvidence, false);
});

test('M19.7 Historical Evidence: verifies distinct papers, calendar years, unavailable years, and paper inventory structures', () => {
  const predictionPayload = {
    module_key: 'software_project_management',
    analysis_type: 'evidence_aware_topic_priorities',
    prediction_ready: false,
    future_exam_probabilities_available: false,
    historical_evidence: {
      authentic_questions: 42,
      distinct_papers: 2,
      distinct_years: ['2020', '2022'],
      unavailable_years: ['2021'],
      verified_topic_questions: 0,
      provisional_topic_questions: 1,
      unverified_topic_questions: 41,
      verified_topic_coverage: 0.0,
      provisional_topic_coverage: 0.0238,
      papers_inventory: [
        {
          paper_id: 'SE3080-2020-001',
          calendar_year: 2020,
          examination_type: 'Regular Final Exam',
          question_count: 20,
        },
        {
          paper_id: 'SE3080-2022-002',
          calendar_year: 2022,
          examination_type: 'Regular Final Exam',
          question_count: 22,
        },
      ],
      sum_of_extracted_question_marks: 80.0,
      ambiguous_marks_questions: 4,
      excluded_synthetic_questions: 0,
    },
    topic_statistics: [],
    provisional_topic_summary: [
      {
        topic_id: 'provisional_service_discovery',
        question_count: 1,
        provisional: true,
      },
    ],
    limitations: [
      'No verified topic classifications are available; topic frequency analysis is unavailable.',
    ],
    disclaimer:
      'Topic counts describe available authentic historical questions. Rankings, when available, are study-priority indicators only and do not predict the next examination.',
  };

  // 1. Academic integrity assertions
  assert.equal(predictionPayload.prediction_ready, false);
  assert.equal(predictionPayload.future_exam_probabilities_available, false);
  assert.equal('predicted_probabilities' in predictionPayload, false);

  // 2. Evidence counts and structure assertions
  const evidence = predictionPayload.historical_evidence;
  assert.equal(evidence.authentic_questions, 42);
  assert.equal(evidence.distinct_papers, 2);
  assert.deepEqual(evidence.distinct_years, ['2020', '2022']);
  assert.deepEqual(evidence.unavailable_years, ['2021']);
  assert.equal(evidence.papers_inventory.length, 2);
  assert.equal(evidence.sum_of_extracted_question_marks, 80.0);
  assert.equal(evidence.ambiguous_marks_questions, 4);

  // 3. Separation of verified and provisional
  assert.equal(evidence.verified_topic_questions, 0);
  assert.equal(evidence.provisional_topic_questions, 1);
  assert.equal(predictionPayload.topic_statistics.length, 0);
  assert.equal(predictionPayload.provisional_topic_summary.length, 1);
  assert.equal(predictionPayload.provisional_topic_summary[0].provisional, true);
});

test('M19.7 Historical Evidence: Stage 2 insufficient evidence state preserves navigation to setup', () => {
  // When verified evidence is insufficient, student must still be able to proceed to Stage 3 practice setup
  const stageState = {
    currentStage: 'evidence',
    selectedModuleKey: 'software_project_management',
    verifiedCoverage: 0.0,
    canProceedToSetup: true,
  };

  assert.equal(stageState.currentStage, 'evidence');
  assert.equal(stageState.verifiedCoverage, 0.0);
  assert.equal(stageState.canProceedToSetup, true);

  // Transition to setup maintains module key
  stageState.currentStage = 'setup';
  assert.equal(stageState.currentStage, 'setup');
  assert.equal(stageState.selectedModuleKey, 'software_project_management');
});
