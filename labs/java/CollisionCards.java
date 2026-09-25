// lab: CollisionCards
import java.util.*;
public class CollisionCards {
  record Key(int id) { @Override public int hashCode() { return 7; } }
  public static void main(String[] args) {
    Map<Key,String> cards = new HashMap<>();
    cards.put(new Key(1), "Alice");
    cards.put(new Key(2), "Bob");
    assert cards.size() == 2;
    assert cards.get(new Key(1)).equals("Alice");
    cards.put(new Key(1), "Alicia");
    assert cards.size() == 2;
    assert cards.get(new Key(1)).equals("Alicia");
    System.out.println("Unequal colliding keys coexist; equal keys replace values.");
  }
}
