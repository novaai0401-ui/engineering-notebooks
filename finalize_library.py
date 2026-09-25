"""Render final reading editions and package verified classroom artifacts."""
from pathlib import Path
import json, re, zipfile, os
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
import nbformat
root=Path(__file__).resolve().parent
report=json.loads((root/'validation.json').read_text(encoding='utf-8'))
assert len(report['books'])==len(list(root.glob('[0-9][0-9]-*.md'))) and all(x['status']=='passed' for x in report['labs'])
scope={'__file__':str(root/'build_notebooks.py')}
exec((root/'build_notebooks.py').read_text(encoding='utf-8-sig').split('\ncards=[]')[0],scope)
system=json.loads((root/'labs/study-coach/system-report.json').read_text())
mcp=json.loads((root/'labs/remote-mcp/test-report.json').read_text())
evaluation=json.loads((root/'labs/agent-evaluation/evaluation-report.json').read_text())
assert all(case['passed'] for case in evaluation['cases'])
browser=json.loads((root/'labs/study-coach/frontend/test-results/report.json').read_text())
assert browser['stats']['unexpected']==0 and browser['stats']['expected']==12
junit=[]
for xml in (root/'labs/study-coach/java/target/surefire-reports').glob('TEST-*.xml'):
    suite=ET.parse(xml).getroot()
    assert int(suite.get('failures','0'))==0 and int(suite.get('errors','0'))==0
    junit.append({'suite':suite.get('name'),'passed':int(suite.get('tests'))})
assert sum(x['passed'] for x in junit)==8
cards=[]
for book in report['books']:
    stem=book['name'];source=(root/(stem+'.md')).read_text(encoding='utf-8')
    body,toc,chapters=scope['render_markdown'](source)
    book['words']=len(source.split());book['chapters']=chapters
    downloads=f'<p class="downloads"><a href="{stem}.ipynb">Jupyter notebook</a><a href="{stem}.md">Markdown</a><a href="index.html">Library home</a></p>'
    (root/(stem+'.html')).write_text(scope['page'](book['title'],body,toc,downloads),encoding='utf-8')
    notebook=nbformat.read(root/(stem+'.ipynb'),as_version=4)
    # Refresh all prose while retaining verified executable cells and their outputs.
    executed=iter(cell for cell in notebook.cells if cell.cell_type=='code')
    cells=[notebook.cells[0]];cursor=0
    for match in re.finditer(r'^```([^\n]*)\n(.*?)^```\s*$',source,re.M|re.S):
        before=source[cursor:match.start()]
        if before.strip():cells.append(nbformat.v4.new_markdown_cell(before))
        info=match.group(1).strip();code=match.group(2);language=info.split()[0] if info else ''
        marker=re.search(r'^(?:#|//) lab: ([A-Za-z0-9_]+)',code,re.M)
        if marker and language in ('python','java','javascript'):
            if language!='python':cells.append(nbformat.v4.new_markdown_cell(match.group(0)))
            cell=next(executed)
            assert cell.source==scope['wrapper'](language,code,marker.group(1)),f'Code changed without execution: {stem}'
            cells.append(cell)
        else:cells.append(nbformat.v4.new_markdown_cell(match.group(0)))
        cursor=match.end()
    if source[cursor:].strip():cells.append(nbformat.v4.new_markdown_cell(source[cursor:]))
    assert next(executed,None) is None
    notebook.cells=cells
    nbformat.validate(notebook);nbformat.write(notebook,root/(stem+'.ipynb'))
    cards.append(f'<article class="card"><h2><a href="{stem}.html">{book["title"]}</a></h2><p>{chapters} lessons · {book["words"]:,} words</p><p><a href="{stem}.ipynb">Notebook</a> · <a href="{stem}.md">Source</a></p></article>')
