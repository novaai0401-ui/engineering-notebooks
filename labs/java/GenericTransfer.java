// lab: GenericTransfer
import java.util.*;
public class GenericTransfer {
 static <T> void copy(List<? extends T> source,List<? super T> target){
  for(T value:source)target.add(value);
 }
 static double total(List<? extends Number> values){
  return values.stream().mapToDouble(Number::doubleValue).sum();
 }
 public static void main(String[] args){
  List<Integer> integers=List.of(1,2,3);
  List<Number> numbers=new ArrayList<>();copy(integers,numbers);
  assert total(numbers)==6;
  System.out.println("A producer of integers can feed a consumer of numbers");
 }
}
