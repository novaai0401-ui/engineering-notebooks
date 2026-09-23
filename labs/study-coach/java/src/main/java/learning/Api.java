package learning;
import java.security.Principal;
import java.util.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.web.csrf.CsrfToken;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
@RestController
public class Api {
 @org.springframework.beans.factory.annotation.Value("${coach.auth-mode:basic}") String authMode;
 final Jobs jobs;
 public Api(Jobs jobs){this.jobs=jobs;}
 @GetMapping("/health") public Map<String,String> health(){return Map.of("status","up");}
 @GetMapping("/config") public Map<String,String> config(){return Map.of("authMode",authMode);}
 @GetMapping("/api/admin/status") public Map<String,String> admin(){return Map.of("administration","authorized");}
 @GetMapping("/api/csrf") public Map<String,String> csrf(CsrfToken token){return Map.of("header",token.getHeaderName(),"token",token.getToken(),"parameter",token.getParameterName());}
 @GetMapping("/api/me") public Map<String,String> me(Principal p){return Map.of("user",p.getName());}
 public record Input(String question){}
 @PostMapping("/api/jobs") public Jobs.Job create(Principal p,@RequestHeader("Idempotency-Key")String key,@RequestBody Input body){return jobs.create(p.getName(),key,body.question());}
 @GetMapping("/api/jobs/{id}") public Jobs.Job get(Principal p,@PathVariable String id){return jobs.get(id,p.getName());}
 @PostMapping("/api/jobs/{id}/approve") public Jobs.Job approve(Principal p,@PathVariable String id){return jobs.approve(id,p.getName());}
 @PostMapping("/api/jobs/{id}/cancel") public Jobs.Job cancel(Principal p,@PathVariable String id){return jobs.cancel(id,p.getName());}
 @GetMapping(value="/api/jobs/{id}/events",produces="text/event-stream") public SseEmitter events(Principal p,@PathVariable String id){
  String user=p.getName(); jobs.get(id,user); var emitter=new SseEmitter(25000L);
  Thread.startVirtualThread(()->{
   try {long deadline=System.nanoTime()+20_000_000_000L;String previous="";
    while(System.nanoTime()<deadline){var job=jobs.get(id,user);String marker=job.status()+":"+job.attempt()+":"+job.answer();
     if(!marker.equals(previous)){emitter.send(SseEmitter.event().name("snapshot").data(job));previous=marker;}
     if(Jobs.terminal(job.status()))break;Thread.sleep(100);
    }emitter.complete();
   }catch(Exception e){emitter.completeWithError(e);}
  });return emitter;
 }
 @GetMapping("/api/metrics") public Map<String,Object> metrics(Principal p){return Map.of("jobs",jobs.database().queryForList("select status,count(*) as total from jobs where owner_name=? group by status",p.getName()));}
}
