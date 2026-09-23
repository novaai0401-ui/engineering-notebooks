"""Verify already-built Study Coach images on the task-owned K3s cluster."""
import base64,http.cookiejar,json,secrets,subprocess,time,urllib.error,urllib.request
from pathlib import Path
def verify(kubectl,config,run):
 build=json.loads((Path(__file__).parent/'study-coach/container-report.json').read_text());assert build['status']=='passed'
 namespace='studycapstone-'+secrets.token_hex(3);password=secrets.token_urlsafe(24);token=secrets.token_urlsafe(24)
 for service,tag in build['images'].items():
  archive=run/(service+'.tar')
  with archive.open('wb') as out:subprocess.run(['/usr/bin/docker','save',tag],stdout=out,check=True,timeout=180)
  subprocess.run(['/usr/local/bin/k3s','ctr','images','import',str(archive)],capture_output=True,check=True,timeout=180)
 kubectl('create','namespace',namespace);forward=None;logs=[]
 def meta(name):return {'name':name,'namespace':namespace}
 resources=[{'apiVersion':'v1','kind':'Secret','metadata':meta('credentials'),'stringData':{'COACH_PASSWORD':password,'COACH_SERVICE_TOKEN':token}}, {'apiVersion':'v1','kind':'PersistentVolumeClaim','metadata':meta('database'),'spec':{'accessModes':['ReadWriteOnce'],'resources':{'requests':{'storage':'1Gi'}}}}]
 for service,port in (('ai',8092),('web',8091)):
  env=[{'name':'COACH_SERVICE_TOKEN','valueFrom':{'secretKeyRef':{'name':'credentials','key':'COACH_SERVICE_TOKEN'}}}]
  if service=='web':env += [{'name':'COACH_PASSWORD','valueFrom':{'secretKeyRef':{'name':'credentials','key':'COACH_PASSWORD'}}},{'name':'COACH_AI_URL','value':'http://ai:8092/answer'},{'name':'JAVA_TOOL_OPTIONS','value':'-Xmx256m'}]
  container={'name':service,'image':'docker.io/library/'+build['images'][service],'imagePullPolicy':'Never','env':env,'ports':[{'containerPort':port}],'securityContext':{'runAsNonRoot':True,'runAsUser':10001,'allowPrivilegeEscalation':False,'capabilities':{'drop':['ALL']}},'resources':{'requests':{'cpu':'50m','memory':'128Mi'},'limits':{'cpu':'1000m','memory':'768Mi'}},'readinessProbe':{'httpGet':{'path':'/health','port':port},'periodSeconds':5,'timeoutSeconds':3}}
  pod={'automountServiceAccountToken':False,'securityContext':{'fsGroup':10001},'containers':[container]}
  if service=='web':pod['volumes']=[{'name':'database','persistentVolumeClaim':{'claimName':'database'}}];container['volumeMounts']=[{'name':'database','mountPath':'/data'}]
  resources += [{'apiVersion':'apps/v1','kind':'Deployment','metadata':meta(service),'spec':{'replicas':1,'strategy':{'type':'Recreate'},'selector':{'matchLabels':{'app':service}},'template':{'metadata':{'labels':{'app':service}},'spec':pod}}},{'apiVersion':'v1','kind':'Service','metadata':meta(service),'spec':{'selector':{'app':service},'ports':[{'port':port,'targetPort':port}]}}]
 try:
  manifest=run/'capstone-private.json';manifest.write_text(json.dumps({'apiVersion':'v1','kind':'List','items':resources}));manifest.chmod(0o600)
  kubectl('apply','-f',str(manifest))
  for service in ('ai','web'):kubectl('-n',namespace,'rollout','status','deployment/'+service,'--timeout=300s')
  def start_forward():
   stream=(run/('forward-'+str(len(logs))+'.log')).open('w');logs.append(stream)
   p=subprocess.Popen(['/usr/local/bin/k3s','kubectl','--kubeconfig',str(config),'-n',namespace,'port-forward','service/web','18091:8091','--address','127.0.0.1'],stdout=stream,stderr=stream)
   until=time.monotonic()+30
   while time.monotonic()<until:
    try:
     with urllib.request.urlopen('http://127.0.0.1:18091/health',timeout=2) as response:
      if response.status==200:return p
    except (OSError,urllib.error.URLError):pass
    time.sleep(.2)
   p.terminate();p.wait(timeout=10);raise TimeoutError('Port forward')
  forward=start_forward();base='http://127.0.0.1:18091'
  opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
  headers={'Authorization':'Basic '+base64.b64encode(('alice:'+password).encode()).decode(),'Content-Type':'application/json'}
  def request(path,body=None,extra=None):
   req=urllib.request.Request(base+path,data=None if body is None else json.dumps(body).encode(),headers=dict(headers,**(extra or {})))
   with opener.open(req,timeout=30) as response:return json.load(response)
  csrf=request('/api/csrf');headers[csrf['header']]=csrf['token']
  job=request('/api/jobs',{'question':'What is a checkpoint?'},{'Idempotency-Key':secrets.token_hex(12)});request('/api/jobs/'+job['id']+'/approve',{})
  until=time.monotonic()+90
  while True:
   result=request('/api/jobs/'+job['id'])
   if result['status']=='done':break
   if result['status']=='failed' or time.monotonic()>until:raise AssertionError('Cluster job failed or timed out')
   time.sleep(.25)
  assert '[checkpoint]' in result['answer'];forward.terminate();forward.wait(timeout=10);forward=None
  kubectl('-n',namespace,'delete','pods','-l','app=web','--wait=true');kubectl('-n',namespace,'rollout','status','deployment/web','--timeout=300s')
  forward=start_forward();assert request('/api/jobs/'+job['id'])['answer']==result['answer']
  return ['Actual Study Coach images imported into K3s and deployed as non-root pods','Cluster Service networking and Secret configured authenticated Java-to-Python work','Completed job survived web pod deletion and replacement through its persistent volume']
 finally:
  if forward:forward.terminate();forward.wait(timeout=10)
  for log in logs:log.close()
  kubectl('delete','namespace',namespace,'--wait=false',check=False)
