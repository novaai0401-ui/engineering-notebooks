import asyncio, json, os, secrets, socket, subprocess, sys, time
from pathlib import Path
from fastmcp import Client
import httpx
root=Path(__file__).resolve().parent
env=os.environ.copy()
for name in ['MCP_ALICE_READ_TOKEN','MCP_ALICE_WRITE_TOKEN','MCP_BOB_READ_TOKEN']:
    env[name]=secrets.token_urlsafe(32)
with socket.socket() as probe:
    probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
env['MCP_PORT']=str(port)
url=f'http://127.0.0.1:{port}/mcp'
results=[]
async def check():
    with httpx.Client() as http:
        assert http.post(url,json={}).status_code==401
        assert http.post(url,json={},headers={'Authorization':'Bearer invalid'}).status_code==401
    results.append('missing and invalid credentials rejected over HTTP')
    async with Client(url,auth=env['MCP_ALICE_READ_TOKEN'],timeout=15) as client:
        data=(await client.call_tool('read_note',{})).data
        assert data['owner']=='alice' and 'Bob' not in data['text']
        results.append('Alice read is owner-scoped')
        denied=False
        try: await client.call_tool('write_note',{'text':'forbidden'})
        except Exception: denied=True
        assert denied
        results.append('reader cannot directly call the write tool')
        assert await client.read_resource('study://principles')
        assert (await client.get_prompt('explain',{'topic':'leases'})).messages
        results.append('resource and prompt work over HTTP')
    async with Client(url,auth=env['MCP_BOB_READ_TOKEN'],timeout=15) as client:
        assert (await client.call_tool('read_note',{})).data['owner']=='bob'
        results.append('Bob sees his own note')
    async with Client(url,auth=env['MCP_ALICE_WRITE_TOKEN'],timeout=15) as client:
        assert (await client.call_tool('write_note',{'text':'Alice revised note'})).data['saved']
        assert (await client.call_tool('read_note',{})).data['text']=='Alice revised note'
        invalid=False
        try:await client.call_tool('write_note',{'text':''})
        except Exception:invalid=True
        assert invalid
        results.append('editor writes and malformed note is rejected')
    async with Client(url,auth=env['MCP_ALICE_READ_TOKEN'],timeout=15,init_timeout=15) as client:
        began=time.monotonic();timed_out=False
        try:await client.call_tool('slow_read',{'seconds':1.5},timeout=0.1)
        except Exception as error:
            timed_out='timeout' in type(error).__name__.lower() or 'timed out' in str(error).lower() or 'timeout' in str(error).lower()
        assert timed_out and time.monotonic()-began<1.4
        results.append('client deadline stops waiting for slow tool')
with (root/'server-test.log').open('w',encoding='utf-8') as log:
    process=subprocess.Popen([sys.executable,str(root/'server.py')],env=env,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        for _ in range(120):
            if process.poll() is not None:raise RuntimeError('MCP server failed; inspect server-test.log')
            try:
                with socket.create_connection(('127.0.0.1',port),timeout=.1):break
            except OSError:time.sleep(.25)
        else:raise TimeoutError('MCP startup')
        asyncio.run(check())
        (root/'test-report.json').write_text(json.dumps({'passed':results},indent=2))
        print(json.dumps({'checks_passed':len(results),'checks':results},indent=2))
    finally:
        if os.name=='nt':subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True)
        else:process.terminate()
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:process.kill();process.wait()

