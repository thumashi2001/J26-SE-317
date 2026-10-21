// All real, slide-based question content for Component 1.
// One file per module. Add a new module file here to include it everywhere.
import af from './af.js';
import csse from './csse.js';
import ds from './ds.js';
import dsys from './dsys.js';
import sa from './sa.js';
import sepqm from './sepqm.js';
import spm from './spm.js';
import uee from './uee.js';

export const MODULES = [csse, spm, uee, ds, dsys, sa, sepqm, af];

// topic key -> { semester, module_code, module_name, label, lectures, practice, diagnostic }
export const TOPICS = {};
for (const m of MODULES) {
  for (const [key, t] of Object.entries(m.topics)) {
    if (TOPICS[key]) throw new Error(`Duplicate topic key: ${key}`);
    TOPICS[key] = { semester: m.semester, module_code: m.module_code, module_name: m.module_name, ...t };
  }
}

export const topicsForSemester = (semester) => Object.entries(TOPICS).filter(([, t]) => t.semester === semester).map(([k]) => k);
