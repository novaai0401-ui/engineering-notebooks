"""Native single-node Kafka exercise; local plaintext only, not a production cluster."""
import json,os,re,secrets,socket,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent;RUN=ROOT.parents[1]/'.runtime'/('kafka-'+secrets.token_hex(4));RUN.mkdir(parents=True)
for port in (19092,19093):
 with socket.socket() as probe:probe.bind(('127.0.0.1',port))
props=subprocess.run(['java','-XshowSettings:properties','-version'],capture_output=True,text=True,check=True).stderr
JAVA=Path(re.search(r'java.home\s*=\s*(.+)',props).group(1).strip())/'bin/java.exe'
cp=str(ROOT/'target/classes')+os.pathsep+str(ROOT/'target/dependency/*');base=[str(JAVA),'-Xmx384m','-cp',cp]
config=RUN/'server.properties'
config.write_text('process.roles=broker,controller\nnode.id=1\ncontroller.quorum.voters=1@127.0.0.1:19093\nlisteners=PLAINTEXT://127.0.0.1:19092,CONTROLLER://127.0.0.1:19093\nadvertised.listeners=PLAINTEXT://127.0.0.1:19092\ncontroller.listener.names=CONTROLLER\nlistener.security.protocol.map=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT\ninter.broker.listener.name=PLAINTEXT\noffsets.topic.replication.factor=1\ntransaction.state.log.replication.factor=1\ntransaction.state.log.min.isr=1\ngroup.initial.rebalance.delay.ms=0\nauto.create.topics.enable=false\nlog.dirs='+str(RUN/'data').replace('\\','/')+'\n')
def command(args):return subprocess.run(base+args,cwd=ROOT,capture_output=True,text=True,check=True,timeout=120)
cluster=command(['kafka.tools.StorageTool','random-uuid']).stdout.strip().splitlines()[-1]
command(['kafka.tools.StorageTool','format','-t',cluster,'-c',str(config)])
handles=[];processes=[];checks=[]
def start():
 f=(RUN/('broker-'+str(len(processes))+'.log')).open('w');handles.append(f)
 p=subprocess.Popen(base+['kafka.Kafka',str(config)],stdout=f,stderr=f,cwd=ROOT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));processes.append(p)
 until=time.monotonic()+180
 while time.monotonic()<until:
  if p.poll() is not None:raise RuntimeError(f'Broker exited; logs {RUN}')
  try:
   with socket.create_connection(('127.0.0.1',19092),1):return p
  except OSError:time.sleep(.5)
 raise TimeoutError('broker startup')
def stop(p):
 if p.poll() is None:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True);p.wait(timeout=20)
try:
 p=start();checks.append(command(['learning.KafkaExercise','write']).stdout.strip());stop(p)
 p=start();checks.append('Broker process restarted using retained KRaft/log state')
 for stage in ('read','group'):checks.append(command(['learning.KafkaExercise',stage]).stdout.strip())
 report={'version':'4.1.2','passed':checks,'limitations':'One local plaintext KRaft node on Windows; no replication, network-partition or SASL/TLS certification; Kafka transactions do not include an external database.'}
 (ROOT/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
finally:
 for p in processes:stop(p)
 for f in handles:f.close()
