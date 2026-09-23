"""Fetch pinned official K3s binary and install only inside the task-owned WSL distro."""
import hashlib,json,subprocess
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1];binary=ROOT/'.runtime/k3s-v1.37.0';digest='39eed8f53f277497dfc2542f66eab0ed68a94dfc598946dbebfb50366916c7a2';name='EngineeringNotebookLab-13e66a98'
if not binary.exists():
 with httpx.stream('GET','https://github.com/k3s-io/k3s/releases/download/v1.37.0%2Bk3s1/k3s',follow_redirects=True,timeout=120) as response:
  response.raise_for_status()
  with binary.open('wb') as output:
   for chunk in response.iter_bytes():output.write(chunk)
assert hashlib.sha256(binary.read_bytes()).hexdigest()==digest
source='/mnt/'+binary.drive[0].lower()+'/'+binary.as_posix().split(':/',1)[1]
for command in [['/bin/cp',source,'/usr/local/bin/k3s'],['/bin/chmod','755','/usr/local/bin/k3s']]:subprocess.run(['wsl','-d',name,'--exec']+command,check=True,capture_output=True,timeout=30)
report={'version':'v1.37.0+k3s1','binary_sha256':digest,'distribution':name,'scope':'Official binary verified; installation alone is not a Kubernetes execution pass.'}
(ROOT/'labs/k3s-install-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
