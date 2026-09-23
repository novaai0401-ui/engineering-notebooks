"""Download the pinned official Keycloak archive into this project's private runtime."""
import hashlib,json,re,zipfile
from pathlib import Path
import httpx
root=Path(__file__).resolve().parents[2]/'.runtime'
root.mkdir(exist_ok=True)
version='26.7.4'
url=f'https://github.com/keycloak/keycloak/releases/download/{version}/keycloak-{version}.zip'
archive=root/f'keycloak-{version}.zip'
with httpx.Client(follow_redirects=True,timeout=120) as client:
    expected='a286e98b4296d4e75ee88d8527c7cd463b307caa022f088c9f22cffccc741fa1'
    if not archive.exists():
        with client.stream('GET',url) as response:
            response.raise_for_status()
            with archive.open('wb') as output:
                for chunk in response.iter_bytes():output.write(chunk)
    actual=hashlib.sha256(archive.read_bytes()).hexdigest()
    if actual!=expected:raise SystemExit('Archive checksum mismatch; not extracting')
    with zipfile.ZipFile(archive) as package:
        for name in package.namelist():
            target=(root/name).resolve()
            if not target.is_relative_to(root.resolve()):raise ValueError('archive path escapes runtime')
        package.extractall(root)
(root/'identity-download.json').write_text(json.dumps({'version':version,'url':url,'sha256':actual},indent=2))
print('Verified and extracted Keycloak',version)
