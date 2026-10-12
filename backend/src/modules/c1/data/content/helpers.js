// Helpers used by every module content file.
//   S(text, [4 options], correctIndex, why, tipKind)       practice, one correct answer
//   M(text, [4 options], [correctIndexes], why, tipKind)    practice, select all that apply
//   D(text, [4 options], correctIndex, why, tipKind)        diagnostic, one correct answer
// Indexes start at 0 (0 = first option). The seeding script shuffles option order for balance.
export const S = (text, options, correct, why, tip = 'concept') => ({ text, options, correct: [correct], why, tip });
export const M = (text, options, correct, why, tip = 'multi') => ({ text, options, correct, why, tip });
export const D = (text, options, correct, why, tip = 'concept') => ({ text, options, correct: [correct], why, tip });
