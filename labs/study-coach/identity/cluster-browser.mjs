import {chromium} from '../frontend/node_modules/playwright/index.mjs';
const browser=await chromium.launch();const sessions=[];
try{
 for(const port of [8091,8096]){
  const context=await browser.newContext();const page=await context.newPage();const base=`http://127.0.0.1:${port}`;
  await page.goto(base+'/');await page.getByRole('link',{name:'Sign in with identity provider'}).click();
  if(new URL(page.url()).searchParams.get('code_challenge_method')!=='S256')throw Error('PKCE absent');
  await page.locator('#username').fill('alice');await page.locator('#password').fill(process.env.COACH_IDENTITY_PASSWORD);await page.locator('#kc-login').click();
  try{await Promise.race([page.getByLabel('Study question').waitFor({timeout:90000}),page.getByText('Invalid credentials',{exact:true}).waitFor({timeout:90000}).then(()=>{throw Error('OIDC callback rejected credentials');})]);}
  catch(error){const u=new URL(page.url());console.error('Login did not reach the application at '+u.origin+u.pathname+'; page text: '+(await page.locator('body').innerText()).slice(0,1600));throw error;}
  if((await context.request.get(base+'/api/me')).status()!==200)throw Error('Fresh login failed');
  sessions.push({context,base});
 }
 if(process.argv[2]==='revoke'){
  const response=await fetch('http://127.0.0.1:8094/realms/master/protocol/openid-connect/token',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({grant_type:'password',client_id:'admin-cli',username:process.env.KC_BOOTSTRAP_ADMIN_USERNAME,password:process.env.KC_BOOTSTRAP_ADMIN_PASSWORD})});
  if(!response.ok)throw Error('Admin token failed');const headers={Authorization:'Bearer '+(await response.json()).access_token};
  const lookup=await fetch('http://127.0.0.1:8094/admin/realms/study/users?username=alice&exact=true',{headers});if(!lookup.ok)throw Error('Lookup failed');const users=await lookup.json();
  const logout=await fetch('http://127.0.0.1:8094/admin/realms/study/users/'+users[0].id+'/logout',{method:'POST',headers});if(!logout.ok)throw Error('Logout failed');
  for(const {context,base} of sessions){
   let status;for(let attempt=0;attempt<30;attempt++){status=(await context.request.get(base+'/api/me')).status();if(status===401)break;await new Promise(r=>setTimeout(r,300));}
   if(status!==401)throw Error('Session survived provider revocation at '+base);
  }
 }
 console.log(process.argv[2]+': both instances passed');
}finally{await browser.close();}
