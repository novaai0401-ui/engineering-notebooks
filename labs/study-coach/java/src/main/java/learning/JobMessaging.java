package learning;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.jms.annotation.JmsListener;
import org.springframework.jms.core.JmsTemplate;
import org.springframework.dao.DuplicateKeyException;
import tools.jackson.databind.json.JsonMapper;
import java.util.Map;
@Component @Profile("broker")
public class JobMessaging {
 final Jobs jobs;final Worker worker;final JmsTemplate jms;final JsonMapper json=JsonMapper.builder().build();
 public JobMessaging(Jobs jobs,Worker worker,JmsTemplate jms){this.jobs=jobs;this.worker=worker;this.jms=jms;}
 @Scheduled(fixedDelay=1000) public void relay(){
  long now=System.currentTimeMillis();
  jobs.database().update("update jobs set status='failed',last_error='attempt budget exhausted' where status in ('running','retry') and lease_until<? and attempt>=3",now);
  // Reconcile expired/unclaimed work even if broker redelivery was exhausted.
  // Re-publication is safe because claims, terminal results and inbox IDs are durable.
  jobs.database().update("update job_events set published=false where published=true and job_id in (select id from jobs where status in ('pending','retry','running') and lease_until<=? and created_at<? and attempt<3)",now,now-5000);
  // Publishing may repeat after a crash; durable inbox/result checks make duplicates harmless.
  for(var row:jobs.database().queryForList("select event_id,job_id from job_events where published=false fetch first 20 rows only")){
   try{
    String event=(String)row.get("event_id");
    jms.convertAndSend("coach.jobs",json.writeValueAsString(Map.of("event",event,"job",row.get("job_id"))));
    jobs.database().update("update job_events set published=true where event_id=?",event);
   }catch(Exception unavailable){break;}
  }
 }
 @JmsListener(destination="coach.jobs",concurrency="2-4") public void consume(String payload){
  var message=json.readTree(payload);String event=message.get("event").asText(),job=message.get("job").asText();
  if(jobs.database().queryForObject("select count(*) from job_inbox where event_id=?",Integer.class,event)>0)return;
  worker.runJob(job);
  String status=jobs.database().queryForObject("select status from jobs where id=?",String.class,job);
  if(!Jobs.terminal(status))throw new IllegalStateException("retry when job lease or backoff permits");
  try{jobs.database().update("insert into job_inbox(event_id,handled_at) values(?,?)",event,System.currentTimeMillis());}
  catch(DuplicateKeyException duplicate){/* result and receipt were already committed */}
 }
}
