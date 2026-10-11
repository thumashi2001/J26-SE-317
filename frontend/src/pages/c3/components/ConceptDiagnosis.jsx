import React, { useState } from 'react';

/**
 * Concept Analysis & Lexical Evidence Diagnosis Table
 * Displays fine-grained concept coverage, token overlap score, and sentence grounding.
 */
export default function ConceptDiagnosis({ analysis, sentenceMap }) {
  const [activeTab, setActiveTab] = useState('all');

  if (!analysis || !analysis.concept_matches) return null;

  const {
    concept_matches = [],
    sentence_count,
    token_count,
    reference_similarity,
    analysis_version,
  } = analysis;

  const filtered = concept_matches.filter((c) => {
    if (activeTab === 'all') return true;
    return c.status === activeTab;
  });

  const demonstratedCount = concept_matches.filter((c) => c.status === 'demonstrated').length;
  const partialCount = concept_matches.filter((c) => c.status === 'partial').length;
  const missingCount = concept_matches.filter((c) => c.status === 'not_demonstrated').length;

  return (
    <div className="panel c3-concept-diagnosis-panel">
      <div className="c3-diagnosis-head">
        <div>
          <h3>Concept-Level Diagnosis & Semantic Evidence</h3>
          <p className="small muted" style={{ margin: '2px 0 0' }}>
            Function 1 lexical overlap analysis • Version: {analysis_version || 'baseline-v1'}
          </p>
        </div>

        {/* NLP Lexical Stats Pills */}
        <div className="c3-nlp-stats">
          <span className="c3-stat-tag">
            <strong>{sentence_count}</strong> Sentences
          </span>
          <span className="c3-stat-tag">
            <strong>{token_count}</strong> Tokens
          </span>
          {reference_similarity !== null && reference_similarity !== undefined && (
            <span className="c3-stat-tag">
              Reference Sim: <strong>{Math.round(reference_similarity * 100)}%</strong>
            </span>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="c3-concept-tabs">
        <button
          type="button"
          className={`c3-tab-btn ${activeTab === 'all' ? 'active' : ''}`}
          onClick={() => setActiveTab('all')}
        >
          All Concepts ({concept_matches.length})
        </button>
        <button
          type="button"
          className={`c3-tab-btn demonstrated ${activeTab === 'demonstrated' ? 'active' : ''}`}
          onClick={() => setActiveTab('demonstrated')}
        >
          ✓ Demonstrated ({demonstratedCount})
        </button>
        <button
          type="button"
          className={`c3-tab-btn partial ${activeTab === 'partial' ? 'active' : ''}`}
          onClick={() => setActiveTab('partial')}
        >
          △ Partial ({partialCount})
        </button>
        <button
          type="button"
          className={`c3-tab-btn missing ${activeTab === 'not_demonstrated' ? 'active' : ''}`}
          onClick={() => setActiveTab('not_demonstrated')}
        >
          ○ Missing ({missingCount})
        </button>
      </div>

      {/* Table */}
      <div className="c3-concept-table-wrap">
        <table className="c3-concept-table">
          <thead>
            <tr>
              <th>Expected Concept</th>
              <th>Status</th>
              <th>Token Overlap</th>
              <th>Evidence Sentences</th>
              <th>Sentence Excerpt</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan="5" className="c3-empty-td muted">
                  No concepts match this filter.
                </td>
              </tr>
            ) : (
              filtered.map((item, idx) => {
                const isDem = item.status === 'demonstrated';
                const isPart = item.status === 'partial';
                return (
                  <tr key={idx}>
                    <td>
                      <strong className="c3-concept-name">{item.concept}</strong>
                    </td>
                    <td>
                      <span
                        className={`chip ${
                          isDem
                            ? 'c3-status-demonstrated'
                            : isPart
                            ? 'c3-status-partial'
                            : 'c3-status-missing'
                        }`}
                      >
                        {isDem ? '✓ Demonstrated' : isPart ? '△ Partial' : '○ Not Demonstrated'}
                      </span>
                    </td>
                    <td>
                      <div className="c3-overlap-bar-wrap">
                        <div
                          className="c3-overlap-bar"
                          style={{
                            width: `${Math.round(item.overlap_score * 100)}%`,
                            backgroundColor: isDem ? '#0f9a78' : isPart ? '#d9901a' : '#d6453d',
                          }}
                        />
                        <span className="c3-overlap-pct">
                          {Math.round(item.overlap_score * 100)}%
                        </span>
                      </div>
                    </td>
                    <td>
                      {item.evidence_sentence_ids && item.evidence_sentence_ids.length > 0 ? (
                        <div className="c3-sids-wrap">
                          {item.evidence_sentence_ids.map((sid) => (
                            <span key={sid} className="c3-sentence-tag">
                              S{sid}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="small muted">—</span>
                      )}
                    </td>
                    <td className="c3-excerpt-td">
                      {item.evidence_sentence_ids && item.evidence_sentence_ids.length > 0 ? (
                        <span className="small">
                          &ldquo;{sentenceMap?.get(item.evidence_sentence_ids[0]) || ''}&rdquo;
                        </span>
                      ) : (
                        <span className="small muted">No matching sentence text</span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
