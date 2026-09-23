"""Two real HTTP processes share a SQLite journal; cross-instance SSE/WS and duplicate race."""
import asyncio,concurrent.futures,json,os,secrets,socket,sqlite3,subprocess,sys,time
from pathlib import Path
import httpx,websockets
ROOT=Path(__file__).resolve().parent;RUN=ROOT.parents[1]/'.runtime'/('realtime-pair-'+secrets.token_hex(4));RUN.mkdir()
env=dict(os.environ,EVENT_PASSWORD=secrets.token_urlsafe(24),EVENT_DB=str(RUN/'events.db'))
processes=[];logs=[];clients=[]
for port in (8105,8106):
 with socket.socket() as probe:probe.bind(('127.0.0.1',port))
def start(port):
 base=f'http://127.0.0.1:{port}';log=(RUN/f'{port}.log').open('w');logs.append(log)
 p=subprocess.Popen([sys.executable,'-m','uvicorn','app:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=dict(env,EVENT_ORIGIN=base),stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));processes.append(p)
 for _ in range(200):
  if p.poll() is not None:raise RuntimeError('Server exited')
  try:
   if httpx.get(base+'/health',timeout=1).status_code==200:break
  except httpx.HTTPError:pass
  time.sleep(.2)
 else:raise TimeoutError('startup')
 c=httpx.Client(base_url=base,headers={'Origin':base},timeout=15);clients.append(c)
 response=c.post('/login',json={'user':'alice','password':env['EVENT_PASSWORD']});response.raise_for_status();c.headers['x-csrf-token']=response.json()['csrf'];return c
def send(c,key,text):
 r=c.post('/messages',json={'key':key,'text':text});r.raise_for_status();return r.json()
async def stream_check(a,b):
 cookie='event_session='+b.cookies.get('event_session')
 async with websockets.connect('ws://127.0.0.1:8106/ws?after=0',origin='http://127.0.0.1:8106',additional_headers={'Cookie':cookie}) as ws:
  event=await asyncio.to_thread(send,a,'cross-websocket','Written on A, received on B')
  received=json.loads(await asyncio.wait_for(ws.recv(),5));assert received['seq']==event['seq'] and received['text']==event['text']
 return event['seq']
try:
 a=start(8105);b=start(8106)
 empty=b.get('/snapshot');empty.raise_for_status();assert empty.json()['revision']==0
 seq=asyncio.run(stream_check(a,b))
 snapshot=b.get('/snapshot',headers={'If-None-Match':empty.headers['etag']});snapshot.raise_for_status();assert snapshot.json()['revision']==seq
 with b.stream('GET','/events',headers={'Last-Event-ID':str(seq)}) as response:
  response.raise_for_status();event=send(a,'cross-sse-event','SSE from the other instance')
  for line in response.iter_lines():
   if line.startswith('data:'):assert json.loads(line[5:])['seq']==event['seq'];break
  else:raise AssertionError('No cross-instance SSE event')
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  futures=[pool.submit(send,c,'same-logical-key','same payload') for c in (a,b)]
  values=[f.result() for f in futures]
 assert values[0]['seq']==values[1]['seq'] and sorted(v['duplicate'] for v in values)==[False,True]
 def writes(c,prefix):
  return [send(c,f'{prefix}-key-{i}',f'{prefix}-{i}')['seq'] for i in range(40)]
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  futures=[pool.submit(writes,c,prefix) for c,prefix in ((a,'left'),(b,'right'))];sequences=[seq for f in futures for seq in f.result()]
 assert len(set(sequences))==80
 with sqlite3.connect(env['EVENT_DB']) as db:
  assert db.execute('SELECT COUNT(*) FROM requests').fetchone()[0]==83
  assert db.execute('SELECT COUNT(DISTINCT seq) FROM requests').fetchone()[0]==83
 report={'passed':['Two real service processes share an event journal','Write on A delivered through live WebSocket and SSE on B','B rejects stale cache version/ETag after write on A','Concurrent same-key requests across instances return one durable sequence','Eighty concurrent distinct writes across instances retain unique sequences'],'logical_writes':83,'limitations':'Same-host SQLite WAL journal, polling fanout, separate in-memory sessions. Not Redis pub/sub, independent hosts, shared-session revocation, unbounded fanout or cloud capacity.'}
 (ROOT/'multi-instance-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
finally:
 for c in clients:c.close()
 for p in processes:
  if p.poll() is None:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True);p.wait(timeout=20)
 for log in logs:log.close()
