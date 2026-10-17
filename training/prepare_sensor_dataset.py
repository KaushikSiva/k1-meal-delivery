#!/usr/bin/env python3
"""Package successful sensor-only teacher episodes, keeping failures in the audit.

This is a pilot imitation dataset, not a robot success benchmark. Splits are
frozen by episode before collection. No ground-truth values enter model inputs.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def episode_arrays(rows, directory):
    if not rows or any(r['privileged_features'] for r in rows):
        raise ValueError('empty or privileged demonstration')
    state = np.asarray([r['observation.state'] for r in rows],np.float32)
    action = np.asarray([r['action'] for r in rows],np.float32)
    if state.shape != (len(rows),16) or action.shape != (len(rows),5):
        raise ValueError('unexpected feature shape')
    if not np.isfinite(state).all() or not np.isfinite(action).all() or np.abs(action).max()>1.000001:
        raise ValueError('invalid feature values')
    times = np.asarray([r['timestamp'] for r in rows])
    if np.any(np.diff(times)<=0) or np.any(np.abs(np.diff(times)-.2)>1e-6):
        raise ValueError('non-contiguous 5Hz episode')
    images=[]
    for row in rows:
        path=(directory/row['image_ref']).resolve()
        if path.parent != directory.resolve(): raise ValueError('invalid image reference')
        with np.load(path,allow_pickle=False) as f: images.append(f['rgb'])
    rgb=np.stack(images)
    if rgb.dtype!=np.uint8 or rgb.shape[1:]!=(480,640,3):raise ValueError('invalid image shape')
    tasks=np.asarray([f"{r['task']} | state: {r['executive_state']} | memory: {r['memory_text']}" for r in rows])
    return dict(state=state,action=action,rgb=rgb,task=tasks,timestamp=times)


def normalization(train_states):
    if not train_states: raise ValueError('no qualified training episodes')
    a=np.concatenate(train_states)
    return {'mean':a.mean(axis=0).tolist(),'std':np.maximum(a.std(axis=0),.05).tolist(),
            'source':'training episodes only','minimum_std':.05}


def chunk(actions,index,size=10):
    indices=np.arange(index,index+size)
    return actions[np.minimum(indices,len(actions)-1)].copy(),indices>=len(actions)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--collection',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    collection=json.loads((args.collection/'collection.json').read_text())
    if 'finished_at_utc' not in collection:raise ValueError('collection still running')
    report={'created_at_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'tiny unloaded simulator imitation pilot; no task performance claim',
        'collection_sha256':sha(args.collection/'collection.json'),
        'protocol':collection['protocol'],'episodes':[],
        'quality_filter':'delivered, no room contact, no privileged features; all rejected trials retained',
        'source_sha256':sha(__file__)}
    states=[];sources=None
    for episode in collection['episodes']:
        directory=args.collection/episode['id'];manifest=json.loads((directory/'manifest.json').read_text())
        if sha(directory/'manifest.json') != episode['manifest_sha256']:raise ValueError('manifest changed')
        reason=None
        if episode['returncode']!=0 or manifest.get('outcome')!='delivered':reason='not delivered'
        elif manifest.get('collision_contact_steps')!=0:reason='room contact or missing contact accounting'
        elif manifest.get('navigation_privileged_inputs')!=[]:reason='privileged navigation inputs'
        audit={'id':episode['id'],'split':episode['split'],'outcome':manifest.get('outcome'),
               'manifest_sha256':episode['manifest_sha256'],'included':reason is None,'exclusion':reason,
               'final_xy_error_m':manifest.get('final_xy_error_m'),
               'final_true_speed_m_s':manifest.get('final_true_speed_m_s')}
        if reason is None:
            if sources is None:sources=manifest['source_hashes']
            elif sources!=manifest['source_hashes']:raise ValueError('executed sources changed during collection')
            demo=directory/'demonstrations'
            for name,h in manifest['demo_files'].items():
                if sha(demo/name)!=h:raise ValueError('demo hash mismatch')
            rows=[json.loads(line) for line in (demo/(episode['id']+'.jsonl')).read_text().splitlines()]
            for row in rows:
                if sha(directory/row['image_ref'])!=manifest['artifacts'][row['image_ref']]:raise ValueError('image hash mismatch')
            arrays=episode_arrays(rows,directory)
            dest=args.output/(episode['id']+'.npz');np.savez_compressed(dest,**arrays)
            audit.update(file=dest.name,sha256=sha(dest),frames=len(rows))
            if episode['split']=='train':states.append(arrays['state'])
        report['episodes'].append(audit)
    report['source_hashes']=sources
    report['normalization']=normalization(states)
    (args.output/'dataset.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['protocol','source_hashes','normalization']},indent=2))


if __name__=='__main__':main()
