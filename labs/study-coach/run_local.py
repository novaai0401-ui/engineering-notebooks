"""Run the classroom services; Ctrl+C stops only processes started here."""
import os,re,socket,subprocess,sys,time
from pathlib import Path
root=Path(__file__).resolve().parent
for key in ['COACH_PASSWORD','COACH_SERVICE_TOKEN']:
    if len(os.environ.get(key,''))<12:raise SystemExit(f'Set {key} to a sufficiently long local secret first')
for port in [8091,8092]:
    with socket.socket() as s:
        try:s.bind(('127.0.0.1',port))
        except OSError:raise SystemExit(f'Port {port} is already used; existing processes were left untouched')
jar=root/'java/target/study-coach-1.0.0.jar'
if not jar.exists():raise SystemExit('Build the frontend and Java package first; see README.md')
processes=[];logs=[]
properties=subprocess.run(['java','-XshowSettings:properties','-version'],capture_output=True,text=True,check=True)
java_home=re.search(r'java.home\s*=\s*(.+)',properties.stderr).group(1).strip()
java_exe=str(Path(java_home)/'bin'/('java.exe' if os.name=='nt' else 'java'))
try:
    for name,command,cwd in [('python',[sys.executable,'-m','uvicorn','coach_ai:app','--host','127.0.0.1','--port','8092'],root/'python'),('java',[java_exe,'-jar',str(jar)],root/'java')]:
        log=(root/(name+'-local.log')).open('w',encoding='utf-8');logs.append(log)
        processes.append(subprocess.Popen(command,cwd=cwd,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)))
    print('Services are starting. Open http://127.0.0.1:8091 when ready. Learners: alice or bob. Use COACH_PASSWORD. Ctrl+C stops both.')
    while all(p.poll() is None for p in processes):time.sleep(1)
    raise SystemExit('A service exited; inspect the local log files')
except KeyboardInterrupt:pass
finally:
    for process in processes:
        if process.poll() is None:
            if os.name=='nt':subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True)
            else:process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait()
    for log in logs:log.close()
