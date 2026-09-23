/* Offline browser checks. Install Playwright, then run node scripts/test_tuning_browser.cjs.
   PLAYWRIGHT_MODULE can point to an existing Playwright install. No browser downloads here. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {pathToFileURL} = require('node:url');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'intro-browser-'));
const output = path.join(temp, 'review.html');
const generated = spawnSync(process.env.PYTHON || 'python3', ['-c', `
import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import tuning
rows=[]
for t in range(311):
 for c in range(294):
  rows.append(dict(id=f'p{t}-{c}',target_id=f't{t}',target_name=f'Target {t:03d}',target_company=f'Account {t%25:02d}',connector_id=f'c{c}',connector_name=f'Connector {c:03d}',baseline_score=0,review_status='needs_confirmation',features={'investor_portfolio':dict(value=1 if c==293 else 0,evidence_ids=['e'] if c==293 else [],explanation='Company context only.',timing_status='not_applicable')}))
Path(sys.argv[2]).write_text(tuning.render(dict(as_of='2026-09-23',paths=rows,evidence=[dict(id='e',source='https://example.com',detail='Portfolio fact.',observed_at='2026-09-23')])))
`, __dirname, output], {encoding:'utf8', maxBuffer:1024*1024});
assert.equal(generated.status, 0, generated.stderr);
(async()=>{
 const browser=await chromium.launch({headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
  const errors=[],network=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url());});
  const start=Date.now();await page.goto(pathToFileURL(output).href);await page.waitForSelector('.card');
  const loadMs=Date.now()-start;
  assert.equal(await page.locator('.target').count(),311);assert.equal(await page.locator('.card').count(),3);
  assert.match(await page.locator('#coverage').innerText(),/91,434 candidate paths/);
  assert.equal(await page.locator('.detail-content').count(),0,'Evidence should be lazy.');
  await page.locator('.detail summary').first().click();await page.waitForSelector('.detail-content');
  assert.equal(await page.locator('.detail-content').count(),1);
  await page.selectOption('#limit','all');assert.equal(await page.locator('.card').count(),20);
  await page.locator('.load-more').click();assert.equal(await page.locator('.card').count(),40);
  const first=page.locator('.card').first();const pathId=await first.getAttribute('data-path-id');
  await first.locator('.feedback select').selectOption('good');await first.locator('textarea').fill('Useful route <script> remains plain text.');
  const oldCache=await page.evaluate(()=>{window.testRankingCache=rankingCache;return true;});assert(oldCache);
  await page.locator('.target').nth(1).click();assert.equal(await page.locator('.card').count(),20);
  assert.equal(await page.evaluate(()=>window.testRankingCache===rankingCache),true,'Selection must reuse ranked candidates.');
  await page.locator('#search').fill('no matching contact');assert.equal(await page.locator('.card').count(),0);assert.match(await page.locator('#target-heading').innerText(),/No contacts match/);
  await page.locator('#search').fill('');await page.selectOption('#account','Account 01');assert.equal(await page.locator('.target').count(),13);
  assert.match(await page.locator('#target-heading').innerText(),/Account 01/);
  await page.selectOption('#account','');await page.locator('.target').first().click();assert.equal(await page.locator('.card').first().getAttribute('data-path-id'),pathId);
  assert.equal(await page.locator('.card').first().locator('.feedback select').inputValue(),'good');
  await page.locator('#toggle-weights').click();await page.getByRole('spinbutton',{name:'Investor company link weight',exact:true}).fill('0');
  assert.equal(await page.evaluate(()=>window.testRankingCache===rankingCache),false,'Weight edits must rerank all candidates.');
  assert.equal(await page.locator('.card').first().getAttribute('data-path-id'),'p0-0','Formerly lower candidate can become top ranked.');
  const download=page.waitForEvent('download');await page.locator('#export-feedback').click();const saved=await download;await saved.saveAs(path.join(temp,'feedback.json'));
  const feedback=JSON.parse(fs.readFileSync(path.join(temp,'feedback.json'),'utf8'));
  assert.equal(feedback.model,'evidence-feature-heuristic-v4');assert.equal(feedback.reviews.length,1);assert.equal(feedback.reviews[0].path_id,pathId);assert.equal(feedback.reviews[0].weights.investor_portfolio,3);assert.equal(feedback.current_weights.investor_portfolio,0);assert.equal(feedback.reviews[0].rating,'good');assert.equal(feedback.reviews[0].review_status,'needs_confirmation');
  await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true,'Mobile page must not overflow.');
  await page.reload();await page.waitForSelector('.card');assert.equal(await page.locator('#export-feedback').innerText(),'Download feedback (0)','Feedback must not be retained across reloads.');
  assert.deepEqual(errors,[]);assert.deepEqual(network,[]);
  console.log(JSON.stringify({paths:91434,targets:311,initialLoadMs:loadMs,checks:'passed'}));
 } finally {await browser.close();fs.rmSync(temp,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1;});
