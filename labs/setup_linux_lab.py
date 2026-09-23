"""Import one task-owned Alpine WSL distribution; never enable OS features or reboot."""
import hashlib,json,subprocess
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1];RUNTIME=ROOT/'.runtime';RUNTIME.mkdir(exist_ok=True)
NAME='EngineeringNotebookLab-13e66a98';archive=RUNTIME/'alpine-minirootfs-3.22.1-x86_64.tar.gz';install=(RUNTIME/'wsl-alpine').resolve()
assert install.is_relative_to(RUNTIME.resolve())
digest='0e5cc5702ad72a4e151f219976ba946d50161c3acce210ef3b122a529aba1270'
def decode(raw):return raw.decode('utf-16-le' if b'\x00' in raw else 'utf-8',errors='replace')
listing=subprocess.run(['wsl','--list','--quiet'],capture_output=True,check=True);names=decode(listing.stdout).split()
if NAME not in names:
 if not archive.exists():
  response=httpx.get('https://dl-cdn.alpinelinux.org/alpine/v3.22/releases/x86_64/'+archive.name,timeout=90);response.raise_for_status();archive.write_bytes(response.content)
 assert hashlib.sha256(archive.read_bytes()).hexdigest()==digest
 install.mkdir(exist_ok=True)
 result=subprocess.run(['wsl','--import',NAME,str(install),str(archive),'--version','2'],capture_output=True,timeout=120)
 if result.returncode:
  report={'status':'blocked','action':'Import isolated WSL lab','diagnostic':decode(result.stdout+result.stderr),'changes_not_attempted':'No Windows feature enablement, reboot or global WSL settings change'}
  (ROOT/'labs/linux-runtime-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2));raise SystemExit(1)
result=subprocess.run(['wsl','-d',NAME,'--exec','cat','/etc/alpine-release'],capture_output=True,timeout=60,check=True)
report={'status':'available','distribution':NAME,'installation':str(install),'rootfs_sha256':digest,'alpine':decode(result.stdout).strip(),'scope':'Task-owned WSL 2 environment under excluded .runtime. Existing distributions and Windows features are unchanged. Stop only this distribution with wsl --terminate '+NAME+'.'}
(ROOT/'labs/linux-runtime-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
