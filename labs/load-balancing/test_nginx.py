"""Real NGINX and two subprocess backends, run on Linux/isolated WSL. No cloud resources."""
import collections,json,os,secrets,signal,socket,subprocess,sys,tempfile,time,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parent;RUN=Path(tempfile.mkdtemp(prefix='notebook-nginx-'));token=secrets.token_urlsafe(32)
processes=[];streams=[];proxy=None;report={'status':'failed','passed':[]}
def stop(p):
    if p and p.poll() is None:
        p.terminate()
        try:p.wait(timeout=10)
        except subprocess.TimeoutExpired:p.kill();p.wait()
def call(port,path='/who',method='GET',authorized=True,headers=None):
    h={'Authorization':'Bearer '+token} if authorized else {}
    h.update(headers or {});request=urllib.request.Request(f'http://127.0.0.1:{port}'+path,headers=h,method=method,data=b'{}' if method=='POST' else None)
    try:
        with urllib.request.urlopen(request,timeout=5) as response:return response.status,json.load(response)
    except urllib.error.HTTPError as error:
        body=error.read()
        try:data=json.loads(body)
        except ValueError:data={'error':'proxy error page'}
        return error.code,data
def start_backend(name):
    ready=RUN/(name+'.port');log=(RUN/(name+'.log')).open('w');streams.append(log)
    p=subprocess.Popen([sys.executable,str(ROOT/'backend.py'),'--name',name,'--ready',str(ready),'--release',str(RUN/'release')],env=dict(os.environ,LAB_TOKEN=token),stdout=log,stderr=log);processes.append(p)
    deadline=time.monotonic()+15
    while not ready.exists():
        if p.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Backend startup failed')
        time.sleep(.05)
    return p,int(ready.read_text())
def start_proxy(a,b,weighted=False):
    global proxy
    stop(proxy)
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    config=RUN/'nginx.conf'
    config.write_text(f'''worker_processes 1;
pid {RUN}/nginx.pid;
error_log {RUN}/nginx-error.log warn;
events {{ worker_connections 128; }}
http {{
  access_log off;
  client_body_temp_path {RUN}/body;
  proxy_temp_path {RUN}/proxy;
  upstream classroom {{
    server 127.0.0.1:{a} weight={3 if weighted else 1} max_fails=1 fail_timeout=30s;
    server 127.0.0.1:{b} weight=1 max_fails=1 fail_timeout=30s;
  }}
  server {{
    listen 127.0.0.1:{port};
    location = /ready {{ return 200 "ready"; }}
    location / {{
      proxy_pass http://classroom;
      proxy_http_version 1.1;
      proxy_set_header Connection "";
      proxy_set_header X-Forwarded-For $remote_addr;
      proxy_connect_timeout 1s;
      proxy_read_timeout 10s;
      proxy_next_upstream error timeout http_503;
      proxy_next_upstream_tries 2;
      proxy_buffering off;
    }}
  }}
}}
''')
    subprocess.run(['nginx','-t','-p',str(RUN)+'/', '-c',str(config)],check=True,capture_output=True)
    log=(RUN/('master-'+secrets.token_hex(2)+'.log')).open('w');streams.append(log)
    proxy=subprocess.Popen(['nginx','-p',str(RUN)+'/', '-c',str(config),'-g','daemon off;'],stdout=log,stderr=log)
    deadline=time.monotonic()+15
    while True:
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/ready',timeout=1):return port
        except OSError:
            if proxy.poll() is not None or time.monotonic()>deadline:raise RuntimeError('NGINX readiness failed')
            time.sleep(.05)
try:
    report['nginx_version']=subprocess.run(['nginx','-v'],capture_output=True,text=True,check=True).stderr.strip()
    pa,a=start_backend('A');pb,b=start_backend('B');port=start_proxy(a,b)
    assert call(port,authorized=False)[0]==401
    distribution=collections.Counter(call(port)[1]['instance'] for _ in range(20));assert distribution=={'A':10,'B':10}
    report['passed'].append('Actual round-robin proxy distributed 20 authenticated requests equally; anonymous request rejected')
    assert call(port,headers={'X-Forwarded-For':'203.0.113.99'})[1]['forwarded_for']=='127.0.0.1'
    report['passed'].append('Proxy replaced forged forwarding header with the observed loopback peer')
    request=urllib.request.Request(f'http://127.0.0.1:{port}/stream',headers={'Authorization':'Bearer '+token})
    with urllib.request.urlopen(request,timeout=3) as stream:
        assert stream.readline()==b'data: first\n'
        (RUN/'release').write_text('continue')
        assert b'data: second' in stream.read()
    report['passed'].append('First SSE event reached client before backend was permitted to produce its second event')
    port=start_proxy(a,b,weighted=True)
    distribution=collections.Counter(call(port)[1]['instance'] for _ in range(40));assert distribution=={'A':30,'B':10}
    report['weighted_counts']=dict(distribution);report['passed'].append('Real weighted round robin produced 30:10 requests for configured 3:1 weights')
    port=start_proxy(a,b)
    assert call(port,method='POST')[0]==503
    assert call(a,'/stats')[1]['writes']+call(b,'/stats')[1]['writes']==1
    report['passed'].append('POST that applied an effect then returned 503 was not replayed on the other backend')
    port=start_proxy(a,b);stop(pa)
    assert all(call(port)[1]['instance']=='B' for _ in range(12))
    report['passed'].append('Killing backend A allowed safe GET traffic to reach B through passive failure detection/retry')
    stop(pb);assert call(port)[0] in (502,504)
    report['passed'].append('Both backends unavailable produced an explicit proxy error, not fabricated success')
    report.update(status='passed',scope='One local NGINX process and two Python backend processes with loopback bearer authentication. No public TLS, WebSocket tunnel, L4 proxy, active health checker, multi-host failure or cloud certification. Algorithm/queue simulations are separate notebook cells.')
finally:
    stop(proxy)
    for p in processes:stop(p)
    for stream in streams:stream.close()
    (ROOT/'test-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
