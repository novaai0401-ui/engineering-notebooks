"""Download a pinned official collector, verify digest, export one real OTLP span."""
from pathlib import Path
import hashlib,json,secrets,socket,subprocess,tarfile,time
import httpx
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
ROOT=Path(__file__).resolve().parent
RUNTIME=ROOT.parents[1]/'.runtime';RUNTIME.mkdir(exist_ok=True)
VERSION='0.161.0';DIGEST='d51435b421f78bcbb17200adc2ee802abf629bc77dcb2edd44c2566078515f08'
archive=RUNTIME/f'otelcol_{VERSION}_windows_amd64.tar.gz'
if not archive.exists():
    with httpx.stream('GET',f'https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v{VERSION}/{archive.name}',follow_redirects=True,timeout=120) as response:
        response.raise_for_status()
        with archive.open('wb') as output:
            for chunk in response.iter_bytes():output.write(chunk)
assert hashlib.sha256(archive.read_bytes()).hexdigest()==DIGEST
install=RUNTIME/f'otelcol-{VERSION}';install.mkdir(exist_ok=True)
with tarfile.open(archive) as bundle:bundle.extractall(install,filter='data')
exe=next(install.rglob('otelcol.exe'))
run=RUNTIME/('collector-'+secrets.token_hex(4));run.mkdir()
config=run/'collector.yaml'
config.write_text('''receivers:
  otlp:
    protocols:
      http:
        endpoint: 127.0.0.1:14318
processors:
  batch: {}
exporters:
  debug:
    verbosity: detailed
service:
  telemetry:
    logs:
      level: info
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [debug]
''',encoding='utf-8')
with socket.socket() as check:check.bind(('127.0.0.1',14318))
subprocess.run([str(exe),'validate','--config',str(config)],check=True,capture_output=True,timeout=30)
log=run/'collector.log';stream=log.open('w')
p=subprocess.Popen([str(exe),'--config',str(config)],stdout=stream,stderr=stream,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
provider=None
try:
    for _ in range(100):
        if p.poll() is not None:raise RuntimeError(log.read_text(encoding='utf-8'))
        try:
            with socket.create_connection(('127.0.0.1',14318),timeout=.2):break
        except OSError:time.sleep(.2)
    else:raise TimeoutError('collector startup')
    provider=TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint='http://127.0.0.1:14318/v1/traces',timeout=10)))
    with provider.get_tracer('classroom').start_as_current_span('classroom-real-otlp') as span:
        span.set_attribute('lesson.name','collector verification')
        trace_id=format(span.get_span_context().trace_id,'032x')
    provider.force_flush()
    for _ in range(100):
        output=log.read_text(encoding='utf-8')
        if trace_id in output and 'classroom-real-otlp' in output:break
        time.sleep(.2)
    else:raise AssertionError('Expected exported trace absent from collector debug output')
    report={'version':VERSION,'archive_sha256':DIGEST,'passed':['Official collector archive digest verified','Collector configuration validation passed','Python SDK exported a real OTLP/HTTP span and collector debug output contained its trace ID and name'],'limitations':'Local loopback HTTP and debug exporter only; no TLS/auth, durable telemetry backend, tail sampling, Grafana or collector outage/load validation.'}
    (ROOT/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
finally:
    if provider:provider.shutdown()
    if p.poll() is None:p.terminate();p.wait(timeout=15)
    stream.close()
