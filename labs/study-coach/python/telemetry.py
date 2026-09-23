import json,os,time,threading
from pathlib import Path
from opentelemetry import trace
from opentelemetry.propagate import extract
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor,SpanExporter,SpanExportResult,BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from prometheus_client import Counter,Histogram

class JsonFileExporter(SpanExporter):
    def __init__(self,path):self.path=Path(path);self.lock=threading.Lock()
    def export(self,spans):
        with self.lock,self.path.open('a',encoding='utf-8') as file:
            for span in spans:
                file.write(json.dumps({'service':'python','name':span.name,'trace_id':f'{span.context.trace_id:032x}','span_id':f'{span.context.span_id:016x}','parent_span_id':f'{span.parent.span_id:016x}' if span.parent else None,'start_ns':span.start_time,'end_ns':span.end_time,'status':span.status.status_code.name})+'\n')
        return SpanExportResult.SUCCESS
    def shutdown(self):pass
provider=TracerProvider(resource=Resource.create({'service.name':'study-coach-python'}))
if os.getenv('COACH_TRACE_FILE'):provider.add_span_processor(SimpleSpanProcessor(JsonFileExporter(os.environ['COACH_TRACE_FILE'])))
if os.getenv('COACH_OTLP_ENDPOINT'):
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=os.environ['COACH_OTLP_ENDPOINT']+'/v1/traces')))
tracer=provider.get_tracer('study-coach')
requests=Counter('coach_ai_requests','AI HTTP requests',['route','status'])
duration=Histogram('coach_ai_duration_seconds','AI HTTP duration',['route'])
class TraceMiddleware:
    def __init__(self,app):self.app=app
    async def __call__(self,scope,receive,send):
        if scope['type']!='http':return await self.app(scope,receive,send)
        route=scope['path'] if scope['path'] in ('/answer','/health','/metrics') else 'other'
        headers={k.decode():v.decode() for k,v in scope['headers']};status=500;began=time.monotonic()
        async def traced_send(message):
            nonlocal status
            if message['type']=='http.response.start':status=message['status']
            await send(message)
        with tracer.start_as_current_span('ai'+route,context=extract(headers),kind=trace.SpanKind.SERVER):
            try:await self.app(scope,receive,traced_send)
            finally:requests.labels(route,str(status)).inc();duration.labels(route).observe(time.monotonic()-began)
