// lab: CollectionDemo
import java.util.*;
public class CollectionDemo {
    public static void main(String[] args) {
        Map<String, Integer> counts = new HashMap<>();
        for (String word : List.of("ai", "java", "ai")) {
            counts.merge(word, 1, Integer::sum);
        }
        if (counts.get("ai") != 2) throw new AssertionError();
        List<String> ranked = counts.keySet().stream()
            .sorted(Comparator.comparingInt((String k) -> counts.get(k))
                .reversed().thenComparing(Comparator.naturalOrder()))
            .toList();
        if (!ranked.equals(List.of("ai", "java"))) throw new AssertionError();
        System.out.println(ranked);
    }
}
