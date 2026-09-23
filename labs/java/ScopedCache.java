// lab: ScopedCache
import java.util.*;
public class ScopedCache {
 record Key(String owner,String query){}
 record Entry(String value,long expires){}
 static class Cache {
  final Map<Key,Entry> entries=new LinkedHashMap<>();
  final int capacity;
  Cache(int capacity){if(capacity<1)throw new IllegalArgumentException();this.capacity=capacity;}
  synchronized void put(Key key,String value,long now,long ttl){
   entries.remove(key);entries.put(key,new Entry(value,now+ttl));
   while(entries.size()>capacity)entries.remove(entries.keySet().iterator().next());
  }
  synchronized Optional<String> get(Key key,long now){
   Entry item=entries.get(key);
   if(item==null)return Optional.empty();
   if(item.expires()<=now){entries.remove(key);return Optional.empty();}
   return Optional.of(item.value());
  }
  synchronized void invalidate(Key key){entries.remove(key);}
 }
 public static void main(String[] args){
  Cache cache=new Cache(2);Key alice=new Key("alice","plan");
  cache.put(alice,"private",0,10);
  assert cache.get(new Key("bob","plan"),1).isEmpty();
  assert cache.get(alice,10).isEmpty();
  cache.put(alice,"new",10,10);cache.invalidate(alice);
  assert cache.get(alice,11).isEmpty();
  System.out.println("Cache keys include owner; expiration and invalidation are tested");
 }
}
