import json
from pathlib import Path
from rag_flow import run
checks=[]
for mode in ['simple','hybrid','graph','multi_hop','agentic','adaptive']:
    config={'mode':mode,'top_k':2,'max_steps':3,'subquestions':['Orion maintained team','Payments led Mira']}
    result=run(config,'Orion team','bob')
    assert result['evidence'] and all(d['id']!='d5' for d in result['evidence'])
    checks.append(mode+' route returns permitted evidence and a trace')
result=run({'mode':'agentic'},'reimbursement')
assert 'd6' in [d['id'] for d in result['evidence']]
assert len([s for s in result['trace'] if s['step']=='retrieve'])==2
checks.append('Bounded tool policy falls back from lexical miss to synonym concept retrieval')
assert not run({'mode':'hybrid'},'SUNRISE','bob')['evidence']
assert run({'mode':'hybrid'},'SUNRISE','alice')['evidence'][0]['id']=='d5'
assert not run({'mode':'simple'},'unicornzz')['evidence']
checks.append('Private source denied to Bob, allowed to Alice; missing evidence abstains')
multi=run({'mode':'multi_hop','subquestions':['Orion maintained','Payments led'],'top_k':1},'Who leads Orion?')
assert {'d1','d2'}.issubset({d['id'] for d in multi['evidence']})
graph=run({'mode':'graph','top_k':1,'max_steps':2},'Orion maintained')
assert 'd2' in [d['id'] for d in graph['evidence']]
checks.append('Multi-hop plan and bounded graph expansion retrieve the two-link evidence chain')
for bad in [{'mode':'unknown'},{'mode':'simple','top_k':0},{'mode':'simple','max_steps':100}]:
    try:run(bad,'Orion')
    except ValueError:pass
    else:raise AssertionError('Invalid configuration accepted')
checks.append('Unknown routes and invalid budgets rejected')
report={'passed':checks,'limitations':'Offline toy corpus, transparent synonym vectors, deterministic tool/router policy and extractive evidence output. No pretrained embedding, autonomous LLM planning, Microsoft GraphRAG community pipeline or general factual-quality claim. Ollama adapter not exercised by this test.'}
Path(__file__).with_name('report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
