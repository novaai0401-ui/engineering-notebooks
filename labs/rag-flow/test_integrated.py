"""Verify optional pretrained integration; --model adds actual bounded model tool selection."""
import json,sys,time
from pathlib import Path
from rag_flow import run
from model_controller import validate
checks=[];began=time.monotonic()
for bad in [{'action':'shell','query':'anything'},{'action':'search','query':'a','retriever':'http'},{'action':'finish','user':'alice'},{'action':'search','query':'x'*501,'retriever':'hybrid'}]:
 try:validate(bad)
 except ValueError:pass
 else:raise AssertionError('Unsafe decision accepted')
checks.append('Unknown tools, extra authority fields and oversized queries rejected')
result=run({'mode':'hybrid','embedding':'pretrained','top_k':2},'What does E104 mean?','bob')
assert 'd4' in [d['id'] for d in result['evidence']] and 'd5' not in [d['id'] for d in result['evidence']]
checks.append('Actual pretrained retrieval integrated into configurable hybrid pipeline after authorization')
for mode in ('graph','multi_hop','adaptive'):
 result=run({'mode':mode,'embedding':'pretrained','top_k':1,'subquestions':['Orion maintained','Payments led']},'Who leads the team maintaining Orion?','bob')
 assert {'d1','d2'}<=set(d['id'] for d in result['evidence']),(mode,result)
checks.append('Pretrained-backed graph expansion and explicit/adaptive multi-hop preserve two-link evidence')
report={'passed':checks,'seconds':round(time.monotonic()-began,2),'limitations':'Small local corpus; graph entities remain curated. No automatic graph extraction/community summarization or production benchmark.'}
if '--model' in sys.argv:
 result=run({'mode':'agentic','embedding':'pretrained','controller':'ollama','top_k':2,'max_steps':1},'What does E104 mean?','bob')
 assert any(t['step']=='model_decision' and t['decision']['action']=='search' for t in result['trace'])
 assert 'd4' in [d['id'] for d in result['evidence']] and 'd5' not in [d['id'] for d in result['evidence']]
 assert len([t for t in result['trace'] if t['step']=='model_decision'])==1
 checks.append('Actual Ollama selected a validated read-only search; execution enforced permission and one-step budget')
 report['trace']=result['trace'];report['seconds']=round(time.monotonic()-began,2)
 report['limitations']+=' One real model decision, not broad autonomous-agent reliability; final answer remains extractive.'
Path(__file__).with_name('model-integration-report.json' if '--model' in sys.argv else 'pretrained-integration-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
