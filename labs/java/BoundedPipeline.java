// lab: BoundedPipeline
import java.util.concurrent.*;
public class BoundedPipeline {
 public static void main(String[] args)throws Exception{
  BlockingQueue<Integer> queue=new ArrayBlockingQueue<>(2);
  try(var executor=Executors.newVirtualThreadPerTaskExecutor()){
   Future<Integer> consumer=executor.submit(()->{
    int sum=0;
    while(true){int value=queue.take();if(value==-1)return sum;sum+=value;}
   });
   Future<?> producer=executor.submit(()->{
    try{for(int i=1;i<=5;i++)queue.put(i);queue.put(-1);}
    catch(InterruptedException e){Thread.currentThread().interrupt();throw new RuntimeException(e);}
   });
   producer.get(2,TimeUnit.SECONDS);
   assert consumer.get(2,TimeUnit.SECONDS)==15;
  }
  System.out.println("A bounded queue applies backpressure between producer and consumer");
 }
}
