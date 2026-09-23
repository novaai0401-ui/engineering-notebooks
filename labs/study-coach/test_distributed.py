"""Isolated native deployment: PostgreSQL, persistent broker, two workers, tracing, restore.
No existing database or broker is modified. Runtime credentials are random and excluded.
"""
import concurrent.futures, json, os, re, secrets, socket, statistics, subprocess, sys, time, shutil
from pathlib import Path
PG=Path(os.environ.get('PG_BIN','C:/Program Files/PostgreSQL/18/bin'))
if os.name=='nt':
    os.environ['PATH']=str(PG)+os.pathsep+os.environ['PATH']
    os.environ.setdefault('PSYCOPG_IMPL','python')
import httpx, psycopg
from contextlib import closing
ROOT=Path(__file__).resolve().parent
RUN=ROOT.parents[1]/'.runtime'/('distributed-'+secrets.token_hex(5));RUN.mkdir(parents=True)
env=os.environ.copy(); env.update(COACH_PASSWORD=secrets.token_urlsafe(24),COACH_SERVICE_TOKEN=secrets.token_urlsafe(32),COACH_DB_PASSWORD=secrets.token_urlsafe(24),COACH_BROKER_PASSWORD=secrets.token_urlsafe(24))
env.update(COACH_DB='jdbc:postgresql://127.0.0.1:55439/coach',COACH_DB_USER='coach',COACH_MIGRATIONS='classpath:db/migration-postgres',COACH_BROKER_DATA=str(RUN/'broker'),SPRING_PROFILES_ACTIVE='broker',COACH_LEASE_MS='4000',COACH_PORT='8097')
flags=getattr(subprocess,'CREATE_NO_WINDOW',0); processes=[];handles=[];checks=[];pg_started=False
def command(args,**kwargs):return subprocess.run([str(x) for x in args],env=env,capture_output=True,text=True,check=True,**kwargs)
def start(args,cwd,name,extra=None):
    log=(RUN/(name+'.log')).open('w');handles.append(log)
    childenv=env|{'COACH_TRACE_FILE':str(RUN/(name+'-traces.jsonl'))}|(extra or {})
    p=subprocess.Popen([str(x) for x in args],cwd=cwd,env=childenv,stdout=log,stderr=log,creationflags=flags);processes.append(p);return p
def stop(p):
    if p.poll() is None:
        if os.name=='nt':subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True)
        else:p.kill()
        p.wait(timeout=15)
def wait_port(port,p):
    until=time.monotonic()+300
    while time.monotonic()<until:
        if p.poll() is not None:raise RuntimeError(f'Process exited; inspect {RUN}')
        try:
            with socket.create_connection(('127.0.0.1',port),1):return
        except OSError:time.sleep(.3)
    raise TimeoutError(port)
def ready(port,p):
    wait_port(port,p)
    for _ in range(120):
        try:
            if httpx.get(f'http://127.0.0.1:{port}/health',timeout=2).status_code==200:return
        except httpx.HTTPError:pass
        time.sleep(.5)
    raise TimeoutError(port)
def client():
    c=httpx.Client(base_url='http://127.0.0.1:8097',auth=('alice',env['COACH_PASSWORD']),timeout=30)
    r=c.get('/api/csrf');r.raise_for_status();v=r.json();c.headers[v['header']]=v['token'];return closing(c)
def submit(c):
    r=c.post('/api/jobs',headers={'Idempotency-Key':secrets.token_hex(12)},json={'question':'What is a checkpoint?'});r.raise_for_status();jid=r.json()['id']
    c.post('/api/jobs/'+jid+'/approve').raise_for_status();return jid
def finished(c,jid):
    until=time.monotonic()+60
    while time.monotonic()<until:
        r=c.get('/api/jobs/'+jid);r.raise_for_status();j=r.json()
        if j['status'] in ('done','failed'):assert j['status']=='done',j;return j
        time.sleep(.1)
    raise TimeoutError(jid)
for port in (55439,61629,8097,8092,8096):
    with socket.socket() as probe:probe.bind(('127.0.0.1',port))
