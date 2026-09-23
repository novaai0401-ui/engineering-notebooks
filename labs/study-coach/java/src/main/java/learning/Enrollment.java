package learning;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.annotation.Transactional;
@Service
public class Enrollment {
 final JdbcTemplate db;
 public Enrollment(JdbcTemplate db){this.db=db;}
 @Transactional public void addCourseAndEvent(long id,boolean fail){
  db.update("insert into course(id,title,version) values(?,'Transactions',0)",id);
  db.update("insert into outbox(id,payload) values(?,?)",UUID.randomUUID().toString(),"course-created:"+id);
  if(fail)throw new IllegalStateException("simulate failure before commit");
 }
}
