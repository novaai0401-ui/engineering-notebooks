"""Read-only classroom server. No installation beyond Python; no code execution endpoints."""
import argparse,mimetypes,socket
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote,urlsplit
ROOT=Path(__file__).resolve().parent
BLOCKED={'.runtime','.venv','node_modules','target','__pycache__','.git','data','build','test-results'}
EXTENSIONS={'.html','.css','.js','.mjs','.md','.ipynb','.json','.txt','.py','.java','.xml','.toml','.yaml','.yml','.sql','.png','.svg'}
def resolve_resource(url):
    relative=unquote(urlsplit(url).path).lstrip('/') or 'index.html'
    parts=Path(relative).parts
    if any(p.startswith('.') or p in BLOCKED for p in parts):return None
    path=(ROOT/relative).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file() or path.suffix.lower() not in EXTENSIONS:return None
    if any(p.startswith('.') or p in BLOCKED for p in path.relative_to(ROOT).parts):return None
    return path
class Handler(BaseHTTPRequestHandler):
    def do_HEAD(self):self.send_file(False)
    def do_GET(self):self.send_file(True)
    def send_file(self,body):
        path=resolve_resource(self.path)
        if path is None:self.send_error(404);return
        content=path.read_bytes()
        kind=mimetypes.guess_type(path.name)[0] or 'text/plain'
        if path.suffix in {'.py','.java','.md','.toml','.yaml','.yml','.sql','.txt'}:kind='text/plain; charset=utf-8'
        self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(content)))
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-cache');self.end_headers()
        if body:self.wfile.write(content)
    def log_message(self,fmt,*args):pass
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--lan',action='store_true',help='Allow devices on your trusted network to read the public learning files');parser.add_argument('--port',type=int,default=8765);args=parser.parse_args()
    host='0.0.0.0' if args.lan else '127.0.0.1'
    server=ThreadingHTTPServer((host,args.port),Handler)
    print(f'Laptop: http://127.0.0.1:{args.port}/',flush=True)
    if args.lan:
        addresses=sorted({entry[4][0] for entry in socket.getaddrinfo(socket.gethostname(),None,socket.AF_INET) if not entry[4][0].startswith('127.')})
        for address in addresses:print(f'Phone on the same trusted Wi-Fi: http://{address}:{args.port}/',flush=True)
        print('LAN mode has no login. It serves learning files only; use a private trusted network, not public port forwarding.',flush=True)
    print('Keep this terminal open. Press Ctrl+C to stop. Phone reading does not execute Java/Python labs.',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
