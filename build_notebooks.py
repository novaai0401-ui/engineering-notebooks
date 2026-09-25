from pathlib import Path
import ast
import asyncio
import contextlib
import html
import inspect
import io
import json
import re
import subprocess
import sys
import time
import importlib.metadata as metadata

import nbformat
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent
SOURCES = sorted(ROOT.glob('[0-9][0-9]-*.md'))
assert len(SOURCES) >= 15
REPORT = {'runtime':sys.version.split()[0], 'books':[], 'labs':[], 'recipes':[], 'packages':{}}
for name in ['langchain','langgraph','deepagents','fastmcp','mcp','numpy','pandas','scikit-learn','torch','nbformat','markdown-it-py','langgraph-checkpoint-sqlite','fastapi','uvicorn','httpx','pytest','mypy','build','psycopg','prometheus-client','opentelemetry-api','opentelemetry-sdk','opentelemetry-exporter-otlp-proto-http']:
    try: REPORT['packages'][name] = metadata.version(name)
    except metadata.PackageNotFoundError: REPORT['packages'][name] = 'unavailable'

CSS = '''
:root{color-scheme:light;--ink:#19313f;--muted:#475c65;--paper:#fffdf8;--accent:#095769;--line:#ced9db}
*{box-sizing:border-box}body{margin:0;color:var(--ink);background:var(--paper);font:18px/1.75 Georgia,serif}
a{color:var(--accent);text-underline-offset:3px}a:focus-visible,summary:focus-visible{outline:3px solid #b15a15;outline-offset:4px}
nav{position:fixed;inset:0 auto 0 0;width:290px;overflow:auto;background:#edf3f2;border-right:1px solid var(--line);padding:25px;font:14px/1.5 system-ui,sans-serif}
nav strong{font-size:20px}nav ul{list-style:none;padding:0}nav li{margin:10px 0}nav a{text-decoration:none}nav details{font-size:12px;margin-top:5px}nav details ul{padding-left:12px}summary{cursor:pointer}
main{max-width:1060px;margin-left:290px;padding:60px 55px 90px}h1,h2,h3{font-family:system-ui,sans-serif;line-height:1.25;letter-spacing:-.025em}
h1{font-size:43px}h2{font-size:29px;margin-top:65px;border-top:2px solid var(--line);padding-top:25px}h3{font-size:22px;margin-top:35px}
pre{font:13.5px/1.65 Consolas,monospace;white-space:pre;overflow:auto;padding:20px;background:#e9f0f2;border-left:4px solid var(--accent)}
p code,li code,td code{font: .87em Consolas,monospace;background:#e9f0f2;padding:2px 4px;overflow-wrap:anywhere}
.table-wrap{overflow:auto}table{border-collapse:collapse;width:100%;font:14px/1.55 system-ui,sans-serif;margin:24px 0}th,td{border:1px solid var(--line);padding:10px;vertical-align:top;text-align:left}th{background:#e1edeb}
.meta,.downloads,.notice{font:14px/1.6 system-ui,sans-serif;color:var(--muted)}.notice{background:#edf3f2;border-left:4px solid var(--accent);padding:16px}.downloads a{margin-right:15px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:20px}.card{border:1px solid var(--line);padding:22px;background:white}.card h2{font-size:22px;border:0;margin:0;padding:0}
.index{margin:0 auto;max-width:1150px}.skip{position:absolute;top:-70px;left:10px}.skip:focus{top:10px;background:white;padding:10px}
@media(max-width:900px){nav{position:static;width:100%;max-height:300px}main{margin:0;padding:25px 20px 60px}body{font-size:17px}h1{font-size:34px}}
@media print{nav,.downloads,.skip{display:none}main{margin:0;padding:0;max-width:none}body{font-size:11pt}h1{font-size:28pt}h2{break-before:page;font-size:20pt}h3{break-after:avoid}pre{font-size:8pt;white-space:pre-wrap}table{font-size:8pt}tr{break-inside:avoid}.table-wrap{overflow:visible}}
'''

def page(title, body, toc='', downloads=''):
    nav = '<nav aria-label="Notebook navigation"><strong>Engineering notebooks</strong><p><a href="index.html">All notebooks</a></p>'+toc+'</nav>' if toc else ''
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>'+html.escape(title)+'</title><style>'+CSS+'</style></head><body><a class="skip" href="#content">Skip to content</a>'+nav+'<main id="content"'+(' class="index"' if not toc else '')+'>'+downloads+body+'</main></body></html>'

