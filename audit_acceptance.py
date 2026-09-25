"""Summarize evidence without treating missing reports or model failures as success."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
checks=[]
for name,relative in [
 ('Generated-draft publication boundary','labs/study-coach/python/generation-boundary-report.json'),
 ('Controlled identity session race','labs/study-coach/identity-session-race-report.json'),
 ('MySQL execution and restore','labs/database-plan-workshop/mysql-report.json'),
 ('Oracle execution plans','labs/database-plan-workshop/oracle-report.json'),
 ('TLS and WebSocket proxy','labs/load-balancing/tls-websocket-report.json'),
 ('Spring process crash','labs/study-coach/durable-spring-crash-report.json'),
 ('Expired delivery and fail-closed restart','labs/study-coach/durable-spring-expiry-report.json'),
 ('Provider secret overlap','labs/study-coach/secret-overlap-report.json'),
 ('Thirty-minute endurance','labs/realtime-cache/endurance-1800-report.json'),
 ('Automated reading accessibility','reading-accessibility-report.json'),
 ('Tutor-authored AI evaluation','labs/rag-flow/expanded-evaluation-report.json'),
 ('Public externally labelled AI evaluation','labs/rag-flow/public-evaluation-report.json')]:
    path=ROOT/relative
    item={'area':name,'evidence':relative,'status':'not recorded'}
    if path.exists():
        data=json.loads(path.read_text(encoding='utf-8'))
        if 'total' in data:
            item.update(status='passed' if data.get('completed')==data['total'] and data.get('passed')==data['total'] else 'failed' if data.get('completed')==data['total'] else 'incomplete',score=f"{data.get('passed',0)}/{data['total']}")
        elif 'status' in data:item['status']=data['status']
        elif data.get('passed') is True or isinstance(data.get('passed'),list) and data['passed']:item['status']='passed'
        else:item['status']='failed or incomplete'
    checks.append(item)
external=[
 {'area':'Public cloud, public TLS and provider recovery','status':'requires target access','needed':'Authorized account/project, region and spending limit; execute destination-specific deployment and recovery.'},
 {'area':'Physical mobile and screen reader','status':'requires physical observations','needed':'Complete labs/MANUAL-ACCEPTANCE.md on the actual device and assistive technology.'},
 {'area':'Personal interview grading','status':'requires learner answers','needed':'Original unaided responses and elapsed time, followed by targeted reassessment.'},
 {'area':'Independent-host and production identity acceptance','status':'requires target environment','needed':'Separate-host failures, shared persistent-session reconciliation, production rolling cutover and disaster recovery.'},
 {'area':'Historical intermittent login root cause','status':'unresolved','needed':'Conclusive reproduction or diagnostic evidence; passing mitigation tests do not prove the original cause.'}
]
report={'scope':'Local evidence register, not automatic production certification. A passing provider test is not a passing production rollout. External requirements are not inferred from local simulations.','local_checks':checks,'external_requirements':external,'all_requested_acceptance_complete':False}
(ROOT/'acceptance-status.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
