import fs from 'node:fs';
import { config, verifyIsolation } from './guard.mjs';
const OUT = process.argv[2];
const PW = config.password;
const B = config.apiBase;
await verifyIsolation(); // aborts before any test write unless the backend uses the same local test database
const call = async (t, m, p, body) => { const r = await fetch(B + p, { method: m, headers: { 'Content-Type': 'application/json', ...(t ? { Authorization: `Bearer ${t}` } : {}) }, body: body ? JSON.stringify(body) : undefined }); return { status: r.status, json: await r.json() }; };
const login = async (id) => (await call(null, 'POST', '/auth/login', { userId: id, password: PW })).json.token;
const ts = await login('IT10000001'), tl = await login('SLIITLEC101');
const save = (n, o) => fs.writeFileSync(`${OUT}/${n}.json`, JSON.stringify(o, null, 1));
// subjective, partial credit (real Python service output)
const sub = await call(ts, 'POST', '/c3/assess', { demo_id: 'arch-partial', student_answer: 'Software architecture provides a high-level structure for large-scale software systems. It guides developers.' });
save('subjective_student_live', sub.json);
save('subjective_lecturer_detail', (await call(tl, 'GET', `/c3/submissions/${sub.json.submission_id}`)).json);
save('subjective_student_detail', (await call(ts, 'GET', `/c3/submissions/${sub.json.submission_id}`)).json);
// MCQ wrong answer
const mcq = await call(ts, 'POST', '/c3/assess', { demo_id: 'mcq-correct', selected_option_id: 'A' });
save('mcq_student_live', mcq.json);
save('mcq_student_detail', (await call(ts, 'GET', `/c3/submissions/${mcq.json.submission_id}`)).json);
save('mcq_lecturer_detail', (await call(tl, 'GET', `/c3/submissions/${mcq.json.submission_id}`)).json);
console.log(sub.status, mcq.status, Object.keys(sub.json).join(','));
