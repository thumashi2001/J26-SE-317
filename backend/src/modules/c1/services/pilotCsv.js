// Reads a Google Form responses file (CSV) and turns it into answer events for the item analysis.
// No database and no dependencies. See docs/c1-question-method.md, section 6.

// Minimal CSV reader: handles quoted fields, commas and new lines inside quotes, and "" for a quote.
export function parseCsv(text) {
  const rows = [];
  let row = [], field = '', quoted = false;
  const src = text.replace(/^﻿/, '');
  for (let i = 0; i < src.length; i++) {
    const ch = src[i];
    if (quoted) {
      if (ch === '"') { if (src[i + 1] === '"') { field += '"'; i++; } else quoted = false; } else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ',') { row.push(field); field = ''; }
    else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && src[i + 1] === '\n') i++;
      row.push(field); field = '';
      if (row.some((c) => c !== '')) rows.push(row);
      row = [];
    } else field += ch;
  }
  row.push(field);
  if (row.some((c) => c !== '')) rows.push(row);
  return rows;
}

// A checkbox answer arrives as "option A, option B" and options may contain commas themselves,
// so find each known option text inside the cell (longest first, removing what was found).
export function pickedOptions(cell, options) {
  let rest = String(cell || '');
  const picked = [];
  [...options.keys()].sort((a, b) => options[b].length - options[a].length).forEach((i) => {
    if (options[i] && rest.includes(options[i])) { picked.push(i); rest = rest.replace(options[i], '\u0000'); }
  });
  return picked.sort((a, b) => a - b);
}

// key: [{ n, question_id, options, correct, multi }]  rows: parsed CSV (first row = headers)
export function eventsFromResponses(rows, key) {
  const [head, ...data] = rows;
  const colOf = {};
  head.forEach((h, c) => { const m = /^Q(\d+)\./.exec(String(h).trim()); if (m) colOf[Number(m[1])] = c; });
  const events = [];
  const unreadable = [];
  data.forEach((r, ri) => {
    key.forEach((k) => {
      const c = colOf[k.n];
      if (c === undefined) { if (ri === 0) unreadable.push(k.n); return; }
      const cell = r[c];
      if (cell === undefined || String(cell).trim() === '') return;
      const picked = pickedOptions(cell, k.options);
      if (!picked.length) return;
      const right = picked.length === k.correct.length && picked.every((p, i) => p === [...k.correct].sort((a, b) => a - b)[i]);
      events.push({ student_id: `R${ri + 1}`, question_id: k.question_id, correct: right, timestamp: new Date(1e12 + ri * 1000 + k.n) });
    });
  });
  return { events, respondents: data.length, missingColumns: unreadable };
}
