import {chromium} from '@playwright/test';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {resolve,dirname} from 'node:path';
import {mkdir,writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../../..');
await mkdir(resolve(root,'previews'),{recursive:true});
const browser=await chromium.launch();const page=await browser.newPage();
const results=[];
try{
 for(const width of [1280,390]){
  await page.setViewportSize({width,height:900});
  for(const name of ['index','07-durable-agents','13-patterns-workshop']){
   await page.goto(pathToFileURL(resolve(root,name+'.html')).href);
   assert.equal(await page.locator('h1').count(),1);
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);
   assert.equal(overflow,false,`${name} overflows at ${width}`);
   await page.screenshot({path:resolve(root,'previews',`${name}-${width}.png`)});
   results.push({page:name,width,horizontalOverflow:false});
  }
 }
 await writeFile(resolve(root,'reading-layout-report.json'),JSON.stringify(results,null,2));
 console.log('Six desktop/mobile reading layout checks passed');
}finally{await browser.close();}
