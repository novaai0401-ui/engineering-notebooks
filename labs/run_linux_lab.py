"""Portable Windows wrapper for the two lab-owned Linux verification runners."""
import argparse,subprocess
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('lab',choices=['redis','kubernetes']);parser.add_argument('--capstone',action='store_true');args=parser.parse_args()
script=Path(__file__).resolve().with_name('test_redis_failover.py' if args.lab=='redis' else 'test_kubernetes.py')
if len(script.drive)!=2 or script.drive[1]!=':':raise SystemExit('Use an extracted library on a local Windows drive')
linux='/mnt/'+script.drive[0].lower()+'/'+script.as_posix().split(':/',1)[1]
command=['wsl','-d','EngineeringNotebookLab-13e66a98','--exec','/usr/bin/env','PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin','/usr/bin/python3',linux]
if args.capstone:
 if args.lab!='kubernetes':raise SystemExit('--capstone requires kubernetes')
 command.append('--capstone')
raise SystemExit(subprocess.run(command).returncode)
