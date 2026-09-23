"""Start Docker only in the task-owned WSL lab; daemon exposes a Unix socket only."""
import json,subprocess,time
from pathlib import Path
NAME='EngineeringNotebookLab-13e66a98';ROOT=Path(__file__).resolve().parents[1]
def run(args,**kw):return subprocess.run(['wsl','-d',NAME,'--exec']+args,capture_output=True,text=True,**kw)
if run(['/usr/bin/docker','info'],timeout=20).returncode:
 runtime=ROOT/'.runtime';runtime.mkdir(exist_ok=True)
 # Keep a WSL client attached to the daemon; a detached shell can disappear on distro idle shutdown.
 with (runtime/'docker-daemon.log').open('w',encoding='utf-8') as log:
  daemon=subprocess.Popen(['wsl','-d',NAME,'--exec','/usr/bin/env','PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','/usr/bin/dockerd','--host=unix:///var/run/docker.sock'],stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
 for _ in range(120):
  probe=run(['/usr/bin/docker','info','--format','{{json .ServerVersion}}'],timeout=10)
  if probe.returncode==0:break
  time.sleep(.5)
 else:
  raise RuntimeError('Docker daemon unavailable; inspect .runtime/docker-daemon.log')
version=run(['/usr/bin/docker','version','--format','{{json .Server}}'],timeout=20);version.check_returncode()
report={'status':'available','distribution':NAME,'server':json.loads(version.stdout),'scope':'Lab-owned Linux daemon; Unix socket only. Stop the named WSL distribution after tests.'}
(ROOT/'labs/docker-runtime-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