try:
    pw=RUN/'pg-password';pw.write_text(env['COACH_DB_PASSWORD']);env['PGPASSWORD']=env['COACH_DB_PASSWORD']
    command([PG/'initdb.exe','-D',RUN/'pg','-U','coach','--auth=scram-sha-256','--pwfile',pw,'--encoding=UTF8','--locale=C'])
    with (RUN/'pg-control.log').open('w') as control:
        subprocess.run([str(PG/'pg_ctl.exe'),'-D',str(RUN/'pg'),'-l',str(RUN/'pg.log'),'-o','-h 127.0.0.1 -p 55439','-w','start'],env=env,stdin=subprocess.DEVNULL,stdout=control,stderr=control,check=True,timeout=90)
    pg_started=True
    command([PG/'createdb.exe','-h','127.0.0.1','-p','55439','-U','coach','coach'])
    dsn=dict(host='127.0.0.1',port=55439,user='coach',password=env['COACH_DB_PASSWORD'],dbname='coach')
    props=command(['java','-XshowSettings:properties','-version']).stderr
    java=Path(re.search(r'java.home\s*=\s*(.+)',props).group(1).strip())/'bin/java.exe'
    shutil.copyfile(ROOT/'java/target/study-coach-1.0.0.jar',RUN/'app.jar')
    base=[java,'-Xmx256m','-jar',RUN/'app.jar']
    broker=start(base+['--broker-only'],RUN,'broker');wait_port(61629,broker)
    ai=start([sys.executable,'-m','uvicorn','coach_ai:app','--host','127.0.0.1','--port','8092'],ROOT/'python','python');ready(8092,ai)
    one=start(base,ROOT/'java','worker-one');ready(8097,one)
    two=start(base,ROOT/'java','worker-two',{'COACH_PORT':'8096'});ready(8096,two)
    with client() as c,psycopg.connect(**dsn,autocommit=True) as db:
        jid=submit(c);j=finished(c,jid);assert j['attempt']==1 and '[checkpoint]' in j['answer']
        checks.append('PostgreSQL migrations and broker-delivered approved job completed')
        time.sleep(1)
        db.execute('update job_events set published=false where job_id=%s',(jid,));time.sleep(3)
        assert finished(c,jid)['attempt']==1
        assert db.execute('select count(*) from job_inbox where event_id in (select event_id from job_events where job_id=%s)',(jid,)).fetchone()[0]==1
        checks.append('Republished duplicate event preserved one result and one inbox receipt')
        stop(broker);queued=submit(c);time.sleep(2)
        assert c.get('/api/jobs/'+queued).json()['status']=='pending'
        broker=start(base+['--broker-only'],RUN,'broker-restarted');wait_port(61629,broker);finished(c,queued)
        checks.append('Broker outage retained database outbox; restart delivered pending work')
        # Small measured concurrency exercise, not a capacity or internet load certification.
        def task(_):
            began=time.perf_counter()
            with client() as cc:finished(cc,submit(cc))
            return (time.perf_counter()-began)*1000
        began=time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:latencies=list(pool.map(task,range(12)))
        duration=time.perf_counter()-began
        checks.append('Twelve jobs completed under four concurrent authenticated clients')
        # A SERIALIZABLE write-skew test uses two independent transactions and a real PG engine.
        db.execute('create table duty(id integer primary key, on_call boolean not null)');db.execute('insert into duty values(1,true),(2,true)')
        a=psycopg.connect(**dsn);b=psycopg.connect(**dsn)
        try:
            for conn in (a,b):conn.execute('set transaction isolation level serializable');assert conn.execute('select count(*) from duty where on_call').fetchone()[0]==2
            a.execute('update duty set on_call=false where id=1');b.execute('update duty set on_call=false where id=2');a.commit()
            try:b.commit();raise AssertionError('expected serialization rejection')
            except psycopg.errors.SerializationFailure:b.rollback()
            assert db.execute('select count(*) from duty where on_call').fetchone()[0]==1
        finally:a.close();b.close()
        checks.append('PostgreSQL SERIALIZABLE rejected write skew; business invariant retained')
        expected=db.execute('select count(*) from jobs').fetchone()[0]
        command([PG/'pg_dump.exe','-h','127.0.0.1','-p','55439','-U','coach','-Fc','-f',RUN/'backup.dump','coach'])
        command([PG/'createdb.exe','-h','127.0.0.1','-p','55439','-U','coach','restored'])
        command([PG/'pg_restore.exe','-h','127.0.0.1','-p','55439','-U','coach','-d','restored',RUN/'backup.dump'])
        with psycopg.connect(**(dsn|{'dbname':'restored'})) as restored:assert restored.execute('select count(*) from jobs').fetchone()[0]==expected
        checks.append('Logical backup restored into separate PostgreSQL database with matching job count')
    time.sleep(1)
    spans=[json.loads(line) for path in RUN.glob('*-traces.jsonl') for line in path.read_text().splitlines()]
    java_spans=[s for s in spans if s['service']=='java'];py_spans=[s for s in spans if s['service']!='java']
    linked=sum(any(p['trace_id']==j['trace_id'] and p['parent_span_id']==j['span_id'] for p in py_spans) for j in java_spans)
    assert linked>=1,(java_spans[:1],py_spans[:1]);checks.append('W3C trace context linked Java job spans to Python request spans')
    report={'passed':checks,'jobs':12,'concurrency':4,'elapsed_seconds':duration,'throughput_jobs_per_second':12/duration,'p50_ms':statistics.median(latencies),'p95_ms':sorted(latencies)[-1],'linked_traces':linked,'worker_trace_files':[p.name for p in RUN.glob('worker*-traces.jsonl')],'limitations':'Local native deployment; small load sample; logical backup does not prove PITR; Docker/cloud not executed.'}
    (ROOT/'distributed-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
finally:
    for p in reversed(processes):stop(p)
    for h in handles:h.close()
    if pg_started:command([PG/'pg_ctl.exe','-D',RUN/'pg','-m','fast','-w','stop'])
