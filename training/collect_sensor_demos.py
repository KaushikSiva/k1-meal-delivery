#!/usr/bin/env python3
"""Execute the frozen small teacher-data protocol; retain every attempt."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--protocol', type=Path, default=ROOT/'training/SENSOR_DEMO_PROTOCOL.json')
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    protocol = json.loads(args.protocol.read_text())
    summary = {'started_at_utc': datetime.now(timezone.utc).isoformat(),
               'protocol': protocol, 'protocol_sha256': hashlib.sha256(args.protocol.read_bytes()).hexdigest(),
               'episodes': [], 'training_performed': False}
    for trial in protocol['episodes']:
        out = args.output/trial['id']
        cmd = [sys.executable, str(ROOT/'sim/run_k1_sensor_navigation.py'), '--output', str(out),
               '--duration', str(protocol['duration_s']), '--record-demo', '--seed', str(trial['seed']),
               '--table', *map(str,trial['table']), '--start', *map(str,trial['start'])]
        with (args.output/(trial['id']+'.log')).open('w') as log:
            result = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        manifest = json.loads((out/'manifest.json').read_text()) if (out/'manifest.json').exists() else {}
        summary['episodes'].append(dict(trial, returncode=result.returncode,
            outcome=manifest.get('outcome'), termination=manifest.get('termination'),
            collision_contact_steps=manifest.get('collision_contact_steps'),
            demo_frames=manifest.get('demo_frames'),
            manifest_sha256=hashlib.sha256((out/'manifest.json').read_bytes()).hexdigest() if manifest else None))
        (args.output/'collection.json').write_text(json.dumps(summary,indent=2)+'\n')
        print(json.dumps(summary['episodes'][-1]),flush=True)
    summary['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
    (args.output/'collection.json').write_text(json.dumps(summary,indent=2)+'\n')


if __name__ == '__main__': main()