runtime_results={name:json.loads((root/path).read_text(encoding='utf-8')).get('status','recorded') if (root/path).exists() else 'not recorded' for name,path in {'Docker':'labs/study-coach/container-report.json','Kubernetes':'labs/kubernetes-report.json','Redis failover':'labs/redis-failover-report.json'}.items()}
runtime_summary='; '.join(name+': '+status for name,status in runtime_results.items())+'. Public cloud not deployed.'
report['projects']={'remote_mcp':mcp,'connected_system':system,'java_suites':junit,'browser_stats':browser['stats'],'python_package_tests':5,'react_node_tests':3,'container_runtime':runtime_summary}
report['projects']['retrieval_evaluation']=evaluation
(root/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
words=sum(x['words'] for x in report['books']);lessons=sum(x['chapters'] for x in report['books']);count=len(report['labs'])
summary=f'<h1>Your engineering learning library</h1><p>{len(report["books"])} notebooks · {lessons} lessons · {words:,} words · {count} passing notebook labs</p><p class="notice">Simple explanations lead to working code, failure cases, design choices and interview practice. Includes databases, six RAG routes, Kafka, caching, real-time delivery, Docker and Kubernetes. Read offline; running code requires the documented software. Recipes and verified executions are labelled separately.</p><p><a href="START-HERE.html">Learning route</a> · <a href="STUDY-ON-ANY-DEVICE.html">Laptop and mobile commands</a> · <a href="VALIDATION.html">Evidence and limitations</a> · <a href="COMPLETION-AUDIT.html">Completion audit</a></p><div class="cards">'+''.join(cards)+'</div>'
(root/'index.html').write_text(scope['page']('Engineering Notebook Library',summary),encoding='utf-8')
lines=['# Validation and coverage report','','Updated on 24 September 2026; individual reports include retained earlier evidence. Executable evidence is distinguished from deployment recipes and architectural extensions.','','## Results','','| Check | Result |','| --- | --- |',f'| Notebook execution | {count} passed; no failed cells |',f'| Reading material | 21 notebooks, {lessons} lessons, {words:,} words |','| Connected Java service | 8 integration tests passed |','| Original Spring starter | 3 tests passed in foundation validation |','| React unit/DOM/hydration | 3 tests passed |','| Connected browser tests | 12 passed across Chromium, Firefox and WebKit, including failure journeys and axe checks |','| Python package | Wheel and source distribution built; strict mypy passed; 5 pytest cases passed |',f'| Remote MCP | {len(mcp["passed"])} network check groups passed |',f'| Full-stack HTTP/recovery | {len(system["passed"])} check groups passed |','| Docker/cloud | Docker unavailable; recipes supplied, not executed |','| Local model | Actual Ollama tool calling and generation exercised; see advanced evidence below |','','## Notebook contents','','| Notebook | Lessons | Passing executable cells |','| --- | --- | --- |']
for book in report['books']:
    n=sum(lab['book']==book['name'] for lab in report['labs'])
    lines.append(f'| [{book["title"]}]({book["name"]}.html) | {book["chapters"]} | {n} |')
lines=[line.replace('21 notebooks,',str(len(report['books']))+' notebooks,').replace('Docker unavailable; recipes supplied, not executed',runtime_summary) for line in lines]
lines=[line.replace('Updated on 24 September 2026','Updated on 25 September 2026') for line in lines]
lines.insert(lines.index('## Notebook contents')-1,'**Model-quality finding:** the earlier Study Coach generated answer made an incorrect checkpoint-idempotency claim; its factual review remains failed. The separate RAG lab clarified its source and passed four revised tutor-reviewed development cases after an initial flawed answer and runtime timeout. This small set does not establish general accuracy. The reports preserve all stages, and the extractive mode remains the default.')
lines+=['','Architecture and interview workbooks primarily contain guided reading and exercises. Executable cells retain recorded outputs. Java and JavaScript are launched by Python notebook cells and require their own runtimes. Each of the 23 GoF patterns has a small executable implementation and assertion in Notebook 13.','','## Network test evidence','']
lines+=['A separate versioned retrieval evaluation passed 16 development cases: 10 relevance cases, 4 ownership cases and 2 no-evidence cases. The report stores returned IDs, latency and a source hash. This is not an LLM reasoning benchmark.','']
lines += ['- '+item for item in system['passed']+mcp['passed']]
lines += ['','## Runtime evidence','','Python '+report['runtime']+'; Node.js 24.13.0; Java 26.0.2.1 compiling examples for Java 21; Maven 3.9.12; Spring Boot 4.1.1. Exact frontend packages are in npm lockfiles. Python top-level pins are in requirements-tested.txt.','','| Python package | Version |','| --- | --- |']
lines += [f'| {name} | {version} |' for name,version in report['packages'].items()]
lines += ['','## Practical limitations','','The default classroom profile uses H2, local identities and extractive retrieval. Optional profiles add a real local model, OIDC login, PostgreSQL and a persistent broker. The advanced evidence section reports which integrations passed. These are local educational deployments, not a public cloud rollout or production security certification. The evidence collection remains deliberately small.','','The restart test kills Java and restarts it with the same database. It does not simulate every disk failure or whole-machine power loss. Accessibility testing covers the included completed-page journey, selected automated rules and explicit keyboard interactions; it is not a complete manual certification. H2 tests do not establish another database engine’s semantics.','','Python validation used a local environment inheriting installed scientific packages; every platform and clean installation has not been tested. Framework APIs were checked against official documentation and installed versions. Pins expose tested versions, but transitive dependencies and future releases need compatibility checks. No finite collection guarantees every interview or covers all published algorithms.','','## Recorded notebook outputs','']
for lab in report['labs']:lines += [f'### {lab["book"]} / {lab["name"]}','','Status: passed.','','```text',lab['output'].strip(),'```','']
(root/'VALIDATION.md').write_text('\n'.join(lines),encoding='utf-8')
advanced=[]
for filename in ['live-model-report.json','live-stack-report.json','live-stack-review.json','distributed-report.json','identity-report.json','identity-cluster-report.json','monitoring-report.json']:
    candidate=root/'labs/study-coach'/filename
    if not candidate.exists():
        candidate=root/'labs/study-coach/python'/filename
    if candidate.exists():
        data=json.loads(candidate.read_text());report['projects'][filename]=data
        advanced+=['### '+filename,'','```json',json.dumps(data,indent=2),'```','']
    else:advanced+=['### '+filename,'','No passing report has been recorded for this check.','']
for relative in ['labs/kafka-lab/report.json','labs/realtime-cache/report.json','labs/realtime-cache/browser-report.json','labs/realtime-cache/recovery-report.json','labs/collector-lab/report.json','labs/rag-flow/report.json','labs/rag-flow/live-report.json','labs/rag-flow/live-review.json','labs/rag-flow/live-retest-report.json','labs/study-coach/identity-cluster-initial-report.json','labs/study-coach/identity-cluster-failure-review.json','study-server-report.json','portable-report.json']:
    candidate=root/relative
    if candidate.exists():
        data=json.loads(candidate.read_text(encoding='utf-8'));report['projects'][relative]=data
        advanced+=['### '+relative,'','```json',json.dumps(data,indent=2),'```','']
for relative in ['labs/study-coach/identity-repeat-before-report.json','labs/study-coach/identity-repeat-report.json','labs/study-coach/identity-diagnosis.json','labs/study-coach/durable-relay-report.json','labs/kafka-lab/cluster-report.json','labs/realtime-cache/endurance-report.json','labs/collector-lab/durable-report.json','labs/collector-lab/persistent-report.json','labs/rag-flow/pretrained-report.json','labs/rag-flow/factual-holdout-report.json','labs/rag-flow/factual-holdout-review.json','labs/rag-flow/abstention-retest-report.json','labs/rag-flow/pretrained-integration-report.json','labs/rag-flow/model-integration-report.json','labs/rag-flow/injection-retest-report.json']:
    candidate=root/relative
    if candidate.exists():
        data=json.loads(candidate.read_text(encoding='utf-8'));report['projects'][relative]=data
        advanced+=['### '+relative,'','```json',json.dumps(data,indent=2),'```','']
for relative in ['labs/rag-flow/bounded-generation-report.json','labs/rag-flow/development-regression-report.json','labs/rag-flow/generation-recovery-report.json','labs/rag-flow/graph-pipeline-report.json','labs/study-coach/durable-spring-initial-report.json','labs/study-coach/durable-spring-report.json','labs/realtime-cache/multi-instance-report.json','labs/linux-runtime-report.json','labs/docker-runtime-report.json','labs/k3s-install-report.json','labs/redis-failover-report.json','labs/study-coach/container-report.json','labs/kubernetes-report.json']:
    candidate=root/relative
    if candidate.exists():
        data=json.loads(candidate.read_text(encoding='utf-8'));report['projects'][relative]=data
        advanced+=['### '+relative,'','```json',json.dumps(data,indent=2),'```','']
for candidate in [root/'labs/interview-workshop/test-report.json',root/'labs/kubernetes-initial-report.json',root/'labs/kubernetes-initial-review.json',root/'labs/kubernetes-readiness-race-report.json',*sorted((root/'labs/realtime-cache').glob('endurance-*-report.json'))]:
    if not candidate.exists():continue
    relative=candidate.relative_to(root).as_posix();data=json.loads(candidate.read_text(encoding='utf-8'));report['projects'][relative]=data
    advanced+=['### '+relative,'','```json',json.dumps(data,indent=2),'```','']
advanced+=['## Remaining external verification','',runtime_summary,'','Physical Safari/iOS and a full manual screen-reader audit have not been completed. Real provider logout with a temporarily unavailable receiver, Redis Sentinel promotion, model-extracted graph maintenance, three-process Kafka recovery and persistent telemetry are documented in the reports. The revised eight-case generative development regression passed six cases; one over-abstained and one timed out. This remains an experimental model path, with extractive answers the default. Personal interview grading requires the learner’s own submitted answers. No finite library covers every possible algorithm or guarantees every exam. See COMPLETION-AUDIT.html for current scope and limits.','']
with (root/'VALIDATION.md').open('a',encoding='utf-8') as file:file.write('\n## Advanced integration evidence\n\n'+'\n'.join(advanced))
(root/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
for stem in ['START-HERE','VALIDATION','STUDY-ON-ANY-DEVICE','COMPLETION-AUDIT']:
    source=(root/(stem+'.md')).read_text(encoding='utf-8');body,toc,_=scope['render_markdown'](source)
    (root/(stem+'.html')).write_text(scope['page'](source.splitlines()[0][2:],body,toc),encoding='utf-8')
class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.ids=set()
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'id' in attrs:self.ids.add(attrs['id'])
        if tag=='a' and 'href' in attrs:self.links.append(attrs['href'])
for path in root.glob('*.html'):
    parsed=Links();parsed.feed(path.read_text(encoding='utf-8'))
    for href in parsed.links:
        if href.startswith(('http:','https:','mailto:')):continue
        if href.startswith('#'):assert href[1:] in parsed.ids,(path,href)
        else:assert (path.parent/href.split('#')[0]).exists(),(path,href)
archive=root.parent/'Engineering-Notebooks.zip'
excluded={'.runtime','.venv','node_modules','target','__pycache__','.git','.mypy_cache','.pytest_cache','build','data'}
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as output:
    for folder,dirs,files in os.walk(root):
        dirs[:]=[name for name in dirs if name not in excluded and not name.endswith('.egg-info')]
        for name in files:
            path=Path(folder)/name;relative=path.relative_to(root)
            if path.suffix in {'.log','.pyc'} or name=='.env':continue
            if 'test-results' in relative.parts and path.name!='report.json':continue
            output.write(path,Path('engineering-notebooks')/relative)
with zipfile.ZipFile(archive) as verified:assert verified.testzip() is None
print(json.dumps({'notebooks':len(report['books']),'lessons':lessons,'words':words,'labs':count,'archive_bytes':archive.stat().st_size}))
