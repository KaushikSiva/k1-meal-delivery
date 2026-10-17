#!/usr/bin/env python3
"""Run all frozen executive/VLA pairs and independently score physical stops."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def score(manifest,trajectory,trial,gate):
    a=np.loadtxt(trajectory,delimiter=',',skiprows=1)
    if a.ndim!=2 or a.shape[1]!=13 or not np.isfinite(a).all():raise ValueError('Invalid trajectory')
    tail=a[a[:,0]>=a[-1,0]-1.5]
    tx,ty,hx,hy,height=trial['table']
    front_distance=float(tx-hx-a[-1,1]);lateral=float(abs(a[-1,2]-ty))
    max_speed=float(tail[:,-1].max())
    checks={'executive_delivered':manifest.get('outcome')=='delivered',
        'no_room_contact':manifest.get('collision_contact_steps')==0,
        'no_fall':manifest.get('termination') not in ['fall','upstream_fall_fallback'],
        'front_distance':gate['front_edge_distance_m'][0]<=front_distance<=gate['front_edge_distance_m'][1],
        'lateral_error':lateral<=gate['lateral_error_max_m'],
        'stable_stop':a[-1,0]>=1.5 and max_speed<=gate['last_1p5s_max_true_speed_m_s'],
        'body_tilt':manifest['max_tilt_deg']<=gate['max_body_tilt_deg']}
    return {'physical_delivery_pass':all(checks.values()),'checks':checks,
        'front_edge_distance_m':front_distance,'lateral_error_m':lateral,
        'last_1p5s_max_true_speed_m_s':max_speed,'last_1p5s_net_drift_m':float(np.linalg.norm(tail[-1,1:3]-tail[0,1:3]))}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--checkpoint',type=Path,required=True)
    ap.add_argument('--protocol',type=Path,default=ROOT/'evaluation/VLA_CLOSED_LOOP_PROTOCOL.json')
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    protocol=json.loads(args.protocol.read_text())
    report={'started_at_utc':datetime.now(timezone.utc).isoformat(),'protocol':protocol,
        'protocol_sha256':hashlib.sha256(args.protocol.read_bytes()).hexdigest(),
        'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'training_performed':False,'payload_present':False,'hardware_verified':False,'trials':[]}
    manifest=json.loads((args.checkpoint/'manifest.json').read_text())
    if manifest['checkpoint_files']['policy/model.safetensors']!=protocol['checkpoint_sha256']:
        raise ValueError('Wrong frozen checkpoint')
    for trial in protocol['episodes']:
        for mode in protocol['modes']:
            name=trial['id']+'-'+mode;out=args.output/name
            cmd=[sys.executable,str(ROOT/'sim/run_k1_sensor_navigation.py'),'--output',str(out),
                '--duration',str(protocol['duration_s']),'--seed',str(trial['seed']),
                '--table',*map(str,trial['table']),'--start',*map(str,trial['start']),
                '--policy-seed',str(protocol['policy_seed'])]
            if mode=='smolvla':cmd+=['--vla-checkpoint',str(args.checkpoint)]
            with (args.output/(name+'.log')).open('w') as log:
                result=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            m=json.loads((out/'manifest.json').read_text()) if (out/'manifest.json').exists() else {}
            row={'id':name,'config':trial['id'],'mode':mode,'returncode':result.returncode,
                'outcome':m.get('outcome'),'termination':m.get('termination'),
                'collision_contact_steps':m.get('collision_contact_steps'),
                'max_xy_error_m':m.get('max_xy_error_m'),'vla_summary':m.get('vla_summary')}
            if result.returncode==0 and m.get('status')=='tested':row.update(score(m,out/'trajectory.csv',trial,protocol['acceptance']))
            else:row.update(physical_delivery_pass=False,infrastructure_failure=True,error=m.get('error'))
            if m:row['manifest_sha256']=hashlib.sha256((out/'manifest.json').read_bytes()).hexdigest()
            report['trials'].append(row)
            (args.output/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps(row),flush=True)
    report['finished_at_utc']=datetime.now(timezone.utc).isoformat()
    (args.output/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
