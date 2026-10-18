"""Development ablations of turning drift, not a delivery benchmark."""
import argparse
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path
import mujoco
import numpy as np
import torch
from sim.run_k1_baseline import ScriptedCommandController,K1WalkTaskCfg,DEPLOY
from sim.k1_hand_controller import HandSensorController
from sim.k1_hand_carry import make_model
from sim.k1_observation import sensor_spec


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1)
    protocol=dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),
        conditions=['stock_unloaded','empty_carry_posture','loaded_nominal_arm_obs','loaded_physical_arm_obs'],
        yaw_rates=[0.,-.18,.18],duration_s=8.,move_interval_s=[2.,6.],seed=9851,
        scope='local development ablation; no held-out score or delivery claim',
        limits=['stock differs in arm gains, pose and model initialization; not a single-variable contrast',
                'empty-carry payload bodies displaced 100m and do not touch robot; load feedforward zero',
                'loaded physical-arm observation exposes actual encoders instead of nominal ablation',
                'true root state is evaluation-only; no navigation, VLA or PPO'])
    (args.output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    sources=[Path(__file__),Path('sim/k1_hand_controller.py'),Path('sim/k1_hand_carry.py'),
             Path('sim/run_k1_baseline.py'),DEPLOY/'tasks/locomotion/locomotion.py']
    report=dict(protocol=protocol,source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},trials=[])
    for mode in protocol['conditions']:
        for i,rate in enumerate(protocol['yaw_rates']):
            out=args.output/f'{mode}-{i}';out.mkdir()
            cfg=K1WalkTaskCfg();cfg.mujoco.log_states=None
            cfg.policy.checkpoint_path=str(DEPLOY/'tasks/locomotion/robots/k1/models/k1_walk.pt')
            torch.manual_seed(protocol['seed'])
            if mode=='stock_unloaded':
                ctrl=ScriptedCommandController(cfg)
            else:
                xml=out/'model.xml';make_model(xml,handle_seats=True)
                empty=mode=='empty_carry_posture'
                ctrl=HandSensorController(cfg,sensor_spec(xml),head_pitch=-.2,seed=protocol['seed'],
                    load_mass_kg=0. if empty else 1.98,
                    nominal_arm_observation=mode!='loaded_physical_arm_obs')
                if empty:
                    for name in ('tray_free','pizza_free','drink_free'):
                        q=ctrl.mj_model.joint(name).qposadr[0];ctrl.mj_data.qpos[q]+=100.
                    mujoco.mj_forward(ctrl.mj_model,ctrl.mj_data)
            ctrl.update_state();ctrl.start();d=ctrl.mj_data;initial=d.qpos[:3].copy()
            rows=[];termination='duration_complete'
            for step in range(400):
                command=rate if 100<=step<300 else 0.
                ctrl.vel_command.lin_vel_x=ctrl.vel_command.lin_vel_y=0.
                ctrl.vel_command.ang_vel_yaw=command
                ctrl.update_state();targets=ctrl.policy_step()
                if not ctrl.is_running or not torch.isfinite(targets).all():
                    termination='controller_fallback';break
                ctrl.ctrl_step(targets)
                w,x,y,z=d.qpos[3:7]
                yaw=np.arctan2(2*(w*z+x*y),1-2*(y*y+z*z))
                tilt=np.arccos(np.clip(1-2*(x*x+y*y),-1,1))
                rows.append([float(d.time),*d.qpos[:3],float(yaw),float(np.linalg.norm(d.qvel[:2])),float(tilt),command])
                if d.qpos[2]<.3 or tilt>np.pi/3:
                    termination='height_or_tilt_failure';break
            a=np.asarray(rows)
            trajectory=out/'trajectory.csv'
            np.savetxt(trajectory,a,delimiter=',',header='t,x,y,z,yaw,speed,tilt_rad,command_yaw',comments='')
            moving=a[(a[:,0]>=2.-1e-8)&(a[:,0]<=6.+1e-8)]
            yaw_change=float(np.unwrap(moving[:,4])[-1]-np.unwrap(moving[:,4])[0]) if len(moving)>1 else None
            stopped=a[a[:,0]>=7.-1e-8,5]
            row=dict(mode=mode,yaw_command=rate,termination=termination,simulated_seconds=float(d.time),
                     max_translation_m=float(np.linalg.norm(a[:,1:3]-initial[:2],axis=1).max()),
                     final_speed_m_s=float(a[-1,5]),final_second_max_speed_m_s=float(stopped.max()) if len(stopped) else None,
                     move_yaw_change_rad=yaw_change,expected_yaw_change_rad=4*rate,
                     max_tilt_deg=float(np.degrees(a[:,6].max())),
                     trajectory_sha256=hashlib.sha256(trajectory.read_bytes()).hexdigest())
            if mode.startswith('loaded'):row['hand_metrics']=ctrl.hand_metrics
            report['trials'].append(row)
            (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps(row),flush=True)
    report['finished_at_utc']=datetime.now(timezone.utc).isoformat()
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
