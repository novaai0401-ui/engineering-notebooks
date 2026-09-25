"""Check the delivered archive contains learning artifacts, not private runtimes."""
from pathlib import Path
import json,zipfile,hashlib,subprocess,sys,tempfile,os
root=Path(__file__).resolve().parent;archive=root.parent/'Engineering-Notebooks.zip'
with zipfile.ZipFile(archive) as package:
    assert package.testzip() is None
    names=package.namelist()
    forbidden={'.runtime','.venv','node_modules','target','.git','__pycache__','.env'}
    for name in names:
        p=Path(name)
        assert not (set(p.parts)&forbidden),name
        assert p.suffix.lower() not in {'.exe','.dll','.jar','.hprof','.log','.pyc'},name
    books=[name for name in names if Path(name).suffix=='.ipynb' and Path(name).name[:2].isdigit()]
    evidence=json.loads(package.read('engineering-notebooks/validation.json'))
    assert len(books)==len(evidence['books'])==len(list(root.glob('[0-9][0-9]-*.md')))
    cells=0
    for name in books:
        notebook=json.loads(package.read(name))
        for cell in notebook['cells']:
            if cell['cell_type']=='code':
                cells+=1;assert cell['execution_count'] is not None,name
                assert all(o['output_type']!='error' for o in cell['outputs']),name
    assert cells==len(evidence['labs']) and cells>=134,cells
runtime=root/'.runtime';runtime.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='portable-',dir=runtime) as temporary:
    destination=Path(temporary).resolve();assert destination.is_relative_to(runtime.resolve())
    with zipfile.ZipFile(archive) as package:
        for name in package.namelist():assert (destination/name).resolve().is_relative_to(destination),name
        package.extractall(destination)
    extracted=destination/'engineering-notebooks';environment=dict(os.environ,PYTHONIOENCODING='utf-8')
    commands=[['labs/rag-flow/test_flow.py'],['labs/rag-flow/test_generation_recovery.py'],['run_notebook_labs.py','--book','29-databases-for-fullstack-and-ai'],['run_notebook_labs.py','--book','30-rag-patterns-and-user-defined-flows'],['run_notebook_labs.py','--book','32-load-balancing-from-playground-to-production'],['run_notebook_labs.py','--book','33-production-readiness-and-evidence-workbook'],['test_study_server.py']]
    for command in commands:
        result=subprocess.run([sys.executable,'-S',*command],cwd=extracted,env=environment,capture_output=True,text=True,encoding='utf-8',timeout=45)
        assert result.returncode==0,result.stdout+result.stderr
portable={'passed':['Extracted ZIP passed offline RAG and generation-recovery tests with Python site-packages disabled','Extracted database, RAG, load-balancing and production-readiness notebook cells executed with standard-library-only Python','Extracted study server passed real loopback HTTP and path-boundary tests'],'limitations':'Executed on Windows Python 3.11 with -S; not a physical macOS/Linux/phone test and not all optional service dependencies.'}
(root/'portable-report.json').write_text(json.dumps(portable,indent=2),encoding='utf-8')
print(json.dumps({'archive':archive.name,'books':len(books),'recorded_code_cells':cells,'files':len(names),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'runtime_and_secret_files_excluded':True,'portable_smoke_commands':len(commands)},indent=2))
