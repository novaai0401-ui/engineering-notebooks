"""Real native Prometheus scraping, alert-rule validation and an offline dashboard."""
import json,os,secrets,socket,subprocess,sys,time,datetime,html
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parent;BIN=ROOT.parents[1]/'.runtime/prometheus-3.14.0.windows-amd64'
RUN=ROOT.parents[1]/'.runtime'/('monitor-'+secrets.token_hex(4));RUN.mkdir(parents=True)
env=os.environ.copy();env['COACH_SERVICE_TOKEN']=secrets.token_urlsafe(32);env['COACH_AI_MODE']='extractive'
processes=[];logs=[];checks=[]
def start(args,cwd,name):
 f=(RUN/(name+'.log')).open('w');logs.append(f)
 p=subprocess.Popen([str(x) for x in args],cwd=cwd,env=env,stdout=f,stderr=f,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));processes.append(p);return p
def ready(url,p):
 until=time.monotonic()+120
 while time.monotonic()<until:
  if p.poll() is not None:raise RuntimeError(f'Process exited: inspect {RUN}')
  try:
   if httpx.get(url,timeout=2).status_code==200:return
  except httpx.HTTPError:pass
  time.sleep(.25)
 raise TimeoutError(url)
for port in (8102,9097):
 with socket.socket() as s:s.bind(('127.0.0.1',port))
try:
 for args in (['check','rules','alerts.yaml'],['test','rules','alert-tests.yaml']):
  result=subprocess.run([str(BIN/'promtool.exe'),*args],cwd=ROOT/'observability',capture_output=True,text=True,check=True)
 checks.append('Promtool validated alert syntax and a timed firing-rule fixture')
 token=RUN/'scrape-token';token.write_text(env['COACH_SERVICE_TOKEN'])
 config={'global':{'scrape_interval':'1s','evaluation_interval':'1s'},'rule_files':[str(ROOT/'observability/alerts.yaml')],'scrape_configs':[{'job_name':'coach-python','metrics_path':'/metrics','authorization':{'credentials_file':str(token)},'static_configs':[{'targets':['127.0.0.1:8102']}]}]}
 (RUN/'prometheus.json').write_text(json.dumps(config))
 subprocess.run([str(BIN/'promtool.exe'),'check','config',str(RUN/'prometheus.json')],capture_output=True,text=True,check=True)
 ai=start([sys.executable,'-m','uvicorn','coach_ai:app','--host','127.0.0.1','--port','8102'],ROOT/'python','python');ready('http://127.0.0.1:8102/health',ai)
 assert httpx.get('http://127.0.0.1:8102/metrics').status_code==401
 prom=start([BIN/'prometheus.exe','--config.file='+str(RUN/'prometheus.json'),'--storage.tsdb.path='+str(RUN/'tsdb'),'--web.listen-address=127.0.0.1:9097'],RUN,'prometheus');ready('http://127.0.0.1:9097/-/ready',prom)
 response=httpx.post('http://127.0.0.1:8102/answer',headers={'Authorization':'Bearer '+env['COACH_SERVICE_TOKEN']},json={'question':'checkpoint','user':'alice'},timeout=30);response.raise_for_status();assert '"done": true' in response.text
 samples=[]
 for _ in range(30):
  data=httpx.get('http://127.0.0.1:9097/api/v1/query',params={'query':'sum(coach_ai_requests_total{route="/answer",status="200"})'}).json()
  samples=data['data']['result']
  if samples and float(samples[0]['value'][1])>=1:break
  time.sleep(1)
 assert samples and float(samples[0]['value'][1])>=1
 targets=httpx.get('http://127.0.0.1:9097/api/v1/targets').json()['data']['activeTargets'];assert targets and all(t['health']=='up' for t in targets)
 checks+=['Unauthenticated metrics access was rejected','Prometheus scraped protected Python metrics with a runtime bearer credential','PromQL returned the counter for an actual completed answer request']
 report={'passed':checks,'version':'3.14.0','recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'answer_requests':float(samples[0]['value'][1]),'targets_up':len(targets),'limitations':'Local native Prometheus and one Python target; no public monitoring deployment, Grafana cluster or executed OTLP collector. Alert fixture tests a rule, not a production incident notification.'}
 (ROOT/'monitoring-report.json').write_text(json.dumps(report,indent=2))
 items=''.join('<li>'+html.escape(x)+'</li>' for x in checks)
 (ROOT/'monitoring-dashboard.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Study Coach monitoring evidence</title><style>body{font:18px/1.7 system-ui;background:#fffdf8;color:#19313f;max-width:850px;margin:40px auto;padding:20px}.cards{display:flex;gap:20px;flex-wrap:wrap}article{background:#edf3f2;padding:24px;border-radius:12px}strong{font-size:40px}a{color:#095769}</style><main><h1>Study Coach monitoring evidence</h1><p>Recorded local run: '+html.escape(report['recorded_at'])+'. This page is a saved result, not a live status display.</p><div class="cards"><article><strong>'+str(report['answer_requests'])+'</strong><p>Completed answer requests observed</p></article><article><strong>'+str(report['targets_up'])+'</strong><p>Healthy scrape target</p></article></div><h2>Verified behavior</h2><ul>'+items+'</ul><p>'+html.escape(report['limitations'])+'</p><a href="../../19-observability-and-browser-quality.html">Read the observability lesson</a></main></html>',encoding='utf-8')
 print(json.dumps(report,indent=2))
finally:
 for p in reversed(processes):
  if p.poll() is None:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True);p.wait(timeout=15)
 for f in logs:f.close()
