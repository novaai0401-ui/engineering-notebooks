"""Real HTTP, RSA-signed logout, forced relay process restart and unavailable destination."""
import base64,json,os,secrets,socket,sqlite3,subprocess,sys,threading,time
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import parse_qs
import httpx,jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from identity.durable_relay import Journal,EVENT
ROOT=Path(__file__).resolve().parent;RUN=ROOT.parents[1]/'.runtime'/('durable-logout-'+secrets.token_hex(4));RUN.mkdir()
private=rsa.generate_private_key(public_exponent=65537,key_size=2048);public=private.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
(RUN/'public.pem').write_bytes(public);key=os.urandom(32);issuer='https://classroom-identity.example.test';audience='study-coach'
blocked=[False,True];active=[True,True];servers=[];processes=[];logs=[]
for port in (18108,18109,18110):
    with socket.socket() as check:check.bind(('127.0.0.1',port))
def receiver(index):
    class Receiver(BaseHTTPRequestHandler):
        def do_POST(self):
            if blocked[index]:self.send_error(503);return
            token=parse_qs(self.rfile.read(int(self.headers['Content-Length'])).decode())['logout_token'][0]
            try:claims=jwt.decode(token,public,algorithms=['RS256'],issuer=issuer,audience=audience);assert claims['sid']=='session-7'
            except Exception:self.send_error(400);return
            active[index]=False;self.send_response(200);self.end_headers()
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',18109+index),Receiver);servers.append(server);threading.Thread(target=server.serve_forever,daemon=True).start()
env=dict(os.environ,RELAY_DB=str(RUN/'journal.db'),RELAY_KEY=base64.urlsafe_b64encode(key).decode(),RELAY_PUBLIC_KEY=str(RUN/'public.pem'),RELAY_ISSUER=issuer,RELAY_AUDIENCE=audience,RELAY_TARGETS=json.dumps(['http://127.0.0.1:18109/logout','http://127.0.0.1:18110/logout']))
def start():
    stream=(RUN/(str(len(processes))+'.log')).open('w');logs.append(stream)
    p=subprocess.Popen([sys.executable,str(ROOT/'identity/durable_relay.py')],env=env,stdout=stream,stderr=stream,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));processes.append(p)
    for _ in range(100):
        if p.poll() is not None:raise RuntimeError('Relay exited')
        try:
            if httpx.get('http://127.0.0.1:18108/health',timeout=1).status_code==200:return p
        except httpx.HTTPError:pass
        time.sleep(.2)
    raise TimeoutError('relay start')
def stop(p):
    if p.poll() is None:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True);p.wait(timeout=15)
def wait_until(predicate):
    until=time.monotonic()+30
    while not predicate():
        if time.monotonic()>until:raise TimeoutError('Delivery condition')
        time.sleep(.2)
try:
    receiver(0);receiver(1);p=start();now=int(time.time())
    claims={'iss':issuer,'aud':audience,'iat':now,'exp':now+240,'jti':'event-7','sid':'session-7','events':{EVENT:{}}}
    token=jwt.encode(claims,private,algorithm='RS256')
    assert httpx.post('http://127.0.0.1:18108/logout',data={'logout_token':'forged'}).status_code==400
    wrong=jwt.encode(dict(claims,aud='another-client'),private,algorithm='RS256')
    assert httpx.post('http://127.0.0.1:18108/logout',data={'logout_token':wrong}).status_code==400
    assert httpx.post('http://127.0.0.1:18108/logout',data={'logout_token':token}).status_code==202
    wait_until(lambda:not active[0]);assert active[1]
    assert httpx.post('http://127.0.0.1:18108/logout',data={'logout_token':token}).status_code==202
    stop(p)
    with sqlite3.connect(env['RELAY_DB']) as db:
        assert db.execute('SELECT COUNT(*) FROM events').fetchone()[0]==1
        assert token.encode() not in db.execute('SELECT cipher FROM events').fetchone()[0]
    blocked[1]=False;p=start();wait_until(lambda:not active[1])
    wait_until(lambda:httpx.get('http://127.0.0.1:18108/health').json()['delivered']==2)
    report={'passed':['Forged signature and incorrect audience rejected before persistence','Signed logout acknowledged after durable encrypted SQLite journal commit','Reachable receiver revoked while unavailable receiver stayed pending','Duplicate event did not create duplicate journal records','Hard relay process kill/restart preserved pending delivery; recovered destination revoked its retained session'],'limitations':'Real network/process test with RSA-signed identity fixtures and receiver fixtures, not an additional Keycloak/Spring end-to-end test. Five-minute maximum delivery validity; expiry is reported, not silently claimed delivered. Production needs readiness/session reconciliation beyond expiry, key rotation, retention, TLS and replicated journal storage.'}
    (ROOT/'durable-relay-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
finally:
    for p in processes:stop(p)
    for server in servers:server.shutdown();server.server_close()
    for stream in logs:stream.close()
