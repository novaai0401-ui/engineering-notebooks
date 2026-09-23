"""Loopback study server smoke and path-boundary checks; no LAN publication."""
import http.client,json,threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from study_server import Handler,resolve_resource
server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
try:
    client=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
    for route in ['/','/29-databases-for-fullstack-and-ai.html','/30-rag-patterns-and-user-defined-flows.html','/30-rag-patterns-and-user-defined-flows.ipynb']:
        client.request('GET',route);response=client.getresponse();data=response.read();assert response.status==200 and len(data)>100
        assert response.getheader('X-Content-Type-Options')=='nosniff'
    for route in ['/.runtime/private.json','/.venv/pyvenv.cfg','/labs/kafka-lab/target/classes/private.txt','/%2e%2e/secret.txt','/%2eenv','/labs/','/missing.html']:
        client.request('GET',route);response=client.getresponse();response.read();assert response.status==404,(route,response.status)
    assert resolve_resource('/..%5c..%5csecret.txt') is None
    client.close()
    report={'passed':['Index, database HTML, RAG HTML and Jupyter download served over real loopback HTTP','Hidden/runtime/dependency directories, traversal attempts and directory listing denied'],'limitations':'Loopback tests only. LAN/mobile connectivity depends on the device, trusted Wi-Fi and firewall; no physical phone test was performed.'}
    Path(__file__).with_name('study-server-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
finally:server.shutdown();server.server_close();thread.join(timeout=5)
