"""Portable Windows wrapper for lab-owned Linux verification runners."""
import argparse,subprocess
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('lab',choices=['redis','kubernetes','load-balancing','tls-websocket','mysql','oracle']);parser.add_argument('--capstone',action='store_true');args=parser.parse_args()
script=Path(__file__).resolve().parent/({'redis':'test_redis_failover.py','kubernetes':'test_kubernetes.py','load-balancing':'load-balancing/test_nginx.py','tls-websocket':'load-balancing/test_tls_websocket.py','mysql':'database-plan-workshop/test_engines.py','oracle':'database-plan-workshop/test_engines.py'}[args.lab])
if len(script.drive)!=2 or script.drive[1]!=':':raise SystemExit('Use an extracted library on a local Windows drive')
linux='/mnt/'+script.drive[0].lower()+'/'+script.as_posix().split(':/',1)[1]
command=['wsl','-d','EngineeringNotebookLab-13e66a98','--exec','/usr/bin/env','PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','/usr/bin/python3',linux]
if args.lab in ('mysql','oracle'):command.append(args.lab)
if args.capstone:
 if args.lab!='kubernetes':raise SystemExit('--capstone requires kubernetes')
 command.append('--capstone')
raise SystemExit(subprocess.run(command).returncode)
