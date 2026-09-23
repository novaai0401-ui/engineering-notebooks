package learning;
import java.util.*;
import org.apache.activemq.broker.BrokerService;
import org.apache.activemq.security.*;
public final class BrokerRuntime {
 public static void run()throws Exception{
  String password=System.getenv("COACH_BROKER_PASSWORD");
  if(password==null || password.length()<20)throw new IllegalArgumentException("Provide a random broker password");
  BrokerService broker=new BrokerService();broker.setBrokerName("study-coach");broker.setUseJmx(false);
  broker.setPersistent(true);broker.setDataDirectory(System.getenv().getOrDefault("COACH_BROKER_DATA","./broker-data"));
  broker.setPlugins(new org.apache.activemq.broker.BrokerPlugin[]{new SimpleAuthenticationPlugin(List.of(new AuthenticationUser("coach",password,"workers")))});
  broker.addConnector(System.getenv().getOrDefault("COACH_BROKER_BIND","tcp://127.0.0.1:61629"));
  broker.start();broker.waitUntilStarted();Runtime.getRuntime().addShutdownHook(new Thread(()->{try{broker.stop();}catch(Exception ignored){}}));
  new java.util.concurrent.CountDownLatch(1).await();
 }
}
