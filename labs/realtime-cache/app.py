"""Authenticated local event journal with cache, SSE replay and bidirectional WebSockets."""
import asyncio,hashlib,hmac,json,os,secrets,sqlite3,time
from collections import OrderedDict
from pathlib import Path
from fastapi import FastAPI,Request,HTTPException,WebSocket,WebSocketDisconnect
from fastapi.responses import HTMLResponse,StreamingResponse,Response
from pydantic import BaseModel,Field
ORIGIN=os.getenv('EVENT_ORIGIN','http://127.0.0.1:8105');PASSWORD=os.environ['EVENT_PASSWORD']
db=sqlite3.connect(os.environ['EVENT_DB'],check_same_thread=False);db.execute('pragma journal_mode=WAL')
db.executescript('create table if not exists events(owner text,seq integer,text text,primary key(owner,seq));create table if not exists requests(owner text,key text,digest text,seq integer,primary key(owner,key));')
sessions={};app=FastAPI();RETENTION=50
class VersionCache:
    def __init__(self,capacity=16,ttl=10,clock=time.monotonic):self.items=OrderedDict();self.capacity=capacity;self.ttl=ttl;self.clock=clock;self.hits=0;self.misses=0
    def get(self,key,version):
        item=self.items.get(key)
        if item and item[0]==version and item[1]>self.clock():self.items.move_to_end(key);self.hits+=1;return item[2]
        self.items.pop(key,None);self.misses+=1;return None
    def put(self,key,version,value,current_version):
        if version!=current_version:return False
        self.items[key]=(version,self.clock()+self.ttl,value);self.items.move_to_end(key)
        while len(self.items)>self.capacity:self.items.popitem(last=False)
        return True
    def invalidate(self,key):self.items.pop(key,None)
cache=VersionCache();locks={name:asyncio.Lock() for name in ('alice','bob')}
def identity(token):
    session=sessions.get(token)
    if not session or session['expires']<=time.monotonic():raise HTTPException(401,'sign in again')
    return session
def authenticated(request):return identity(request.cookies.get('event_session'))
def mutation(request):
    s=authenticated(request)
    if request.headers.get('origin')!=ORIGIN or not hmac.compare_digest(request.headers.get('x-csrf-token',''),s['csrf']):raise HTTPException(403,'origin or CSRF rejected')
    return s
def latest(owner):return db.execute('select coalesce(max(seq),0) from events where owner=?',(owner,)).fetchone()[0]
def replay(owner,after):
    top=latest(owner)
    if after<0 or after>top:raise HTTPException(400,'invalid cursor')
    low=db.execute('select min(seq) from events where owner=?',(owner,)).fetchone()[0]
    if low is not None and after<low-1:raise HTTPException(409,'history expired; fetch snapshot and resume at its revision')
    return [{'seq':seq,'text':text} for seq,text in db.execute('select seq,text from events where owner=? and seq>? order by seq limit 20',(owner,after))]
def publish(owner,key,text):
    digest=hashlib.sha256(text.encode()).hexdigest()
    with db:
        # Acquire the database write reservation before reading the sequence or
        # idempotency record; per-process asyncio locks cannot serialize peers.
        db.execute('BEGIN IMMEDIATE')
        old=db.execute('select digest,seq from requests where owner=? and key=?',(owner,key)).fetchone()
        if old:
            if old[0]!=digest:raise HTTPException(409,'idempotency key reused with different content')
            return {'seq':old[1],'text':text,'duplicate':True}
        seq=latest(owner)+1
        db.execute('insert into events values(?,?,?)',(owner,seq,text));db.execute('insert into requests values(?,?,?,?)',(owner,key,digest,seq))
        db.execute('delete from events where owner=? and seq<=?',(owner,seq-RETENTION))
    cache.invalidate(owner);return {'seq':seq,'text':text,'duplicate':False}
