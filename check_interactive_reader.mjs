import {chromium} from './labs/study-coach/frontend/node_modules/playwright/index.mjs';
import fs from 'node:fs';import path from 'node:path';import {pathToFileURL} from 'node:url';
const browser=await chromium.launch(),root=process.cwd(),checks=[];
function assert(value,message){if(!value)throw Error(message)}
try{
 for(const width of [390,1280]){
  const page=await browser.newPage({viewport:{width,height:900}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  const open=async name=>page.goto(pathToFileURL(path.join(root,name)).href);
  await open('index.html');await page.getByPlaceholder('Try Java, RAG, database…').fill('database');assert(await page.locator('.card:visible').count()>0 && await page.locator('.card:visible').evaluateAll(nodes=>nodes.every(n=>n.textContent.toLowerCase().includes('database'))),'Library filter');
  await open('09-python-ai-depth.html');assert((await page.locator('#gradient-result').textContent()).includes('1.0600'),'Gradient default');await page.locator('#rate').fill('0.6');assert((await page.locator('#gradient-result').textContent()).includes('worse'),'Gradient overshoot');
  assert(await page.locator('.section-finish').first().locator('ol li').count()===7,'Seven teaching criteria');assert(await page.locator('.related-sections').first().isHidden(),'Suggestions initially hidden');await page.locator('#prediction').fill('My own derivation');await page.locator('.mark-read').first().click();assert(await page.locator('.related-sections').first().isVisible(),'Completion reveals related sections');assert(await page.locator('.related-sections').first().locator('a').count()>0,'Related destinations');await page.reload();assert(await page.locator('#prediction').inputValue()==='My own derivation','Note persistence');assert(await page.locator('.mark-read').first().getAttribute('aria-pressed')==='true','Reading progress persistence');
  await page.locator('#focus-reader').click();assert(await page.locator('nav').isHidden(),'Focus mode');await page.locator('#focus-reader').click();
  await page.locator('#chapter-search').fill('gradient');assert(await page.locator('nav > ul > li:visible').count()>0,'Lesson search');await page.locator('#chapter-search').fill('');
  for(const theme of ['violet','ocean','night']){
   await page.locator('#palette').selectOption(theme);await page.addScriptTag({path:path.join(root,'labs/study-coach/frontend/node_modules/axe-core/axe.min.js')});
   const violations=await page.evaluate(async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}})).violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)})));
   assert(!violations.length,JSON.stringify({width,theme,violations}));checks.push({width,theme,axe:'passed'});
  }
  await page.locator('#palette').selectOption('violet');await page.locator('#text-size').selectOption('22');assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2),'Large-text overflow');
  await page.screenshot({path:path.join(root,`previews/interactive-reader-${width}.png`)});
  await open('06-algorithms-and-design-patterns.html');await page.locator('#target-value').fill('14');assert((await page.locator('.studio output').textContent()).includes('no match'),'Binary search sentinel');
  await open('07-durable-agents.html');for(let i=0;i<3;i++)await page.locator('#next-step').click();assert((await page.locator('#trace-output').textContent()).includes('original receipt'),'Deduplicated retry');await page.locator('#dedupe').uncheck();assert((await page.locator('#trace-output').textContent()).includes('charges = 2'),'Duplicate effect');await page.locator('#reset-step').click();assert(!(await page.locator('#trace-output').textContent()).includes('Worker crashes'),'Reset');
  await open('32-load-balancing-from-playground-to-production.html');assert((await page.locator('.studio output').textContent()).includes('20.0'),'Little law calculation');assert(!errors.length,JSON.stringify(errors));
  checks.push({width,interactions:'passed',scriptErrors:errors});await page.close();
 }
 fs.writeFileSync('interactive-reader-report.json',JSON.stringify({passed:true,checks,scope:'Chromium desktop/mobile emulation, three palettes, numerical traces, filtering and browser-local persistence. Not physical-device testing.'},null,2));console.log('Interactive reader checks passed');
}finally{await browser.close()}
