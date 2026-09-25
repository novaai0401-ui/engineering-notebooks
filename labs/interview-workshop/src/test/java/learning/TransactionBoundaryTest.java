package learning;
import javax.sql.DataSource;
import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.*;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.annotation.*;
import static org.junit.jupiter.api.Assertions.*;

class TransactionBoundaryTest {
    @Configuration @EnableTransactionManagement(proxyTargetClass=true)
    static class Config {
        @Bean DataSource dataSource() {
            return new DriverManagerDataSource("jdbc:h2:mem:proxy_"+java.util.UUID.randomUUID()+";DB_CLOSE_DELAY=-1","sa","");
        }
        @Bean PlatformTransactionManager transactionManager(DataSource ds) { return new DataSourceTransactionManager(ds); }
        @Bean JdbcTemplate jdbc(DataSource ds) { return new JdbcTemplate(ds); }
        @Bean Operations operations(JdbcTemplate jdbc) { return new Operations(jdbc); }
    }
    public static class Operations {
        private final JdbcTemplate jdbc;
        public Operations(JdbcTemplate jdbc) { this.jdbc=jdbc; }
        @Transactional public void saveAndFail() {
            jdbc.update("INSERT INTO entries(id) VALUES(1)");
            throw new IllegalStateException("fail after insert");
        }
        public void selfInvoke() { saveAndFail(); }
    }
    @Test void proxyRollsBackButSelfInvocationBypassesInterception() {
        try(var context=new AnnotationConfigApplicationContext(Config.class)) {
            var jdbc=context.getBean(JdbcTemplate.class);
            jdbc.execute("CREATE TABLE entries(id INT PRIMARY KEY)");
            var service=context.getBean(Operations.class);
            assertThrows(IllegalStateException.class, service::saveAndFail);
            assertEquals(0,jdbc.queryForObject("SELECT COUNT(*) FROM entries",Integer.class));
            assertThrows(IllegalStateException.class, service::selfInvoke);
            assertEquals(1,jdbc.queryForObject("SELECT COUNT(*) FROM entries",Integer.class));
        }
    }
}
