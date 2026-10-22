import { chromium } from 'playwright-core';
import { config } from './guard.mjs'; // refuses to load unless the test environment is explicit and loopback-only
if (!config.webBase) { console.error('[c3-test-guard] REFUSING TO RUN: C3_WEB_BASE is not set'); process.exit(2); }
export const BASE = config.webBase;
export const ACCOUNTS = {
  student: { id: 'IT10000001', pw: config.password },
  lecturer: { id: 'SLIITLEC101', pw: config.password },
  admin: { id: 'SLIITADMIN1', pw: config.password },
};
export async function launch() {
  return chromium.launch({ executablePath: process.env.C3_CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
}
export async function login(browser, role, opts = {}) {
  const ctx = await browser.newContext({ viewport: opts.viewport || { width: 1280, height: 800 }, colorScheme: opts.colorScheme || 'light' });
  const page = await ctx.newPage();
  const logs = [];
  page.on('console', (m) => { if (['error'].includes(m.type())) logs.push(`[console.${m.type()}] ${m.text().slice(0, 200)}`); });
  page.on('pageerror', (e) => logs.push(`[pageerror @${new URL(page.url()).pathname}] ${e.message.slice(0, 200)}`));
  await page.goto(BASE + '/login');
  await page.fill('#sid', ACCOUNTS[role].id);
  await page.fill('#pw', ACCOUNTS[role].pw);
  await page.click('button[type=submit]');
  await page.waitForLoadState('networkidle');
  return { ctx, page, logs };
}