class Login(BaseModel):user:str;password:str
class Message(BaseModel):key:str=Field(min_length=8,max_length=80);text:str=Field(min_length=1,max_length=500)
@app.get('/',response_class=HTMLResponse)
def page():return (Path(__file__).parent/'index.html').read_text(encoding='utf-8')
@app.get('/health')
def health():return {'status':'up'}
@app.post('/login')
async def login(body:Login,request:Request,response:Response):
    if request.headers.get('origin')!=ORIGIN:raise HTTPException(403,'origin rejected')
    if body.user not in locks or not hmac.compare_digest(body.password,PASSWORD):raise HTTPException(401,'invalid sign-in')
    token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(24);sessions[token]={'owner':body.user,'csrf':csrf,'expires':time.monotonic()+3600}
    response.set_cookie('event_session',token,httponly=True,samesite='strict',secure=ORIGIN.startswith('https:'),max_age=3600)
    return {'csrf':csrf,'owner':body.user}
@app.post('/logout')
async def logout(request:Request,response:Response):
    mutation(request);sessions.pop(request.cookies.get('event_session'),None);response.delete_cookie('event_session');return {'signed_out':True}
@app.post('/messages')
async def post(body:Message,request:Request):
    owner=mutation(request)['owner']
    async with locks[owner]:return publish(owner,body.key,body.text)
@app.get('/snapshot')
async def snapshot(request:Request):
    owner=authenticated(request)['owner']
    async with locks[owner]:
        version=latest(owner);etag='"'+owner+'-'+str(version)+'"'
        headers={'ETag':etag,'Cache-Control':'private, no-cache','Vary':'Cookie'}
        if request.headers.get('if-none-match')==etag:return Response(status_code=304,headers=headers)
        value=cache.get(owner,version)
        if value is None:
            value={'revision':version,'messages':[{'seq':s,'text':t} for s,t in db.execute('select seq,text from events where owner=? order by seq',(owner,))]}
            cache.put(owner,version,value,latest(owner))
        return Response(json.dumps(value),media_type='application/json',headers=headers)
@app.get('/events')
async def events(request:Request,after:int=0):
    token=request.cookies.get('event_session');owner=authenticated(request)['owner']
    try:cursor=int(request.headers.get('last-event-id',after))
    except ValueError:raise HTTPException(400,'invalid cursor')
    replay(owner,cursor)
    async def stream():
        nonlocal cursor
        deadline=time.monotonic()+3
        while time.monotonic()<deadline and not await request.is_disconnected():
            try:identity(token);rows=replay(owner,cursor)
            except HTTPException as error:
                yield 'event: reset\ndata: '+json.dumps({'reason':error.detail})+'\n\n';return
            for row in rows:
                cursor=row['seq'];yield f'id: {cursor}\nevent: message\ndata: '+json.dumps(row)+'\n\n'
            if not rows:yield ': keep-alive\n\n'
            await asyncio.sleep(.1)
    return StreamingResponse(stream(),media_type='text/event-stream',headers={'Cache-Control':'no-store','X-Accel-Buffering':'no'})
@app.websocket('/ws')
async def socket(ws:WebSocket):
    token=ws.cookies.get('event_session')
    try:
        if ws.headers.get('origin')!=ORIGIN:raise HTTPException(403)
        owner=identity(token)['owner'];cursor=int(ws.query_params.get('after','0'));replay(owner,cursor)
    except (HTTPException,ValueError):await ws.close(code=1008);return
    await ws.accept();deadline=time.monotonic()+120
    try:
        while time.monotonic()<deadline:
            try:identity(token);rows=replay(owner,cursor)
            except HTTPException:await ws.close(code=1008,reason='session or cursor invalid');return
            for row in rows:
                await asyncio.wait_for(ws.send_json({'type':'message',**row}),2);cursor=row['seq']
            try:message=await asyncio.wait_for(ws.receive_json(),.1)
            except asyncio.TimeoutError:continue
            if not isinstance(message,dict):raise ValueError('object required')
            if message.get('type')=='ping':await ws.send_json({'type':'pong'})
            elif message.get('type')=='publish':
                body=Message.model_validate(message)
                async with locks[owner]:publish(owner,body.key,body.text)
            else:await ws.close(code=1008,reason='unsupported command');return
        await ws.close(code=1001,reason='reconnect with cursor')
    except WebSocketDisconnect:pass
    except (ValueError,HTTPException):await ws.close(code=1008,reason='invalid message')
    except asyncio.TimeoutError:await ws.close(code=1013,reason='slow receiver')
