"""Summarize actual Surefire XML after mvn test; never infer success from source files."""
from pathlib import Path
import datetime,json,xml.etree.ElementTree as ET
root=Path(__file__).resolve().parent
suites=[]
for path in sorted((root/'target/surefire-reports').glob('TEST-*.xml')):
    suite=ET.parse(path).getroot()
    assert int(suite.get('failures','0'))==0 and int(suite.get('errors','0'))==0 and int(suite.get('skipped','0'))==0,path.name
    suites.append({'suite':suite.get('name'),'passed':int(suite.get('tests')),'tests':[case.get('name') for case in suite.findall('testcase')]})
assert len(suites)==3 and sum(s['passed'] for s in suites)==5,'Expected all three workshop suites'
report={'status':'passed','recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tests':5,'suites':suites,'versions':{'spring-framework':'6.2.12','spring-batch':'5.2.4','junit':'5.13.4','mockito':'5.20.0','h2':'2.3.232','java_target':21},'scope':'Actual Maven/JUnit tests of Mockito boundaries, Spring proxy transaction behavior and a Spring Batch failed-chunk restart. H2 database and stable local file; not MySQL/Oracle, a process-kill restart or remote payment exactly-once certification.'}
(root/'test-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
