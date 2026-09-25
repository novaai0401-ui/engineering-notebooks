// lab: EmployeePredicates
import java.util.*;
import java.util.function.*;
public class EmployeePredicates {
  record Employee(String name, int age) {}
  interface Named { String name(); } // Functional even without the annotation.
  public static void main(String[] args) {
    var people = List.of(new Employee("Asha",40), new Employee("Ravi",41));
    Predicate<Employee> olderThan40 = employee -> employee.age() > 40;
    var names = people.stream().filter(olderThan40).map(Employee::name).toList();
    assert names.equals(List.of("Ravi"));
    Named label = () -> "approved";
    assert label.name().equals("approved");
    System.out.println(names);
  }
}
