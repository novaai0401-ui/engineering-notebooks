"""Build the supplied multi-stage images, exercise real Compose services and retained volume."""
import json,os,secrets,socket,subprocess,time
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parent;RUN=ROOT.parents[1]/'.runtime'/('containers-'+secrets.token_hex(4));RUN.mkdir()
password=secrets.token_urlsafe(28);token=secrets.token_urlsafe(32)
settings=RUN/'container.env';settings.write_text('COACH_PASSWORD='+password+'\nCOACH_SERVICE_TOKEN='+token+'\n',encoding='utf-8')
def linux(path):return '/mnt/'+path.drive[0].lower()+'/'+path.as_posix().split(':/',1)[1]
project='notebooks-'+secrets.token_hex(4)
base=['wsl','-d','EngineeringNotebookLab-13e66a98','--exec','/usr/bin/docker','compose','--project-directory',linux(ROOT),'--env-file',linux(settings),'-p',project]
report={'status':'failed','passed':[],'project':project};began=time.monotonic()
with socket.socket() as probe:probe.bind(('127.0.0.1',8091))
def compose(args,timeout=180):return subprocess.run(base+args,capture_output=True,text=True,timeout=timeout,check=True)
def ready():
 deadline=time.monotonic()+300
 while time.monotonic()<deadline:
  try:
   if httpx.get('http://127.0.0.1:8091/health',timeout=3).status_code==200:return
  except httpx.HTTPError:pass
  time.sleep(1)
 raise TimeoutError('Container web readiness')
try:
 with (RUN/'build.log').open('w',encoding='utf-8') as log:subprocess.run(base+['up','-d','--build'],stdout=log,stderr=log,check=True,timeout=2400)
 ready();report['passed'].append('Supplied Node/Maven multi-stage web image and Python image built; Compose services started')
 assert httpx.get('http://127.0.0.1:8091/api/me').status_code==401
 with httpx.Client(base_url='http://127.0.0.1:8091',auth=('alice',password),timeout=30) as client:
  csrf=client.get('/api/csrf');csrf.raise_for_status();client.headers[csrf.json()['header']]=csrf.json()['token']
  key=secrets.token_hex(16);body={'question':'What is a checkpoint?'}
  response=client.post('/api/jobs',headers={'Idempotency-Key':key},json=body);response.raise_for_status();job=response.json()
  duplicate=client.post('/api/jobs',headers={'Idempotency-Key':key},json=body);duplicate.raise_for_status();assert duplicate.json()['id']==job['id']
  client.post('/api/jobs/'+job['id']+'/approve').raise_for_status()
  snapshots=[]
  with client.stream('GET','/api/jobs/'+job['id']+'/events') as response:
   response.raise_for_status()
   for line in response.iter_lines():
    if line.startswith('data:'):snapshots.append(json.loads(line[5:]))
  assert snapshots and snapshots[-1]['status']=='done' and '[checkpoint]' in snapshots[-1]['answer']
  report['passed'].append('Authenticated Java-to-Python request, approval, idempotency and SSE answer completed inside containers')
  compose(['restart','web']);ready();retained=client.get('/api/jobs/'+job['id']);retained.raise_for_status();assert retained.json()['answer']==snapshots[-1]['answer']
  report['passed'].append('Web container restart retained completed job in the named database volume')
 report.update(status='passed',limitations='Actual local WSL Docker build and Compose execution using the classroom Basic-auth profile and H2 volume. Not public cloud, production OIDC, multi-node database, image signing or vulnerability certification.')
 report['images']={name:project+'-'+name+':latest' for name in ('web','ai')}
 report['image_ids']={name:subprocess.run(['wsl','-d','EngineeringNotebookLab-13e66a98','--exec','/usr/bin/docker','image','inspect',tag,'--format','{{.Id}}'],capture_output=True,text=True,check=True).stdout.strip() for name,tag in report['images'].items()}
except Exception as error:report['error']=type(error).__name__;raise
finally:
 try:compose(['down','--volumes','--remove-orphans'],timeout=120)
 except subprocess.SubprocessError:report['cleanup']='Inspect owned Compose project '+project
 report['seconds']=round(time.monotonic()-began,2);(ROOT/'container-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
