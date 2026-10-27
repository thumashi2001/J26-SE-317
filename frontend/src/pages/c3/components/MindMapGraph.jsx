import React, { useState } from 'react';

const STATUS = {
  demonstrated: { label: 'Demonstrated', cls: 'demonstrated', pill: 'status-approved' },
  partial: { label: 'Partial', cls: 'partial', pill: 'status-pending' },
  not_demonstrated: { label: 'Missing', cls: 'missing', pill: 'status-rejected' },
  missing: { label: 'Missing', cls: 'missing', pill: 'status-rejected' },
};

// Accepts both response shapes: the Python service (node_id, relationships, root_node_id)
// and the in-app MCQ marker (id, edges). Only edges present in the response are drawn.
function normalise(mindmap) {
  const nodes = (mindmap.nodes || []).map((n) => ({
    ...n,
    node_id: n.node_id ?? n.id,
    concept: n.concept ?? n.label,
    label: n.label ?? n.concept ?? '',
  }));
  const edges = (mindmap.relationships || mindmap.edges || []).map((r, i) => ({
    id: r.relationship_id ?? r.id ?? `e${i}`,
    source: r.source_node_id ?? r.source ?? r.from,
    target: r.target_node_id ?? r.target ?? r.to,
    type: r.relationship_type ?? r.type,
    evidence: r.evidence,
  }));
  const rootId = mindmap.root_node_id ?? nodes.find((n) => n.type === 'root')?.node_id ?? nodes[0]?.node_id;
  return { nodes, edges, rootId };
}

// Readable names for relationship types ('co_mentioned' = same sentence only; the others come from a cue phrase).
const REL_LABEL = { co_mentioned: 'Mentioned together', is_a: 'Is a kind of', part_of: 'Is part of', depends_on: 'Depends on', leads_to: 'Leads to', contrasts_with: 'Contrasts with' };

