import React from 'react';

const STAGES = [
  { id: 'overview', number: 1, label: 'Overview', desc: 'Exam Intelligence' },
  { id: 'evidence', number: 2, label: 'Topic Evidence', desc: 'Historical Analysis' },
  { id: 'setup', number: 3, label: 'Practice Setup', desc: 'Configure Mock' },
  { id: 'attempt', number: 4, label: 'Exam Attempt', desc: 'Active Practice' },
  { id: 'results', number: 5, label: 'Results & Feedback', desc: 'Evaluation Status' },
];

export default function ExamIntelligenceStepper({
  currentStage = 'overview',
  onSelectStage,
  canAccessAttempt = false,
  canAccessResults = false,
  hasActiveAttempt = false,
}) {
  const currentIndex = STAGES.findIndex((s) => s.id === currentStage);

  function handleClick(stageId) {
    if (stageId === currentStage) return;

    if (stageId === 'attempt' && !canAccessAttempt && !hasActiveAttempt) {
      return;
    }
    if (stageId === 'results' && !canAccessResults) {
      return;
    }

    if (hasActiveAttempt && stageId !== 'attempt') {
      const confirmLeave = window.confirm(
        'You have an active examination attempt in progress. Leaving this stage may disrupt your attempt. Do you want to proceed?'
      );
      if (!confirmLeave) return;
    }

    if (typeof onSelectStage === 'function') {
      onSelectStage(stageId);
    }
  }

  return (
    <nav className="c2-stepper" aria-label="Exam Intelligence 5-Stage Workflow">
      <ol className="c2-stepper-list">
        {STAGES.map((stage, idx) => {
          const isActive = stage.id === currentStage;
          const isPassed = idx < currentIndex;
          let isLocked = false;

          if (stage.id === 'attempt' && !canAccessAttempt && !hasActiveAttempt) {
            isLocked = true;
          }
          if (stage.id === 'results' && !canAccessResults) {
            isLocked = true;
          }

          let statusClass = 'c2-step-upcoming';
          if (isActive) statusClass = 'c2-step-active';
          else if (isPassed) statusClass = 'c2-step-completed';
          if (isLocked) statusClass += ' c2-step-locked';

          return (
            <li key={stage.id} className={`c2-step-item ${statusClass}`}>
              <button
                type="button"
                className="c2-step-button"
                onClick={() => !isLocked && handleClick(stage.id)}
                disabled={isLocked}
                aria-current={isActive ? 'step' : undefined}
                title={isLocked ? `${stage.label} (Complete previous steps to unlock)` : stage.label}
              >
                <span className="c2-step-indicator">
                  {isPassed ? '✓' : stage.number}
                </span>
                <span className="c2-step-text">
                  <span className="c2-step-num-label">STAGE {stage.number}</span>
                  <span className="c2-step-title">{stage.label}</span>
                  <span className="c2-step-desc">{stage.desc}</span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
