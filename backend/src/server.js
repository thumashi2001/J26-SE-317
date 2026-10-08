import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, '..', '.env') });

import app from './app.js';
import { connectDb } from './config/db.js';
import { seedDevAssessment } from './modules/c3/services/assessmentService.js';

const PORT = process.env.PORT || 3000;

connectDb()
  .then(async () => {
    // Seed the PP1 development assessment if it doesn't exist
    try {
      await seedDevAssessment();
      console.log('C3 dev assessment ready');
    } catch (err) {
      console.warn('C3 seed skipped:', err.message);
    }
    app.listen(PORT, () => console.log(`Backend listening on http://localhost:${PORT}`));
  })
  .catch((err) => {
    console.error('Startup failed:', err.message);
    process.exit(1);
  });