// Draws the answer-to-concept map: nodes are concepts/sentences coloured by status; click a node to see its evidence.
export default function MindMapGraph({ mindmap, sentences = [] }) {
  const [selectedId, setSelectedId] = useState(null);
  const [filter, setFilter] = useState('all');

  if (!mindmap || !Array.isArray(mindmap.nodes) || mindmap.nodes.length === 0) {
    return (
      <div className="panel c3-empty">
        <p className="muted" style={{ margin: 0 }}>
          No concept map was produced for this answer.
        </p>
      </div>
    );
  }

  const { nodes, edges, rootId } = normalise(mindmap);
  const sentenceMap = new Map(sentences.map((s) => [s.sentence_id, s.text]));
  const root = nodes.find((n) => n.node_id === rootId) || nodes[0];
  const concepts = nodes.filter((n) => n.node_id !== root.node_id);
  const counts = { demonstrated: 0, partial: 0, not_demonstrated: 0 };
  concepts.forEach((n) => {
    const k = n.status === 'missing' ? 'not_demonstrated' : n.status;
    if (k in counts) counts[k] += 1;
  });
  const matches = (n) => filter === 'all' || (n.status === 'missing' ? 'not_demonstrated' : n.status) === filter;

  const W = 840;
  const cols = Math.min(4, Math.max(2, concepts.length));
  const H = Math.max(300, 170 + Math.ceil(concepts.length / cols) * 100);
  const rootPos = { x: W / 2, y: 50 };
  const pos = new Map();
  concepts.forEach((n, i) => {
    const row = Math.floor(i / cols);
    const inRow = Math.min(cols, concepts.length - row * cols);
    pos.set(n.node_id, { x: (W / (inRow + 1)) * ((i % cols) + 1), y: 170 + row * 100 });
  });
  pos.set(root.node_id, rootPos);
  const selected = nodes.find((n) => n.node_id === selectedId);
  const trim = (t, n) => (t.length > n ? `${t.slice(0, n - 2)}...` : t);

  return (
    <section className="c3-mindmap-container" aria-label="Concept map">
      <div className="c3-mindmap-header">
        <div>
          <h3 style={{ margin: 0 }}>{mindmap.title || 'Concept map'}</h3>
          <span className="small muted">Built from the concepts found in the answer. Select a concept for its evidence.</span>
        </div>
        <div className="tabs" role="group" aria-label="Filter concept map" style={{ margin: 0 }}>
          {[
            ['all', 'All', concepts.length],
            ['demonstrated', 'Demonstrated', counts.demonstrated],
            ['partial', 'Partial', counts.partial],
            ['not_demonstrated', 'Missing', counts.not_demonstrated],
          ].map(([key, label, n]) => (
            <button key={key} type="button" className={filter === key ? 'on' : ''} aria-pressed={filter === key} onClick={() => setFilter(key)}>
              {label} <span className="tab-count">{n}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="c3-svg-scroll">
        <svg viewBox={`0 0 ${W} ${H}`} className="c3-mindmap-svg" style={{ width: '100%', minWidth: 600, height: H }} role="group" aria-label="Concept map diagram; the same information is listed below">
          {edges.map((e) => {
            const a = pos.get(e.source);
            const b = pos.get(e.target);
            if (!a || !b) return null;
            const active = selectedId && (e.source === selectedId || e.target === selectedId);
            const midY = (a.y + b.y) / 2;
            return <path key={e.id} d={`M ${a.x} ${a.y + 22} C ${a.x} ${midY}, ${b.x} ${midY}, ${b.x} ${b.y - 22}`} className={`c3-mm-edge${active ? ' active' : ''}`} />;
          })}

          <g transform={`translate(${rootPos.x}, ${rootPos.y})`} className="c3-mm-node root" tabIndex={0} role="button" aria-label={`Question: ${root.label}`} onClick={() => setSelectedId(root.node_id)} onKeyDown={(ev) => (ev.key === 'Enter' || ev.key === ' ') && setSelectedId(root.node_id)}>
            <rect x="-120" y="-24" width="240" height="48" rx="12" className={selectedId === root.node_id ? 'sel' : ''} />
            <text textAnchor="middle" y="5">{trim(root.label, 32)}</text>
          </g>

          {concepts.map((n) => {
            const p = pos.get(n.node_id);
            const st = STATUS[n.status] || STATUS.not_demonstrated;
            const label = n.concept || n.label;
            return (
              <g
                key={n.node_id}
                transform={`translate(${p.x}, ${p.y})`}
                className={`c3-mm-node ${st.cls}${matches(n) ? '' : ' dim'}`}
                tabIndex={0}
                role="button"
                aria-label={`${label}: ${st.label}`}
                onClick={() => setSelectedId(n.node_id)}
                onKeyDown={(ev) => (ev.key === 'Enter' || ev.key === ' ') && setSelectedId(n.node_id)}
              >
                <rect x="-90" y="-22" width="180" height="44" rx="10" className={selectedId === n.node_id ? 'sel' : ''} />
                <text textAnchor="middle" y="-3" className="t1">{trim(label, 22)}</text>
                <text textAnchor="middle" y="13" className="t2">
                  {st.label}
                  {n.evidence_sentence_ids?.length > 0 && ` · S${n.evidence_sentence_ids.join(',')}`}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <details className="c3-mm-list">
        <summary>View concepts as a list</summary>
        <ul>
          {concepts.map((n) => (
            <li key={n.node_id}>
              <strong>{n.concept || n.label}</strong> <span className={`pill ${(STATUS[n.status] || STATUS.not_demonstrated).pill}`}>{(STATUS[n.status] || STATUS.not_demonstrated).label}</span>
            </li>
          ))}
        </ul>
      </details>

      {selected && (
        <div className="c3-node-inspector panel" aria-live="polite">
          <div className="c3-inspector-head">
            <div>
              <span className="small muted">Selected concept</span>
              <h4 style={{ margin: '2px 0 0' }}>{selected.concept || selected.label}</h4>
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              {selected.node_id !== root.node_id && <span className={`pill ${(STATUS[selected.status] || STATUS.not_demonstrated).pill}`}>{(STATUS[selected.status] || STATUS.not_demonstrated).label}</span>}
              <button type="button" className="btn-ghost c3-close" onClick={() => setSelectedId(null)}>
                Close
              </button>
            </div>
          </div>
          {/* Concept-to-concept lines touching this node (typed ones name the cue phrase the student used). */}
          {selected.node_id !== root.node_id && edges.filter((e) => e.type !== 'child' && (e.source === selected.node_id || e.target === selected.node_id)).length > 0 && (
            <div className="c3-inspector-evidence">
              <strong>Relationships as the student wrote them</strong>
              {edges.filter((e) => e.type !== 'child' && (e.source === selected.node_id || e.target === selected.node_id)).map((e) => (
                <div key={e.id} className="c3-evidence-quote">
                  <span className="c3-sentence-tag">{REL_LABEL[e.type] || e.type}</span> {e.evidence}
                </div>
              ))}
            </div>
          )}
          {selected.evidence_sentence_ids?.length > 0 ? (
            <div className="c3-inspector-evidence">
              <strong>Evidence in the answer</strong>
              {selected.evidence_sentence_ids.map((id) => (
                <div key={id} className="c3-evidence-quote">
                  <span className="c3-sentence-tag">Sentence {id}</span> &ldquo;{sentenceMap.get(id) || ''}&rdquo;
                </div>
              ))}
            </div>
          ) : (
            <p className="small muted" style={{ margin: '8px 0 0' }}>
              No sentence in the answer supports this item.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
