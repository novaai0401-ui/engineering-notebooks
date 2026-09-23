package learning;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;
@SpringBootApplication @EnableScheduling
public class CoachApplication {
 public static void main(String[] args) throws Exception {
  if(args.length>0 && args[0].equals("--broker-only")){BrokerRuntime.run();return;}
  SpringApplication.run(CoachApplication.class,args);
 }
}
