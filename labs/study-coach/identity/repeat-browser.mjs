import {chromium} from '../frontend/node_modules/playwright/index.mjs';
import fs from 'node:fs';
const browser=await chromium.launch();const cases=[];
try{
 for(let round=0;round<5;round++)for(const port of [8091,8096]){
  const context=await browser.newContext();const page=await context.newPage();const base=`http://127.0.0.1:${port}`;const started=Date.now();
  try{
   const probes=await Promise.all(Array.from({length:4},()=>context.request.get(base+'/api/me')));
   if(probes.some(r=>r.status()!==401||/JSESSIONID=/i.test(r.headers()['set-cookie']||'')))throw Error('Anonymous API probe created a competing session or was not denied');
   await page.goto(base+'/');await page.getByRole('link',{name:'Sign in with identity provider'}).click();
   if(new URL(page.url()).searchParams.get('code_challenge_method')!=='S256')throw Error('PKCE absent');
   await page.locator('#username').fill('alice');await page.locator('#password').fill(process.env.COACH_IDENTITY_PASSWORD);await page.locator('#kc-login').click();
   await Promise.race([page.getByLabel('Study question').waitFor({timeout:45000}),page.getByText('Invalid credentials',{exact:true}).waitFor({timeout:45000}).then(()=>{throw Error('OIDC callback: Invalid credentials');})]);
   if((await context.request.get(base+'/api/me')).status()!==200)throw Error('Protected endpoint denied');
   cases.push({round,port,passed:true,anonymous_api_probes:4,anonymous_api_session_cookie:false,milliseconds:Date.now()-started});
  }catch(error){cases.push({round,port,passed:false,error:String(error).slice(0,300),milliseconds:Date.now()-started});}
  finally{await context.close();}
  fs.writeFileSync(process.env.IDENTITY_TEST_OUTPUT,JSON.stringify({cases},null,2));
 }
}finally{await browser.close();}
if(cases.some(c=>!c.passed))process.exitCode=1;
