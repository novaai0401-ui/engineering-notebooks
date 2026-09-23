"""Run inside the isolated WSL lab after placing verified k3s at /usr/local/bin/k3s."""
import json,os,subprocess,tempfile,time,sys
from pathlib import Path
RUN=Path(tempfile.mkdtemp(prefix='k3s-learning-'));log=(RUN/'server.log').open('w');config=RUN/'kubeconfig'
server=subprocess.Popen(['/usr/local/bin/k3s','server','--data-dir',str(RUN/'data'),'--write-kubeconfig',str(config),'--https-listen-port','16443','--bind-address','0.0.0.0','--disable','traefik','--disable','servicelb','--disable','metrics-server'],env=dict(os.environ,GOMEMLIMIT='600MiB',PATH='/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'),stdout=log,stderr=log)
def kubectl(*args,check=True):return subprocess.run(['/usr/local/bin/k3s','kubectl','--kubeconfig',str(config)]+list(args),capture_output=True,text=True,check=check,timeout=330 if 'rollout' in args or 'wait' in args else 90)
report={'status':'failed','passed':[]}
try:
 deadline=time.monotonic()+300
 while True:
  if server.poll() is not None:raise RuntimeError('K3s server exited; inspect private Linux runtime log')
  if config.exists() and kubectl('get','--raw=/readyz',check=False).returncode==0:break
  if time.monotonic()>deadline:raise TimeoutError('API readiness')
  time.sleep(2)
 kubectl('wait','--for=condition=Ready','node','--all','--timeout=180s')
 for name in ('coredns','local-path-provisioner'):
  deadline=time.monotonic()+120
  while kubectl('-n','kube-system','get','deployment/'+name,check=False).returncode:
   if time.monotonic()>deadline:raise TimeoutError('System deployment was not created: '+name)
   time.sleep(1)
  kubectl('-n','kube-system','rollout','status','deployment/'+name,'--timeout=180s')
 report['version']=json.loads(kubectl('version','-o','json').stdout)['serverVersion']['gitVersion'];report['passed'].append('Actual K3s API and node reached ready state')
 print('Actual K3s API and node are ready',flush=True)
 manifest={'apiVersion':'apps/v1','kind':'Deployment','metadata':{'name':'study-reconcile'},'spec':{'replicas':2,'selector':{'matchLabels':{'app':'study-reconcile'}},'template':{'metadata':{'labels':{'app':'study-reconcile'}},'spec':{'automountServiceAccountToken':False,'containers':[{'name':'worker','image':'busybox:1.37','command':['sh','-c','while true; do sleep 5; done'],'resources':{'requests':{'cpu':'10m','memory':'8Mi'},'limits':{'cpu':'100m','memory':'32Mi'}},'securityContext':{'runAsNonRoot':True,'runAsUser':10001,'allowPrivilegeEscalation':False,'capabilities':{'drop':['ALL']},'readOnlyRootFilesystem':True}}]}}}}
 path=RUN/'deployment.json';path.write_text(json.dumps(manifest));kubectl('apply','-f',str(path));kubectl('rollout','status','deployment/study-reconcile','--timeout=180s')
 initial=json.loads(kubectl('get','pods','-l','app=study-reconcile','-o','json').stdout)['items'];victim=initial[0]['metadata']['name'];uid=initial[0]['metadata']['uid']
 kubectl('delete','pod',victim,'--wait=true');kubectl('rollout','status','deployment/study-reconcile','--timeout=180s')
 pods=json.loads(kubectl('get','pods','-l','app=study-reconcile','-o','json').stdout)['items'];assert len(pods)==2 and uid not in {p['metadata']['uid'] for p in pods}
 report['passed'].append('Two real pods became ready; deleted pod was replaced with a new UID')
 kubectl('scale','deployment/study-reconcile','--replicas=1');kubectl('rollout','status','deployment/study-reconcile','--timeout=120s')
 report['passed'].append('Deployment controller reconciled requested scale-down')
 if '--capstone' in sys.argv:
  print('Pod replacement and scale-down passed; waiting for the Compose image test',flush=True)
  build_report=Path(__file__).parent/'study-coach/container-report.json';deadline=time.monotonic()+1800
  while not build_report.exists():
   if server.poll() is not None or time.monotonic()>deadline:raise TimeoutError('Container prerequisite')
   time.sleep(2)
  from k8s_capstone import verify
  report['passed']+=verify(kubectl,config,RUN)
 report.update(status='passed',limitations='One K3s node in a task-owned WSL VM, using a small non-root workload. Not a Study Coach Kubernetes rollout, multi-node failure, cloud load balancer, TLS ingress, production storage or public-cloud deployment.')
 if '--capstone' in sys.argv:report['limitations']='One local K3s node with actual Study Coach containers, cluster networking, Secret and persistent volume. Not public cloud, production OIDC, TLS ingress, distributed storage or multi-node failure.'
except Exception as error:report['error']=type(error).__name__;raise
finally:
 if config.exists():
  try:kubectl('delete','deployment','study-reconcile','--ignore-not-found=true','--wait=false',check=False)
  except subprocess.SubprocessError:pass
 server.terminate()
 try:server.wait(timeout=30)
 except subprocess.TimeoutExpired:server.kill();server.wait()
 log.close();Path(__file__).with_name('kubernetes-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
