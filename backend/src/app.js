import express from 'express';
import cors from 'cors';
import fs from 'fs';
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const app = express();
app.use(cors());
app.use(express.json());

app.get('/health', (req, res) => res.json({ status: 'ok', service: 'backend' }));

// Every folder in modules/ that has routes/index.js is mounted at /api/v1/<folder>.
// So each member only adds their own module folder and never edits this file.
const modulesDir = path.join(__dirname, 'modules');
for (const name of fs.readdirSync(modulesDir)) {
  const routeFile = path.join(modulesDir, name, 'routes', 'index.js');
  if (fs.existsSync(routeFile)) {
    const mod = await import(pathToFileURL(routeFile).href);
    app.use(`/api/v1/${name}`, mod.default);
    console.log(`Mounted /api/v1/${name}`);
  }
}

export default app;