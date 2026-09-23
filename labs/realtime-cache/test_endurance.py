"""Five-minute bounded HTTP/cache/write soak, retaining measured resource samples."""
import argparse,json,os,secrets,socket,sqlite3,subprocess,sys,time
from pathlib import Path
import httpx,psutil
ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=int,default=300);args=parser.parse_args()
if not 30<=args.seconds<=1800:parser.error('seconds must be between 30 and 1800')
RUN=ROOT.parents[1]/'.runtime'/('endurance-'+secrets.token_hex(4));RUN.mkdir()
env=dict(os.environ,EVENT_PASSWORD=secrets.token_urlsafe(24),EVENT_DB=str(RUN/'events.db'))
BASE='http://127.0.0.1:8105'
with socket.socket() as probe:probe.bind(('127.0.0.1',8105))
with (RUN/'server.log').open('w') as log:
 p=subprocess.Popen([sys.executable,'-m','uvicorn','app:app','--host','127.0.0.1','--port','8105'],cwd=ROOT,env=env,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
 try:
  for _ in range(240):
   if p.poll() is not None:raise RuntimeError('Service exited')
   try:
    if httpx.get(BASE+'/health',timeout=1).status_code==200:break
   except httpx.HTTPError:pass
   time.sleep(.25)
  else:raise TimeoutError('startup')
  samples=[];latencies=[];writes=0;began=time.monotonic();next_sample=began
  with httpx.Client(base_url=BASE,headers={'Origin':BASE},timeout=10) as client:
   login=client.post('/login',json={'user':'alice','password':env['EVENT_PASSWORD']});login.raise_for_status();client.headers['x-csrf-token']=login.json()['csrf']
   while time.monotonic()-began<args.seconds:
    start=time.monotonic();payload={'key':f'soak-key-{writes}','text':f'Entry {writes}'}
    response=client.post('/messages',json=payload);response.raise_for_status()
    duplicate=client.post('/messages',json=payload);duplicate.raise_for_status();assert duplicate.json()['duplicate'] and duplicate.json()['seq']==response.json()['seq']
    read=client.get('/snapshot');read.raise_for_status()
    latencies.append((time.monotonic()-start)*1000);writes+=1
    if time.monotonic()>=next_sample:
     processes=[psutil.Process(p.pid)]+psutil.Process(p.pid).children(recursive=True)
     samples.append({'second':round(time.monotonic()-began,1),'rss_bytes':sum(item.memory_info().rss for item in processes),'handles':sum(item.num_handles() for item in processes)})
     next_sample=time.monotonic()+10
    time.sleep(.2)
  with sqlite3.connect(env['EVENT_DB']) as db:assert db.execute('SELECT COUNT(*) FROM requests').fetchone()[0]==writes
  report={'passed':True,'requested_seconds':args.seconds,'duration_seconds':round(time.monotonic()-began,2),'logical_writes':writes,'request_count':1+3*writes,'cycle_p95_ms':round(sorted(latencies)[int(.95*(len(latencies)-1))],2),'resource_samples':samples,'limitations':'One client, bounded local HTTP/cache/write soak. Resource samples expose trends but do not prove absence of leaks. Not multi-day endurance, Redis failover, WebSocket soak or production capacity.'}
  filename='endurance-report.json' if args.seconds==300 else f'endurance-{args.seconds}-report.json'
  (ROOT/filename).write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
 finally:
  if p.poll() is None:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True);p.wait(timeout=20)
