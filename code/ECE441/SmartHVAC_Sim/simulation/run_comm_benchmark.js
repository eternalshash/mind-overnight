const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

(async () => {
  const piUrl = process.env.PI_URL || 'http://192.168.0.70:8765';
  const outCsv = path.resolve(__dirname, '..', 'sim_comm_speed_benchmark.csv');

  console.log(`[SIM-BENCH] Launching headless browser against Raspberry Pi 5 at ${piUrl}...`);
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();

  page.on('console', msg => {
    const text = msg.text();
    if (text.includes('[BENCHMARK]') || text.includes('[RPI]') || text.includes('Speed:')) {
      console.log(`  [SIM-CONSOLE] ${text}`);
    }
  });

  const simUrl = `file://${path.resolve(__dirname, 'index.html')}?rpi=${encodeURIComponent(piUrl)}`;
  await page.goto(simUrl, { waitUntil: 'networkidle0' });

  // Ensure Pi URL input is set and sync is enabled
  await page.$eval('#rpiServerUrl', (el, url) => { el.value = url; }, piUrl);
  const syncState = await page.$eval('#rpiSyncBadge', el => el.textContent.trim());
  if (syncState !== 'SYNC: ON') {
    await page.click('#rpiSyncBadge');
  }

  console.log('[SIM-BENCH] Running 30-packet live communication benchmark from simulation to Pi...');
  const stats = await page.evaluate(async () => {
    return await window.runCommSpeedBenchmark(30);
  });

  console.log('[SIM-BENCH] Benchmark completed:', JSON.stringify(stats));

  // Extract CSV from simulation state
  const csvContent = await page.evaluate(() => window.exportCommCSV(false));
  fs.writeFileSync(outCsv, csvContent, 'utf-8');
  console.log(`[SIM-BENCH] Successfully saved readable CSV to ${outCsv} (${csvContent.split('\n').length - 1} rows)`);

  const latencyText = await page.$eval('#rpiLatencyBadge', el => el.textContent.trim());
  const statusLine = await page.$eval('#rpiStatusLine', el => el.textContent.trim());
  console.log(`[SIM-BENCH] UI Latency Badge: ${latencyText}`);
  console.log(`[SIM-BENCH] UI Status Line:   ${statusLine}`);

  console.log('[SIM-BENCH] Headless test finished successfully.');
  try { if (browser.process()) browser.process().kill('SIGKILL'); } catch (e) {}
  process.exit(0);
})().catch(err => {
  console.error('[SIM-BENCH] Error:', err);
  process.exit(1);
});
