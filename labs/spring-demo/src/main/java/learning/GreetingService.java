package learning;

import org.springframework.stereotype.Service;

@Service
public class GreetingService {
    public String greet(String name) {
        if (name == null || name.isBlank() || name.length() > 80) {
            throw new IllegalArgumentException("Name must contain 1 to 80 characters");
        }
        return "Hello, " + name;
    }
}
