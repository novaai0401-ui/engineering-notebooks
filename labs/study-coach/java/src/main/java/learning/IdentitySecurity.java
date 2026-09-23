package learning;
import java.util.*;
import org.springframework.context.annotation.*;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.client.oidc.userinfo.*;
import org.springframework.security.oauth2.client.registration.ClientRegistrationRepository;
import org.springframework.security.oauth2.client.web.*;
import org.springframework.security.oauth2.client.oidc.web.logout.OidcClientInitiatedLogoutSuccessHandler;
import org.springframework.security.oauth2.core.oidc.user.*;
import org.springframework.security.oauth2.client.userinfo.OAuth2UserService;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.HttpStatusEntryPoint;
import org.springframework.http.HttpStatus;
@Configuration @Profile("oidc")
public class IdentitySecurity {
 @Bean org.springframework.security.web.session.HttpSessionEventPublisher sessionEvents(){return new org.springframework.security.web.session.HttpSessionEventPublisher();}
 @Bean OAuth2UserService<OidcUserRequest,OidcUser> identityUsers(){
  var delegate=new OidcUserService();
  return request->{
   var user=delegate.loadUser(request);
   var authorities=new HashSet<org.springframework.security.core.GrantedAuthority>(user.getAuthorities());
   Object access=user.getClaims().get("realm_access");
   if(access instanceof Map<?,?> map && map.get("roles") instanceof Collection<?> roles)
    for(Object role:roles)if(Set.of("coach-learner","coach-admin").contains(role))authorities.add(new SimpleGrantedAuthority("ROLE_"+role));
   return new DefaultOidcUser(authorities,user.getIdToken(),user.getUserInfo(),"sub");
  };
 }
 @Bean SecurityFilterChain identityChain(HttpSecurity http,ClientRegistrationRepository clients,OAuth2UserService<OidcUserRequest,OidcUser> users)throws Exception{
  var resolver=new DefaultOAuth2AuthorizationRequestResolver(clients,"/oauth2/authorization");
  resolver.setAuthorizationRequestCustomizer(OAuth2AuthorizationRequestCustomizers.withPkce());
  var logout=new OidcClientInitiatedLogoutSuccessHandler(clients);logout.setPostLogoutRedirectUri("{baseUrl}/");
  return http.authorizeHttpRequests(a->a.requestMatchers("/","/index.html","/app.js","/health","/config","/oauth2/**","/login/**").permitAll()
   .requestMatchers("/api/admin/**","/actuator/**").hasRole("coach-admin")
   .requestMatchers("/api/**").hasRole("coach-learner").anyRequest().authenticated())
   // The SPA always returns to '/'. Saving concurrent anonymous API requests can
   // create competing sessions during the OIDC redirect; no saved request is needed.
   .requestCache(c->c.requestCache(new org.springframework.security.web.savedrequest.NullRequestCache()))
   .exceptionHandling(e->e.defaultAuthenticationEntryPointFor(new HttpStatusEntryPoint(HttpStatus.UNAUTHORIZED),request->request.getRequestURI().startsWith("/api/")))
   .oauth2Login(o->o.authorizationEndpoint(a->a.authorizationRequestResolver(resolver)).userInfoEndpoint(u->u.oidcUserService(users)).defaultSuccessUrl("/",true)
    .failureHandler((request,response,error)->{
     String code=error instanceof org.springframework.security.oauth2.core.OAuth2AuthenticationException oauth?oauth.getError().getErrorCode():error.getClass().getSimpleName();
     org.slf4j.LoggerFactory.getLogger(IdentitySecurity.class).warn("OIDC login rejected: {}",code);
     response.sendRedirect("/login?error");
    }))
   .oidcLogout(o->o.backChannel(org.springframework.security.config.Customizer.withDefaults()))
   .logout(l->l.logoutSuccessHandler(logout))
   .headers(h->h.contentSecurityPolicy(c->c.policyDirectives("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; object-src 'none'; frame-ancestors 'none'")))
   .build();
 }
}
