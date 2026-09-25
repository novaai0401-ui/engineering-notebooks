"""Loopback-only teaching backend for a real NGINX experiment; not a production server."""
import argparse,json,os,secrets,time,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--ready',required=True);p.add_argument('--release',required=True);args=p.parse_args()
token=os.environ['LAB_TOKEN'];writes=0;lock=threading.Lock()
class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def log_message(self,*args):pass
    def reply(self,status,data):
        body=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def authorized(self):
        if not secrets.compare_digest(self.headers.get('Authorization',''),'Bearer '+token):
            self.reply(401,{'error':'unauthorized'});return False
        return True
    def do_GET(self):
        if self.path=='/health':self.reply(200,{'ready':True});return
        if not self.authorized():return
        if self.path=='/stream':
            self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Connection','close');self.end_headers()
            self.wfile.write(b'data: first\n\n');self.wfile.flush()
            deadline=time.monotonic()+8
            while not Path(args.release).exists() and time.monotonic()<deadline:time.sleep(.02)
            self.wfile.write(b'data: second\n\n');self.wfile.flush();self.close_connection=True;return
        self.reply(200,{'instance':args.name,'writes':writes,'forwarded_for':self.headers.get('X-Forwarded-For')})
    def do_POST(self):
        global writes
        if not self.authorized():return
        size=int(self.headers.get('Content-Length','0'))
        if size>1024:self.reply(413,{'error':'too large'});self.close_connection=True;return
        self.rfile.read(size)
        with lock:writes+=1
        self.reply(503,{'instance':args.name,'effect_applied':True})
server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
Path(args.ready).write_text(str(server.server_port))
server.serve_forever()
