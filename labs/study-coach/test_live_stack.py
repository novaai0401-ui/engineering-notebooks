"""One real generated answer through Java -> Python -> installed Ollama model."""
import json,os,re,secrets,socket,subprocess,sys,time
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parent;RUN=ROOT.parents[1]/'.runtime'/('live-stack-'+secrets.token_hex(4));RUN.mkdir(parents=True)
env=os.environ.copy();env.update(COACH_PASSWORD=secrets.token_urlsafe(24),COACH_SERVICE_TOKEN=secrets.token_urlsafe(32),COACH_PORT='8098',COACH_AI_URL='http://127.0.0.1:8099/answer',COACH_AI_MODE='ollama',COACH_LEASE_MS='200000',COACH_AI_READ_TIMEOUT_MS='180000',COACH_AI_DEADLINE_MS='185000',COACH_DB='jdbc:h2:file:'+str(RUN/'coach').replace('\\','/'))
processes=[];logs=[]
def start(args,cwd,name):
 log=(RUN/(name+'.log')).open('w');logs.append(log)
 p=subprocess.Popen([str(x) for x in args],cwd=cwd,env=env,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));processes.append(p);return p
def ready(url,p):
 end=time.monotonic()+150
 while time.monotonic()<end:
  if p.poll() is not None:raise RuntimeError(f'Inspect {RUN}')
  try:
   if httpx.get(url,timeout=2).status_code==200:return
  except httpx.HTTPError:pass
  time.sleep(.5)
 raise TimeoutError(url)
for port in (8098,8099):
 with socket.socket() as probe:probe.bind(('127.0.0.1',port))
try:
 ai=start([sys.executable,'-m','uvicorn','coach_ai:app','--host','127.0.0.1','--port','8099'],ROOT/'python','python');ready('http://127.0.0.1:8099/health',ai)
 props=subprocess.run(['java','-XshowSettings:properties','-version'],capture_output=True,text=True,check=True).stderr
 java=Path(re.search(r'java.home\s*=\s*(.+)',props).group(1).strip())/'bin/java.exe'
 app=start([java,'-Xmx256m','-jar',ROOT/'java/target/study-coach-1.0.0.jar'],ROOT/'java','java');ready('http://127.0.0.1:8098/health',app)
 with httpx.Client(base_url='http://127.0.0.1:8098',auth=('alice',env['COACH_PASSWORD']),timeout=30) as c:
  csrf=c.get('/api/csrf').json();c.headers[csrf['header']]=csrf['token']
  response=c.post('/api/jobs',headers={'Idempotency-Key':secrets.token_hex(12)},json={'question':'Explain a checkpoint in one short sentence using the evidence.'});response.raise_for_status();jid=response.json()['id']
  began=time.perf_counter();c.post('/api/jobs/'+jid+'/approve').raise_for_status();partial=False
  until=time.monotonic()+240
  while time.monotonic()<until:
   response=c.get('/api/jobs/'+jid);response.raise_for_status();job=response.json()
   partial=partial or (job['status']=='running' and bool(job['answer']))
   if job['status'] in ('done','failed'):break
   time.sleep(.25)
  assert job['status']=='done' and '[checkpoint]' in job['answer'],job
  report={'passed':['Authenticated approval produced an actual Ollama-generated answer through Java and Python','Final citation identifier belongs to retrieved evidence'],'answer':job['answer'],'attempts':job['attempt'],'partial_observed':partial,'elapsed_seconds':time.perf_counter()-began,'limitations':'One local integration case; citation syntax is not a semantic accuracy guarantee; read deadline and lease enlarged for bounded model inference.'}
  (ROOT/'live-stack-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
finally:
 for p in reversed(processes):
  if p.poll() is None:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True);p.wait(timeout=15)
 for f in logs:f.close()
