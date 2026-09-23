"""Real Keycloak + Spring OIDC browser integration, isolated runtime state."""
import json,os,re,secrets,shutil,socket,subprocess,time
from pathlib import Path
import httpx
from identity.admin import IdentityAdmin
ROOT=Path(__file__).resolve().parent;RUNTIME=ROOT.parents[1]/'.runtime';KC=RUNTIME/'keycloak-26.7.4'
RUN=RUNTIME/('identity-'+secrets.token_hex(4));RUN.mkdir(parents=True)
env=os.environ.copy()
for key in ('COACH_PASSWORD','COACH_SERVICE_TOKEN','COACH_OIDC_SECRET','COACH_IDENTITY_PASSWORD','COACH_IDENTITY_ADMIN_PASSWORD','KC_BOOTSTRAP_ADMIN_PASSWORD'):env[key]=secrets.token_urlsafe(28)
env.update(KC_BOOTSTRAP_ADMIN_USERNAME='classroom-bootstrap',KC_HTTP_PORT='8094',KC_HTTP_HOST='127.0.0.1',KC_DB='dev-file',KC_DB_URL='jdbc:h2:file:'+str(RUN/'keycloak-db').replace('\\','/'),SPRING_PROFILES_ACTIVE='oidc',COACH_WORKER_ENABLED='false',COACH_DB='jdbc:h2:file:'+str(RUN/'coach').replace('\\','/'))
flags=getattr(subprocess,'CREATE_NO_WINDOW',0);processes=[];logs=[]
env['KC_DB_URL']+=';NON_KEYWORDS=VALUE'
env['JAVA_OPTS_KC_HEAP']='-Xms64m -Xmx384m'
def start(args,cwd,name):
 log=(RUN/(name+'.log')).open('w');logs.append(log);p=subprocess.Popen([str(a) for a in args],cwd=cwd,env=env,stdout=log,stderr=log,creationflags=flags);processes.append(p);return p
def ready(url,p):
 until=time.monotonic()+480
 while time.monotonic()<until:
  if p.poll() is not None:raise RuntimeError(f'Process exited; logs {RUN}')
  try:
   if httpx.get(url,timeout=2).status_code==200:return
  except httpx.HTTPError:pass
  time.sleep(.5)
 raise TimeoutError(url)
for port in (8091,8094):
 with socket.socket() as probe:probe.bind(('127.0.0.1',port))
try:
 template=(ROOT/'identity/realm-template.json').read_text()
 for key,value in env.items():template=template.replace('${'+key+'}',value)
 settings=json.loads(template)
 settings['clients'][0]['attributes'].update({'backchannel.logout.url':'http://127.0.0.1:8091/logout/connect/back-channel/coach','backchannel.logout.session.required':'true'})
 template=json.dumps(settings)
 realm=RUN/'realm.json';realm.write_text(template)
 # Explicit import into this run's private database, then launch that database.
 importer=start([KC/'bin/kc.bat','import','--file',realm],KC,'import')
 if importer.wait(timeout=480)!=0:raise RuntimeError(f'Identity import failed; inspect {RUN}')
 kc=start([KC/'bin/kc.bat','start-dev'],KC,'keycloak');ready('http://127.0.0.1:8094/realms/study/.well-known/openid-configuration',kc)
 props=subprocess.run(['java','-XshowSettings:properties','-version'],capture_output=True,text=True,check=True).stderr
 java=Path(re.search(r'java.home\s*=\s*(.+)',props).group(1).strip())/'bin/java.exe'
 shutil.copyfile(ROOT/'java/target/study-coach-1.0.0.jar',RUN/'app.jar')
 app=start([java,'-Xmx256m','-jar',RUN/'app.jar'],ROOT/'java','app');ready('http://127.0.0.1:8091/health',app)
 # Resolve Playwright from the existing frontend dependency installation.
 script=(ROOT/'identity/browser.mjs').read_text().replace("from 'playwright'","from '../frontend/node_modules/playwright/index.mjs'")
 runner=ROOT/'identity/browser-run.mjs';runner.write_text(script)
 result=subprocess.run(['node',str(runner)],env=env,capture_output=True,text=True,timeout=180)
 (RUN/'browser.log').write_text(result.stdout+result.stderr);result.check_returncode()
 admin=IdentityAdmin('http://127.0.0.1:8094',env['KC_BOOTSTRAP_ADMIN_USERNAME'],env['KC_BOOTSTRAP_ADMIN_PASSWORD'])
 try:
  admin.reset_password('bob',secrets.token_urlsafe(28));admin.disable('bob');assert admin.user('bob')['enabled'] is False
  changed=admin.rotate_client_secret();assert changed and changed!=env['COACH_OIDC_SECRET']
 finally:admin.close()
 report=json.loads((ROOT/'identity-browser-report.json').read_text());report['passed']+=['Identity administration changed password, disabled account and rotated confidential client secret']
 report['limitations']='Local HTTP dev realm with one application instance. Password re-login and single-instance back-channel revocation tested. Client-secret rotation state verified, but application cutover to the new secret and clustered session revocation are not tested. Use TLS, managed storage and shared session design for public deployment.'
 (ROOT/'identity-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
finally:
 for p in reversed(processes):
  if p.poll() is None:
   subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True);p.wait(timeout=15)
 for f in logs:f.close()
