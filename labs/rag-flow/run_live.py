"""Generate four reviewable answers through the optional local-model boundary."""
import hashlib,json,time
from pathlib import Path
from rag_flow import run
cases=[('two-hop-team','Who leads the team maintaining Orion?',{'mode':'multi_hop','subquestions':['Orion maintained','Payments led'],'top_k':1}),('checkpoint-boundary','Does saving a checkpoint make external side effects idempotent?',{'mode':'hybrid','top_k':2}),('reconciliation-boundary','Does reconciliation guarantee idempotent execution?',{'mode':'hybrid','top_k':1}),('error-retry','What does E104 mean and how should it be retried?',{'mode':'hybrid','top_k':1})]
results=[]
for case_id,question,config in cases:
    began=time.monotonic()
    try:result=run(dict(config,generator='ollama'),question)
    except Exception as error:
        failure={'status':'runtime_failed','case':case_id,'error_type':type(error).__name__,'seconds':round(time.monotonic()-began,2),'completed_cases':results,'source_sha256':hashlib.sha256(Path(__file__).with_name('rag_flow.py').read_bytes()).hexdigest(),'consequence':'No factual pass claimed for incomplete cases; earlier successful execution report retained.'}
        Path(__file__).with_name('live-retest-report.json').write_text(json.dumps(failure,indent=2),encoding='utf-8')
        raise
    results.append({'id':case_id,'question':question,'seconds':round(time.monotonic()-began,2),**result})
    print(case_id+': '+result['answer'],flush=True)
report={'model':'qwen2.5:7b-instruct-q4_K_M','source_sha256':hashlib.sha256(Path(__file__).with_name('rag_flow.py').read_bytes()).hexdigest(),'cases':results,'review_status':'pending claim-level review; successful generation is not factual validation'}
Path(__file__).with_name('live-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
