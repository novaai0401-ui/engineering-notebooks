import os,secrets,socket,subprocess,sys,time
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parent;run=ROOT.parents[1]/'.runtime'/('realtime-browser-'+secrets.token_hex(4));run.mkdir(parents=True)
env=dict(os.environ,EVENT_PASSWORD=secrets.token_urlsafe(28),EVENT_DB=str(run/'events.db'))
with socket.socket() as probe:probe.bind(('127.0.0.1',8105))
with (run/'server.log').open('w') as log:
    p=subprocess.Popen([sys.executable,'-m','uvicorn','app:app','--host','127.0.0.1','--port','8105','--ws-max-size','4096'],cwd=ROOT,env=env,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        for _ in range(120):
            if p.poll() is not None:raise RuntimeError('Server exited')
            try:
                if httpx.get('http://127.0.0.1:8105/health',timeout=1).status_code==200:break
            except httpx.HTTPError:pass
            time.sleep(.5)
        else:raise TimeoutError('Server startup')
        browser_log=run/'browser.log'
        with browser_log.open('w',encoding='utf-8') as output:
            browser=subprocess.Popen(['node',str(ROOT/'browser.mjs')],env=env,stdout=output,stderr=output,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            try:
                if browser.wait(timeout=240)!=0:raise RuntimeError('Browser assertions failed; '+str(browser_log))
            finally:
                if browser.poll() is None:
                    subprocess.run(['taskkill','/PID',str(browser.pid),'/T','/F'],capture_output=True);browser.wait(timeout=15)
        print(browser_log.read_text(encoding='utf-8'))
    finally:
        if p.poll() is None:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True);p.wait(timeout=15)
