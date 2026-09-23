package learning;
import java.nio.file.*;
import java.util.*;
import org.springframework.stereotype.Component;
import jakarta.annotation.PreDestroy;
import io.opentelemetry.api.trace.*;
import io.opentelemetry.sdk.OpenTelemetrySdk;
import io.opentelemetry.sdk.trace.*;
import io.opentelemetry.sdk.trace.data.SpanData;
import io.opentelemetry.sdk.trace.export.*;
import io.opentelemetry.sdk.common.CompletableResultCode;
import io.opentelemetry.context.Context;
import io.opentelemetry.api.trace.propagation.W3CTraceContextPropagator;
import io.opentelemetry.exporter.otlp.http.trace.OtlpHttpSpanExporter;
import tools.jackson.databind.json.JsonMapper;
@Component
public class Telemetry {
 final SdkTracerProvider provider;public final Tracer tracer;
 public Telemetry(){
  var builder=SdkTracerProvider.builder();String file=System.getenv("COACH_TRACE_FILE");
  if(file!=null)builder.addSpanProcessor(SimpleSpanProcessor.create(new SpanExporter(){
   public synchronized CompletableResultCode export(Collection<SpanData> spans){
    try{var mapper=JsonMapper.builder().build();for(var span:spans)Files.writeString(Path.of(file),mapper.writeValueAsString(Map.of("service","java","name",span.getName(),"trace_id",span.getTraceId(),"span_id",span.getSpanId(),"parent_span_id",span.getParentSpanId(),"start_ns",span.getStartEpochNanos(),"end_ns",span.getEndEpochNanos(),"status",span.getStatus().getStatusCode().name()))+"\n",StandardOpenOption.CREATE,StandardOpenOption.APPEND);return CompletableResultCode.ofSuccess();}
    catch(Exception e){return CompletableResultCode.ofFailure();}
   }
   public CompletableResultCode flush(){return CompletableResultCode.ofSuccess();}
   public CompletableResultCode shutdown(){return CompletableResultCode.ofSuccess();}
  }));
  String endpoint=System.getenv("COACH_OTLP_ENDPOINT");
  if(endpoint!=null)builder.addSpanProcessor(BatchSpanProcessor.builder(OtlpHttpSpanExporter.builder().setEndpoint(endpoint+"/v1/traces").build()).build());
  provider=builder.build();tracer=OpenTelemetrySdk.builder().setTracerProvider(provider).build().getTracer("study-coach");
 }
 public void inject(java.net.HttpURLConnection connection){W3CTraceContextPropagator.getInstance().inject(Context.current(),connection,(carrier,key,value)->carrier.setRequestProperty(key,value));}
 @PreDestroy public void close(){provider.close();}
}
