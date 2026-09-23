package learning;
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.jdbc.core.JdbcTemplate;
import jakarta.persistence.*;
import org.hibernate.SessionFactory;
import javax.sql.DataSource;
import java.sql.Connection;
@SpringBootTest(properties={"spring.datasource.url=jdbc:h2:mem:persistence;DB_CLOSE_DELAY=-1","coach.password=test-password-not-for-deployment","coach.service-token=test-service-token","coach.worker-enabled=false","spring.jpa.properties.hibernate.generate_statistics=true"})
class PersistenceTests {
 @Autowired CourseRepository courses; @Autowired JdbcTemplate db; @Autowired Enrollment enrollment;
 @Autowired DataSource dataSource; @PersistenceContext EntityManager em; @Autowired EntityManagerFactory emf;
 @Test @Transactional void fetchJoinAvoidsNPlusOne(){
  db.update("delete from lesson");db.update("delete from course");
  for(int i=1;i<=3;i++){db.update("insert into course(id,title,version) values(?,?,0)",i,"Course "+i);db.update("insert into lesson(id,title,course_id) values(?,?,?)",i,"Lesson",i);}
  em.clear();var stats=emf.unwrap(SessionFactory.class).getStatistics();stats.clear();
  courses.findAll().forEach(c->assertEquals(1,c.lessons.size()));long naive=stats.getPrepareStatementCount();
  em.clear();stats.clear();courses.withLessons().forEach(c->assertEquals(1,c.lessons.size()));long joined=stats.getPrepareStatementCount();
  assertEquals(4,naive);assertEquals(1,joined);
 }
 @Test void transactionalOutboxRollsBackTogether(){
  assertThrows(IllegalStateException.class,()->enrollment.addCourseAndEvent(100,true));
  assertEquals(0,db.queryForObject("select count(*) from course where id=100",Integer.class));
  assertEquals(0,db.queryForObject("select count(*) from outbox where payload='course-created:100'",Integer.class));
  enrollment.addCourseAndEvent(101,false);
  assertEquals(1,db.queryForObject("select count(*) from outbox where payload='course-created:101'",Integer.class));
 }
 @Test void optimisticVersionRejectsStaleUpdate(){
  courses.saveAndFlush(new Course(200,"Original"));
  Course first=courses.findById(200L).orElseThrow(),stale=courses.findById(200L).orElseThrow();
  first.title="First update";courses.saveAndFlush(first);stale.title="Stale update";
  assertThrows(org.springframework.orm.ObjectOptimisticLockingFailureException.class,()->courses.saveAndFlush(stale));
 }
 @Test void readCommittedHidesUncommittedData()throws Exception{
  try(var a=dataSource.getConnection();var b=dataSource.getConnection()){
   a.setAutoCommit(false);b.setAutoCommit(false);b.setTransactionIsolation(Connection.TRANSACTION_READ_COMMITTED);
   a.createStatement().executeUpdate("insert into course(id,title,version) values(300,'Uncommitted',0)");
   try(var result=b.createStatement().executeQuery("select count(*) from course where id=300")){result.next();assertEquals(0,result.getInt(1));}
   a.commit();
   try(var result=b.createStatement().executeQuery("select count(*) from course where id=300")){result.next();assertEquals(1,result.getInt(1));}b.rollback();
  }
 }
}
