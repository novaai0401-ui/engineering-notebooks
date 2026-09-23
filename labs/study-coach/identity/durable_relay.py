"""Bounded durable signed-logout delivery. Private TLS/network deployment is separate."""
import base64,hashlib,json,os,sqlite3,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import parse_qs
import httpx,jwt
from contextlib import contextmanager
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
EVENT='http://schemas.openid.net/event/backchannel-logout'
class Journal:
    def __init__(self,path,key,public_key,issuer,audience,targets):
        self.path=path;self.cipher=AESGCM(key);self.public_key=public_key;self.issuer=issuer;self.audience=audience;self.targets=targets
        with self.connect() as db:db.executescript('PRAGMA journal_mode=WAL; CREATE TABLE IF NOT EXISTS events(jti TEXT PRIMARY KEY,digest TEXT NOT NULL,cipher BLOB NOT NULL,expires REAL NOT NULL); CREATE TABLE IF NOT EXISTS delivery(jti TEXT,target TEXT,done INTEGER DEFAULT 0,attempts INTEGER DEFAULT 0,next REAL DEFAULT 0,PRIMARY KEY(jti,target));')
    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=10)
        try:
            with db:yield db
        finally:db.close()
    def accept(self,token):
        claims=jwt.decode(token,self.public_key,algorithms=['RS256'],audience=self.audience,issuer=self.issuer,options={'require':['iss','aud','iat','jti']})
        if not isinstance(claims['jti'],str) or not claims['jti'] or any(k in claims and not isinstance(claims[k],str) for k in ('sid','sub')):raise ValueError('Invalid identifier types')
        if 'nonce' in claims or not isinstance(claims.get('events'),dict) or EVENT not in claims['events'] or not (claims.get('sid') or claims.get('sub')):raise ValueError('Invalid logout claims')
        if time.time()-claims['iat']>300:raise ValueError('Logout token too old')
        deadline=min(float(claims.get('exp',claims['iat']+300)),claims['iat']+300)
        digest=hashlib.sha256(token.encode()).hexdigest();nonce=os.urandom(12)
        encrypted=nonce+self.cipher.encrypt(nonce,token.encode(),claims['jti'].encode())
        with self.connect() as db:
            previous=db.execute('SELECT digest FROM events WHERE jti=?',(claims['jti'],)).fetchone()
            if previous:
                if previous[0]!=digest:raise ValueError('Event identifier reused with different content')
                return False
            db.execute('INSERT INTO events VALUES(?,?,?,?)',(claims['jti'],digest,encrypted,deadline))
            db.executemany('INSERT INTO delivery(jti,target) VALUES(?,?)',[(claims['jti'],target) for target in self.targets])
        return True
    def deliver(self):
        with self.connect() as db:rows=db.execute('SELECT d.jti,d.target,e.cipher,e.expires,d.attempts FROM delivery d JOIN events e USING(jti) WHERE d.done=0 AND d.next<=? LIMIT 20',(time.time(),)).fetchall()
        for jti,target,encrypted,expires,attempts in rows:
            if time.time()>=expires:
                with self.connect() as db:db.execute('UPDATE delivery SET done=-1 WHERE jti=? AND target=?',(jti,target))
                continue
            token=self.cipher.decrypt(encrypted[:12],encrypted[12:],jti.encode()).decode()
            try:delivered=200<=httpx.post(target,data={'logout_token':token},timeout=2).status_code<300
            except httpx.HTTPError:delivered=False
            with self.connect() as db:db.execute('UPDATE delivery SET done=?,attempts=attempts+1,next=? WHERE jti=? AND target=?',(int(delivered),time.time()+min(5,2**min(attempts,3)),jti,target))
    def status(self):
        with self.connect() as db:return {'pending':db.execute('SELECT COUNT(*) FROM delivery WHERE done=0').fetchone()[0],'delivered':db.execute('SELECT COUNT(*) FROM delivery WHERE done=1').fetchone()[0],'expired':db.execute('SELECT COUNT(*) FROM delivery WHERE done=-1').fetchone()[0]}
def serve(journal,port):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path!='/health':self.send_error(404);return
            self.send_response(200);self.end_headers();self.wfile.write(json.dumps(journal.status()).encode())
        def do_POST(self):
            try:
                length=int(self.headers.get('Content-Length','0'))
                if self.path!='/logout' or not 1<=length<=32768:raise ValueError('Invalid request')
                token=parse_qs(self.rfile.read(length).decode(),strict_parsing=True).get('logout_token',[])
                if len(token)!=1:raise ValueError('Expected one token')
                journal.accept(token[0])
            except (ValueError,jwt.PyJWTError):self.send_error(400);return
            self.send_response(202);self.end_headers()
        def log_message(self,*args):pass
    def worker():
        while True:
            try:journal.deliver()
            except sqlite3.OperationalError:time.sleep(1)
            time.sleep(.2)
    threading.Thread(target=worker,daemon=True).start()
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
if __name__=='__main__':
    from pathlib import Path
    journal=Journal(os.environ['RELAY_DB'],base64.urlsafe_b64decode(os.environ['RELAY_KEY']),Path(os.environ['RELAY_PUBLIC_KEY']).read_bytes(),os.environ['RELAY_ISSUER'],os.environ['RELAY_AUDIENCE'],json.loads(os.environ['RELAY_TARGETS']))
    serve(journal,int(os.environ.get('RELAY_PORT','18108')))
