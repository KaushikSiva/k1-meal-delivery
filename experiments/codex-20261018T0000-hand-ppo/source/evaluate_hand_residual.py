"""Matched physical evaluation of baseline and trained hand-carry leg residual."""
import argparse
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path
import numpy as np
import torch
from training.hand_carry_env import HandCarryEnv
from deployment.hand_residual import HandResidualPolicy


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--checkpoint',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--protocol',type=Path,default=Path('evaluation/HAND_PPO_PROTOCOL.json'))
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1)
    protocol=json.loads(args.protocol.read_text())
    policy=HandResidualPolicy(args.checkpoint)
    report=dict(started_at_utc=datetime.now(timezone.utc).isoformat(),protocol=protocol,
                checkpoint_sha256=policy.sha256,
                protocol_sha256=hashlib.sha256(args.protocol.read_bytes()).hexdigest(),trials=[])
    for i,command in enumerate(protocol['commands']):
        for mode in protocol['modes']:
            run=args.output/f'condition{i:02d}-{mode}'
            env=HandCarryEnv(run,9811)
            obs=env.reset(command=command,yaw=protocol['initial_yaw'])
            assert [env.cfg.robot.joint_names[j] for j in env.legs]==policy.report['leg_joint_names']
            rows=[];rewards=[];terminated=False
            while True:
                action=policy.action(obs) if mode=='trained_residual' else np.zeros(12,np.float32)
                obs,reward,terminated,done,info=env.step(action)
                d=env.ctrl.mj_data;w,x,y,z=d.qpos[3:7]
                yaw=float(np.arctan2(2*(w*z+x*y),1-2*(y*y+z*z)))
                rows.append([float(d.time),*d.qpos[:3],yaw,info['speed_m_s'],*action])
                rewards.append(reward)
                if done:break
            a=np.asarray(rows);h=env.ctrl.hand_metrics;gate=protocol['criteria']
            checks=dict(no_fall_or_drop=not terminated and not h['payload_drop'],
                        hand_only_support=not h['other_robot_contact_steps'],
                        tray_tilt=h['max_tray_tilt_deg']<=gate['max_tray_tilt_deg'],
                        payload_shift=h['max_payload_shift_m']<=gate['max_payload_shift_m'],
                        stopped=float(a[-1,5])<=gate['final_speed_m_s'])
            displacement=float(np.linalg.norm(a[:,1:3],axis=1).max())
            if command[:2]==[0,0]:checks['turn_translation']=displacement<=gate['turn_only_max_translation_m']
            move_start=int(np.argmin(np.abs(a[:,0]-2.)))
            move_end=int(np.argmin(np.abs(a[:,0]-6.)))
            yaw_change=float(np.unwrap(a[:,4])[move_end]-np.unwrap(a[:,4])[move_start])
            expected_yaw=4*command[2]
            checks['yaw_tracking']=abs(yaw_change-expected_yaw)<=gate['yaw_error_rad']
            forward=float((a[move_end,1:3]-a[move_start,1:3])@np.array([np.cos(a[move_start,4]),np.sin(a[move_start,4])]))
            if command[0]>0:checks['forward_progress']=forward>=gate['min_forward_progress_m']
            stop_window=a[a[:,0]>=7.-1e-8,5]
            checks['stable_stop']=len(stop_window)>=49 and float(stop_window.max())<=gate['final_speed_m_s']
            trajectory=run/'trajectory.csv'
            np.savetxt(trajectory,a,delimiter=',',header='t,x,y,z,yaw,speed,'+','.join(policy.report['leg_joint_names']),comments='')
            row=dict(condition=i,mode=mode,command=command,diagnostic_pass=all(checks.values()),
                     checks=checks,reward_mean=float(np.mean(rewards)),
                     max_translation_m=displacement,final_xy=a[-1,1:3].tolist(),
                     final_yaw_rad=float(a[-1,4]),final_speed_m_s=float(a[-1,5]),
                     move_yaw_change_rad=yaw_change,expected_yaw_change_rad=expected_yaw,
                     move_forward_progress_m=forward,
                     final_second_max_speed_m_s=float(stop_window.max()) if len(stop_window) else None,
                     simulated_seconds=float(a[-1,0]),hand_metrics=h,
                     trajectory_sha256=hashlib.sha256(trajectory.read_bytes()).hexdigest())
            report['trials'].append(row)
            (args.output/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps(row),flush=True)
    report['finished_at_utc']=datetime.now(timezone.utc).isoformat()
    (args.output/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
