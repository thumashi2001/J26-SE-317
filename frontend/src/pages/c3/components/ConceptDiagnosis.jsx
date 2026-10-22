import React, { useState } from 'react';

const STATUS_LABEL = { demonstrated: 'Demonstrated', partial: 'Partial', not_demonstrated: 'Missing', missing: 'Missing' };
const STATUS_CLASS = { demonstrated: 'status-approved', partial: 'status-pending', not_demonstrated: 'status-rejected', missing: 'status-rejected' };

// Concept coverage of the answer, with the sentences that support each concept.
// The overlap figure is the share of the concept's words found in the answer (a word-match measure, not a meaning score).
export default function ConceptDiagnosis({ analysis, sentenceMap }) {
  const [filter, setFilter] = useState('all');
  if (!analysis || !analysis.concept_matches || analysis.concept_matches.length === 0) return null;

  const { concept_matches: matches, sentence_count } = analysis;
  const norm = (s) => (s === 'missing' ? 'not_demonstrated' : s);
  const count = (s) => matches.filter((c) => norm(c.status) === s).length;
  const shown = matches.filter((c) => filter === 'all' || norm(c.status) === filter);
  const tabs = [
    ['all', 'All', matches.length],
    ['demonstrated', 'Demonstrated', count('demonstrated')],
    ['partial', 'Partial', count('partial')],
    ['not_demonstrated', 'Missing', count('not_demonstrated')],
  ];

  return (
    <section className="panel c3-concept-diagnosis-panel" aria-label="Concept diagnosis">
      <div className="c3-diagnosis-head">
        <div>
          <h3>Concept diagnosis</h3>
          <p className="small muted" style={{ margin: '2px 0 0' }}>
            Which expected concepts the answer covers{sentence_count ? ` · ${sentence_count} sentences analysed` : ''}
          </p>
        </div>
      </div>

      <div className="tabs" role="group" aria-label="Filter concepts">
        {tabs.map(([key, label, n]) => (
          <button key={key} type="button" className={filter === key ? 'on' : ''} aria-pressed={filter === key} onClick={() => setFilter(key)}>
            {label} <span className="tab-count">{n}</span>
          </button>
        ))}
      </div>

      <div className="table-wrap">
        <table className="data-table c3-table">
          <thead>
            <tr>
              <th>Concept</th>
              <th>Status</th>
              <th>Word overlap</th>
              <th>Supporting sentence</th>
            </tr>
          </thead>
          <tbody>
            {shown.length === 0 ? (
              <tr>
                <td colSpan="4" className="muted">
                  No concepts in this group.
                </td>
              </tr>
            ) : (
              shown.map((item) => {
                const pct = Math.round((item.overlap_score || 0) * 100);
                const ids = item.evidence_sentence_ids || [];
                return (
                  <tr key={item.concept}>
                    <td>
                      <strong>{item.concept}</strong>
                    </td>
                    <td>
                      <span className={`pill ${STATUS_CLASS[item.status] || 'c3-status-info'}`}>{STATUS_LABEL[item.status] || item.status}</span>
                    </td>
                    <td style={{ minWidth: 120 }}>
                      <div className="c3-bar" role="img" aria-label={`${pct}% of the concept's words found`}>
                        <span style={{ width: `${pct}%` }} />
                      </div>
                      <span className="small muted">{pct}%</span>
                    </td>
                    <td>
                      {ids.length > 0 ? (
                        <span className="small">
                          <span className="c3-sentence-tag">S{ids[0]}</span> &ldquo;{sentenceMap?.get(ids[0]) || ''}&rdquo;
                        </span>
                      ) : (
                        <span className="small muted">No matching sentence</span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
