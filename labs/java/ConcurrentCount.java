// lab: ConcurrentCount
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
public class ConcurrentCount {
    public static void main(String[] args) throws Exception {
        AtomicInteger count = new AtomicInteger();
        ExecutorService pool = Executors.newFixedThreadPool(2);
        try {
            Future<?> a = pool.submit(() -> { for(int i=0;i<1000;i++) count.incrementAndGet(); });
            Future<?> b = pool.submit(() -> { for(int i=0;i<1000;i++) count.incrementAndGet(); });
            a.get(); b.get();
            if (count.get() != 2000) throw new AssertionError();
            System.out.println(count.get());
        } finally { pool.shutdown(); }
    }
}
