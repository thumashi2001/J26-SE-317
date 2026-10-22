// Turns a stored/returned evaluation into what the result view can show, and says explicitly when a part of the
// analysis does not exist. Pure functions: no data is invented here; a missing part stays missing and gets a reason.

const SUBJECTIVE_FEEDBACK_BLOCKS = [
  ['overall_strengths', 'Strengths'],
  ['overall_missing_concepts', 'Concepts to revisit'],
  ['overall_improvement_suggestions', 'How to improve'],
  ['overall_next_level_improvements', 'To reach the next level'],
];

const MCQ_FEEDBACK_BLOCKS = [
  ['strengths', 'Strengths'],
  ['missing_concepts', 'Answer key'],
  ['misconceptions', 'Misconceptions'],
];

const list = (v) => (Array.isArray(v) ? v.filter((x) => x != null && String(x).trim() !== '') : []);

export function isMcq(ev) {
  if (!ev || typeof ev !== 'object') return false;
  const type = String(ev.answer_type || '').toLowerCase();
  return type === 'mcq' || type === 'multiple-choice' || String(ev.marking?.marking_version || '').startsWith('mcq-');
}

// The Python service says "Function 2 proposed ..." in its summary; show it in plain language.
export const plainSummary = (t) => String(t).replace(/^Function \d+ proposed/, 'The automatic marking proposed');

export function normaliseEvaluation(ev) {
  const empty = !ev || typeof ev !== 'object' || !(ev.marking || ev.analysis || ev.feedback || ev.mindmap || ev.total_awarded_marks != null);
  if (empty) {
    return {
      kind: 'none',
      warnings: [],
      criteria: [],
      sentences: [],
      concepts: { available: false, reason: 'No analysis was saved for this submission.' },
      feedback: { available: false, reason: 'No analysis was saved for this submission.' },
      map: { available: false, reason: 'No analysis was saved for this submission.' },
      answerKey: null,
    };
  }

  const mcq = isMcq(ev);
  const warnings = [...list(ev.warnings), ...list(ev.marking?.warnings)].filter((w, i, a) => a.indexOf(w) === i);
  const criteria = Array.isArray(ev.marking?.criteria_results) ? ev.marking.criteria_results : [];
  const sentences = Array.isArray(ev.analysis?.sentences) ? ev.analysis.sentences : [];

  // concept diagnosis
  let concepts;
  if (mcq) {
    concepts = { available: false, reason: 'Not produced for multiple-choice questions, where the mark depends only on the chosen option.' };
  } else if (!ev.analysis) {
    concepts = { available: false, reason: 'No concept analysis was saved for this submission.' };
  } else if (!Array.isArray(ev.analysis.concept_matches) || ev.analysis.concept_matches.length === 0) {
    concepts = { available: false, reason: 'This question has no expected concepts, so no concept diagnosis was produced.' };
  } else {
    concepts = { available: true, analysis: ev.analysis };
  }

  // feedback
  let feedback;
  if (mcq) {
    const f = ev.feedback;
    if (!f || (!f.summary && !f.actionable_guidance && list(f.strengths).length === 0)) {
      feedback = { available: false, reason: 'No feedback was saved for this submission.' };
    } else {
      const sections = MCQ_FEEDBACK_BLOCKS.map(([key, title]) => ({ key, title, items: list(f[key]) })).filter((s) => s.items.length > 0);
      if (f.actionable_guidance) sections.push({ key: 'guidance', title: 'How to improve', items: [f.actionable_guidance] });
      feedback = { available: true, summary: f.summary || null, sections, note: f.rubric_alignment || null };
    }
  } else {
    const o = ev.feedback?.overall_feedback;
    if (!o) {
      feedback = { available: false, reason: ev.feedback ? 'Feedback was not generated for this answer.' : 'No feedback was saved for this submission.' };
    } else {
      feedback = {
        available: true,
        summary: o.overall_summary ? plainSummary(o.overall_summary) : null,
        sections: SUBJECTIVE_FEEDBACK_BLOCKS.map(([key, title]) => ({ key, title, items: list(o[key]) })).filter((s) => s.items.length > 0),
        note: null,
      };
    }
  }

  // concept map
  let map;
  if (mcq) {
    map = { available: false, reason: 'Not produced for multiple-choice questions.' };
  } else if (!ev.mindmap) {
    map = { available: false, reason: 'No concept map was saved for this submission.' };
  } else if (!Array.isArray(ev.mindmap.nodes) || ev.mindmap.nodes.length === 0) {
    map = { available: false, reason: 'No concepts were found in the answer to build a map from.' };
  } else {
    map = { available: true, mindmap: ev.mindmap };
  }

  const answerKey = mcq && list(ev.correct_labels).length > 0
    ? { selected: list(ev.selected_labels), correct: list(ev.correct_labels), isCorrect: ev.is_correct === true, unanswered: ev.is_unanswered === true }
    : null;

  return { kind: mcq ? 'mcq' : 'subjective', warnings, criteria, sentences, concepts, feedback, map, answerKey };
}
