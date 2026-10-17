#!/usr/bin/env python3
"""Summarize evaluator-only trajectory measurements without inventing success gates."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('experiment',type=Path)
    args=ap.parse_args();p=args.experiment/'trajectory.csv'
    a=np.loadtxt(p,delimiter=',',skiprows=1)
    if a.ndim!=2 or a.shape[1]!=13 or not np.isfinite(a).all():raise ValueError('Invalid sensor-nav trajectory')
    tail=a[a[:,0]>=a[-1,0]-1.5]
    # Geometry declared by this runner; not a hidden destination hint to the actor.
    nearest=np.clip(a[-1,1:3],[3.6,-.5],[4.4,.5])
    report={'scope':'post-run evaluator summaries; no additional success criterion',
        'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'trajectory_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
        'samples':len(a),'last_sample_time_s':float(a[-1,0]),
        'final_distance_to_table_edge_m':float(np.linalg.norm(a[-1,1:3]-nearest)),
        'last_1p5s_max_true_xy_speed_m_s':float(tail[:,-1].max()),
        'last_1p5s_net_xy_drift_m':float(np.linalg.norm(tail[-1,1:3]-tail[0,1:3])),
        'collision_count':None,'collision_count_reason':'not instrumented in these historical trials',
        'payload_present':False,'hardware_verified':False}
    (args.experiment/'evaluation_summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
