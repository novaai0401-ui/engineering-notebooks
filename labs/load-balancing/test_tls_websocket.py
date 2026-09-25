"""Actual NGINX TLS termination and authenticated WebSocket tunnel on loopback."""
import asyncio,json,os,secrets,socket,ssl,subprocess,tempfile,time
from pathlib import Path
from aiohttp import web,ClientSession,WSServerHandshakeError,ClientConnectorCertificateError
ROOT=Path(__file__).resolve().parent
def port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
async def main():
    report={'status':'failed','checks':[],'scope':'Real local TLS with an explicitly trusted test certificate and real WebSocket upgrade/proxy/reload. No public CA/domain, cloud ingress, or production session store.'}
    token=secrets.token_urlsafe(32);front=port();back=port();origin=f'https://localhost:{front}';proxy=None;runner=None
    with tempfile.TemporaryDirectory(prefix='notebook-tls-') as temp:
        run=Path(temp)
        async def ws(request):
            if not secrets.compare_digest(request.headers.get('Authorization',''),'Bearer '+token):raise web.HTTPUnauthorized()
            if request.headers.get('Origin')!=origin:raise web.HTTPForbidden()
            stream=web.WebSocketResponse(max_msg_size=1024,heartbeat=2);await stream.prepare(request)
            async for msg in stream:
                if msg.type==web.WSMsgType.TEXT:await stream.send_str('echo:'+msg.data)
            return stream
        try:
            subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost','-keyout',str(run/'key.pem'),'-out',str(run/'cert.pem')],check=True,capture_output=True)
            os.chmod(run/'key.pem',0o600)
            app=web.Application();app.router.add_get('/ws',ws);runner=web.AppRunner(app);await runner.setup();await web.TCPSite(runner,'127.0.0.1',back).start()
            config=run/'nginx.conf';config.write_text(f'''worker_processes 1;
pid {run}/nginx.pid;
error_log {run}/error.log warn;
events {{ worker_connections 128; }}
http {{
access_log off;
client_body_temp_path {run}/body;
proxy_temp_path {run}/proxy;
map $http_upgrade $connection_upgrade {{ default upgrade; '' close; }}
server {{
listen 127.0.0.1:{front} ssl;
ssl_certificate {run}/cert.pem;
ssl_certificate_key {run}/key.pem;
ssl_protocols TLSv1.2 TLSv1.3;
location = /health {{ return 200 'ready'; }}
location /ws {{
proxy_pass http://127.0.0.1:{back};
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection $connection_upgrade;
proxy_set_header X-Forwarded-For $remote_addr;
proxy_read_timeout 10s;
}}
}}
}}
''')
            base=['nginx','-p',str(run)+'/', '-c',str(config)]
            subprocess.run(base+['-t'],check=True,capture_output=True)
            with (run/'master.log').open('w') as log:
                proxy=subprocess.Popen(base+['-g','daemon off;'],stdout=log,stderr=log)
                context=ssl.create_default_context(cafile=str(run/'cert.pem'))
                async with ClientSession() as client:
                    for _ in range(100):
                        try:
                            async with client.get(origin+'/health',ssl=context) as response:
                                assert response.status==200;break
                        except OSError:await asyncio.sleep(.05)
                    else:raise TimeoutError('TLS readiness')
                    report['checks'].append('Trusted certificate and localhost hostname validation accepted')
                    try:await client.get(origin+'/health')
                    except ClientConnectorCertificateError:pass
                    else:raise AssertionError('Untrusted certificate unexpectedly accepted')
                    report['checks'].append('Untrusted certificate rejected; verification never disabled')
                    for headers,status in [({'Origin':origin},401),({'Origin':'https://evil.example','Authorization':'Bearer '+token},403)]:
                        try:await client.ws_connect(origin+'/ws',ssl=context,headers=headers)
                        except WSServerHandshakeError as error:assert error.status==status
                        else:raise AssertionError('Unauthorized WebSocket accepted')
                    report['checks'].append('Missing bearer token and hostile Origin rejected before upgrade')
                    async with client.ws_connect(origin+'/ws',ssl=context,headers={'Origin':origin,'Authorization':'Bearer '+token}) as stream:
                        await stream.send_str('before');assert (await stream.receive(timeout=5)).data=='echo:before'
                        subprocess.run(base+['-s','reload'],check=True,capture_output=True)
                        await asyncio.sleep(.3)
                        await stream.send_str('after');assert (await stream.receive(timeout=5)).data=='echo:after'
                    report['checks'].append('Bidirectional frames survive graceful NGINX configuration reload')
                report['status']='passed'
        finally:
            if proxy is not None:
                proxy.terminate()
                try:proxy.wait(timeout=5)
                except subprocess.TimeoutExpired:proxy.kill();proxy.wait()
            if runner is not None:await runner.cleanup()
            (ROOT/'tls-websocket-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
asyncio.run(main())