def render_markdown(text):
    md = MarkdownIt('commonmark', {'html':False}).enable('table')
    tokens = md.parse(text)
    sections=[]
    for i, token in enumerate(tokens):
        if token.type == 'heading_open':
            label=tokens[i+1].content
            anchor='section-'+str(i)
            token.attrSet('id',anchor)
            if token.tag=='h2': sections.append({'anchor':anchor,'label':label,'children':[]})
            elif token.tag=='h3' and sections: sections[-1]['children'].append((anchor,label))
    body=md.renderer.render(tokens,md.options,{})
    body=body.replace('<table>', '<div class="table-wrap" role="region" aria-label="Reference table" tabindex="0"><table>').replace('</table>','</table></div>')
    toc='<ul>'
    for section in sections:
        toc+='<li><a href="#'+section['anchor']+'">'+html.escape(section['label'])+'</a>'
        if section['children']:
            toc+='<details><summary>Examples and subtopics</summary><ul>'+''.join('<li><a href="#'+a+'">'+html.escape(t)+'</a></li>' for a,t in section['children'])+'</ul></details>'
        toc+='</li>'
    return body,toc+'</ul>',len(sections)

def wrapper(language, source, name):
    if language=='python': return source
    if language=='java':
        return f'''# Run the Java example using your installed JDK.
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
source = {source!r}
with TemporaryDirectory() as folder:
    java_file = Path(folder) / "{name}.java"
    java_file.write_text(source, encoding="utf-8")
    compiled = subprocess.run(["javac", "--release", "21", str(java_file)], capture_output=True, text=True, timeout=60)
    if compiled.returncode: raise RuntimeError(compiled.stderr)
    result = subprocess.run(["java", "-ea", "-cp", folder, "{name}"], capture_output=True, text=True, timeout=30)
    if result.returncode: raise RuntimeError(result.stderr)
    print(result.stdout.strip())
'''
    if language=='javascript':
        return f'''# Run the JavaScript example using your installed Node.js.
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
source = {source!r}
with TemporaryDirectory() as folder:
    script = Path(folder) / "{name}.mjs"
    script.write_text(source, encoding="utf-8")
    result = subprocess.run(["node", str(script)], capture_output=True, text=True, timeout=30)
    if result.returncode: raise RuntimeError(result.stderr)
    print(result.stdout.strip())
'''
    raise ValueError(language)

