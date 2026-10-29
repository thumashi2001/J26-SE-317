// MCQ wrong-answer penalty (FR-C3-010) and multi-question total (FR-C3-011).
// Pure functions: no server, database or AI service is started.
import test from 'node:test';
import assert from 'node:assert';

import { aggregateMcqResults, evaluateMcqAnswer } from '../services/mcqMarkingService.js';

const question = (extra = {}) => ({
  question_id: 'Q1',
  question_text: 'Which layer routes packets?',
  options: { A: 'Application', B: 'Network', C: 'Physical' },
  correct_answer: 'B',
  max_marks: 2,
  ...extra,
});

test('a wrong answer still scores 0 on its own question, with or without a penalty', () => {
  const plain = evaluateMcqAnswer(question({ selected_option_id: 'A' }));
  const penalised = evaluateMcqAnswer(question({ selected_option_id: 'A', incorrect_penalty: 1 }));
  assert.strictEqual(plain.total_awarded_marks, 0);
  assert.strictEqual(penalised.total_awarded_marks, 0);
  assert.strictEqual(plain.incorrect_penalty, 0);
  assert.strictEqual(plain.penalty_applied, 0);
  assert.strictEqual(penalised.incorrect_penalty, 1);
  assert.strictEqual(penalised.penalty_applied, 1);
});

test('a correct or unanswered question is never penalised', () => {
  const correct = evaluateMcqAnswer(question({ selected_option_id: 'B', incorrect_penalty: 1 }));
  const blank = evaluateMcqAnswer(question({ selected_option_id: '', incorrect_penalty: 1 }));
  assert.strictEqual(correct.total_awarded_marks, 2);
  assert.strictEqual(correct.penalty_applied, 0);
  assert.strictEqual(blank.is_unanswered, true);
  assert.strictEqual(blank.penalty_applied, 0);
});

test('an invalid penalty is rejected with 400', () => {
  for (const bad of [-1, 3, 'abc', NaN]) {
    assert.throws(() => evaluateMcqAnswer(question({ selected_option_id: 'A', incorrect_penalty: bad })), (err) => err.status === 400);
  }
  assert.doesNotThrow(() => evaluateMcqAnswer(question({ selected_option_id: 'A', incorrect_penalty: 2 })));
});

test('totals add up the marks and, with no penalty, net equals awarded', () => {
  const results = [
    evaluateMcqAnswer(question({ question_id: 'Q1', selected_option_id: 'B' })),
    evaluateMcqAnswer(question({ question_id: 'Q2', selected_option_id: 'A' })),
    evaluateMcqAnswer(question({ question_id: 'Q3', selected_option_id: '' })),
  ];
  const total = aggregateMcqResults(results);
  assert.deepStrictEqual(total, {
    question_count: 3,
    answered_count: 2,
    correct_count: 1,
    total_awarded_marks: 2,
    total_penalty: 0,
    net_total_marks: 2,
    total_possible_marks: 6,
    percentage: 33.3,
  });
});

test('penalties are subtracted from the total and the net total never goes below zero', () => {
  const mixed = aggregateMcqResults([
    evaluateMcqAnswer(question({ question_id: 'Q1', selected_option_id: 'B', incorrect_penalty: 1 })),
    evaluateMcqAnswer(question({ question_id: 'Q2', selected_option_id: 'A', incorrect_penalty: 1 })),
  ]);
  assert.strictEqual(mixed.total_awarded_marks, 2);
  assert.strictEqual(mixed.total_penalty, 1);
  assert.strictEqual(mixed.net_total_marks, 1);

  const allWrong = aggregateMcqResults([
    evaluateMcqAnswer(question({ question_id: 'Q1', selected_option_id: 'A', incorrect_penalty: 2 })),
    evaluateMcqAnswer(question({ question_id: 'Q2', selected_option_id: 'C', incorrect_penalty: 2 })),
  ]);
  assert.strictEqual(allWrong.total_penalty, 4);
  assert.strictEqual(allWrong.net_total_marks, 0);
  assert.strictEqual(allWrong.percentage, 0);
});

test('an empty list totals to zero without dividing by zero', () => {
  assert.deepStrictEqual(aggregateMcqResults([]), {
    question_count: 0, answered_count: 0, correct_count: 0, total_awarded_marks: 0,
    total_penalty: 0, net_total_marks: 0, total_possible_marks: 0, percentage: 0,
  });
  assert.strictEqual(aggregateMcqResults(undefined).question_count, 0);
});
