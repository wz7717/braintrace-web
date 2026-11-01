"""Synthetic lifetime test ONLY; never selected by HTTP input or normal server startup."""
from pathlib import Path
import argparse, json, os, subprocess, sys, time
ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,required=True);args=ap.parse_args()
w=args.work
while not (w/'START').exists():time.sleep(.01)
spec=json.loads((w/'request.json').read_text());mode=spec['sample_id']
if mode in ('hang','orphan'):
    marker=Path((w/'input.bin').read_text())
    child=subprocess.Popen([sys.executable,'-c', 'import os,sys,time; from pathlib import Path; Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(60)',str(marker)],
        creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    deadline=time.monotonic()+5
    while not marker.exists() and time.monotonic()<deadline:time.sleep(.01)
    if mode=='orphan':os._exit(3)
    time.sleep(60)
elif mode=='crash':
    raise SystemExit(4)
else:
    (w/'response.json').write_text(json.dumps({'ok':True,'result':{'sample_id':mode,'synthetic':True}}))
