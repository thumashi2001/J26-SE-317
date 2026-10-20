/** Display wording for C4 screens. Does not change stored values or requests. */

export function activityKindLabel(kind) {
  if (kind === 'c1_revision') return 'Review';
  if (kind === 'c4_quiz') return 'Practice quiz';
  if (kind === 'c1_practice') return 'Practice';
  return 'Activity';
}

export function activityOpenLabel(kind) {
  if (kind === 'c1_revision') return 'Review topic';
  if (kind === 'c4_quiz') return 'Open quiz';
  return 'Open practice';
}

export function activityStatusLabel(status) {
  if (status === 'practice_verified') return 'Verified practice (session finished)';
  if (status === 'practice_observed') return 'Practice in progress (not complete)';
  if (status === 'self_reported_complete') return 'Marked done (self-reported)';
  if (status === 'overdue') return 'Overdue';
  if (status === 'pending' || status === 'scheduled') return 'Scheduled';
  return 'Up next';
}

export function attemptStatusLabel(status) {
  if (status === 'in_progress') return 'In progress';
  if (status === 'submitted') return 'Submitted';
  return status ? 'Saved' : '';
}

export function actionTypeLabel(type) {
  if (type === 'practice' || type === 'c1_practice') return 'Practice';
  if (type === 'revision' || type === 'c1_revision') return 'Review';
  if (type === 'quiz' || type === 'c4_quiz') return 'Practice quiz';
  return 'Activity';
}

export function planRefreshNote(note) {
  if (!note) return 'Refreshed from your latest progress.';
  if (/merged/i.test(note)) return 'Updated your latest practice on the current plan.';
  if (/no new practice/i.test(note)) return 'Plan refreshed. No new completed practice was found.';
  if (/updated practice/i.test(note)) return 'Updated completed practice and refreshed your plan.';
  if (/\bC[1-4]\b|protocol|heuristic/i.test(note)) return 'Refreshed from your latest progress.';
  return note;
}

export function studentReason(text) {
  if (!text) return '';
  const urgency = /within 14 days/i.test(text) ? ' Your exam date is within 14 days.' : '';
  if (/se-path|experimental|maskable|heuristic/i.test(text)) {
    return `Experimental recommendation.${urgency}`;
  }
  if (/kept from earlier/i.test(text)) return 'Kept from an earlier version of your plan.';
  if (/mock quiz|practice-bank|practice quiz/i.test(text)) {
    return `Practice quiz focused on a weaker topic.${urgency}`;
  }
  if (/^revision|topic page|weak topic/i.test(text)) {
    return `Review for a weaker topic.${urgency}`;
  }
  if (/lowest|prioritised|prioritized|mastery/i.test(text)) {
    return `Suggested because this topic is among your weaker areas.${urgency}`;
  }
  if (/\bC[1-4]\b|protocol|catalogue|checkpoint|\bapi\b/i.test(text)) {
    return `Suggested from your current plan.${urgency}`;
  }
  return text;
}

export function unavailableReason(text) {
  if (!text) return '';
  if (/diagnostic|not on this student/i.test(text)) {
    return 'Not on your learner profile yet. A diagnostic may be needed first.';
  }
  if (/practice page|catalogue|no .*practice/i.test(text)) {
    return 'No practice questions are available for this topic yet.';
  }
  if (/non-finite|cannot rank/i.test(text)) {
    return 'No mastery score is available, so this topic cannot be ranked.';
  }
  if (/could not fit|time budget|plan length/i.test(text)) {
    return 'This did not fit your time budget. Increase your daily minutes, study days, or plan length.';
  }
  return studentReason(text);
}

export function revisionReason(text) {
  if (!text || text === 'replan') return 'Plan updated';
  return studentReason(text);
}

export function examSourceCopy(source) {
  if (source?.id === 'c2_past_paper') {
    return {
      label: 'Past papers',
      detail: source.available ? 'Available.' : 'Past papers are currently unavailable.',
    };
  }
  if (source?.id === 'c1_practice_bank') {
    return {
      label: 'Practice quiz',
      detail: source.available
        ? 'Uses practice questions saved into this attempt. Not a past paper.'
        : 'Practice questions are currently unavailable.',
    };
  }
  return {
    label: 'Quiz source',
    detail: source?.available ? 'Available.' : 'Currently unavailable.',
  };
}

export function examContentNote(note) {
  if (!note) return '';
  if (/\bC[1-4]\b|practice-bank|university module exam/i.test(note)) {
    return 'This score is from a practice quiz. It is not a university exam result.';
  }
  return note;
}

export function lecturerAccessMessage(text) {
  if (
    !text ||
    text === 'lecturer_scope_unavailable' ||
    /lecturer_scope_unavailable/i.test(text) ||
    /approved class roster|assignment scope|studentId is not authorization/i.test(text)
  ) {
    return 'Student access has not been assigned to your account.';
  }
  if (/this c4 view is for lecturer/i.test(text)) {
    return 'This page is for lecturer accounts only.';
  }
  return text;
}

export function visibleError(text) {
  if (!text) return '';
  if (
    text === 'lecturer_scope_unavailable' ||
    /lecturer_scope_unavailable|approved class roster|assignment scope|studentId is not authorization/i.test(text)
  ) {
    return 'Student access has not been assigned to your account.';
  }
  if (/this c4 view is for lecturer/i.test(text)) return 'This page is for lecturer accounts only.';
  if (/c1 diagnostic/i.test(text)) return 'Complete the diagnostic before creating a study plan.';
  return text;
}

export function feedbackTargetLabel(target) {
  if (target === 'study_plan') return 'Study plan';
  if (target === 'mock_exam') return 'Practice quiz';
  if (target === 'simulation_demo') return 'Simulation demo';
  if (target === 'overall') return 'Overall';
  return 'Feedback';
}
