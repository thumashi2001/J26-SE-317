import { connectDb, getDb } from './src/config/db.js';
import dotenv from 'dotenv';
dotenv.config();

async function run() {
  await connectDb();
  const db = getDb();
  const results = await db.collection('c3_results').find().sort({_id: -1}).limit(1).toArray();
  const res = results[0];
  
  console.log("=== FUNCTION 1 (ANALYSIS) ===");
  console.log("Tokens:", res.ai_result.analysis.token_count);
  console.log("Sentences:", res.ai_result.analysis.sentence_count);
  console.log("Concept Matches:", res.ai_result.analysis.concept_matches.map(c => `${c.concept} (${c.status}) - Sentences: ${c.evidence_sentence_ids.join(',')}`));
  
  console.log("\n=== FUNCTION 2 (MARKING) ===");
  console.log("Total Awarded:", res.ai_result.marking.total_awarded_marks);
  res.ai_result.marking.criteria_results.forEach(c => {
     console.log(`- ${c.criterion_id}: ${c.awarded_mark}/${c.max_marks} [${c.selected_level_id}] -> ${c.selected_level_label}`);
  });

  console.log("\n=== FUNCTION 3 (FEEDBACK) ===");
  console.log("Strengths:", res.ai_result.feedback.overall_feedback.overall_strengths.length);
  
  console.log("\n=== FUNCTION 4 (MIND MAP) ===");
  const root = res.ai_result.mindmap.nodes.find(n => n.type === 'root');
  console.log("Root Node:", root.concept, "Status:", root.status);
  console.log("Total Nodes:", res.ai_result.mindmap.summary.total_nodes);
  console.log("Demonstrated Nodes:", res.ai_result.mindmap.summary.demonstrated_count);
  console.log("Sample relationship:", res.ai_result.mindmap.relationships[0]);

  console.log("\n=== OVERRIDE ===");
  console.log("Final Mark:", res.final_mark);
  console.log("Decision:", res.lecturer_decision);
  console.log("Reason:", res.override_reason);

  process.exit(0);
}
run().catch(console.error);
