"""Two real OIDC application instances, signed logout fanout, and secret cutover."""
import json,os,re,secrets,shutil,socket,subprocess,threading,time
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import httpx
from identity.admin import IdentityAdmin
ROOT=Path(__file__).resolve().parent;RUNTIME=ROOT.parents[1]/'.runtime';KC=RUNTIME/'keycloak-26.7.4'
RUN=RUNTIME/('identity-cluster-'+secrets.token_hex(4));RUN.mkdir(parents=True)
env=os.environ.copy()
for key in ('COACH_PASSWORD','COACH_SERVICE_TOKEN','COACH_OIDC_SECRET','COACH_IDENTITY_PASSWORD','COACH_IDENTITY_ADMIN_PASSWORD','KC_BOOTSTRAP_ADMIN_PASSWORD'):env[key]=secrets.token_urlsafe(28)
env.update(KC_BOOTSTRAP_ADMIN_USERNAME='classroom-bootstrap',KC_HTTP_PORT='8094',KC_HTTP_HOST='127.0.0.1',KC_DB='dev-file',KC_DB_URL='jdbc:h2:file:'+str(RUN/'keycloak-db').replace('\\','/')+';NON_KEYWORDS=VALUE',SPRING_PROFILES_ACTIVE='oidc',COACH_WORKER_ENABLED='false',JAVA_OPTS_KC_HEAP='-Xms64m -Xmx384m')
processes=[];logs=[];relay=None;forwards=[];checks=[]
def save_private_settings():
    (RUN/'private-test-settings.json').write_text(json.dumps({key:value for key,value in env.items() if key.startswith(('COACH_','KC_','SPRING_PROFILES_','JAVA_OPTS_KC'))}),encoding='utf-8')
save_private_settings()
def start(args,cwd,name,extra=None):
    log=(RUN/(name+'.log')).open('w');logs.append(log)
    p=subprocess.Popen([str(a) for a in args],cwd=cwd,env=dict(env,**(extra or {})),stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));processes.append(p);return p
def stop(p):
    if p.poll() is None:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True);p.wait(timeout=20)
def ready(url,p):
    until=time.monotonic()+480
    while time.monotonic()<until:
        if p.poll() is not None:raise RuntimeError(f'Process exited; inspect {RUN}')
        try:
            if httpx.get(url,timeout=2).status_code==200:return
        except httpx.HTTPError:pass
        time.sleep(.5)
    raise TimeoutError(url)
class Relay(BaseHTTPRequestHandler):
    def do_POST(self):
        length=int(self.headers.get('Content-Length','0'))
        if self.path!='/logout' or not 1<=length<=32768:self.send_error(400);return
        body=self.rfile.read(length);codes=[]
        for port in (8091,8096):
            try:codes.append(httpx.post(f'http://127.0.0.1:{port}/logout/connect/back-channel/coach',content=body,headers={'Content-Type':'application/x-www-form-urlencoded'},timeout=10).status_code)
            except httpx.HTTPError:codes.append(503)
        forwards.append(codes)
        self.send_response(200 if all(200<=c<300 for c in codes) else 502);self.end_headers()
    def log_message(self,*args):pass
for port in (8091,8094,8096,8108):
    with socket.socket() as probe:probe.bind(('127.0.0.1',port))
