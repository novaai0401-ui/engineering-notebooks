package learning;
import java.net.URI;
import java.net.http.*;
import java.time.Duration;
import java.util.*;
import java.io.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import tools.jackson.databind.json.JsonMapper;
@Component
public class Worker {
 final Jobs jobs; final String token,url; final long leaseMs; final boolean enabled;
 final Telemetry telemetry;
 final io.micrometer.core.instrument.MeterRegistry meters;
 @Value("${coach.ai-read-timeout-ms:2000}") int readTimeout;
 @Value("${coach.ai-deadline-ms:8000}") long deadlineMs;
 final JsonMapper json=JsonMapper.builder().build();
 public Worker(Jobs jobs,@Value("${coach.service-token}")String token,@Value("${coach.ai-url}")String url,
  @Value("${coach.lease-ms}")long leaseMs,@Value("${coach.worker-enabled}")boolean enabled,Telemetry telemetry,io.micrometer.core.instrument.MeterRegistry meters){this.jobs=jobs;this.token=token;this.url=url;this.leaseMs=leaseMs;this.enabled=enabled;this.telemetry=telemetry;this.meters=meters;}
 @Scheduled(fixedDelay=250) public void tick(){if(enabled)runOne();}
 public boolean runOne(){return runJob(null);}
 public boolean runJob(String target){
  long now=System.currentTimeMillis();
  // Expired leases are reclaimable. Three failed claims are terminal, even after crashes.
  jobs.database().update("update jobs set status='failed',last_error='attempt budget exhausted' where status in ('running','retry') and lease_until<? and attempt>=3",now);
  String selection="select id,owner_name from jobs where status in ('pending','retry','running') and lease_until<=? and attempt<3";
  var due=target==null?jobs.database().queryForList(selection+" order by created_at fetch first 1 rows only",now):jobs.database().queryForList(selection+" and id=?",now,target);
  if(due.isEmpty())return false;
  String id=(String)due.get(0).get("ID"),user=(String)due.get(0).get("OWNER_NAME"),fence=UUID.randomUUID().toString();
  int claimed=jobs.database().update("update jobs set status='running',attempt=attempt+1,lease_token=?,lease_until=?,answer_text='',last_error='' where id=? and status in ('pending','retry','running') and lease_until<=? and attempt<3",fence,now+leaseMs,id,now);
  if(claimed==0)return false;
  long began=System.nanoTime();
  var span=telemetry.tracer.spanBuilder("job.execute").setAttribute("job.id",id).startSpan();
  try (var traceScope=span.makeCurrent()) {
   var connection=(java.net.HttpURLConnection)URI.create(url).toURL().openConnection();
   connection.setConnectTimeout(2000);connection.setReadTimeout(readTimeout);connection.setRequestMethod("POST");connection.setDoOutput(true);
   connection.setRequestProperty("Authorization","Bearer "+token);connection.setRequestProperty("Content-Type","application/json");
   telemetry.inject(connection);
   try {
   try(var output=connection.getOutputStream()){output.write(json.writeValueAsString(Map.of("question",jobs.get(id,user).question(),"user",user)).getBytes(java.nio.charset.StandardCharsets.UTF_8));}
   if(connection.getResponseCode()!=200)throw new IOException("upstream status");
   boolean done=false;
   try(var input=new BufferedReader(new InputStreamReader(connection.getInputStream(),java.nio.charset.StandardCharsets.UTF_8))){
   String line;
   while((line=input.readLine())!=null){
    if(System.nanoTime()-began>deadlineMs*1_000_000L)throw new IOException("job deadline");
    var item=json.readTree(line);
    if(item.has("error"))throw new IOException("model validation failed");
    if(item.has("delta")){
     int accepted=jobs.database().update("update jobs set answer_text=answer_text || ?,lease_until=? where id=? and status='running' and lease_token=?",item.get("delta").asText(),System.currentTimeMillis()+leaseMs,id,fence);
     if(accepted==0)return true;
    }
    if(item.has("done") && item.get("done").asBoolean())done=true;
   }}
   if(!done)throw new IOException("incomplete stream");
   jobs.database().update("update jobs set status='done',lease_token=null where id=? and status='running' and lease_token=?",id,fence);
   }finally{connection.disconnect();}
  }catch(Exception ex){
   span.setStatus(io.opentelemetry.api.trace.StatusCode.ERROR,"job execution failed");meters.counter("coach.job.failures").increment();
   jobs.database().update("update jobs set status=case when attempt>=3 then 'failed' else 'retry' end,last_error='AI service unavailable or incomplete',lease_until=?,lease_token=null where id=? and status='running' and lease_token=?",System.currentTimeMillis()+1000,id,fence);
   if(ex instanceof InterruptedException)Thread.currentThread().interrupt();
  }finally {meters.timer("coach.job.duration").record(System.nanoTime()-began,java.util.concurrent.TimeUnit.NANOSECONDS);span.end();System.out.println("job="+id+" duration_ms="+(System.nanoTime()-began)/1_000_000);}
  return true;
 }
}
