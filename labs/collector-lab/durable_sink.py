"""Loopback teaching OTLP trace sink; commits before acknowledging, no production API."""
import json,sqlite3,sys
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
DB=sys.argv[1]
def connect():return sqlite3.connect(DB,timeout=10)
db=connect();db.execute('CREATE TABLE IF NOT EXISTS spans(trace_id TEXT,span_id TEXT,name TEXT,PRIMARY KEY(trace_id,span_id))');db.commit();db.close()
class Handler(BaseHTTPRequestHandler):
 def do_POST(self):
  if self.path!='/v1/traces':self.send_error(404);return
  length=int(self.headers.get('Content-Length','0'))
  if not 0<length<=1048576:self.send_error(413);return
  try:request=ExportTraceServiceRequest.FromString(self.rfile.read(length))
  except Exception:self.send_error(400);return
  db=connect()
  try:
   with db:
    for resource in request.resource_spans:
     for scope in resource.scope_spans:
      for span in scope.spans:db.execute('INSERT OR IGNORE INTO spans VALUES(?,?,?)',(span.trace_id.hex(),span.span_id.hex(),span.name))
  finally:db.close()
  self.send_response(200);self.send_header('Content-Type','application/x-protobuf');self.send_header('Content-Length','0');self.end_headers()
 def do_GET(self):
  if self.path!='/count':self.send_error(404);return
  db=connect()
  try:count=db.execute('SELECT COUNT(*) FROM spans').fetchone()[0]
  finally:db.close()
  self.send_response(200);self.end_headers();self.wfile.write(json.dumps({'count':count}).encode())
 def log_message(self,*args):pass
ThreadingHTTPServer(('127.0.0.1',14319),Handler).serve_forever()
