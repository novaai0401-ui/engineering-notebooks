package learning;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api")
public class GreetingController {
    private final GreetingService service;
    public GreetingController(GreetingService service) { this.service = service; }

    @GetMapping("/greeting")
    public Greeting greeting(@RequestParam(defaultValue="learner") String name) {
        try { return new Greeting(service.greet(name)); }
        catch (IllegalArgumentException exception) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, exception.getMessage());
        }
    }
    public record Greeting(String message) {}
}
