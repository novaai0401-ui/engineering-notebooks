import {chromium} from 'playwright';
import fs from 'node:fs';
const browser=await chromium.launch();const checks=[];
async function login(user,password){
 const context=await browser.newContext();const page=await context.newPage();await page.goto('http://127.0.0.1:8091/');
 await page.getByRole('link',{name:'Sign in with identity provider'}).click();
 const url=new URL(page.url());
 if(url.searchParams.get('code_challenge_method')!=='S256')throw Error('PKCE missing');
 await page.locator('#username').fill(user);await page.locator('#password').fill(password);await page.locator('#kc-login').click();
 return {context,page};
}
try{
 const {context,page}=await login('alice',process.env.COACH_IDENTITY_PASSWORD);
 await page.getByLabel('Study question').waitFor();
 let response=await context.request.get('http://127.0.0.1:8091/api/me');if(response.status()!==200)throw Error('login failed');
 response=await context.request.get('http://127.0.0.1:8091/api/admin/status');if(response.status()!==403)throw Error('learner admin access');
 response=await context.request.post('http://127.0.0.1:8091/api/jobs',{data:{question:'checkpoint'},headers:{'Idempotency-Key':'no-csrf-123'}});if(response.status()!==403)throw Error('missing csrf accepted');
 checks.push('Real authorization-code login used S256 PKCE, session cookie, learner role, and CSRF enforcement');
 await page.getByRole('button',{name:'Sign out of identity session',exact:true}).click();
 await page.waitForURL('http://127.0.0.1:8091/');
 response=await context.request.get('http://127.0.0.1:8091/api/me');if(response.status()!==401)throw Error('logout retained session');
 checks.push('RP-initiated logout invalidated application session');await context.close();
 const admin=await login('coachadmin',process.env.COACH_IDENTITY_ADMIN_PASSWORD);await admin.page.getByLabel('Study question').waitFor();
 response=await admin.context.request.get('http://127.0.0.1:8091/api/admin/status');if(response.status()!==200)throw Error('admin denied');
 response=await admin.context.request.get('http://127.0.0.1:8091/actuator/prometheus');if(response.status()!==200 || !(await response.text()).includes('jvm_memory'))throw Error('metrics unavailable');
 checks.push('Mapped administrator role permits protected metrics and administration');await admin.context.close();
 const tokenResponse=await fetch('http://127.0.0.1:8094/realms/master/protocol/openid-connect/token',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({grant_type:'password',client_id:'admin-cli',username:process.env.KC_BOOTSTRAP_ADMIN_USERNAME,password:process.env.KC_BOOTSTRAP_ADMIN_PASSWORD})});
 if(!tokenResponse.ok)throw Error('administration authentication failed');
 const headers={Authorization:'Bearer '+(await tokenResponse.json()).access_token,'Content-Type':'application/json'};
 const clients=await(await fetch('http://127.0.0.1:8094/admin/realms/study/clients?clientId=study-coach',{headers})).json();
 const client=clients[0];client.attributes={...client.attributes,'backchannel.logout.url':'http://127.0.0.1:8091/logout/connect/back-channel/coach','backchannel.logout.session.required':'true'};
 const configured=await fetch('http://127.0.0.1:8094/admin/realms/study/clients/'+client.id,{method:'PUT',headers,body:JSON.stringify(client)});if(!configured.ok)throw Error('back-channel configuration failed');
 const aliceUsers=await(await fetch('http://127.0.0.1:8094/admin/realms/study/users?username=alice&exact=true',{headers})).json();
 const rotated='Rotated-'+crypto.randomUUID();
 const reset=await fetch('http://127.0.0.1:8094/admin/realms/study/users/'+aliceUsers[0].id+'/reset-password',{method:'PUT',headers,body:JSON.stringify({type:'password',temporary:false,value:rotated})});if(!reset.ok)throw Error('password reset failed');
 const old=await login('alice',process.env.COACH_IDENTITY_PASSWORD);await old.page.locator('#password').waitFor();
 if((await old.context.request.get('http://127.0.0.1:8091/api/me')).status()!==401)throw Error('old password still works');await old.context.close();
 const fresh=await login('alice',rotated);await fresh.page.getByLabel('Study question').waitFor();await fresh.context.close();
 checks.push('Password rotation rejected the old password and accepted the new password in fresh browser sessions');
 const users=await(await fetch('http://127.0.0.1:8094/admin/realms/study/users?username=bob&exact=true',{headers})).json();
 const bob=await login('bob',process.env.COACH_IDENTITY_PASSWORD);await bob.page.getByLabel('Study question').waitFor();
 const disable=await fetch('http://127.0.0.1:8094/admin/realms/study/users/'+users[0].id,{method:'PUT',headers,body:JSON.stringify({enabled:false})});if(!disable.ok)throw Error('disable failed');
 const logout=await fetch('http://127.0.0.1:8094/admin/realms/study/users/'+users[0].id+'/logout',{method:'POST',headers});if(!logout.ok)throw Error('provider logout failed');
 // Back-channel session invalidation requires the matching realm client attribute.
 for(let i=0;i<30;i++){response=await bob.context.request.get('http://127.0.0.1:8091/api/me');if(response.status()===401)break;await new Promise(r=>setTimeout(r,500));}
 if(response.status()!==401)throw Error('application session not revoked by provider logout');
 checks.push('Disabling an account and provider back-channel logout invalidated its existing application session');await bob.context.close();
 fs.writeFileSync(new URL('../identity-browser-report.json',import.meta.url),JSON.stringify({passed:checks},null,2));
}finally{await browser.close();}
