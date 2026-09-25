"""Actual Keycloak dual-secret acceptance and explicit retirement in a disposable realm."""
import json,os,secrets,socket,subprocess,time
from pathlib import Path
import httpx
from identity.admin import IdentityAdmin
ROOT=Path(__file__).resolve().parent;RUNTIME=ROOT.parents[1]/'.runtime';KC=RUNTIME/'keycloak-26.7.4'
source=max([p for p in RUNTIME.glob('identity-cluster-*') if (p/'private-test-settings.json').exists()],key=lambda p:p.stat().st_mtime)
env=dict(os.environ,**json.loads((source/'private-test-settings.json').read_text()))
run=RUNTIME/('secret-overlap-'+secrets.token_hex(4));run.mkdir();realm='overlap-'+secrets.token_hex(4);admin=None;created=False
report={'status':'failed','checks':[],'scope':'Actual Keycloak 26.7.4 client-credentials exchanges in a disposable realm, local HTTP. Tests provider overlap and retirement, not a rolling Spring/browser deployment or production zero-downtime certification.'}
with socket.socket() as probe:probe.bind(('127.0.0.1',8094))
with (run/'keycloak.log').open('w') as log:
    process=subprocess.Popen([str(KC/'bin/kc.bat'),'start-dev','--features=client-secret-rotation'],cwd=KC,env=env,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        deadline=time.monotonic()+360
        while True:
            if process.poll() is not None:raise RuntimeError('Keycloak exited')
            try:
                if httpx.get('http://127.0.0.1:8094/realms/master',timeout=2).status_code==200:break
            except httpx.HTTPError:pass
            if time.monotonic()>deadline:raise TimeoutError('Keycloak readiness')
            time.sleep(.5)
        admin=IdentityAdmin('http://127.0.0.1:8094',env['KC_BOOTSTRAP_ADMIN_USERNAME'],env['KC_BOOTSTRAP_ADMIN_PASSWORD'])
        admin.http.post('/admin/realms',json={'realm':realm,'enabled':True,'accessTokenLifespan':1800}).raise_for_status();created=True;base='/admin/realms/'+realm
        profile={'profiles':[{'name':'classroom-overlap','executors':[{'executor':'secret-rotation','configuration':{'expiration-period':3600,'rotated-expiration-period':600,'remaining-rotation-period':60}}]}]}
        admin.http.put(base+'/client-policies/profiles',json=profile).raise_for_status()
        policy={'policies':[{'name':'classroom-overlap','enabled':True,'conditions':[{'condition':'any-client','configuration':{}}],'profiles':['classroom-overlap']}]}
        admin.http.put(base+'/client-policies/policies',json=policy).raise_for_status()
        admin.http.post(base+'/clients',json={'clientId':'rotation-lab','enabled':True,'publicClient':False,'serviceAccountsEnabled':True,'standardFlowEnabled':False,'protocol':'openid-connect'}).raise_for_status()
        client=admin.http.get(base+'/clients',params={'clientId':'rotation-lab'}).json()[0];path=base+'/clients/'+client['id']
        old=admin.http.get(path+'/client-secret').json()['value']
        endpoint='http://127.0.0.1:8094/realms/'+realm+'/protocol/openid-connect/token'
        def exchange(secret):return httpx.post(endpoint,data={'grant_type':'client_credentials','client_id':'rotation-lab','client_secret':secret},timeout=10)
        response=exchange(old);response.raise_for_status();issued_token=response.json()['access_token']
        before=httpx.post(endpoint+'/introspect',data={'token':issued_token,'client_id':'rotation-lab','client_secret':old},timeout=10);before.raise_for_status()
        report['token_active_before_rotation']=before.json()['active']
        response=admin.http.post(path+'/client-secret');response.raise_for_status();new=response.json()['value'];assert old!=new
        for _ in range(10):
            exchange(old).raise_for_status();exchange(new).raise_for_status()
        report['checks'].append('Twenty real token exchanges accepted both old and new secrets during configured overlap')
        admin.http.delete(path+'/client-secret/rotated').raise_for_status()
        assert exchange(old).status_code==401
        exchange(new).raise_for_status();report['checks'].append('Retired secret rejected; new secret still authenticates')
        response=httpx.post(endpoint+'/introspect',data={'token':issued_token,'client_id':'rotation-lab','client_secret':new},timeout=10);response.raise_for_status();report['token_active_after_retirement']=response.json()['active']
        report['checks'].append('Recorded token introspection before rotation and after retirement separately from client authentication')
        report['token_observation_limit']='Introspection status is recorded separately; inactive before rotation cannot establish rotation-induced revocation. Authentication overlap/retirement uses token-endpoint responses.'
        report['status']='passed'
    except Exception as error:report['error']=type(error).__name__;raise
    finally:
        try:
            if admin:
                if created:admin.http.delete('/admin/realms/'+realm).raise_for_status()
                admin.close()
        finally:
            if process.poll() is None:subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True);process.wait(timeout=20)
        (ROOT/'secret-overlap-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
