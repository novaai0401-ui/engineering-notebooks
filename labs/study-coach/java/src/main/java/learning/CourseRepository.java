package learning;
import java.util.List;
import org.springframework.data.jpa.repository.*;
public interface CourseRepository extends JpaRepository<Course,Long> {
 @Query("select distinct c from Course c left join fetch c.lessons") List<Course> withLessons();
}
