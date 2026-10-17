"""Measure unintended translation during pure-yaw commands; no navigation claim."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import numpy as np
import torch
import mujoco
from sim.k1_hand_carry import make_model
from sim.k1_hand_controller import HandSensorController
from sim.k1_observation import sensor_spec
from sim.run_k1_baseline import K1WalkTaskCfg, DEPLOY


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1)
    protocol=dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),
                  yaw_rates=[0.,-.05,.05,-.15,.15,-.25,.25],
                  duration_s=8.,command_interval_s=[2.,6.],initial_yaw=-.12,
                  initial_xy=[0.,.5],seed=9602,translational_commands=[0.,0.],
                  scope='pure yaw command diagnostic, no delivery or hardware claim')
    (args.output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    source_files=[Path(__file__),Path('sim/k1_hand_controller.py'),Path('sim/k1_hand_carry.py')]
    report=dict(protocol=protocol,source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files},trials=[])
    for i,rate in enumerate(protocol['yaw_rates']):
        run=args.output/f'trial{i:02d}';run.mkdir()
        model=run/'model.xml';make_model(model,handle_seats=True)
        cfg=K1WalkTaskCfg();cfg.mujoco.log_states=None
        cfg.policy.checkpoint_path=str(DEPLOY/'tasks/locomotion/robots/k1/models/k1_walk.pt')
        torch.manual_seed(0)
        ctrl=HandSensorController(cfg,sensor_spec(model),start=(0.,.5,-.12),seed=9602,head_pitch=-.2)
        ctrl.update_state();ctrl.start();d=ctrl.mj_data;rows=[];termination='duration_complete'
        while d.time < 8.-1e-8:
            t=float(d.time)
            ctrl.vel_command.lin_vel_x=ctrl.vel_command.lin_vel_y=0.
            ctrl.vel_command.ang_vel_yaw=rate if 2.<=t<6. else 0.
            ctrl.update_state();target=ctrl.policy_step()
            if not ctrl.is_running or not torch.isfinite(target).all():
                termination='controller_fallback';break
            ctrl.ctrl_step(target)
            w,x,y,z=d.qpos[3:7]
            yaw=float(np.arctan2(2*(w*z+x*y),1-2*(y*y+z*z)))
            rows.append([float(d.time),*d.qpos[:3],yaw,float(np.linalg.norm(d.qvel[:2]))])
            if d.qpos[2]<.3 or ctrl.hand_metrics['payload_drop']:
                termination='fall_or_drop';break
        arr=np.asarray(rows)
        np.savetxt(run/'trajectory.csv',arr,delimiter=',',header='t,x,y,z,yaw,speed',comments='')
        row=dict(yaw_command_rad_s=rate,termination=termination,
                 final_xy=arr[-1,1:3].tolist(),final_yaw_rad=float(arr[-1,4]),
                 max_translation_m=float(np.linalg.norm(arr[:,1:3]-[0.,.5],axis=1).max()),
                 final_speed_m_s=float(arr[-1,5]),hand_metrics=ctrl.hand_metrics,
                 trajectory_sha256=hashlib.sha256((run/'trajectory.csv').read_bytes()).hexdigest())
        report['trials'].append(row)
        (args.output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(row),flush=True)
    report['finished_at_utc']=datetime.now(timezone.utc).isoformat()
    (args.output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
