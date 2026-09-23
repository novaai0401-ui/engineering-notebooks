"""Three real combined KRaft/broker processes; leader kill, continued writes, replica recovery."""
import json,os,re,secrets,socket,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent;RUN=ROOT.parents[1]/'.runtime'/('kafka-cluster-'+secrets.token_hex(4));RUN.mkdir()
for port in range(19092,19098):
 with socket.socket() as probe:probe.bind(('127.0.0.1',port))
props=subprocess.run(['java','-XshowSettings:properties','-version'],capture_output=True,text=True,check=True).stderr
JAVA=Path(re.search(r'java.home\s*=\s*(.+)',props).group(1).strip())/'bin/java.exe'
cp=str(ROOT/'target/classes')+os.pathsep+str(ROOT/'target/dependency/*');base=[str(JAVA),'-Xmx256m','-cp',cp]
def command(args):return subprocess.run(base+args,cwd=ROOT,capture_output=True,text=True,check=True,timeout=120).stdout
cluster=command(['kafka.tools.StorageTool','random-uuid']).strip().splitlines()[-1];configs={};processes={};logs=[]
for node in range(1,4):
 port=19090+2*node;config=RUN/f'{node}.properties';configs[node]=config
 config.write_text(f'process.roles=broker,controller\nnode.id={node}\ncontroller.quorum.voters=1@127.0.0.1:19093,2@127.0.0.1:19095,3@127.0.0.1:19097\nlisteners=PLAINTEXT://127.0.0.1:{port},CONTROLLER://127.0.0.1:{port+1}\nadvertised.listeners=PLAINTEXT://127.0.0.1:{port}\ncontroller.listener.names=CONTROLLER\nlistener.security.protocol.map=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT\ninter.broker.listener.name=PLAINTEXT\nnum.network.threads=2\nnum.io.threads=2\nlog.dirs='+str(RUN/f'data-{node}').replace('\\','/')+'\n',encoding='utf-8')
 command(['kafka.tools.StorageTool','format','-t',cluster,'-c',str(config)])
def start(node):
 f=(RUN/f'broker-{node}-{len(logs)}.log').open('w');logs.append(f)
 processes[node]=subprocess.Popen(base+['kafka.Kafka',str(configs[node])],stdout=f,stderr=f,cwd=ROOT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
def stop(node):
 p=processes[node]
 if p.poll() is None:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True);p.wait(timeout=20)
def state():
 output=command(['learning.ClusterExercise','state']);m=re.search(r'STATE (\d+) (\d+)',output);return tuple(map(int,m.groups()))
try:
 for node in range(1,4):start(node)
 command(['learning.ClusterExercise','create']);command(['learning.ClusterExercise','write','before-'])
 leader,isr=state();assert isr==3;stop(leader)
 command(['learning.ClusterExercise','write','after-']);replacement,remaining=state();assert replacement!=leader and remaining>=2
 command(['learning.ClusterExercise','read']);start(leader)
 until=time.monotonic()+120
 while state()[1]!=3:
  if time.monotonic()>until:raise TimeoutError('Replica did not recover')
  time.sleep(1)
 command(['learning.ClusterExercise','read'])
 report={'passed':['Three real KRaft/broker processes with replication factor 3 and minimum ISR 2','Killed actual partition leader; remaining quorum accepted acks=all writes','All 20 acknowledged records retained in order before and after restart','Restarted broker caught up to ISR 3'],'killed_leader':leader,'replacement_leader':replacement,'limitations':'Three processes on one Windows host, plaintext loopback. Not independent machines, network partition, rolling upgrades, disk loss, TLS/SASL or cloud certification.'}
 (ROOT/'cluster-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
finally:
 for node in processes:stop(node)
 for log in logs:log.close()
