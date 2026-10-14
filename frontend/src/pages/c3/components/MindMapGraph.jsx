import React, { useState } from 'react';

/**
 * Interactive SVG Concept Mind Map Visualizer
 * Renders the authoritative Function 4 graph structure directly from the API response.
 */
export default function MindMapGraph({ mindmap, sentences = [] }) {
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [filterStatus, setFilterStatus] = useState('all');

  if (!mindmap || !mindmap.nodes || mindmap.nodes.length === 0) {
    return (
      <div className="c3-empty-card">
        <p className="muted">No mind map generated for this assessment.</p>
      </div>
    );
  }

  const { nodes, relationships, summary, title, root_node_id } = mindmap;

  // Map sentence IDs to sentence text
  const sentenceMap = new Map();
  sentences.forEach((s) => sentenceMap.set(s.sentence_id, s.text));

  // Partition root and concept nodes
  const rootNode = nodes.find((n) => n.node_id === root_node_id) || nodes[0];
  const conceptNodes = nodes.filter((n) => n.node_id !== rootNode.node_id);

  // Filter concept nodes if filter is active
  const visibleConceptNodes = conceptNodes.filter((n) => {
    if (filterStatus === 'all') return true;
    return n.status === filterStatus;
  });

  // Calculate layout coordinates
  // Root at top center; concept nodes in a row or arc below
  const width = 840;
  const height = Math.max(340, 160 + Math.ceil(conceptNodes.length / 4) * 110);
  const rootX = width / 2;
  const rootY = 60;

  // Position concept nodes in a clean grid below the root
  const cols = Math.min(4, Math.max(2, conceptNodes.length));
  const conceptPositions = new Map();

  conceptNodes.forEach((node, index) => {
    const row = Math.floor(index / cols);
    const col = index % cols;
    const totalInRow = Math.min(cols, conceptNodes.length - row * cols);
    const spacingX = width / (totalInRow + 1);
    const x = spacingX * (col + 1);
    const y = 190 + row * 110;
    conceptPositions.set(node.node_id, { x, y });
  });

  const selectedNode = nodes.find((n) => n.node_id === selectedNodeId);

  const getStatusColor = (status) => {
    switch (status) {
      case 'demonstrated':
        return {
          bg: '#e6f7f2',
          border: '#0f9a78',
          text: '#065543',
          badge: '✓ Demonstrated',
          chipClass: 'c3-status-demonstrated',
        };
      case 'partial':
        return {
          bg: '#fef5e7',
          border: '#d9901a',
          text: '#7a5200',
          badge: '△ Partial',
          chipClass: 'c3-status-partial',
        };
      case 'not_demonstrated':
        return {
          bg: '#fdf0ef',
          border: '#d6453d',
          text: '#8a1f17',
          badge: '○ Missing',
          chipClass: 'c3-status-missing',
        };
      default:
        return {
          bg: '#f3f6f8',
          border: '#0e2238',
          text: '#0e2238',
          badge: 'Root Topic',
          chipClass: 'c3-status-root',
        };
    }
  };

  return (
    <div className="c3-mindmap-container">
      {/* Mind Map Header & Summary Statistics */}
      <div className="c3-mindmap-header">
        <div>
          <h3 style={{ margin: 0 }}>{title || 'Concept Mind Map'}</h3>
          <span className="small muted">
            Generated via Function 4 deterministic hierarchy & lexical evidence
          </span>
        </div>
        <div className="c3-mindmap-filters">
          <button
            type="button"
            className={`c3-filter-pill ${filterStatus === 'all' ? 'active' : ''}`}
            onClick={() => setFilterStatus('all')}
          >
            All ({summary?.total_nodes || nodes.length})
          </button>
          <button
            type="button"
            className={`c3-filter-pill demonstrated ${filterStatus === 'demonstrated' ? 'active' : ''}`}
            onClick={() => setFilterStatus('demonstrated')}
          >
            ✓ Demonstrated ({summary?.demonstrated_count || 0})
          </button>
          <button
            type="button"
            className={`c3-filter-pill partial ${filterStatus === 'partial' ? 'active' : ''}`}
            onClick={() => setFilterStatus('partial')}
          >
            △ Partial ({summary?.partial_count || 0})
          </button>
          <button
            type="button"
            className={`c3-filter-pill missing ${filterStatus === 'not_demonstrated' ? 'active' : ''}`}
            onClick={() => setFilterStatus('not_demonstrated')}
          >
            ○ Missing ({summary?.missing_count || 0})
          </button>
        </div>
      </div>

      {/* SVG Canvas */}
      <div className="c3-svg-scroll">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="c3-mindmap-svg"
          style={{ width: '100%', minWidth: '600px', height: `${height}px` }}
        >
          <defs>
            <marker
              id="arrow-default"
              viewBox="0 0 10 10"
              refX="18"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#8aa3ba" />
            </marker>
            <marker
              id="arrow-active"
              viewBox="0 0 10 10"
              refX="18"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#087a63" />
            </marker>
          </defs>

          {/* Relationship Edges */}
          {relationships.map((rel) => {
            const isSourceRoot = rel.source_node_id === rootNode.node_id;
            const sourcePos = isSourceRoot
              ? { x: rootX, y: rootY + 20 }
              : conceptPositions.get(rel.source_node_id);
            const targetPos = conceptPositions.get(rel.target_node_id);

            if (!sourcePos || !targetPos) return null;

            const isConnectedToSelected =
              selectedNodeId &&
              (rel.source_node_id === selectedNodeId || rel.target_node_id === selectedNodeId);

            // Curved cubic bezier path
            const midY = (sourcePos.y + targetPos.y) / 2;
            const pathData = `M ${sourcePos.x} ${sourcePos.y} C ${sourcePos.x} ${midY}, ${targetPos.x} ${midY}, ${targetPos.x} ${targetPos.y}`;

            return (
              <g key={rel.relationship_id}>
                <path
                  d={pathData}
                  fill="none"
                  stroke={isConnectedToSelected ? '#087a63' : '#bccad7'}
                  strokeWidth={isConnectedToSelected ? 2.5 : 1.5}
                  strokeDasharray={rel.relationship_type === 'UNLINKED_FALLBACK' ? '4 4' : 'none'}
                  markerEnd={isConnectedToSelected ? 'url(#arrow-active)' : 'url(#arrow-default)'}
                />
              </g>
            );
          })}

          {/* Root Node */}
          <g
            className="c3-node-group"
            transform={`translate(${rootX}, ${rootY})`}
            onClick={() => setSelectedNodeId(rootNode.node_id)}
            style={{ cursor: 'pointer' }}
          >
            <rect
              x="-110"
              y="-24"
              width="220"
              height="48"
              rx="12"
              fill="#0e2238"
              stroke={selectedNodeId === rootNode.node_id ? '#4aa3ff' : '#1b3a59'}
              strokeWidth={selectedNodeId === rootNode.node_id ? 3 : 1.5}
            />
            <text
              textAnchor="middle"
              y="5"
              fill="#ffffff"
              fontFamily="var(--font-head)"
              fontWeight="700"
              fontSize="13"
            >
              {rootNode.label.length > 28 ? rootNode.label.slice(0, 25) + '...' : rootNode.label}
            </text>
          </g>

          {/* Concept Nodes */}
          {conceptNodes.map((node) => {
            const pos = conceptPositions.get(node.node_id);
            if (!pos) return null;

            const colors = getStatusColor(node.status);
            const isSelected = selectedNodeId === node.node_id;
            const isDimmed = filterStatus !== 'all' && node.status !== filterStatus;

            return (
              <g
                key={node.node_id}
                className={`c3-node-group ${isDimmed ? 'dimmed' : ''}`}
                transform={`translate(${pos.x}, ${pos.y})`}
                onClick={() => setSelectedNodeId(node.node_id)}
                style={{ cursor: 'pointer', opacity: isDimmed ? 0.3 : 1 }}
              >
                <rect
                  x="-90"
                  y="-22"
                  width="180"
                  height="44"
                  rx="10"
                  fill={colors.bg}
                  stroke={isSelected ? '#0e2238' : colors.border}
                  strokeWidth={isSelected ? 3 : 1.5}
                />
                <text
                  textAnchor="middle"
                  y="-3"
                  fill={colors.text}
                  fontFamily="var(--font-body)"
                  fontWeight="600"
                  fontSize="12"
                >
                  {node.concept.length > 22 ? node.concept.slice(0, 20) + '...' : node.concept}
                </text>
                <text
                  textAnchor="middle"
                  y="13"
                  fill={colors.border}
                  fontFamily="var(--font-body)"
                  fontWeight="500"
                  fontSize="10"
                >
                  {colors.badge}
                  {node.evidence_sentence_ids?.length > 0 &&
                    ` • S[${node.evidence_sentence_ids.join(',')}]`}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Inspector Panel for Selected Node */}
      {selectedNode && (
        <div className="c3-node-inspector panel">
          <div className="c3-inspector-head">
            <div>
              <span className="small muted">Node Details</span>
              <h4 style={{ margin: '2px 0 0' }}>{selectedNode.concept || selectedNode.label}</h4>
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <span className={`chip ${getStatusColor(selectedNode.status).chipClass}`}>
                {getStatusColor(selectedNode.status).badge}
              </span>
              <button
                type="button"
                className="btn-ghost"
                style={{ padding: '3px 8px', width: 'auto' }}
                onClick={() => setSelectedNodeId(null)}
              >
                ✕ Close
              </button>
            </div>
          </div>

          <div className="c3-inspector-grid">
            <div>
              <strong>Node ID:</strong> <span className="small muted">{selectedNode.node_id}</span>
            </div>
            <div>
              <strong>Type / Source:</strong>{' '}
              <span className="small muted">
                {selectedNode.type} ({selectedNode.source})
              </span>
            </div>
            <div>
              <strong>Evidence Sentences:</strong>{' '}
              <span className="small">
                {selectedNode.evidence_sentence_ids?.length > 0
                  ? selectedNode.evidence_sentence_ids.map((id) => `Sentence ${id}`).join(', ')
                  : 'None detected'}
              </span>
            </div>
          </div>

          {selectedNode.evidence_sentence_ids?.length > 0 && (
            <div className="c3-inspector-evidence">
              <strong>Grounding Evidence in Student Answer:</strong>
              {selectedNode.evidence_sentence_ids.map((id) => {
                const text = sentenceMap.get(id);
                return (
                  <div key={id} className="c3-evidence-quote">
                    <span className="c3-sentence-tag">Sentence {id}:</span> &ldquo;{text}&rdquo;
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
