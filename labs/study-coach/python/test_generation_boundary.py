"""Fault injection around the actual adapter and ASGI route, not model accuracy scoring."""
import asyncio,json,os,secrets,unittest
from pathlib import Path
from unittest.mock import patch
import httpx
os.environ.setdefault('COACH_SERVICE_TOKEN',secrets.token_urlsafe(32))
import ollama_agent
import coach_ai

class FakeStream:
    def __init__(self,events):self.events=events
    async def __aenter__(self):return self
    async def __aexit__(self,*args):pass
    def raise_for_status(self):pass
    async def aiter_lines(self):
        for event in self.events:
            if isinstance(event,BaseException):raise event
            yield event if isinstance(event,str) else json.dumps(event)
class FakeClient:
    events=[]
    def __init__(self,*args,**kwargs):pass
    async def __aenter__(self):return self
    async def __aexit__(self,*args):pass
    def stream(self,*args,**kwargs):return FakeStream(self.events)

class BoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def collect(self,events):
        FakeClient.events=events;seen=[]
        with patch.object(ollama_agent.httpx,'AsyncClient',FakeClient):
            try:
                async for event in ollama_agent.generate_evidence('What?', [{'id':'allowed','text':'Authorized evidence.'}]):seen.append(event)
            except ValueError:return seen,True
        return seen,False
    async def test_unknown_citation_never_publishes_draft(self):
        seen,rejected=await self.collect([{'message':{'content':'UNTRUSTED DRAFT [private]'}},{'done':True}]);self.assertTrue(rejected);self.assertEqual(seen,[])
    async def test_missing_citation_never_publishes_draft(self):
        seen,rejected=await self.collect([{'message':{'content':'Unsupported claim'}},{'done':True}]);self.assertTrue(rejected);self.assertEqual(seen,[])
    async def test_incomplete_response_never_publishes_draft(self):
        seen,rejected=await self.collect([{'message':{'content':'Partial [allowed]'}}]);self.assertTrue(rejected);self.assertEqual(seen,[])
    async def test_invalid_events_never_publish_draft(self):
        for bad in ['{not-json}',[],{'message':None},{'message':{'content':42}},{'done':'true'},{'done':True,'eval_count':None},{'done':True,'eval_count':-1},{'done':True,'eval_count':129}]:
            seen,rejected=await self.collect([{'message':{'content':'First [allowed]'}},bad]);self.assertTrue(rejected);self.assertEqual(seen,[])
    async def test_oversize_draft_never_publishes(self):
        seen,rejected=await self.collect([{'message':{'content':'x'*8001+' [allowed]'}},{'done':True}]);self.assertTrue(rejected);self.assertEqual(seen,[])
    async def test_cancellation_propagates(self):
        with self.assertRaises(asyncio.CancelledError):
            await self.collect([{'message':{'content':'Partial [allowed]'}},asyncio.CancelledError()])
    async def test_valid_format_still_requires_factual_review(self):
        seen,rejected=await self.collect([{'message':{'content':'A claim [allowed]'}},{'done':True,'eval_count':5}]);self.assertFalse(rejected);self.assertEqual(seen[0]['delta'],'Generated draft; requires factual review.\nA claim [allowed]');self.assertTrue(seen[-1]['requires_review']);self.assertTrue(seen[-1]['citation_gate'])
    async def test_real_route_returns_authorized_fallback_on_transport_failure(self):
        async def failed(*args):
            raise httpx.ReadTimeout('private provider detail must not be returned')
            yield
        with patch.object(coach_ai,'MODE','ollama'),patch.object(ollama_agent,'generate_evidence',failed):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=coach_ai.app),base_url='http://test') as client:
                response=await client.post('/answer',json={'question':'Alice private plan','user':'bob'},headers={'Authorization':'Bearer '+coach_ai.SERVICE_TOKEN})
        self.assertEqual(response.status_code,200);events=[json.loads(line) for line in response.text.splitlines()];self.assertEqual(events[-1]['mode'],'extractive-fallback');self.assertTrue(events[-1]['done']);self.assertNotIn('alice-plan',events[-1]['sources']);self.assertNotIn('Alice private plan:',response.text);self.assertNotIn('private provider detail',response.text)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BoundaryTests))
    report={'status':'passed' if result.wasSuccessful() else 'failed','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'scope':'Actual adapter and ASGI route with injected provider events/failure. Tests publication boundaries and authorized fallback; does not establish factual accuracy or live provider availability.'}
    Path(__file__).with_name('generation-boundary-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');raise SystemExit(0 if result.wasSuccessful() else 1)
