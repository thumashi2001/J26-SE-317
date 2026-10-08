import { connectDb } from './src/config/db.js';
import * as authService from './src/modules/auth/services/authService.js';
import * as c3AppController from './src/modules/c3/controllers/c3AppController.js';
import * as submissionSvc from './src/modules/c3/services/submissionService.js';
import * as assessmentSvc from './src/modules/c3/services/assessmentService.js';
import { signToken } from './src/middleware/auth.js';
import dotenv from 'dotenv';

dotenv.config();

async function runE2E() {
  console.log("Starting E2E C3 Pipeline Test...");
  const db = await connectDb();

  // 1. Get the assessment ID for PP1
  const assessments = await assessmentSvc.listAssessments();
  const pp1 = assessments[0];
  if (!pp1) throw new Error("No assessments found!");
  console.log("Found Assessment:", pp1.title, "ID:", pp1._id);

  // 2. Generate a token for student IT10000001
  const studentToken = signToken({ sub: 'IT10000001', role: 'student' });
  const req = {
    user: { sub: 'IT10000001', role: 'student' },
    body: {
      assessment_id: String(pp1._id),
      student_answer: "Database normalization is the process of organizing data in a relational database to reduce redundancy and improve data integrity.\n\nFirst Normal Form (1NF) requires each attribute to contain atomic values and removes repeating groups. Each row should represent a unique record.\n\nSecond Normal Form (2NF) requires the relation to already be in 1NF and removes partial dependencies. Every non-key attribute must depend on the whole primary key rather than only part of a composite key.\n\nThird Normal Form (3NF) requires the relation to already be in 2NF and removes transitive dependencies. Non-key attributes should depend directly on the primary key and not on another non-key attribute.\n\nNormalization therefore reduces duplicate data, prevents update, insertion, and deletion anomalies, and improves data consistency."
    }
  };

  const res = {
    json: (data) => data,
    status: (code) => ({ json: (data) => { throw new Error(JSON.stringify(data)); } })
  };

  console.log("Submitting answer...");
  
  // Submit answer
  // We need to bypass the Express 'handle' wrapper to capture the returned data directly if we call the underlying logic, 
  // but c3AppController.submitAnswer is wrapped.
  // We'll mock the res.json.
  
  let responseData;
  const mockRes = {
    json: (data) => { responseData = data; },
    status: (code) => ({ json: (data) => { console.error("Error status", code, data); throw new Error(JSON.stringify(data)); } })
  };

  await c3AppController.submitAnswer(req, mockRes);
  
  console.log("Pipeline Submission Response:", responseData);

  // Fetch the result
  if (responseData.status === 'awaiting_review' && responseData.submission_id) {
    const result = await submissionSvc.getResultBySubmissionId(responseData.submission_id);
    console.log("Result created in DB!");
    console.log("- Analysis nodes:", result.ai_result?.analysis ? 'YES' : 'NO');
    console.log("- Marking rules applied:", result.ai_result?.marking ? 'YES' : 'NO');
    console.log("- Feedback generated:", result.ai_result?.feedback ? 'YES' : 'NO');
    console.log("- Mind map generated:", result.ai_result?.mindmap ? 'YES' : 'NO');
    console.log("AI Mark Awarded:", result.ai_result?.marking?.total_awarded_marks);
    
    // Test Lecturer Overriding
    console.log("Testing Lecturer Override...");
    const lecturerReq = {
      user: { sub: 'IT20000001', role: 'lecturer' },
      params: { submissionId: responseData.submission_id },
      body: { revised_mark: 9.5, reason: "Excellent explanation, slightly missed 1NF edge cases." }
    };
    let overrideResp;
    const mockOverrideRes = {
       json: (data) => { overrideResp = data; },
       status: (code) => ({ json: (data) => { throw new Error(JSON.stringify(data)); } })
    };
    await c3AppController.lecturerOverride(lecturerReq, mockOverrideRes);
    console.log("Override successful:", overrideResp.decision);
    
    const finalCheck = await submissionSvc.getResultBySubmissionId(responseData.submission_id);
    console.log("Finalized Mark in DB:", finalCheck.final_mark);
    console.log("Original AI Mark preserved:", finalCheck.ai_result.marking.total_awarded_marks);
  }

  process.exit(0);
}

runE2E().catch(err => {
  console.error("E2E Failed:", err);
  process.exit(1);
});
