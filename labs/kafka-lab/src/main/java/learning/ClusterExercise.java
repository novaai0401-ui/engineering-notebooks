package learning;
import java.util.*;
import java.time.Duration;
import java.util.concurrent.TimeUnit;
import org.apache.kafka.clients.admin.*;
import org.apache.kafka.clients.producer.*;
import org.apache.kafka.clients.consumer.*;
import org.apache.kafka.common.TopicPartition;
public class ClusterExercise {
 static Properties props(){var p=new Properties();p.put("bootstrap.servers","127.0.0.1:19092,127.0.0.1:19094,127.0.0.1:19096");p.put("request.timeout.ms","10000");p.put("default.api.timeout.ms","60000");return p;}
 public static void main(String[] args)throws Exception{
  switch(args[0]){
   case "create":try(var a=Admin.create(props())){a.createTopics(List.of(new NewTopic("replicated",1,(short)3).configs(Map.of("min.insync.replicas","2")))).all().get(60,TimeUnit.SECONDS);}break;
   case "state":try(var a=Admin.create(props())){var part=a.describeTopics(List.of("replicated")).allTopicNames().get(60,TimeUnit.SECONDS).get("replicated").partitions().get(0);System.out.println("STATE "+part.leader().id()+" "+part.isr().size());}break;
   case "write":var p=props();p.put("key.serializer","org.apache.kafka.common.serialization.StringSerializer");p.put("value.serializer","org.apache.kafka.common.serialization.StringSerializer");p.put("acks","all");p.put("enable.idempotence","true");p.put("delivery.timeout.ms","60000");
    try(var producer=new KafkaProducer<String,String>(p)){for(int i=0;i<10;i++)producer.send(new ProducerRecord<>("replicated","key",args[1]+i)).get(70,TimeUnit.SECONDS);}break;
   case "read":var cprops=props();cprops.put("key.deserializer","org.apache.kafka.common.serialization.StringDeserializer");cprops.put("value.deserializer","org.apache.kafka.common.serialization.StringDeserializer");cprops.put("enable.auto.commit","false");
    try(var c=new KafkaConsumer<String,String>(cprops)){c.assign(List.of(new TopicPartition("replicated",0)));c.seekToBeginning(c.assignment());var values=new ArrayList<String>();long until=System.nanoTime()+60_000_000_000L;while(values.size()<20&&System.nanoTime()<until)for(var r:c.poll(Duration.ofMillis(200)))values.add(r.value());var expected=new ArrayList<String>();for(var prefix:List.of("before-","after-"))for(int i=0;i<10;i++)expected.add(prefix+i);if(!values.equals(expected))throw new AssertionError(values);System.out.println("All 20 acknowledged records retained in order");}break;
   default:throw new IllegalArgumentException(args[0]);
  }
 }
}
