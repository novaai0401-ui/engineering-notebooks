"""Real Keycloak -> encrypted durable relay -> real Spring session revocation after link outage."""
import argparse,base64,json,os,re,secrets,socket,sqlite3,subprocess,sys,threading,time
parser=argparse.ArgumentParser();parser.add_argument("--crash",action="store_true");parser.add_argument("--expire",action="store_true");args=parser.parse_args()
if args.expire and not args.crash:parser.error("--expire requires --crash")
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import httpx,jwt
from cryptography.hazmat.primitives import serialization
from identity.admin import IdentityAdmin
ROOT=Path(__file__).resolve().parent;RUNTIME=ROOT.parents[1]/'.runtime'
source=max([p for p in RUNTIME.glob('identity-cluster-*') if (p/'private-test-settings.json').exists()],key=lambda p:p.stat().st_mtime)
RUN=RUNTIME/('durable-spring-'+secrets.token_hex(4));RUN.mkdir()
env=dict(os.environ,**json.loads((source/'private-test-settings.json').read_text(encoding='utf-8')));env['DURABLE_RUN']=str(RUN)
props=subprocess.run(['java','-XshowSettings:properties','-version'],capture_output=True,text=True,check=True).stderr
java=Path(re.search(r'java.home\s*=\s*(.+)',props).group(1).strip())/'bin/java.exe'
processes=[];logs=[];proxy=None;blocked=True;applications={}
for port in (8091,8094,8096,8108,18110):
 with socket.socket() as probe:probe.bind(('127.0.0.1',port))
def start(args,cwd,name,extra=None):
 stream=(RUN/(name+'.log')).open('w');logs.append(stream)
 p=subprocess.Popen(list(map(str,args)),cwd=cwd,env=dict(env,**(extra or {})),stdout=stream,stderr=stream,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));processes.append(p);return p
def stop(p):
 if p.poll() is None:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True);p.wait(timeout=20)
def wait(predicate,seconds=90):
 until=time.monotonic()+seconds
 while not predicate():
  if time.monotonic()>until:raise TimeoutError('Condition deadline')
  time.sleep(.25)
def ready(url,p):
 def check():
  if p.poll() is not None:raise RuntimeError('Owned service exited')
  try:return httpx.get(url,timeout=2).status_code==200
  except httpx.HTTPError:return False
 wait(check,360)
class Proxy(BaseHTTPRequestHandler):
 def do_POST(self):
  if blocked:self.send_error(503);return
  body=self.rfile.read(int(self.headers['Content-Length']))
  try:
   response=httpx.post('http://127.0.0.1:8096/logout/connect/back-channel/coach',content=body,headers={'Content-Type':'application/x-www-form-urlencoded'},timeout=10)
   self.send_response(response.status_code);self.end_headers()
  except httpx.HTTPError:self.send_error(503)
 def log_message(self,*args):pass
