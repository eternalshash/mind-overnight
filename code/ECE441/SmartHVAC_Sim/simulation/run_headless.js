const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', error => console.log('PAGE ERROR:', error.message));
  page.on('requestfailed', request => console.log('REQUEST FAILED:', request.url(), request.failure().errorText));

  await page.goto('file:///Users/schoudhry/Desktop/mind-overnight/code/ECE441/SmartHVAC_Sim/simulation/index.html', { waitUntil: 'networkidle0' });
  const autoBadge = await page.$eval('#iotAutoBadge', el => el.textContent.trim());
  const previewText = await page.$eval('#iotPreview', el => el.innerText);
  if (autoBadge !== 'AUTO-SEND: OFF' || previewText.includes('->')) {
    console.error('IOT GATEWAY ASSERTION FAILED:', autoBadge, previewText);
    process.exit(1);
  }
  await page.click('#f_blower');
  const sentCount = await page.$eval('#iotSentCount', el => el.textContent.trim());
  const faultPreview = await page.$eval('#iotPreview', el => el.innerText);
  if (sentCount !== '0 SENT' || !faultPreview.includes('Blower motor failure')) {
    console.error('AUTO-SEND OFF FAULT GUARD FAILED:', sentCount, faultPreview);
    process.exit(1);
  }
  await browser.close();
})();
