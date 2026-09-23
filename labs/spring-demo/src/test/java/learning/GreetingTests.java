package learning;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.context.WebApplicationContext;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
class GreetingTests {
    @Autowired WebApplicationContext context;
    @Test void greetingIsSerializedOverMvc() throws Exception {
        MockMvcBuilders.webAppContextSetup(context).build()
            .perform(get("/api/greeting").param("name", "Asha"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.message").value("Hello, Asha"));
    }
    @Test void invalidNameIsBadRequest() throws Exception {
        MockMvcBuilders.webAppContextSetup(context).build()
            .perform(get("/api/greeting").param("name", " "))
            .andExpect(status().isBadRequest());
    }
    @Test void serviceValidatesIndependently() {
        assertThrows(IllegalArgumentException.class, () -> new GreetingService().greet(null));
    }
}
