import {chromium} from './labs/study-coach/frontend/node_modules/playwright/index.mjs';
import fs from 'node:fs';import path from 'node:path';import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));const browser=await chromium.launch();const checks=[];
try{
 for(const width of [1280,390]){
  const page=await browser.newPage({viewport:{width,height:900}});
  for(const name of fs.readdirSync(root).filter(x=>/^\d\d-.*\.html$/.test(x)||['index.html','START-HERE.html','VALIDATION.html','STUDY-ON-ANY-DEVICE.html','COMPLETION-AUDIT.html'].includes(x))){
   await page.goto(pathToFileURL(path.join(root,name)).href);
   const result=await page.evaluate(()=>({title:document.querySelector('h1')?.textContent,overflow:document.documentElement.scrollWidth>innerWidth+2,text:document.querySelector('main')?.textContent?.length||0}));
   if(!result.title||result.text<300||result.overflow)throw Error(JSON.stringify({name,width,...result}));
   checks.push({page:name,width,passed:true});
   if(['index.html','29-databases-for-fullstack-and-ai.html','30-rag-patterns-and-user-defined-flows.html'].includes(name)){
    fs.mkdirSync(path.join(root,'previews'),{recursive:true});await page.screenshot({path:path.join(root,'previews',name.replace('.html','')+'-'+width+'.png')});
   }
  }
  await page.close();
 }
 fs.writeFileSync(path.join(root,'reading-layout-report.json'),JSON.stringify({checks},null,2));console.log(JSON.stringify({layouts:checks.length,passed:true}));
}finally{await browser.close();}
