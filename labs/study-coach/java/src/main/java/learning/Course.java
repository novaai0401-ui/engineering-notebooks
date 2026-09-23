package learning;
import jakarta.persistence.*;
import java.util.*;
@Entity
public class Course {
 @Id Long id;
 String title;
 @Version long version;
 @OneToMany(mappedBy="course",fetch=FetchType.LAZY) List<Lesson> lessons=new ArrayList<>();
 protected Course(){}
 public Course(long id,String title){this.id=id;this.title=title;}
}
@Entity
class Lesson {
 @Id Long id; String title;
 @ManyToOne(fetch=FetchType.LAZY) @JoinColumn(name="course_id") Course course;
 protected Lesson(){}
}
