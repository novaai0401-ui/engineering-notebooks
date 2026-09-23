"""Exercise real Python + Java HTTP services and the React browser journey."""
import json, os, re, secrets, shutil, socket, subprocess, sys, tempfile, time
from pathlib import Path
from contextlib import contextmanager
import httpx
ROOT=Path(__file__).resolve().parent
env=os.environ.copy()
env['COACH_PASSWORD']=secrets.token_urlsafe(24)
env['COACH_SERVICE_TOKEN']=secrets.token_urlsafe(32)
env['COACH_LEASE_MS']='3000'
checks=[];processes=[];handles=[]
flags=getattr(subprocess,'CREATE_NO_WINDOW',0)

def start(command,cwd,name):
    log=(ROOT/(name+'.log')).open('w',encoding='utf-8');handles.append(log)
    process=subprocess.Popen(command,cwd=cwd,env=env,stdout=log,stderr=log,creationflags=flags)
    processes.append(process);return process
def stop(process):
    if process.poll() is None:
        if os.name=='nt':subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True)
        else:process.kill()
        process.wait(timeout=10)
def ready(url,process):
    deadline=time.monotonic()+120
    while time.monotonic()<deadline:
        if process.poll() is not None:raise RuntimeError(f'Service exited before ready: {url}; inspect logs')
        try:
            if httpx.get(url,timeout=1).status_code==200:return
        except httpx.HTTPError:pass
        time.sleep(.25)
    raise TimeoutError(url)
def wait_job(client,id,predicate,timeout=25):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        response=client.get('/api/jobs/'+id);response.raise_for_status();job=response.json()
        if predicate(job):return job
        time.sleep(.05)
    raise AssertionError(f'job did not reach expected state: {job}')
@contextmanager
def sign_in(user='alice'):
    with httpx.Client(base_url='http://127.0.0.1:8091',auth=(user,env['COACH_PASSWORD']),timeout=30) as client:
        response=client.get('/api/csrf');response.raise_for_status();csrf=response.json()
        client.headers[csrf['header']]=csrf['token']
        yield client
def create(client,question='What is a checkpoint?',key=None):
    response=client.post('/api/jobs',headers={'Idempotency-Key':key or secrets.token_hex(12)},json={'question':question})
    response.raise_for_status();return response.json()

for port in [8091,8092]:
    with socket.socket() as probe:
        try:probe.bind(('127.0.0.1',port))
        except OSError:raise SystemExit(f'Port {port} is already occupied; no process was stopped')
