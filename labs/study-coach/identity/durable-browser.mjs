import {chromium} from '../frontend/node_modules/playwright/index.mjs';
import fs from 'node:fs';import path from 'node:path';
const run=process.env.DURABLE_RUN;const browser=await chromium.launch();const sessions=[];
async function signal(name){const until=Date.now()+120000;while(!fs.existsSync(path.join(run,name))){if(Date.now()>until)throw Error('Phase deadline '+name);await new Promise(r=>setTimeout(r,200));}}
try{
 for(const port of [8091,8096]){
  const context=await browser.newContext();const page=await context.newPage();const base=`http://127.0.0.1:${port}`;
  await page.goto(base);await page.getByRole('link',{name:'Sign in with identity provider'}).click();
  await page.locator('#username').fill('alice');await page.locator('#password').fill(process.env.COACH_IDENTITY_PASSWORD);await page.locator('#kc-login').click();
  await page.getByLabel('Study question').waitFor({timeout:90000});
  if((await context.request.get(base+'/api/me')).status()!==200)throw Error('Login failed');
  sessions.push({context,base});
 }
 fs.writeFileSync(path.join(run,'ready'),'ready');await signal('phase1');
 if((await sessions[0].context.request.get(sessions[0].base+'/api/me')).status()!==401)throw Error('Reachable Spring session survived logout');
 if((await sessions[1].context.request.get(sessions[1].base+'/api/me')).status()!==200)throw Error('Blocked Spring session did not remain active before delivery');
 fs.writeFileSync(path.join(run,'phase1done'),'observed');await signal('phase2');
 for(const {context,base} of sessions)if((await context.request.get(base+'/api/me')).status()!==401)throw Error('Spring session survived recovered logout delivery');
 fs.writeFileSync(path.join(run,'browser-result.json'),JSON.stringify({passed:true,checks:['Real OIDC logins on both Spring instances','Reachable session revoked while network-isolated logout receiver retained its session','Recovered durable delivery revoked the retained real Spring session']}));
}finally{await browser.close();}
