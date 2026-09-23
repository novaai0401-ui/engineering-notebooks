"""Fetch the pinned official Windows Prometheus archive for the local monitoring lab."""
import hashlib,zipfile
from pathlib import Path
import httpx
root=Path(__file__).resolve().parents[2]/'.runtime';root.mkdir(exist_ok=True)
name='prometheus-3.14.0.windows-amd64';archive=root/(name+'.zip')
expected='e57fbb99e4d0bc734d2f2b3aeb68c02fba38862259dc99a95c27ea46d9ccba0a'
if not archive.exists():
 with httpx.stream('GET','https://github.com/prometheus/prometheus/releases/download/v3.14.0/'+name+'.zip',follow_redirects=True,timeout=120) as response:
  response.raise_for_status()
  with archive.open('wb') as file:
   for chunk in response.iter_bytes():file.write(chunk)
assert hashlib.sha256(archive.read_bytes()).hexdigest()==expected,'archive checksum mismatch'
if not (root/name/'prometheus.exe').exists():
 with zipfile.ZipFile(archive) as source:source.extractall(root)
print('Verified Prometheus 3.14.0 archive and extracted private runtime.')
