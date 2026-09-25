"""Actual disposable MySQL/Oracle containers; Linux Docker, no published ports."""
import argparse,json,os,secrets,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('engine',choices=['mysql','oracle']);p.add_argument('--image',help='Explicit trusted registry image override, recorded in evidence');args=p.parse_args()
engine=args.engine;name='notebook-plan-'+engine+'-'+secrets.token_hex(4)
image=args.image or ('mysql:8.4' if engine=='mysql' else 'gvenzl/oracle-free:23-slim')
report={'status':'failed','engine':engine,'image':image,'checks':[], 'scope':'Disposable actual engine on one local Docker host; 1000 synthetic rows. Oracle Free is not Oracle 19c certification. No production benchmark.'}
def docker(*args,input=None,timeout=120,check=True):
    r=subprocess.run(['docker',*args],input=input,capture_output=True,text=True,timeout=timeout)
    if check and r.returncode:raise RuntimeError('Docker operation failed: '+(r.stderr or r.stdout)[-2000:])
    return r
def sql(text,check=True):
    if engine=='mysql':
        return docker('exec','-i',name,'sh','-c','MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot --batch --raw',input=text,check=check)
    return docker('exec','-i',name,'sqlplus','-s','/ as sysdba',input='whenever sqlerror exit failure rollback\nset linesize 220 pagesize 500 trimspool on\n'+text+'\nexit\n',check=check)
try:
    if docker('image','inspect',image,check=False).returncode:
        print('Pulling '+image,flush=True);docker('pull',image,timeout=1200)
    report['image_digest']=json.loads(docker('image','inspect',image,'--format','{{json .RepoDigests}}').stdout)
    with tempfile.TemporaryDirectory(prefix='notebook-db-') as temp:
        env=Path(temp)/'env';env.write_text(('MYSQL_ROOT_PASSWORD='+secrets.token_urlsafe(32)) if engine=='mysql' else 'ORACLE_RANDOM_PASSWORD=yes');os.chmod(env,0o600)
        docker('run','-d','--name',name,'--memory','3g','--env-file',str(env),image)
    print('Waiting for '+engine,flush=True)
    deadline=time.monotonic()+360
    while True:
        r=sql('SELECT 1;' if engine=='mysql' else "SELECT open_mode FROM v$pdbs WHERE name='FREEPDB1';",check=False)
        if r.returncode==0 and 'ORA-' not in r.stdout and (engine=='mysql' or 'READ WRITE' in r.stdout):break
        if time.monotonic()>deadline:raise TimeoutError('Database readiness')
        time.sleep(2)
    if engine=='mysql':
        report['version']=sql('SELECT VERSION();').stdout.strip()
        text='CREATE DATABASE notebook_plans; USE notebook_plans;\n'+(ROOT/'mysql.sql').read_text()
        output=sql(text).stdout
        assert '1000' in output and 'nb_tickets_lookup' in output and 'actual time=' in output
        assert 'Table scan on nb_tickets' in output and 'Covering index lookup' in output
        report['checks']=['Seeded 1000 rows','Executed EXPLAIN and EXPLAIN ANALYZE','Observed table scan before and covering index lookup after','Executed changed query without status equality']
        began=time.monotonic()
        dump=docker('exec',name,'sh','-c','MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump -uroot --single-transaction --set-gtid-purged=OFF --no-tablespaces --skip-add-drop-table notebook_plans').stdout
        sql('CREATE DATABASE notebook_restore; USE notebook_restore;\n'+dump)
        compare=sql('SELECT COUNT(*) AS mismatches FROM notebook_plans.nb_tickets a LEFT JOIN notebook_restore.nb_tickets b USING(id) WHERE b.id IS NULL OR a.tenant_id<>b.tenant_id OR a.status<>b.status OR a.created_at<>b.created_at OR a.price_minor<>b.price_minor; SELECT COUNT(*) AS restored_rows FROM notebook_restore.nb_tickets;').stdout
        assert 'mismatches\n0\n' in compare and 'restored_rows\n1000\n' in compare
        report['local_backup_restore_seconds']=round(time.monotonic()-began,2)
        report['checks'].append('Logical backup restored into separate database; all 1000 rows and fields reconciled')
    else:
        report['version']=sql('SELECT banner_full FROM v$version;').stdout.strip()
        setup='ALTER SESSION SET CONTAINER=FREEPDB1;\nCREATE USER nb_lab NO AUTHENTICATION;\nALTER USER nb_lab QUOTA UNLIMITED ON users;\nALTER SESSION SET CURRENT_SCHEMA=nb_lab;\n'
        text=(ROOT/'oracle.sql').read_text().replace("DBMS_STATS.GATHER_TABLE_STATS(USER,", "DBMS_STATS.GATHER_TABLE_STATS('NB_LAB',")
        text+='\nCOLUMN target_sql NEW_VALUE target_sql NOPRINT\nCOLUMN target_child NEW_VALUE target_child NOPRINT\nSELECT sql_id target_sql,child_number target_child FROM v$sql WHERE sql_text LIKE \'SELECT /*+ gather_plan_statistics */ /* nb_after */%\' ORDER BY last_active_time DESC FETCH FIRST 1 ROW ONLY;\nSELECT * FROM TABLE(DBMS_XPLAN.DISPLAY_CURSOR(\'&target_sql\',&target_child,\'ALLSTATS LAST +PREDICATE\'));\n'
        output=sql(setup+text).stdout
        assert '1000' in output and 'NB_TICKETS_LOOKUP' in output and 'A-Rows' in output
        assert 'TABLE ACCESS FULL' in output and 'INDEX RANGE SCAN' in output
        report['checks']=['Seeded 1000 rows in isolated schema','Executed EXPLAIN PLAN and DBMS_XPLAN.DISPLAY','Gathered optimizer statistics','Captured executed cursor and ALLSTATS LAST with actual rows','Observed table scan before and index range scan after']
    (ROOT/(engine+'-plans.txt')).write_text(output.rstrip()+'\n',encoding='utf-8')
    report['status']='passed'
except Exception as error:
    report['error']=str(error);raise
finally:
    docker('rm','-f','-v',name,check=False)
    (ROOT/(engine+'-report.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)
