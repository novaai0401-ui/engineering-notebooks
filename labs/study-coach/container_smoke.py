"""Reference container CI smoke test; does not launch or claim a deployment itself."""
import os,secrets,time
import httpx
base='http://127.0.0.1:8091'
for attempt in range(120):
    try:
        if httpx.get(base+'/health',timeout=2).status_code==200:break
    except httpx.HTTPError:pass
    time.sleep(1)
else:raise TimeoutError('container readiness')
with httpx.Client(base_url=base,auth=('alice',os.environ['COACH_PASSWORD']),timeout=20) as c:
    response=c.get('/api/csrf');response.raise_for_status();csrf=response.json();c.headers[csrf['header']]=csrf['token']
    response=c.post('/api/jobs',headers={'Idempotency-Key':secrets.token_hex(12)},json={'question':'checkpoint'});response.raise_for_status();jid=response.json()['id']
    c.post('/api/jobs/'+jid+'/approve').raise_for_status()
    for attempt in range(60):
        response=c.get('/api/jobs/'+jid);response.raise_for_status();job=response.json()
        if job['status']=='done':assert '[checkpoint]' in job['answer'];print('Container integration smoke passed');break
        if job['status']=='failed':raise AssertionError(job['error'])
        time.sleep(1)
    else:raise TimeoutError('container job completion')