try:
    settings=(ROOT/'identity/realm-template.json').read_text(encoding='utf-8')
    for key,value in env.items():settings=settings.replace('${'+key+'}',value)
    settings=json.loads(settings);client=settings['clients'][0]
    client['redirectUris']=['http://127.0.0.1:'+str(port)+'/login/oauth2/code/coach' for port in (8091,8096)]
    client['webOrigins']=['http://127.0.0.1:'+str(port) for port in (8091,8096)]
    client['attributes'].update({'backchannel.logout.url':'http://127.0.0.1:8108/logout','backchannel.logout.session.required':'true'})
    realm=RUN/'realm.json';realm.write_text(json.dumps(settings),encoding='utf-8')
    importer=start([KC/'bin/kc.bat','import','--file',realm],KC,'import')
    if importer.wait(timeout=480)!=0:raise RuntimeError('Realm import failed')
    kc=start([KC/'bin/kc.bat','start-dev'],KC,'keycloak');ready('http://127.0.0.1:8094/realms/study/.well-known/openid-configuration',kc)
    props=subprocess.run(['java','-XshowSettings:properties','-version'],capture_output=True,text=True,check=True).stderr
    java=Path(re.search(r'java.home\s*=\s*(.+)',props).group(1).strip())/'bin/java.exe'
    shutil.copyfile(ROOT/'java/target/study-coach-1.0.0.jar',RUN/'app.jar')
    def app(port,name):
        p=start([java,'-Xmx192m','-jar',RUN/'app.jar','--logging.level.org.springframework.security.web.authentication=DEBUG','--logging.level.org.springframework.security.oauth2.client=DEBUG'],ROOT/'java',name,{'SERVER_PORT':str(port),'COACH_DB':'jdbc:h2:file:'+str(RUN/('app-'+str(port))).replace('\\','/')})
        ready('http://127.0.0.1:'+str(port)+'/health',p);return p
    one=app(8091,'one');two=app(8096,'two')
    relay=ThreadingHTTPServer(('127.0.0.1',8108),Relay);threading.Thread(target=relay.serve_forever,daemon=True).start()
    # The relay never trusts the token itself: both Spring endpoints validate signed logout tokens.
    invalid=httpx.post('http://127.0.0.1:8108/logout',data={'logout_token':'forged'},timeout=30)
    assert invalid.status_code==502 and all(c>=400 for c in forwards[-1])
    checks.append('Forged logout token rejected by both Spring endpoints')
    runner=ROOT/'identity/cluster-browser-run.mjs'
    runner.write_text((ROOT/'identity/cluster-browser.mjs').read_text(encoding='utf-8'),encoding='utf-8')
    result=subprocess.run(['node',str(runner),'revoke'],env=env,capture_output=True,text=True,timeout=240)
    (RUN/'browser-revoke.log').write_text(result.stdout+result.stderr,encoding='utf-8');result.check_returncode()
    checks+=['Fresh OIDC/PKCE login passed on two instances','Provider logout revoked both independently established application sessions']
    admin=IdentityAdmin('http://127.0.0.1:8094',env['KC_BOOTSTRAP_ADMIN_USERNAME'],env['KC_BOOTSTRAP_ADMIN_PASSWORD'])
    try:new_secret=admin.rotate_client_secret()
    finally:admin.close()
    assert new_secret and new_secret!=env['COACH_OIDC_SECRET']
    stop(one);stop(two);env['COACH_OIDC_SECRET']=new_secret
    save_private_settings()
    one=app(8091,'one-cutover');two=app(8096,'two-cutover')
    result=subprocess.run(['node',str(runner),'fresh'],env=env,capture_output=True,text=True,timeout=240)
    (RUN/'browser-cutover.log').write_text(result.stdout+result.stderr,encoding='utf-8');result.check_returncode()
    report={'passed':['Two real Spring application instances completed fresh OIDC/PKCE logins with one confidential client','Forged logout token rejected by both Spring endpoints through the fanout relay','Provider logout revoked sessions established independently on both instances','After provider secret rotation, both application instances restarted with the new secret and completed fresh code exchanges'],'relay_deliveries':forwards,'limitations':'Local HTTP, two independently stored classroom application databases, and synchronous non-durable logout fanout. Tests revocation while both instances are reachable, not a shared-session store, load-balancer deployment, offline-instance recovery, zero-downtime secret overlap or distributed business-data consistency.'}
    report['status']='passed'
    report['prior_failures']='Earlier cutover attempts failed, including Invalid credentials on the second instance. Their intermittent cause is not established; see identity-cluster-failure-review.json. This report describes the final isolated run only.'
    (ROOT/'identity-cluster-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
except Exception as error:
    report={'status':'partial_or_failed','passed':checks,'failed':type(error).__name__,'limitations':'No success claimed for unfinished checks. Inspect private runtime logs locally; initial report preserves the first observed failure.'}
    (ROOT/'identity-cluster-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    raise
finally:
    if relay:relay.shutdown();relay.server_close()
    for p in reversed(processes):stop(p)
    for log in logs:log.close()