try:
 kc=RUNTIME/'keycloak-26.7.4';p=start([kc/'bin/kc.bat','start-dev'],kc,'keycloak');ready('http://127.0.0.1:8094/realms/study/.well-known/openid-configuration',p)
 # Retained test realms contain old browser sessions. Clear those before the
 # relay/new application sessions exist, so this experiment has two fresh SIDs.
 cleanup=IdentityAdmin('http://127.0.0.1:8094',env['KC_BOOTSTRAP_ADMIN_USERNAME'],env['KC_BOOTSTRAP_ADMIN_PASSWORD'])
 try:cleanup.http.post('/admin/realms/study/users/'+cleanup.user('alice')['id']+'/logout').raise_for_status()
 finally:cleanup.close()
 for port in (8091,8096):
  p=start([java,'-Xmx192m','-jar',ROOT/'java/target/study-coach-1.0.0.jar'],ROOT/'java',str(port),{'SERVER_PORT':str(port),'COACH_DB':'jdbc:h2:file:'+str(source/('app-'+str(port))).replace('\\','/')});ready(f'http://127.0.0.1:{port}/health',p);applications[port]=p
 keys=httpx.get('http://127.0.0.1:8094/realms/study/protocol/openid-connect/certs',timeout=10).json()['keys'];key=next(k for k in keys if k.get('alg')=='RS256' and k.get('use')=='sig')
 public=jwt.PyJWK.from_dict(key).key.public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo);(RUN/'public.pem').write_bytes(public)
 relay_env={'RELAY_DB':str(RUN/'journal.db'),'RELAY_KEY':base64.urlsafe_b64encode(os.urandom(32)).decode(),'RELAY_PUBLIC_KEY':str(RUN/'public.pem'),'RELAY_ISSUER':'http://127.0.0.1:8094/realms/study','RELAY_AUDIENCE':'study-coach','RELAY_PORT':'8108','RELAY_TARGETS':json.dumps(['http://127.0.0.1:8091/logout/connect/back-channel/coach','http://127.0.0.1:18110/logout'])}
 proxy=ThreadingHTTPServer(('127.0.0.1',18110),Proxy);threading.Thread(target=proxy.serve_forever,daemon=True).start()
 def relay(name):
  p=start([sys.executable,ROOT/'identity/durable_relay.py'],ROOT,name,relay_env);ready('http://127.0.0.1:8108/health',p);return p
 p=relay('relay-before');browser=start(['node',ROOT/'identity/durable-browser.mjs'],ROOT,'browser')
 wait(lambda:(RUN/'ready').exists() or browser.poll() is not None,240);assert (RUN/'ready').exists(),'Browser login failed'
 admin=IdentityAdmin('http://127.0.0.1:8094',env['KC_BOOTSTRAP_ADMIN_USERNAME'],env['KC_BOOTSTRAP_ADMIN_PASSWORD'])
 try:admin.http.post('/admin/realms/study/users/'+admin.user('alice')['id']+'/logout').raise_for_status()
 finally:admin.close()
 def health():return httpx.get('http://127.0.0.1:8108/health',timeout=3).json()
 wait(lambda:health()['pending']==2 and health()['delivered']==2)
 (RUN/'phase1').write_text('check');wait(lambda:(RUN/'phase1done').exists() or browser.poll() is not None)
 assert (RUN/'phase1done').exists(),'Browser phase-one assertion failed'
 before=health();stop(p);p=relay('relay-after');assert health()['pending']>=1
 if args.crash:
  stop(applications[8096])
  recovered=start([java,'-Xmx192m','-jar',ROOT/'java/target/study-coach-1.0.0.jar'],ROOT/'java','8096-recovered',{'SERVER_PORT':'8096','COACH_DB':'jdbc:h2:file:'+str(source/'app-8096').replace('\\','/')})
  ready('http://127.0.0.1:8096/health',recovered)
  (RUN/'phase2').write_text('check');assert browser.wait(timeout=120)==0
  assert health()['pending']>=1,'Recovery assertion must precede delayed delivery'
 if args.expire:
  with sqlite3.connect(RUN/'journal.db') as journal:journal.execute('UPDATE events SET expires=?',(time.time()-1,))
  wait(lambda:health()['pending']==0);assert health()['expired']==2
 blocked=False;wait(lambda:health()['pending']==0);assert health()['expired']==(2 if args.expire else 0)
 (RUN/'phase2').write_text('check');assert browser.wait(timeout=120)==0
 observed=json.loads((RUN/'browser-result.json').read_text());report={'passed':observed['checks']+['Keycloak RS256 logout verified before journal commit','Relay hard restart preserved pending real Spring deliveries'],'before_restart':before,'after_recovery':health(),'limitations':'Real Keycloak and Spring instances; a 503 proxy isolates the second logout endpoint while its application session remains live. Not an application-process crash, shared-session store, expired-token reconciliation, key rotation or zero-downtime secret cutover.'}
 if args.crash:
  report['passed']=observed['checks'][:2]+['Actual second Spring process killed and restarted; old browser cookie rejected before delayed logout delivery','Relay hard restart retained pending deliveries, delivered after connectivity recovery']
  report['limitations']='Current Spring profile uses in-memory sessions: process death loses them and old cookies fail closed. Does not demonstrate shared durable session recovery, expired-token reconciliation, zero-downtime rotation or historical root-cause proof.'
 if args.expire:
  report['passed'][-1]='Injected delivery-deadline expiry marked two offline deliveries expired; original cookie had already been rejected on restart before expiry injection'
  report['limitations']='Forced journal deadline expiry and actual process restart. In-memory sessions fail closed on restart; this does not reconcile a shared persistent session store or replay an expired JWT. No claim of production outage certification.'
 (ROOT/('durable-spring-expiry-report.json' if args.expire else 'durable-spring-crash-report.json' if args.crash else 'durable-spring-report.json')).write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
except Exception as error:
 (ROOT/'durable-spring-failure-report.json').write_text(json.dumps({'status':'failed','error':type(error).__name__,'phase1_observed':(RUN/'phase1done').exists(),'limitations':'No successful integration claimed for incomplete phases; inspect private runtime logs locally.'},indent=2),encoding='utf-8')
 raise
finally:
 for p in reversed(processes):stop(p)
 if proxy:proxy.shutdown();proxy.server_close()
 for log in logs:log.close()
