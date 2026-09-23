"""Kill the owned service during concurrent writes; retry with stable logical keys."""
import concurrent.futures,json,os,secrets,socket,sqlite3,subprocess,sys,threading,time
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parent;RUN=ROOT.parents[1]/'.runtime'/('recovery-load-'+secrets.token_hex(4));RUN.mkdir(parents=True)
env=dict(os.environ,EVENT_PASSWORD=secrets.token_urlsafe(28),EVENT_DB=str(RUN/'events.db'))
BASE='http://127.0.0.1:8105';processes=[];logs=[];guard=threading.Lock();completed=[];retries=[]
def start():
    log=(RUN/(str(len(processes))+'.log')).open('w');logs.append(log)
    p=subprocess.Popen([sys.executable,'-m','uvicorn','app:app','--host','127.0.0.1','--port','8105'],cwd=ROOT,env=env,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));processes.append(p)
    for _ in range(180):
        if p.poll() is not None:raise RuntimeError('Owned service exited')
        try:
            if httpx.get(BASE+'/health',timeout=1).status_code==200:return p
        except httpx.HTTPError:pass
        time.sleep(.2)
    raise TimeoutError('startup')
def stop(p):
    if p.poll() is None:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True);p.wait(timeout=20)
def worker(number):
    owner='alice' if number%2==0 else 'bob'
    with httpx.Client(base_url=BASE,headers={'Origin':BASE},timeout=2) as client:
        authenticated=False
        for index in range(20):
            key=f'worker-{number}-{index}';payload={'key':key,'text':key};deadline=time.monotonic()+60
            while True:
                if time.monotonic()>=deadline:raise TimeoutError('Recovery deadline exhausted')
                try:
                    if not authenticated:
                        login=client.post('/login',json={'user':owner,'password':env['EVENT_PASSWORD']});login.raise_for_status()
                        client.headers['x-csrf-token']=login.json()['csrf'];authenticated=True
                    response=client.post('/messages',json=payload)
                    if response.status_code==401:
                        authenticated=False
                        with guard:retries.append('session_expired_after_restart')
                        continue
                    response.raise_for_status();result=response.json()
                    duplicate=client.post('/messages',json=payload)
                    if duplicate.status_code==401:authenticated=False;continue
                    duplicate.raise_for_status();assert duplicate.json()['duplicate'] and duplicate.json()['seq']==result['seq']
                    with guard:completed.append((owner,key,result['seq']))
                    break
                except httpx.HTTPError as error:
                    if isinstance(error,httpx.HTTPStatusError) and error.response.status_code<500:raise
                    with guard:retries.append(type(error).__name__)
                    if time.monotonic()>=deadline:raise TimeoutError('Recovery retry deadline') from error
                    time.sleep(.2)
            time.sleep(.15)
with socket.socket() as probe:probe.bind(('127.0.0.1',8105))
began=time.monotonic()
try:
    service=start()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(worker,i) for i in range(4)]
        until=time.monotonic()+60
        while len(completed)<12:
            if time.monotonic()>until:raise TimeoutError('No write progress')
            time.sleep(.05)
        at_kill=len(completed);stop(service);time.sleep(.6);service=start()
        for future in futures:future.result(timeout=90)
    stop(service)
    with sqlite3.connect(env['EVENT_DB']) as db:
        requests=db.execute('SELECT owner,key,seq FROM requests').fetchall()
        event_count=db.execute('SELECT COUNT(*) FROM events').fetchone()[0]
    assert len(completed)==len(requests)==80 and event_count==80
    assert set(completed)==set(requests) and len(set((owner,seq) for owner,_,seq in requests))==80
    assert retries and 0<at_kill<80
    report={'passed':['Service killed after partial progress while four clients were writing','Clients reauthenticated after in-memory session loss and retried stable idempotency keys','Eighty acknowledged logical writes correspond to exactly eighty durable request records and eighty events; explicit duplicate submissions reused sequence IDs'],'clients':4,'logical_writes':80,'completed_at_kill':at_kill,'retry_observations':len(retries),'elapsed_seconds':round(time.monotonic()-began,2),'limitations':'One forced process outage in a bounded local run, not long endurance, disk corruption, distributed cache, machine power-loss or cloud certification.'}
    (ROOT/'recovery-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
finally:
    for p in reversed(processes):stop(p)
    for log in logs:log.close()
