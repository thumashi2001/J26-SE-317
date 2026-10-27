import React from 'react';

// Pure form for step 1 (assessment setup). Errors are computed by the page and shown next to each field.
export default function SetupForm({ value, onChange, errors, showErrors, criteriaSum, examples, onLoadExample, onSubmit, saving, saveError }) {
  const set = (k) => (e) => onChange({ [k]: e.target.value });
  const isMcq = value.answerType === 'mcq';
  const err = (k) => (showErrors && errors[k] ? <p className="c3-error" id={`${k}-err`} role="alert">{errors[k]}</p> : null);
  const aria = (k) => (showErrors && errors[k] ? { 'aria-invalid': true, 'aria-describedby': `${k}-err` } : {});

  // Rubric editing helpers: add/remove criteria and options, keep ids and marks consistent.
  const updateCriterion = (i, patch) => {
    const next = value.criteria.map((c, idx) => {
      if (idx !== i) return c;
      const merged = { ...c, ...patch };
      // Changing the marks resets the example's levels; the server then builds "none / full marks" levels.
      if ('max_marks' in patch && c.scoring_levels) delete merged.scoring_levels;
      return merged;
    });
    onChange({ criteria: next });
  };
  const addCriterion = () => onChange({ criteria: [...value.criteria, { criterion_id: `C${value.criteria.length + 1}`, description: '', max_marks: 1 }] });
  const removeCriterion = (i) => value.criteria.length > 1 && onChange({ criteria: value.criteria.filter((_, idx) => idx !== i) });
  const updateOption = (i, text) => onChange({ mcqOptions: value.mcqOptions.map((o, idx) => (idx === i ? { ...o, text } : o)) });
  const addOption = () => {
    const label = String.fromCharCode(65 + value.mcqOptions.length);
    onChange({ mcqOptions: [...value.mcqOptions, { option_id: label, label, text: '' }] });
  };
  const removeOption = (i) => {
    if (value.mcqOptions.length <= 2) return;
    const kept = value.mcqOptions.filter((_, idx) => idx !== i).map((o, idx) => ({ ...o, option_id: String.fromCharCode(65 + idx), label: String.fromCharCode(65 + idx) }));
    onChange({ mcqOptions: kept, mcqCorrectAnswer: kept.some((o) => o.option_id === value.mcqCorrectAnswer) ? value.mcqCorrectAnswer : '' });
  };

  return (
    <form
      className="panel"
      noValidate
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
      aria-label="Assessment setup"
    >
      <h2 style={{ margin: '0 0 4px' }}>Assessment setup</h2>
      <p className="muted" style={{ margin: '0 0 14px' }}>Set the question and marking scheme once. Every answer in this batch is marked against it.</p>

      {examples.length > 0 && (
        <div className="c3-example-row">
          <span className="small muted">Start from an example:</span>
          {examples.map((x) => (
            <button key={x.id} type="button" className="btn-ghost c3-chip-btn" onClick={() => onLoadExample(x.id)}>{x.title}</button>
          ))}
        </div>
      )}

      <div className="c3-grid-3">
        <div className="c3-field">
          <label htmlFor="b-module">Module code</label>
          <input id="b-module" value={value.moduleId} onChange={set('moduleId')} />
        </div>
        <div className="c3-field">
          <label htmlFor="b-qid">Question ID</label>
          <input id="b-qid" value={value.questionId} onChange={set('questionId')} />
        </div>
        <div className="c3-field">
          <label htmlFor="b-type">Answer type</label>
          <select id="b-type" value={value.answerType} onChange={set('answerType')}>
            <option value="short">Written answer (short)</option>
            <option value="essay">Written answer (essay)</option>
            <option value="mcq">Multiple choice</option>
          </select>
        </div>
      </div>

      <div className="c3-grid-2">
        <div className="c3-field">
          <label htmlFor="b-title">Assessment title</label>
          <input id="b-title" value={value.title} onChange={set('title')} {...aria('title')} />
          {err('title')}
        </div>
        <div className="c3-field">
          <label htmlFor="b-max">Total marks</label>
          <input id="b-max" type="number" min="0" step="0.5" value={value.maxMarks} onChange={set('maxMarks')} {...aria('maxMarks')} />
          {err('maxMarks')}
        </div>
      </div>

      <div className="c3-field">
        <label htmlFor="b-q">Question</label>
        <textarea id="b-q" style={{ minHeight: 90 }} value={value.questionText} onChange={set('questionText')} {...aria('questionText')} />
        {err('questionText')}
      </div>

      {isMcq ? (
        <fieldset className="c3-field" style={{ border: 0, padding: 0 }}>
          <legend className="c3-label">Options and correct answer</legend>
          {value.mcqOptions.map((o, i) => (
            <div key={o.option_id} className="c3-opt-row">
              <label className="c3-opt-correct" title="Mark as the correct answer">
                <input type="radio" name="correct" checked={value.mcqCorrectAnswer === o.option_id} onChange={() => onChange({ mcqCorrectAnswer: o.option_id })} aria-label={`Option ${o.label} is correct`} />
                <span>{o.label}</span>
              </label>
              <input value={o.text} onChange={(e) => updateOption(i, e.target.value)} placeholder={`Option ${o.label} text`} aria-label={`Option ${o.label} text`} />
              <button type="button" className="btn-ghost c3-close" onClick={() => removeOption(i)} disabled={value.mcqOptions.length <= 2} aria-label={`Remove option ${o.label}`}>Remove</button>
            </div>
          ))}
          <div><button type="button" className="btn secondary c3-sm" onClick={addOption} disabled={value.mcqOptions.length >= 8}>Add option</button></div>
          {err('mcq')}
        </fieldset>
      ) : (
        <>
          <div className="c3-grid-2">
            <div className="c3-field">
              <label htmlFor="b-ref">Reference answer <span className="muted">(optional)</span></label>
              <textarea id="b-ref" style={{ minHeight: 100 }} value={value.referenceAnswer} onChange={set('referenceAnswer')} />
            </div>
            <div className="c3-field">
              <label htmlFor="b-concepts">Expected concepts <span className="muted">(comma separated)</span></label>
              <textarea id="b-concepts" style={{ minHeight: 100 }} value={value.expectedConceptsStr} onChange={set('expectedConceptsStr')} />
            </div>
          </div>

          <fieldset className="c3-rubric" aria-describedby="rubric-sum">
            <legend>Rubric criteria</legend>
            <div className="c3-field">
              <label htmlFor="b-rtitle">Rubric name</label>
              <input id="b-rtitle" value={value.rubricTitle} onChange={set('rubricTitle')} />
            </div>
            {value.criteria.map((c, i) => (
              <div key={i} className="c3-crit-row">
                <div className="c3-field">
                  <label htmlFor={`c-id-${i}`}>ID</label>
                  <input id={`c-id-${i}`} value={c.criterion_id} onChange={(e) => updateCriterion(i, { criterion_id: e.target.value })} />
                </div>
                <div className="c3-field c3-grow">
                  <label htmlFor={`c-d-${i}`}>What is being marked</label>
                  <input id={`c-d-${i}`} value={c.description} onChange={(e) => updateCriterion(i, { description: e.target.value })} />
                </div>
                <div className="c3-field">
                  <label htmlFor={`c-m-${i}`}>Marks</label>
                  <input id={`c-m-${i}`} type="number" min="0" step="0.5" value={c.max_marks} onChange={(e) => updateCriterion(i, { max_marks: e.target.value })} />
                </div>
                <button type="button" className="btn-ghost c3-close" onClick={() => removeCriterion(i)} disabled={value.criteria.length <= 1} aria-label={`Remove criterion ${c.criterion_id}`}>Remove</button>
              </div>
            ))}
            <div className="c3-rubric-foot">
              <button type="button" className="btn secondary c3-sm" onClick={addCriterion}>Add criterion</button>
              <span id="rubric-sum" className={`c3-sum${errors.rubricSum ? ' bad' : ' ok'}`} role="status">
                Criteria total {criteriaSum} of {Number(value.maxMarks) || 0} marks{errors.rubricSum ? '. They must match.' : ''}
              </span>
            </div>
            {err('rubric')}
            <p className="hint" style={{ margin: '8px 0 0' }}>Criteria loaded from an example keep their scoring levels. Changing a criterion's marks resets it to two levels (none or full marks).</p>
          </fieldset>
        </>
      )}

      {saveError && <p className="c3-error" role="alert">{saveError}</p>}
      <div className="c3-form-actions" style={{ marginTop: 16 }}>
        <button type="submit" className="btn" disabled={saving}>{saving ? 'Saving setup...' : 'Save setup and add answers'}</button>
      </div>
    </form>
  );
}
