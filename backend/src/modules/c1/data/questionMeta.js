// Question metadata for Component 1: thinking level (Bloom) and expected difficulty.
// Nothing here is stored inside the question files. It is worked out from the question itself, so the
// rule is written down in one place and can be defended and changed. See docs/c1-question-method.md.
//
// Thinking level follows the revised Bloom taxonomy (Anderson and Krathwohl, 2001), four levels used for
// multiple-choice questions: Remember, Understand, Apply, Analyse.
//
// Rule 1: the question type tag that the author already gave each question decides the level.
//   concept  -> Remember, or Understand when the stem asks why / purpose / role / how / benefit
//   order    -> Understand (put steps in a sensible order)
//   scenario -> Apply     (use an idea in a short situation)
//   calc     -> Apply     (do steps with numbers)
//   compare  -> Analyse   (tell ideas apart)
//   not      -> Analyse   (check every option, find the false one)
//   multi    -> same rule as concept (select all is a question FORMAT; what it asks decides the level)
//
// Rule 2: the EXPECTED difficulty before any student answers (a prior). The item analysis script later
// replaces this with real difficulty from student answers.
//   Easy   : Remember
//   Medium : Understand, Apply (scenario), Analyse (compare, not)
//   Hard   : multi (select all that apply is harder to get fully right) and calc (several steps)

export const BLOOM = ['Remember', 'Understand', 'Apply', 'Analyse'];
export const DIFFICULTY = ['Easy', 'Medium', 'Hard'];

// Typical share of students who answer correctly for each prior band (used to shrink the real result).
export const PRIOR_P = { Easy: 0.8, Medium: 0.6, Hard: 0.4 };

const UNDERSTAND_STEM = /\b(why|purpose|main role|role of|best describes|how does|how do|how can|benefit|advantage|reason|explains?|means|used for|used to)\b/i;

export function bloomOf(q) {
  switch (q.tip) {
    case 'scenario': case 'calc': return 'Apply';
    case 'compare': case 'not': return 'Analyse';
    case 'order': return 'Understand';
    default: return UNDERSTAND_STEM.test(q.text) ? 'Understand' : 'Remember';
  }
}

export function difficultyOf(q) {
  if (q.tip === 'multi' || q.tip === 'calc' || (q.correct && q.correct.length > 1)) return 'Hard';
  return bloomOf(q) === 'Remember' ? 'Easy' : 'Medium';
}

export const describeQuestion = (q) => ({ bloom: bloomOf(q), difficulty: difficultyOf(q) });
