const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', error => console.log('PAGE ERROR:', error.message));
  page.on('requestfailed', request => console.log('REQUEST FAILED:', request.url(), request.failure().errorText));

  await page.goto('https://raw.githack.com/eternalshash/mind-overnight/main/code/ECE441/SmartHVAC_Sim/simulation/index.html', { waitUntil: 'networkidle2' });
  await browser.close();
})();