try:
    with tempfile.TemporaryDirectory(prefix='coach-e2e-') as temp:
        env['COACH_DB']='jdbc:h2:file:'+str(Path(temp)/'coach').replace('\\','/')+';WRITE_DELAY=0'
        python_cmd=[sys.executable,'-m','uvicorn','coach_ai:app','--host','127.0.0.1','--port','8092']
        properties=subprocess.run(['java','-XshowSettings:properties','-version'],capture_output=True,text=True,check=True)
        java_home=re.search(r'java.home\s*=\s*(.+)',properties.stderr).group(1).strip()
        java_exe=str(Path(java_home)/'bin'/('java.exe' if os.name=='nt' else 'java'))
        java_cmd=[java_exe,'-jar',str(ROOT/'java/target/study-coach-1.0.0.jar')]
        py=start(python_cmd,ROOT/'python','python-system');ready('http://127.0.0.1:8092/health',py)
        java=start(java_cmd,ROOT/'java','java-system');ready('http://127.0.0.1:8091/health',java)
        assert httpx.get('http://127.0.0.1:8091/api/me').status_code==401
        with httpx.Client(base_url='http://127.0.0.1:8091',auth=('alice',env['COACH_PASSWORD'])) as no_csrf:
            assert no_csrf.get('/api/me').status_code==200
            rejected=no_csrf.post('/api/jobs',headers={'Idempotency-Key':'missing-csrf'},json={'question':'hello'})
            # CSRF can reject before Basic authentication runs on this new request.
            assert rejected.status_code in (401,403),rejected.status_code
        assert httpx.post('http://127.0.0.1:8092/answer',json={'question':'hello','user':'alice'}).status_code==401
        checks.append('Java authentication, CSRF and Python service authentication enforce boundaries')
        with sign_in() as alice,sign_in('bob') as bob:
            key=secrets.token_hex(12);job=create(alice,key=key)
            assert create(alice,key=key)['id']==job['id']
            assert alice.post('/api/jobs',headers={'Idempotency-Key':key},json={'question':'changed'}).status_code==409
            assert bob.get('/api/jobs/'+job['id']).status_code==404
            assert bob.post('/api/jobs/'+job['id']+'/approve').status_code==404
            checks.append('Idempotency binds payload; another owner cannot read or approve')
            assert job['status']=='approval' and job['attempt']==0
            alice.post('/api/jobs/'+job['id']+'/approve').raise_for_status()
            snapshots=[]
            with alice.stream('GET','/api/jobs/'+job['id']+'/events') as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line.startswith('data:'):snapshots.append(json.loads(line[5:]))
            assert len(snapshots)>1 and snapshots[-1]['status']=='done'
            assert any(0<len(x['answer'])<len(snapshots[-1]['answer']) for x in snapshots)
            assert '[checkpoint]' in snapshots[-1]['answer']
            checks.append('Approval starts background work; real SSE contains partial and final answers')
            private=create(alice,'Alice private plan')
            alice.post('/api/jobs/'+private['id']+'/approve').raise_for_status()
            result=wait_job(alice,private['id'],lambda x:x['status']=='done')
            assert 'Bob private plan' not in result['answer'] and '[alice-plan]' in result['answer']
            checks.append('Retrieval filters documents by authenticated owner before ranking')
            cancelled=create(alice);alice.post('/api/jobs/'+cancelled['id']+'/cancel').raise_for_status()
            alice.post('/api/jobs/'+cancelled['id']+'/approve').raise_for_status()
            assert alice.get('/api/jobs/'+cancelled['id']).json()['status']=='cancelled'
            checks.append('Cancelled jobs cannot be reapproved')
        npm=shutil.which('npm.cmd') or shutil.which('npm')
        browser=subprocess.run([npm,'test'],cwd=ROOT/'frontend',env=env,text=True,capture_output=True,timeout=600)
        (ROOT/'browser-tests.log').write_text(browser.stdout+browser.stderr,encoding='utf-8')
        if browser.returncode:raise RuntimeError('Browser tests failed; inspect browser-tests.log')
        checks.append('Chromium, Firefox and WebKit journeys passed, including keyboard approval, cancellation, injected failures, reconnect and axe checks')
        with sign_in() as alice:
            recovery=create(alice,'Explain a checkpoint and a transaction')
            alice.post('/api/jobs/'+recovery['id']+'/approve').raise_for_status()
            wait_job(alice,recovery['id'],lambda x:x['status']=='running')
            stop(java)
        java=start(java_cmd,ROOT/'java','java-restarted');ready('http://127.0.0.1:8091/health',java)
        with sign_in() as alice:
            recovered=wait_job(alice,recovery['id'],lambda x:x['status']=='done')
            assert recovered['attempt']>=2
            checks.append('Hard process kill followed by same-database restart recovers an expired running job')
            stop(py)
            failure=create(alice);alice.post('/api/jobs/'+failure['id']+'/approve').raise_for_status()
            failed=wait_job(alice,failure['id'],lambda x:x['status']=='failed')
            assert failed['attempt']==3 and failed['error']
            checks.append('Upstream outage reaches a bounded three-attempt failure state')
            py=start(python_cmd,ROOT/'python','python-restarted');ready('http://127.0.0.1:8092/health',py)
            restored=create(alice);alice.post('/api/jobs/'+restored['id']+'/approve').raise_for_status()
            assert wait_job(alice,restored['id'],lambda x:x['status']=='done')['answer']
            checks.append('New work succeeds after the upstream service returns')
        # Close processes before Windows removes the temporary H2 files.
        for process in processes:stop(process)
    (ROOT/'system-report.json').write_text(json.dumps({'passed':checks},indent=2),encoding='utf-8')
    print(json.dumps({'checks_passed':len(checks),'checks':checks},indent=2))
finally:
    for process in processes:stop(process)
    for handle in handles:handle.close()
