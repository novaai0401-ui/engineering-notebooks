"""Versioned evidence/permission regression evaluation; no LLM quality claim."""
from pathlib import Path
import hashlib, importlib.util, json, os, secrets, statistics, sys, time
root=Path(__file__).resolve().parent
source=root.parent/'study-coach/python/coach_ai.py'
sys.path.insert(0,str(source.parent))
os.environ.setdefault('COACH_SERVICE_TOKEN',secrets.token_urlsafe(32))
spec=importlib.util.spec_from_file_location('coach_evaluated',source)
module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
dataset=json.loads((root/'cases.json').read_text())
records=[]
for case in dataset['cases']:
    began=time.perf_counter();hits=module.retrieve(case['question'],case['user']);elapsed=(time.perf_counter()-began)*1000
    ids=[hit['id'] for hit in hits]
    passed=True
    if 'expected_first' in case:passed=bool(ids) and ids[0]==case['expected_first']
    if 'forbidden' in case:passed=passed and case['forbidden'] not in ids
    if case.get('empty'):passed=passed and not ids
    records.append({'id':case['id'],'category':case['category'],'passed':passed,'returned_ids':ids,'latency_ms':round(elapsed,3)})
categories={category:{'passed':sum(r['passed'] for r in records if r['category']==category),'total':sum(r['category']==category for r in records)} for category in sorted({r['category'] for r in records})}
report={'dataset_version':dataset['version'],'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'categories':categories,'median_latency_ms':statistics.median(r['latency_ms'] for r in records),'cases':records,'limitations':'Small deterministic development regression set, not a held-out measure of LLM reasoning or production quality.'}
(root/'evaluation-report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(categories,indent=2))
if not all(r['passed'] for r in records):raise SystemExit('Evaluation gate failed; inspect evaluation-report.json')
