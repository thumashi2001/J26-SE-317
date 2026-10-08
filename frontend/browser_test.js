import puppeteer from 'puppeteer';

async function run() {
  console.log("Starting Browser E2E Test...");
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  
  try {
    // 1. Student Login
    console.log("Logging in as Student (IT10000001)...");
    await page.goto('http://localhost:5173/login');
    await page.type('input[type="text"]', 'IT10000001');
    await page.type('input[type="password"]', 'password');
    await page.click('button[type="submit"]');
    
    // Wait for redirect to student area
    await page.waitForSelector('.shell');
    
    // 2. Click Automated Marking
    console.log("Navigating to C3 Automated Marking...");
    await page.goto('http://localhost:5173/c3');
    await page.waitForSelector('.c3-card');
    
    // 3. Start Assessment
    console.log("Opening PP1 Demonstration...");
    // Find a link or button that navigates to the assessment
    const startBtns = await page.$$('button, a');
    let startFound = false;
    for (const btn of startBtns) {
      const text = await page.evaluate(el => el.textContent, btn);
      if (text.includes('Start Assessment')) {
        await btn.click();
        startFound = true;
        break;
      }
    }
    
    await page.waitForSelector('textarea');
    console.log("Typing answer...");
    await page.type('textarea', 'Database normalization reduces redundancy and anomalies. 1NF ensures atomic values. 2NF ensures the entire primary key is used without partial dependency. 3NF removes transitive dependency.');
    
    console.log("Submitting answer...");
    await page.click('button.c3-btn-primary');
    
    console.log("Waiting for AI processing...");
    // Wait for the result page to load - usually has "AI Suggested Mark" or "Processing"
    await page.waitForFunction(() => {
      return document.body.innerText.includes('AI Suggested Mark') || document.body.innerText.includes('Concept Analysis');
    }, { timeout: 30000 });
    
    const content = await page.evaluate(() => document.body.innerText);
    if (content.includes('AI Suggested Mark')) {
       console.log("Student Result successfully verified!");
       if (content.includes('Concept Mind Map')) console.log("Mind map section verified.");
    }

    // 4. Logout
    console.log("Logging out...");
    const buttons = await page.$$('button');
    for (const btn of buttons) {
      const text = await page.evaluate(el => el.textContent, btn);
      if (text.includes('Log out')) {
        await btn.click();
        break;
      }
    }
    await page.waitForSelector('input[type="text"]');
    
    // 5. Lecturer Login
    console.log("Logging in as Lecturer (IT20000001)...");
    await page.type('input[type="text"]', 'IT20000001');
    await page.type('input[type="password"]', 'password');
    await page.click('button[type="submit"]');
    await page.waitForSelector('.shell');

    console.log("Navigating to Lecturer C3 Review...");
    await page.goto('http://localhost:5173/lecturer/c3');
    await page.waitForSelector('.c3-card');

    console.log("Opening latest submission...");
    const reviewBtns = await page.$$('button, a');
    for (const btn of reviewBtns) {
      const text = await page.evaluate(el => el.textContent, btn);
      if (text.includes('Review')) {
        await btn.click();
        break;
      }
    }

    await page.waitForFunction(() => {
      return document.body.innerText.includes('Accept AI Mark');
    }, { timeout: 10000 });

    console.log("Accepting AI Mark...");
    const lButtons = await page.$$('button');
    for (const btn of lButtons) {
      const text = await page.evaluate(el => el.textContent, btn);
      if (text.includes('Accept AI Mark')) {
        await btn.click();
        break;
      }
    }
    
    await page.waitForFunction(() => {
      return document.body.innerText.includes('Confirm & Finalize');
    }, { timeout: 5000 });
    
    const confirmBtns = await page.$$('button');
    for (const btn of confirmBtns) {
      const text = await page.evaluate(el => el.textContent, btn);
      if (text.includes('Confirm & Finalize')) {
        await btn.click();
        break;
      }
    }

    await page.waitForFunction(() => {
      return document.body.innerText.includes('Finalized');
    }, { timeout: 15000 });
    console.log("Lecturer workflow verified!");

    // 6. Admin Login
    console.log("Logging out...");
    const l2Btns = await page.$$('button');
    for (const btn of l2Btns) {
      const text = await page.evaluate(el => el.textContent, btn);
      if (text.includes('Log out')) {
        await btn.click();
        break;
      }
    }
    await page.waitForSelector('input[type="text"]');

    console.log("Logging in as Admin (IT30000001)...");
    await page.type('input[type="text"]', 'IT30000001');
    await page.type('input[type="password"]', 'password');
    await page.click('button[type="submit"]');
    await page.waitForSelector('.shell');

    console.log("Navigating to Admin Dashboard...");
    await page.goto('http://localhost:5173/admin/c3');
    await page.waitForFunction(() => {
      return document.body.innerText.includes('System statistics successfully retrieved');
    }, { timeout: 10000 });
    console.log("Admin Dashboard verified!");
    
    console.log("Browser E2E PASS!");
  } catch(e) {
    console.error("Browser E2E FAIL:", e);
  } finally {
    await browser.close();
  }
}

run();
