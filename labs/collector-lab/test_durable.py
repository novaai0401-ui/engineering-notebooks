"""Real collector retries an unavailable OTLP sink, whose committed traces survive restart."""
import hashlib,json,secrets,socket,sqlite3,subprocess,sys,time,tarfile
from pathlib import Path
import httpx
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
ROOT=Path(__file__).resolve().parent;RUNTIME=ROOT.parents[1]/'.runtime';RUN=RUNTIME/('durable-telemetry-'+secrets.token_hex(4));RUN.mkdir()
exe=RUNTIME/'otelcol-0.161.0/otelcol.exe'
persistent='--persistent' in sys.argv
if persistent:
 archive=RUNTIME/'otelcol-contrib_0.161.0_windows_amd64.tar.gz'
 if not archive.exists():
  with httpx.stream('GET','https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v0.161.0/'+archive.name,follow_redirects=True,timeout=120) as response:
   response.raise_for_status()
   with archive.open('wb') as output:
    for chunk in response.iter_bytes():output.write(chunk)
 assert hashlib.sha256(archive.read_bytes()).hexdigest()=='fd1a6d23aa7855efc4fc12e4ee2c21b410e0a35c85587a07def7746eec9cea24'
 install=RUNTIME/'otelcol-contrib-0.161.0';install.mkdir(exist_ok=True)
 with tarfile.open(archive) as bundle:bundle.extractall(install,filter='data')
 exe=next(install.rglob('otelcol-contrib.exe'))
for port in (14318,14319):
 with socket.socket() as probe:probe.bind(('127.0.0.1',port))
config=RUN/'config.yaml'
config.write_text('''receivers:
  otlp:
    protocols:
      http:
        endpoint: 127.0.0.1:14318
exporters:
  otlp_http:
    endpoint: http://127.0.0.1:14319
    compression: none
    retry_on_failure:
      initial_interval: 1s
      max_interval: 3s
      max_elapsed_time: 120s
    sending_queue:
      enabled: true
      num_consumers: 1
      queue_size: 100
service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [otlp_http]
''',encoding='utf-8')
if persistent:
 storage=RUN/'queue';storage.mkdir()
 text=config.read_text(encoding='utf-8').replace('      queue_size: 100','      queue_size: 100\n      storage: file_storage').replace('service:\n','extensions:\n  file_storage:\n    directory: '+str(storage).replace('\\','/')+'\nservice:\n  extensions: [file_storage]\n')
 config.write_text(text,encoding='utf-8')
subprocess.run([str(exe),'validate','--config',str(config)],check=True,capture_output=True,timeout=30)
processes=[];logs=[];provider=TracerProvider()
def start(args,port):
 stream=(RUN/f'{len(logs)}.log').open('w');logs.append(stream)
 p=subprocess.Popen(list(map(str,args)),stdout=stream,stderr=stream,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));processes.append(p)
 for _ in range(200):
  if p.poll() is not None:raise RuntimeError('Owned service exited')
  try:
   with socket.create_connection(('127.0.0.1',port),.2):return p
  except OSError:time.sleep(.2)
 raise TimeoutError('startup')
def stop(p):
 if p.poll() is None:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True);p.wait(timeout=20)
try:
 collector=start([exe,'--config',config],14318)
 provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint='http://127.0.0.1:14318/v1/traces',timeout=10)))
 ids=[]
 for index in range(5):
  with provider.get_tracer('durability').start_as_current_span(f'durable-{index}') as span:ids.append(format(span.get_span_context().trace_id,'032x'))
 provider.force_flush();time.sleep(2)
 if persistent:
  stop(collector)
  collector=start([exe,'--config',config],14318)
 sink=start([sys.executable,ROOT/'durable_sink.py',RUN/'traces.db'],14319)
 until=time.monotonic()+60
 while httpx.get('http://127.0.0.1:14319/count',timeout=3).json()['count']!=5:
  if time.monotonic()>until:raise TimeoutError('Queued traces not delivered')
  time.sleep(.5)
 stop(sink);stop(collector)
 sink=start([sys.executable,ROOT/'durable_sink.py',RUN/'traces.db'],14319)
 assert httpx.get('http://127.0.0.1:14319/count',timeout=3).json()['count']==5
 with sqlite3.connect(RUN/'traces.db') as db:assert {row[0] for row in db.execute('SELECT trace_id FROM spans')}==set(ids)
 report={'passed':['Actual OTLP collector accepted five spans while downstream was unavailable','Collector retry delivered all five spans when downstream recovered','Hard sink restart retained all exact trace IDs in SQLite'],'limitations':'Durable teaching sink, not Tempo/Jaeger/Grafana. Collector queue is memory-only: a collector crash before delivery can lose queued spans. No replicated storage, retention, authorization, TLS or disk-loss test.'}
 if persistent:
  report['passed'].append('Contrib collector killed and restarted while destination remained offline; file_storage queue recovered every trace')
  report['archive_sha256']='fd1a6d23aa7855efc4fc12e4ee2c21b410e0a35c85587a07def7746eec9cea24'
  report['limitations']='Pinned contrib collector 0.161.0 with real file_storage queue and durable teaching SQLite sink. No Tempo/Jaeger/Grafana, replicated storage, retention, TLS or disk-loss test. Process crashes are not whole-machine power failures.'
 (ROOT/('persistent-report.json' if persistent else 'durable-report.json')).write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
finally:
 provider.shutdown()
 for p in reversed(processes):stop(p)
 for log in logs:log.close()
