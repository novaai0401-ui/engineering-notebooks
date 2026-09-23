package learning;
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.web.server.ResponseStatusException;
import java.util.UUID;
@SpringBootTest(properties={"spring.datasource.url=jdbc:h2:mem:jobs;DB_CLOSE_DELAY=-1","coach.password=test-password-not-for-deployment","coach.service-token=test-service-token","coach.worker-enabled=false"})
class JobsTests {
 @Autowired Jobs jobs;
 @Test void idempotencyAndPayloadConflict(){
  String key=UUID.randomUUID().toString();var a=jobs.create("alice",key,"Question");
  assertEquals(a.id(),jobs.create("alice",key,"Question").id());
  assertEquals(409,assertThrows(ResponseStatusException.class,()->jobs.create("alice",key,"Other")).getStatusCode().value());
 }
 @Test void ownershipAndCancel(){
  var a=jobs.create("alice",UUID.randomUUID().toString(),"Question");
  assertThrows(ResponseStatusException.class,()->jobs.get(a.id(),"bob"));
  assertEquals("cancelled",jobs.cancel(a.id(),"alice").status());
  assertEquals("cancelled",jobs.approve(a.id(),"alice").status());
 }
 @Test void staleLeaseCannotWrite(){
  var a=jobs.create("alice",UUID.randomUUID().toString(),"Question");
  jobs.database().update("update jobs set status='running',lease_token='new' where id=?",a.id());
  assertEquals(0,jobs.database().update("update jobs set answer_text='stale' where id=? and lease_token='old'",a.id()));
 }
 @Test void migrationsApplied(){
  assertEquals(4,jobs.database().queryForObject("select count(*) from \"flyway_schema_history\" where \"success\"=true and \"version\" is not null",Integer.class));
 }
}
