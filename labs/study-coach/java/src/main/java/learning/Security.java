package learning;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.*;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.core.userdetails.*;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
@Configuration
@Profile("!oidc")
public class Security {
 @Bean UserDetailsService users(@Value("${coach.password}") String password) {
  if(password.length()<12) throw new IllegalArgumentException("Use a local teaching password of at least 12 characters");
  String hash=new BCryptPasswordEncoder().encode(password);
  return new InMemoryUserDetailsManager(User.withUsername("alice").password(hash).roles("LEARNER").build(),
   User.withUsername("bob").password(hash).roles("LEARNER").build());
 }
 @Bean org.springframework.security.crypto.password.PasswordEncoder encoder(){return new BCryptPasswordEncoder();}
 @Bean SecurityFilterChain chain(HttpSecurity http) throws Exception {
  return http.authorizeHttpRequests(a->a.requestMatchers("/","/index.html","/app.js","/health","/config").permitAll().requestMatchers("/api/admin/**","/actuator/**").hasRole("ADMIN").anyRequest().authenticated())
   .httpBasic(Customizer.withDefaults())
   .headers(h->h.contentSecurityPolicy(c->c.policyDirectives("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; object-src 'none'; frame-ancestors 'none'")))
   .build(); // CSRF stays enabled, including for Basic authentication.
 }
}
