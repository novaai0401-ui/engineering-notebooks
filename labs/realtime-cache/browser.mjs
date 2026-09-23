import {chromium,firefox,webkit} from '../study-coach/frontend/node_modules/playwright/index.mjs';
import {fileURLToPath} from 'node:url';
import fs from 'node:fs';
const checks=[];
for(const [engine,kind] of Object.entries({chromium,firefox,webkit})){
 const browser=await kind.launch();
 try{
  for(const width of [1280,390]){
   console.log('Start '+engine+' '+width);
   const context=await browser.newContext({viewport:{width,height:900}});const page=await context.newPage();
   await page.goto('http://127.0.0.1:8105/');
   await page.getByLabel('Learner').fill('bob');await page.getByLabel('Password').fill(process.env.EVENT_PASSWORD);
   await page.getByRole('button',{name:'Sign in',exact:true}).focus();await page.keyboard.press('Enter');
   await page.getByRole('button',{name:'Connect SSE',exact:true}).click();
   const text=`browser-${engine}-${width}`;await page.getByLabel('Message',{exact:true}).fill(text);await page.getByRole('button',{name:'Publish',exact:true}).click();
   await page.getByRole('listitem').filter({hasText:text}).waitFor();
   await page.getByRole('button',{name:'Connect WebSocket',exact:true}).click();
   await page.getByRole('status').filter({hasText:'WebSocket connected'}).waitFor();
   await page.getByLabel('Message',{exact:true}).fill(text+'-ws');await page.getByRole('button',{name:'Publish',exact:true}).click();
   await page.getByRole('listitem').filter({hasText:text+'-ws'}).waitFor();
   console.log('Delivered '+engine+' '+width);
   await page.addScriptTag({path:fileURLToPath(new URL('../study-coach/frontend/node_modules/axe-core/axe.min.js',import.meta.url))});
   const violations=(await page.evaluate(async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}}))).violations;
   if(violations.length)throw Error(JSON.stringify(violations));
   if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2))throw Error('Horizontal overflow');
   await page.getByRole('button',{name:'Sign out',exact:true}).focus();await page.keyboard.press('Enter');
   await page.getByLabel('Learner').waitFor();
   checks.push({engine,width,passed:true,journey:'Keyboard login/logout, SSE and WebSocket delivery, axe scan and no horizontal overflow'});
   console.log('Passed '+engine+' '+width);
   await context.close();
  }
 }finally{await browser.close();}
}
fs.writeFileSync(new URL('browser-report.json',import.meta.url),JSON.stringify({checks,limitations:'Automated desktop engine emulation, including narrow viewport; no physical Safari/iOS or manual screen-reader audit.'},null,2));console.log(JSON.stringify({passed:checks.length}));
