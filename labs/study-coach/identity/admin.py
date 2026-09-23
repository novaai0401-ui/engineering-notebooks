"""Explicit Keycloak lifecycle operations for the isolated classroom realm."""
import httpx
class IdentityAdmin:
    def __init__(self,url,user,password):
        self.http=httpx.Client(base_url=url,timeout=30)
        response=self.http.post('/realms/master/protocol/openid-connect/token',data={'grant_type':'password','client_id':'admin-cli','username':user,'password':password})
        response.raise_for_status();self.http.headers['Authorization']='Bearer '+response.json()['access_token']
    def user(self,name):
        response=self.http.get('/admin/realms/study/users',params={'username':name,'exact':'true'});response.raise_for_status()
        matches=response.json()
        if len(matches)!=1:raise ValueError('expected one matching identity')
        return matches[0]
    def disable(self,name):
        user=self.user(name)
        self.http.put('/admin/realms/study/users/'+user['id'],json={'enabled':False}).raise_for_status()
        self.http.post('/admin/realms/study/users/'+user['id']+'/logout').raise_for_status()
    def reset_password(self,name,password):
        user=self.user(name)
        self.http.put('/admin/realms/study/users/'+user['id']+'/reset-password',json={'type':'password','temporary':False,'value':password}).raise_for_status()
    def rotate_client_secret(self):
        response=self.http.get('/admin/realms/study/clients',params={'clientId':'study-coach'});response.raise_for_status()
        client=response.json()[0]
        response=self.http.post('/admin/realms/study/clients/'+client['id']+'/client-secret');response.raise_for_status()
        return response.json()['value']
    def close(self):self.http.close()
