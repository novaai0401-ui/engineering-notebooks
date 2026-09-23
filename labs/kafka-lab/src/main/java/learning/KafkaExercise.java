package learning;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.TimeUnit;
import org.apache.kafka.clients.admin.*;
import org.apache.kafka.clients.producer.*;
import org.apache.kafka.clients.consumer.*;
import org.apache.kafka.common.TopicPartition;
public class KafkaExercise {
 static Properties common(){var p=new Properties();p.put("bootstrap.servers","127.0.0.1:19092");return p;}
 static KafkaConsumer<String,String> consumer(String group){var p=common();p.put("group.id",group);p.put("key.deserializer","org.apache.kafka.common.serialization.StringDeserializer");p.put("value.deserializer","org.apache.kafka.common.serialization.StringDeserializer");p.put("enable.auto.commit","false");p.put("auto.offset.reset","earliest");p.put("isolation.level","read_committed");return new KafkaConsumer<>(p);}
 public static void main(String[] args)throws Exception{
  if(args[0].equals("write")){
   try(var admin=Admin.create(common())){admin.createTopics(List.of(new NewTopic("orders",2,(short)1))).all().get(30,TimeUnit.SECONDS);}
   var p=common();p.put("key.serializer","org.apache.kafka.common.serialization.StringSerializer");p.put("value.serializer","org.apache.kafka.common.serialization.StringSerializer");p.put("enable.idempotence","true");p.put("acks","all");p.put("transactional.id","classroom-producer");
   try(var producer=new KafkaProducer<String,String>(p)){
    producer.initTransactions();producer.beginTransaction();producer.send(new ProducerRecord<>("orders",0,"order-7","created")).get();producer.commitTransaction();
    producer.beginTransaction();producer.send(new ProducerRecord<>("orders",0,"order-7","aborted-payment")).get();producer.abortTransaction();
    producer.beginTransaction();producer.send(new ProducerRecord<>("orders",0,"order-7","approved")).get();producer.commitTransaction();
   }
   System.out.println("Committed two ordered records and aborted one transaction.");
  }else if(args[0].equals("read")){
   try(var c=consumer("audit")){
    c.assign(List.of(new TopicPartition("orders",0)));c.seekToBeginning(c.assignment());var values=new ArrayList<String>();long until=System.nanoTime()+30_000_000_000L;
    while(values.size()<2&&System.nanoTime()<until)for(var record:c.poll(Duration.ofMillis(300)))values.add(record.value());
    if(!values.equals(List.of("created","approved")))throw new AssertionError(values);c.commitSync();
   }
   try(var c=consumer("audit")){c.assign(List.of(new TopicPartition("orders",0)));if(!c.poll(Duration.ofSeconds(2)).isEmpty())throw new AssertionError("committed offset replayed");}
   System.out.println("Read-committed excludes aborted output; explicit group offset resumes without replay.");
  }else if(args[0].equals("group")){
   try(var a=consumer("workers");var b=consumer("workers")){
    a.subscribe(List.of("orders"));b.subscribe(List.of("orders"));long until=System.nanoTime()+40_000_000_000L;
    while(System.nanoTime()<until){a.poll(Duration.ofMillis(100));b.poll(Duration.ofMillis(100));if(a.assignment().size()==1&&b.assignment().size()==1)break;}
    var overlap=new HashSet<>(a.assignment());overlap.retainAll(b.assignment());
    if(a.assignment().size()!=1||b.assignment().size()!=1||!overlap.isEmpty())throw new AssertionError("group assignment");
   }
   System.out.println("Two consumers own distinct partitions in one group.");
  }
 }
}
