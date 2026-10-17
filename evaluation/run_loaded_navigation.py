"""Run every frozen loaded-navigation condition without changing the controller."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from evaluation.score_loaded_navigation import score_loaded


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--protocol', type=Path, required=True)
    ap.add_argument('--vla-endpoint')
    ap.add_argument('--vla-lossless-png',action='store_true')
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    protocol = json.loads(args.protocol.read_text())
    (args.output / 'protocol.json').write_bytes(args.protocol.read_bytes())
    report = dict(started_at_utc=datetime.now(timezone.utc).isoformat(),
                  protocol_sha256=hashlib.sha256(args.protocol.read_bytes()).hexdigest(),
                  source_root=str(args.source.resolve()), trials=[])
    for trial in protocol['episodes']:
        out = (args.output / trial['id']).resolve()
        command = [sys.executable, str(args.source.resolve() / 'sim/run_k1_sensor_navigation.py'),
                   '--output', str(out), '--duration', str(protocol['duration_s']),
                   '--seed', str(trial['seed']), '--table', *map(str, trial['table']),
                   '--start', *map(str, trial['start']), '--hand-carried',
                   '--known-load-depth-mask', '--carry-command-guard',
                   '--walk-speed', str(protocol['walk_speed']),
                   '--head-pitch', str(protocol['profile']['head_pitch']),
                   '--prediction-scale', str(protocol['profile']['prediction_scale']),
                   '--settle-seconds', str(protocol['settle_seconds']), '--tracking-evaluator']
        if args.vla_endpoint:
            command+=['--vla-endpoint',args.vla_endpoint]
            if args.vla_lossless_png:command+=['--vla-lossless-png']
        with (args.output / (trial['id'] + '.log')).open('w') as log:
            result = subprocess.run(command, cwd=args.source, stdout=log, stderr=subprocess.STDOUT)
        row = dict(id=trial['id'], command=command, returncode=result.returncode,
                   physical_delivery_pass=False)
        manifest = out / 'manifest.json'
        m = json.loads(manifest.read_text()) if manifest.exists() else {}
        if result.returncode == 0 and m.get('status') == 'tested':
            row.update(score_loaded(out, protocol))
        else:
            row.update(infrastructure_failure=True, error=m.get('error'))
        row.update(outcome=m.get('outcome'), termination=m.get('termination'),
                   max_xy_error_m=m.get('max_xy_error_m'), hand_metrics=m.get('hand_metrics'),
                   collision_contact_steps=m.get('collision_contact_steps'),
                   vla_summary=m.get('vla_summary'),vla_server=m.get('vla_server'))
        if manifest.exists():
            row['manifest_sha256'] = hashlib.sha256(manifest.read_bytes()).hexdigest()
        report['trials'].append(row)
        (args.output / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(row), flush=True)
    report['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
    report['passes'] = sum(row['physical_delivery_pass'] for row in report['trials'])
    report['attempts'] = len(report['trials'])
    (args.output / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
