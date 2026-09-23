import asyncio,concurrent.futures,json,os,secrets,socket,statistics,subprocess,sys,time
from pathlib import Path
from contextlib import contextmanager
import httpx,websockets
ROOT=Path(__file__).resolve().parent;RUN=ROOT.parents[1]/'.runtime'/('realtime-'+secrets.token_hex(4));RUN.mkdir(parents=True)
env=os.environ.copy();env.update(EVENT_DB=str(RUN/'events.db'),EVENT_PASSWORD=secrets.token_urlsafe(28));base='http://127.0.0.1:8105'
os.environ.update({key:env[key] for key in ('EVENT_DB','EVENT_PASSWORD')})
from app import VersionCache
checks=[];processes=[];logs=[]
def start():
 f=(RUN/('server-'+str(len(processes))+'.log')).open('w');logs.append(f)
 p=subprocess.Popen([sys.executable,'-m','uvicorn','app:app','--host','127.0.0.1','--port','8105','--ws-max-size','4096'],cwd=ROOT,env=env,stdout=f,stderr=f,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));processes.append(p)
 for _ in range(180):
  if p.poll() is not None:raise RuntimeError(f'Inspect {RUN}')
  try:
   if httpx.get(base+'/health',timeout=1).status_code==200:return p
  except httpx.HTTPError:pass
  time.sleep(.5)
 raise TimeoutError('startup')
def stop(p):
 if p.poll() is None:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True);p.wait(timeout=15)
@contextmanager
def client(user='alice'):
 with httpx.Client(base_url=base,headers={'Origin':base},timeout=15) as c:
  r=c.post('/login',json={'user':user,'password':env['EVENT_PASSWORD']});r.raise_for_status();c.headers['x-csrf-token']=r.json()['csrf'];yield c
def send(c,text,key=None):
 r=c.post('/messages',json={'key':key or secrets.token_hex(8),'text':text});r.raise_for_status();return r.json()
async def ws_check(cookie,cursor,c):
 try:
  async with websockets.connect('ws://127.0.0.1:8105/ws',origin='https://wrong.example',additional_headers={'Cookie':cookie}):raise AssertionError('foreign origin accepted')
 except websockets.exceptions.InvalidStatus:pass
 async with websockets.connect(f'ws://127.0.0.1:8105/ws?after={cursor}',origin=base,additional_headers={'Cookie':cookie}) as ws:
  await ws.send(json.dumps({'type':'ping'}));assert json.loads(await ws.recv())['type']=='pong'
  await ws.send(json.dumps({'type':'publish','key':'websocket-once','text':'from WebSocket'}));message=json.loads(await ws.recv());assert message['text']=='from WebSocket'
  c.post('/logout',json={}).raise_for_status()
  try:await asyncio.wait_for(ws.recv(),3);raise AssertionError('revoked socket stayed open')
  except websockets.exceptions.ConnectionClosed as error:assert error.rcvd.code==1008
with socket.socket() as probe:probe.bind(('127.0.0.1',8105))
try:
 clock=[0];cache=VersionCache(2,10,lambda:clock[0]);cache.put('a',1,'one',1);assert cache.get('a',1)=='one';clock[0]=11;assert cache.get('a',1) is None
 assert not cache.put('a',1,'stale',2);cache.put('a',2,'two',2);cache.put('b',1,'b',1);cache.get('a',2);cache.put('c',1,'c',1);assert cache.get('b',1) is None
 checks.append('TTL expiry, LRU eviction and stale-version fill rejection passed with a controlled clock')
 p=start();assert httpx.get(base+'/snapshot').status_code==401
 with client() as alice,client('bob') as bob:
  key=secrets.token_hex(8);first=send(alice,'hello',key);assert send(alice,'hello',key)['duplicate']
  assert alice.post('/messages',json={'key':key,'text':'changed'}).status_code==409
  snap=alice.get('/snapshot');assert snap.json()['messages'][0]['text']=='hello'
  assert alice.get('/snapshot',headers={'If-None-Match':snap.headers['etag']}).status_code==304
  assert bob.get('/snapshot').json()['messages']==[]
  second=send(alice,'newer');assert alice.get('/snapshot',headers={'If-None-Match':snap.headers['etag']}).status_code==200
  with alice.stream('GET','/events',headers={'Last-Event-ID':str(first['seq'])}) as response:
   assert response.status_code==200
   for line in response.iter_lines():
    if line.startswith('data:'):assert json.loads(line[5:])['seq']==second['seq'];break
  checks.append('Owner-scoped cache/ETag, mutation invalidation, idempotency and SSE Last-Event-ID replay passed')
  cookie='event_session='+alice.cookies.get('event_session');asyncio.run(ws_check(cookie,second['seq'],alice))
  checks.append('Real WebSocket publish/ping, Origin rejection and logout-driven connection revocation passed')
 def task(i):
  began=time.perf_counter()
  with client() as c:send(c,'load-'+str(i));c.get('/snapshot').raise_for_status()
  return (time.perf_counter()-began)*1000
 began=time.perf_counter()
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:latencies=list(pool.map(task,range(80)))
 elapsed=time.perf_counter()-began
 with client() as c:
  assert c.get('/events',headers={'Last-Event-ID':'0'}).status_code==409
  before=c.get('/snapshot').json()['revision']
 stop(p);p=start()
 with client() as c:assert c.get('/snapshot').json()['revision']==before
 checks.append('Eighty writes under eight concurrent clients, retention-gap rejection, and process-restart persistence passed')
 report={'passed':checks,'load_requests':80,'concurrency':8,'elapsed_seconds':elapsed,'p50_ms':statistics.median(latencies),'p95_ms':sorted(latencies)[75],'limitations':'Single-process SQLite/local cache and in-memory sessions. This is a short load test, not a long endurance, distributed cache or production capacity certification.'}
 (ROOT/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
finally:
 for p in processes:stop(p)
 for f in logs:f.close()
