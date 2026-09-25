import {chromium} from './labs/study-coach/frontend/node_modules/playwright/index.mjs';
import fs from 'node:fs';import path from 'node:path';import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));const browser=await chromium.launch();
const report={scope:'Automated WCAG 2 A/AA and 2.1 A/AA axe checks at desktop and mobile widths. Not physical-device, screen-reader or full manual keyboard certification.',checks:[]};
try{
 for(const width of [1280,390]){
  const page=await browser.newPage({viewport:{width,height:900}});
  for(const name of fs.readdirSync(root).filter(x=>/^\d\d-.*\.html$/.test(x)||['index.html','START-HERE.html','VALIDATION.html','STUDY-ON-ANY-DEVICE.html','COMPLETION-AUDIT.html'].includes(x))){
   await page.goto(pathToFileURL(path.join(root,name)).href);
   await page.addScriptTag({path:path.join(root,'labs/study-coach/frontend/node_modules/axe-core/axe.min.js')});
   const result=await page.evaluate(async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}});return {violations:r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})),incomplete:r.incomplete.map(v=>({id:v.id,count:v.nodes.length}))};});
   const overflowIndex=await page.locator('pre').evaluateAll(nodes=>nodes.findIndex(n=>n.scrollWidth>n.clientWidth+2));
   if(overflowIndex>=0){
    const block=page.locator('pre').nth(overflowIndex);await block.focus();
    await page.keyboard.press('ArrowRight');await page.waitForTimeout(120);
    const moved=await block.evaluate(n=>n.scrollLeft>0);if(!moved)throw Error('Keyboard could not scroll code: '+name);
    await page.keyboard.press('Tab');const trapped=await block.evaluate(n=>document.activeElement===n);if(trapped)throw Error('Code focus trap: '+name);
    result.keyboardScrollableCode='ArrowRight scrolled; Tab left the first overflowing code region';
   }
   report.checks.push({page:name,width,...result});
   fs.writeFileSync(path.join(root,'reading-accessibility-report.json'),JSON.stringify(report,null,2));
  }
  await page.close();console.log('Completed width '+width);
 }
 report.passed=report.checks.every(c=>c.violations.length===0);fs.writeFileSync(path.join(root,'reading-accessibility-report.json'),JSON.stringify(report,null,2));
 console.log(JSON.stringify({checks:report.checks.length,passed:report.passed}));if(!report.passed)process.exitCode=1;
}finally{await browser.close();}
