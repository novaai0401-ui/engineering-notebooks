"""Fault injection for availability and permission boundaries, not model-quality scoring."""
import io,json,urllib.error
from pathlib import Path
from unittest.mock import patch
from rag_flow import run
checks=[]
config={'mode':'hybrid','generator':'ollama','generation_timeout_seconds':2}
for error in [TimeoutError('slow'),urllib.error.URLError('offline'),ValueError('invalid JSON'),KeyError('message')]:
    with patch('urllib.request.urlopen',side_effect=error):
        result=run(config,'Orion','bob')
    assert result['answer'].startswith('Generation unavailable; showing source excerpts only.')
    assert result['evidence'] and all(d['id']!='d5' for d in result['evidence'])
    assert result['trace'][-1]['generator']=='extractive'
    assert result['quality'].startswith('Extractive')
checks.append('Timeout, connection failure and malformed response preserve only permitted excerpts with explicit fallback label')
with patch('urllib.request.urlopen') as call:
    result=run(config,'SUNRISE','bob');call.assert_not_called()
    assert not result['evidence'] and result['answer']=='Insufficient evidence in permitted sources.'
checks.append('No permitted evidence means no model invocation')
with patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps({'message':{'content':'[d1] Example answer'}}).encode())) as call:
    result=run(config,'Orion','bob')
    assert call.call_args.kwargs['timeout']==2 and result['trace'][-1]['generator']=='ollama'
    assert 'requires factual review' in result['quality']
checks.append('Successful adapter output remains explicitly unverified generation; configured timeout reaches transport')
for bad in [True,0,241,float('nan'),'2']:
    try:run(dict(config,generation_timeout_seconds=bad),'Orion','bob')
    except ValueError:pass
    else:raise AssertionError('Invalid timeout accepted')
checks.append('Malformed and unbounded timeout configuration rejected')
report={'status':'passed','passed':checks,'limitations':'Transport fault injection verifies application behavior, not factual correctness or actual provider availability. Actual model failures are preserved in separate reports.'}
Path(__file__).with_name('generation-recovery-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
