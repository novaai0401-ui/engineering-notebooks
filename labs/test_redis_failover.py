"""Run inside the isolated Linux lab: three real Redis servers and three Sentinels."""
import json,secrets,subprocess,tempfile,time
from pathlib import Path
import redis
from redis.sentinel import Sentinel
RUN=Path(tempfile.mkdtemp(prefix='redis-failover-'));password=secrets.token_urlsafe(28);processes=[];logs=[];servers={}
def start(config,name):
 stream=(RUN/(name+'.log')).open('w');logs.append(stream)
 p=subprocess.Popen(['redis-server',str(config)]+(['--sentinel'] if name.startswith('sentinel') else []),stdout=stream,stderr=stream);processes.append(p);return p
def client(port):return redis.Redis(host='127.0.0.1',port=port,password=password,decode_responses=True,socket_timeout=3)
def wait(predicate,seconds=60):
 until=time.monotonic()+seconds
 while True:
  try:
   if predicate():return
  except (redis.RedisError,ConnectionError):pass
  if time.monotonic()>until:raise TimeoutError('Redis recovery deadline')
  time.sleep(.25)
try:
 for port in (16379,16380,16381):
  folder=RUN/str(port);folder.mkdir();config=folder/'redis.conf'
  config.write_text(f'bind 127.0.0.1\nport {port}\nprotected-mode yes\nrequirepass {password}\nmasterauth {password}\ndir {folder}\nappendonly yes\nappendfsync always\n'+('replicaof 127.0.0.1 16379\n' if port!=16379 else ''))
  servers[port]=(start(config,str(port)),config);wait(lambda:client(port).ping())
 for port in (26379,26380,26381):
  config=RUN/f'sentinel-{port}.conf';config.write_text(f'bind 127.0.0.1\nport {port}\nrequirepass {password}\nsentinel monitor classroom 127.0.0.1 16379 2\nsentinel auth-pass classroom {password}\nsentinel down-after-milliseconds classroom 1500\nsentinel failover-timeout classroom 10000\nsentinel parallel-syncs classroom 1\ndir {RUN}\n')
  start(config,'sentinel-'+str(port));wait(lambda:client(port).ping())
 sentinel=Sentinel([('127.0.0.1',p) for p in (26379,26380,26381)],sentinel_kwargs={'password':password},password=password,decode_responses=True,socket_timeout=3)
 master=sentinel.master_for('classroom');master.set('durable-record','before-failure');wait(lambda:master.wait(2,1000)==2)
 servers[16379][0].kill();servers[16379][0].wait(timeout=10)
 wait(lambda:sentinel.discover_master('classroom')[1]!=16379)
 promoted=sentinel.discover_master('classroom')[1];wait(lambda:master.get('durable-record')=='before-failure')
 master.set('after-failure','retained');master.set('cache-entry','temporary',px=700);wait(lambda:master.get('cache-entry') is None,10)
 restarted=start(servers[16379][1],'old-master-restart');wait(lambda:client(16379).info('replication')['role']=='slave')
 wait(lambda:client(16379).get('after-failure')=='retained')
 report={'status':'passed','redis_version':master.info('server')['redis_version'],'promoted_port':promoted,'passed':['Authenticated three-server Redis replication and three-Sentinel quorum','Pre-failure record acknowledged by both replicas','Killed actual primary; Sentinel promoted a replica and client rediscovered it','Existing data retained and new writes/TTL expiration worked after failover','Old primary restarted as replica and caught up'],'limitations':'Six processes on one Linux VM; replication remains asynchronous and WAIT is not a general zero-data-loss guarantee. No independent-host partitions, TLS, disk loss or cloud test.'}
 Path(__file__).with_name('redis-failover-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
finally:
 for p in reversed(processes):
  if p.poll() is None:p.terminate()
 for p in processes:
  try:p.wait(timeout=10)
  except subprocess.TimeoutExpired:p.kill();p.wait()
 for log in logs:log.close()
