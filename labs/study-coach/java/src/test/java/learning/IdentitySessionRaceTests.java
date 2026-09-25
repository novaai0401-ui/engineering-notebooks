package learning;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.mock.web.MockHttpSession;
import org.springframework.security.oauth2.client.web.HttpSessionOAuth2AuthorizationRequestRepository;
import org.springframework.security.oauth2.core.endpoint.OAuth2AuthorizationRequest;
import org.springframework.security.web.savedrequest.HttpSessionRequestCache;
import org.springframework.security.web.savedrequest.NullRequestCache;

/** Actual Spring components with a controlled browser-session selection schedule.
 * This reproduces a mechanism, not the precise historical network incident. */
class IdentitySessionRaceTests {
 private final HttpSessionOAuth2AuthorizationRequestRepository repository =
     new HttpSessionOAuth2AuthorizationRequestRepository();
 private MockHttpSession beginLogin() {
  var request=new MockHttpServletRequest("GET","/oauth2/authorization/coach");
  var authorization=OAuth2AuthorizationRequest.authorizationCode()
      .clientId("classroom").authorizationUri("https://identity.example.test/authorize")
      .redirectUri("https://app.example.test/callback").state("request-state").build();
  repository.saveAuthorizationRequest(authorization,request,new MockHttpServletResponse());
  return (MockHttpSession)request.getSession(false);
 }
 private MockHttpServletRequest callback(MockHttpSession session,String state) {
  var request=new MockHttpServletRequest("GET","/callback");
  request.setSession(session);request.setParameter("state",state);return request;
 }
 @Test void competingAnonymousSessionCannotRecoverTheAuthorizationRequest() {
  var loginSession=beginLogin();
  var anonymous=new MockHttpServletRequest("GET","/api/me");
  new HttpSessionRequestCache().saveRequest(anonymous,new MockHttpServletResponse());
  var competing=(MockHttpSession)anonymous.getSession(false);
  assertNotNull(competing);assertNotEquals(loginSession.getId(),competing.getId());
  // Simulate a late anonymous response making the browser select its session.
  assertNull(repository.loadAuthorizationRequest(callback(competing,"request-state")));
  assertNotNull(repository.loadAuthorizationRequest(callback(loginSession,"request-state")));
 }
 @Test void nullRequestCacheDoesNotCreateACompetingAnonymousSession() {
  var loginSession=beginLogin();
  var anonymous=new MockHttpServletRequest("GET","/api/me");
  new NullRequestCache().saveRequest(anonymous,new MockHttpServletResponse());
  assertNull(anonymous.getSession(false));
  assertNotNull(repository.loadAuthorizationRequest(callback(loginSession,"request-state")));
 }
 @Test void wrongStateRemainsRejectedEvenWithTheCorrectSession() {
  assertNull(repository.loadAuthorizationRequest(callback(beginLogin(),"forged-state")));
 }
}
