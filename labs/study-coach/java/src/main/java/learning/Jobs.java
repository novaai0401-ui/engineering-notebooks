package learning;
import java.util.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
@Service
public class Jobs {
 final JdbcTemplate db;
 public Jobs(JdbcTemplate db){this.db=db;}
 public JdbcTemplate database(){return db;}
 public record Job(String id,String owner,String question,String status,String answer,int attempt,String error){}
 public Job get(String id,String user){
  return db.query("select * from jobs where id=? and owner_name=?",(r,n)->new Job(r.getString("id"),r.getString("owner_name"),r.getString("question"),r.getString("status"),r.getString("answer_text"),r.getInt("attempt"),r.getString("last_error")),id,user)
   .stream().findFirst().orElseThrow(()->new ResponseStatusException(HttpStatus.NOT_FOUND));
 }
 public Job create(String user,String key,String question){
  if(key==null || !key.matches("[a-zA-Z0-9-]{8,80}") || question==null || question.isBlank() || question.length()>500)
   throw new ResponseStatusException(HttpStatus.BAD_REQUEST,"invalid key or question");
  String id=UUID.randomUUID().toString();
  try {db.update("insert into jobs(id,owner_name,request_key,question,status,answer_text,created_at) values(?,?,?,?,'approval','',?)",id,user,key,question,System.currentTimeMillis());}
  catch(DuplicateKeyException ex){
   id=db.queryForObject("select id from jobs where owner_name=? and request_key=?",String.class,user,key);
   if(!get(id,user).question().equals(question))throw new ResponseStatusException(HttpStatus.CONFLICT,"key already used for another question");
  }
  return get(id,user);
 }
 @org.springframework.transaction.annotation.Transactional
 public Job approve(String id,String user){
  get(id,user);
  int changed=db.update("update jobs set status='pending' where id=? and owner_name=? and status='approval'",id,user);
  if(changed==1)db.update("insert into job_events(event_id,job_id) values(?,?)",UUID.randomUUID().toString(),id);
  return get(id,user);
 }
 public Job cancel(String id,String user){
  get(id,user);
  db.update("update jobs set status='cancelled',lease_token=null where id=? and owner_name=? and status in ('approval','pending','running','retry')",id,user);
  return get(id,user);
 }
 public static boolean terminal(String status){return Set.of("done","failed","cancelled").contains(status);}
}
