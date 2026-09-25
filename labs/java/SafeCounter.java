// lab: SafeCounter
import java.util.concurrent.*;
import java.util.concurrent.locks.*;
public class SafeCounter {
  static class Counter {
    private final ReentrantLock lock = new ReentrantLock();
    private int value;
    void increment() {
      lock.lock();
      try { value++; } finally { lock.unlock(); }
    }
    int value() {
      lock.lock();
      try { return value; } finally { lock.unlock(); }
    }
  }
  public static void main(String[] args) throws Exception {
    var counter = new Counter();
    var pool = Executors.newFixedThreadPool(4);
    try {
      var futures = new java.util.ArrayList<Future<?>>();
      for (int i=0;i<4;i++) futures.add(pool.submit(() -> {
        for (int j=0;j<1000;j++) counter.increment();
      }));
      for (var future : futures) future.get();
      assert counter.value() == 4000;
      System.out.println("4000 increments retained; task failures propagate through Future.get.");
    } finally { pool.shutdownNow(); }
  }
}
