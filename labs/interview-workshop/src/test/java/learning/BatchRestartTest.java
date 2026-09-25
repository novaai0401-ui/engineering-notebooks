package learning;
import java.nio.file.*;
import java.util.concurrent.atomic.AtomicBoolean;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.batch.core.*;
import org.springframework.batch.core.job.builder.JobBuilder;
import org.springframework.batch.core.step.builder.StepBuilder;
import org.springframework.batch.core.repository.support.JobRepositoryFactoryBean;
import org.springframework.batch.core.launch.support.TaskExecutorJobLauncher;
import org.springframework.batch.item.file.builder.FlatFileItemReaderBuilder;
import org.springframework.core.io.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.*;
import org.springframework.jdbc.datasource.init.ResourceDatabasePopulator;
import static org.junit.jupiter.api.Assertions.*;

class BatchRestartTest {
    @TempDir Path temp;
    @Test void failedChunkRollsBackAndSameInstanceRestartsFromCommittedCheckpoint() throws Exception {
        var file=temp.resolve("stable-input.txt");
        Files.writeString(file,"1\n2\n3\n4\n5\n");
        var ds=new DriverManagerDataSource("jdbc:h2:mem:batch_"+java.util.UUID.randomUUID()+";DB_CLOSE_DELAY=-1","sa","");
        new ResourceDatabasePopulator(new ClassPathResource("org/springframework/batch/core/schema-h2.sql")).execute(ds);
        var jdbc=new JdbcTemplate(ds);jdbc.execute("CREATE TABLE settled(id INT PRIMARY KEY)");
        var tx=new DataSourceTransactionManager(ds);
        var factory=new JobRepositoryFactoryBean();factory.setDataSource(ds);factory.setTransactionManager(tx);factory.afterPropertiesSet();
        var repository=factory.getObject();
        var launcher=new TaskExecutorJobLauncher();launcher.setJobRepository(repository);launcher.afterPropertiesSet();
        var reader=new FlatFileItemReaderBuilder<Integer>().name("stableRows")
            .resource(new FileSystemResource(file)).lineMapper((line,number)->Integer.valueOf(line)).saveState(true).build();
        var failOnce=new AtomicBoolean(true);
        var step=new StepBuilder("settle",repository).<Integer,Integer>chunk(2,tx).reader(reader)
            .writer(chunk->{
                for(var id:chunk) {
                    jdbc.update("INSERT INTO settled(id) VALUES(?)",id);
                    if(id==3 && failOnce.getAndSet(false)) throw new IllegalStateException("injected writer failure");
                }
            }).build();
        var job=new JobBuilder("settlement",repository).start(step).build();
        var params=new JobParametersBuilder().addString("input",file.toString()).toJobParameters();
        var failed=launcher.run(job,params);
        assertEquals(BatchStatus.FAILED,failed.getStatus());
        assertEquals(java.util.List.of(1,2),jdbc.queryForList("SELECT id FROM settled ORDER BY id",Integer.class));
        var resumed=launcher.run(job,params);
        assertEquals(BatchStatus.COMPLETED,resumed.getStatus());
        assertEquals(failed.getJobInstance().getInstanceId(),resumed.getJobInstance().getInstanceId());
        assertNotEquals(failed.getId(),resumed.getId());
        assertEquals(java.util.List.of(1,2,3,4,5),jdbc.queryForList("SELECT id FROM settled ORDER BY id",Integer.class));
        assertThrows(org.springframework.batch.core.repository.JobInstanceAlreadyCompleteException.class,()->launcher.run(job,params));
    }
}