def execute(code, scope):
    output=io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        compiled=compile(code, '<teaching-lab>', 'exec', flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
        result=eval(compiled,scope)
        if inspect.isawaitable(result): asyncio.run(result)
    return output.getvalue()

cards=[]
previous=json.loads((ROOT/'validation.json').read_text(encoding='utf-8')) if (ROOT/'validation.json').exists() else None
selected_book=sys.argv[sys.argv.index('--book')+1] if '--book' in sys.argv else None
if selected_book and selected_book not in {path.stem for path in SOURCES}:raise ValueError('Unknown notebook stem')
for source_path in SOURCES:
    text=source_path.read_text(encoding='utf-8')
    title=text.splitlines()[0].removeprefix('# ')
    body,toc,chapters=render_markdown(text)
    stem=source_path.stem
    retained=previous and any(book['name']==stem for book in previous['books'])
    if retained and (selected_book and stem!=selected_book or '--new-only' in sys.argv):
        REPORT['books'].append(next(b for b in previous['books'] if b['name']==stem))
        REPORT['labs'].extend(x for x in previous['labs'] if x['book']==stem)
        REPORT['recipes'].extend(x for x in previous['recipes'] if x['book']==stem)
        cards.append('<article class="card"><h2><a href="'+stem+'.html">'+html.escape(title)+'</a></h2><p>Previously verified foundation or workshop</p></article>')
        continue
    cells=[nbformat.v4.new_markdown_cell('# Execution guide\n\nRead the lessons in order. Python labs are executable. Java and JavaScript examples include Python launch cells that use your installed JDK or Node.js; this is a Python-kernel notebook, not a Java kernel. Provider-backed integration recipes remain displayed text and are not run. The React project and Spring project have separate build instructions in START-HERE.md. Recorded outputs came from the accompanying validation run. To rerun, select an environment with the versions in requirements-tested.txt.')]
    scope={'__name__':'__notebook__'}
    cursor=0
    execution_count=0
    for match in re.finditer(r'^```([^\n]*)\n(.*?)^```\s*$', text, re.M|re.S):
        before=text[cursor:match.start()]
        if before.strip(): cells.append(nbformat.v4.new_markdown_cell(before))
        info=match.group(1).strip()
        source=match.group(2)
        language=info.split()[0] if info else ''
        marker=re.search(r'^(?:#|//) lab: ([A-Za-z0-9_]+)',source,re.M)
        if marker and language in ('python','java','javascript'):
            name=marker.group(1)
            if language!='python': cells.append(nbformat.v4.new_markdown_cell(match.group(0)))
            code=wrapper(language,source,name)
            execution_count+=1
            began=time.monotonic()
            try:
                output=execute(code,scope)
                status='passed'
            except Exception as exc:
                output=f'{type(exc).__name__}: {exc}'
                status='failed'
                print(f'FAILED {stem}/{name}: {output}', flush=True)
            REPORT['labs'].append({'book':stem,'name':name,'language':language,'status':status,'output':output,'seconds':round(time.monotonic()-began,3)})
            cell=nbformat.v4.new_code_cell(code,execution_count=execution_count)
            cell.metadata['tags']=['offline-lab',language]
            cell.outputs=[nbformat.v4.new_output('stream',name='stdout',text=output)]
            cells.append(cell)
            print(f'{status.upper()} {stem}/{name}',flush=True)
            lab_dir=ROOT/'labs'/('java' if language=='java' else 'javascript' if language=='javascript' else 'python')
            lab_dir.mkdir(parents=True,exist_ok=True)
            ext={'python':'cell.txt','java':'java','javascript':'mjs'}[language]
            (lab_dir/f'{name}.{ext}').write_text(source,encoding='utf-8')
        else:
            cells.append(nbformat.v4.new_markdown_cell(match.group(0)))
            if 'recipe' in info: REPORT['recipes'].append({'book':stem,'language':language,'status':'reference-only; not provider-executed'})
            if language=='jsx' and marker:
                project=ROOT/'labs'/'react-demo'/'src'
                project.mkdir(parents=True,exist_ok=True)
                (project/'StudyApp.jsx').write_text(source,encoding='utf-8')
        cursor=match.end()
    if text[cursor:].strip(): cells.append(nbformat.v4.new_markdown_cell(text[cursor:]))
    notebook=nbformat.v4.new_notebook(cells=cells,metadata={'kernelspec':{'display_name':'Python 3 (engineering labs)','language':'python','name':'python3'},'language_info':{'name':'python','version':REPORT['runtime']}})
    nbformat.validate(notebook)
    nbformat.write(notebook,ROOT/(stem+'.ipynb'))
    downloads='<p class="downloads"><a href="'+stem+'.ipynb">Jupyter notebook</a><a href="'+stem+'.md">Markdown source</a><a href="index.html">Library home</a></p>'
    (ROOT/(stem+'.html')).write_text(page(title,body,toc,downloads),encoding='utf-8')
    REPORT['books'].append({'name':stem,'title':title,'words':len(text.split()),'chapters':chapters})
    cards.append('<article class="card"><h2><a href="'+stem+'.html">'+html.escape(title)+'</a></h2><p>'+str(chapters)+' lessons · '+f'{len(text.split()):,}'+' words</p><p><a href="'+stem+'.ipynb">Notebook</a> · <a href="'+stem+'.md">Text source</a></p></article>')

summary='<h1>Your engineering learning notebooks</h1><p>Stories first. Small examples next. Then code, design, failure cases, and interview practice.</p><p class="notice">'+str(len(SOURCES))+' original, self-contained workbooks. Read these HTML editions offline. Jupyter editions include recorded lab outputs. Running code needs the stated runtimes and dependencies; integration reports distinguish actual service checks from reference configurations.</p><p><a href="START-HERE.html">Start here and choose your learning route</a> · <a href="VALIDATION.html">Validation and coverage report</a></p><div class="cards">'+''.join(cards)+'</div>'
(ROOT/'index.html').write_text(page('Engineering Notebook Library',summary),encoding='utf-8')
(ROOT/'validation.json').write_text(json.dumps(REPORT,indent=2),encoding='utf-8')
(ROOT/'requirements-tested.txt').write_text('\n'.join(f'{n}=={v}' for n,v in REPORT['packages'].items() if v!='unavailable')+'\n',encoding='utf-8')
failed=[lab for lab in REPORT['labs'] if lab['status']!='passed']
print(json.dumps({'books':len(SOURCES),'words':sum(b['words'] for b in REPORT['books']),'labs':len(REPORT['labs']),'failed':[x['name'] for x in failed]}),flush=True)
sys.exit(1 if failed else 0)

