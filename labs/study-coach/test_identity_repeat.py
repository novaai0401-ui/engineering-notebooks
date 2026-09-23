"""Repeat fresh OIDC logins against retained isolated test settings; never print secrets."""
import json,os,re,secrets,socket,subprocess,time,shutil
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parent;RUNTIME=ROOT.parents[1]/'.runtime'
candidates=[p for p in RUNTIME.glob('identity-cluster-*') if (p/'private-test-settings.json').exists() and (p/'app.jar').exists()]
SOURCE=max(candidates,key=lambda p:p.stat().st_mtime);RUN=RUNTIME/('identity-repeat-'+secrets.token_hex(4));RUN.mkdir()
shutil.copy2(ROOT/'java/target/study-coach-1.0.0.jar',RUN/'app.jar')
env=dict(os.environ,**json.loads((SOURCE/'private-test-settings.json').read_text(encoding='utf-8')))
env['IDENTITY_TEST_OUTPUT']=str(RUN/'browser-result.json')
props=subprocess.run(['java','-XshowSettings:properties','-version'],capture_output=True,text=True,check=True).stderr
java=Path(re.search(r'java.home\s*=\s*(.+)',props).group(1).strip())/'bin/java.exe'
processes=[];logs=[]
def start(args,cwd,name,extra=None):
    stream=(RUN/(name+'.log')).open('w');logs.append(stream)
    p=subprocess.Popen([str(x) for x in args],cwd=cwd,env=dict(env,**(extra or {})),stdout=stream,stderr=stream,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));processes.append(p);return p
def ready(url,p):
    deadline=time.monotonic()+360
    while time.monotonic()<deadline:
        if p.poll() is not None:raise RuntimeError('Owned service exited')
        try:
            if httpx.get(url,timeout=2).status_code==200:return
        except httpx.HTTPError:pass
        time.sleep(.5)
    raise TimeoutError('Service startup')
for port in (8091,8094,8096):
    with socket.socket() as check:check.bind(('127.0.0.1',port))
try:
    kc=RUNTIME/'keycloak-26.7.4';p=start([kc/'bin/kc.bat','start-dev'],kc,'keycloak');ready('http://127.0.0.1:8094/realms/study/.well-known/openid-configuration',p)
    response=httpx.post('http://127.0.0.1:8094/realms/study/protocol/openid-connect/token',data={'grant_type':'authorization_code','client_id':'study-coach','client_secret':env['COACH_OIDC_SECRET'],'code':'deliberately-invalid-code','redirect_uri':'http://127.0.0.1:8091/login/oauth2/code/coach'},timeout=20)
    assert response.json().get('error')=='invalid_grant','Client authentication itself failed'
    for port in (8091,8096):
        p=start([java,'-Xmx256m','-jar',RUN/'app.jar'],ROOT/'java',str(port),{'SERVER_PORT':str(port),'COACH_DB':'jdbc:h2:file:'+str(SOURCE/('app-'+str(port))).replace('\\','/')})
        ready(f'http://127.0.0.1:{port}/health',p)
    result=subprocess.run(['node',str(ROOT/'identity/repeat-browser.mjs')],env=env,capture_output=True,text=True,timeout=600)
    (RUN/'browser.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    report=json.loads((RUN/'browser-result.json').read_text(encoding='utf-8'))
    report['client_authentication_probe']='Rotated client secret accepted; deliberately invalid authorization code rejected with invalid_grant'
    report['limitations']='Repeated local fresh logins using the retained isolated realm. Does not prove production reliability or reproduce every earlier failure.'
    (ROOT/'identity-repeat-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2));result.check_returncode()
finally:
    for p in reversed(processes):
        if p.poll() is None:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True);p.wait(timeout=20)
    for stream in logs:stream.close()
