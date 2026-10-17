#!/usr/bin/env python3
"""Actual unloaded K1 turning diagnostic; gyro relative heading vs evaluator truth."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import mujoco
import torch
from sim.run_k1_baseline import ScriptedCommandController,K1WalkTaskCfg,DEPLOY
from sim.k1_imu import MujocoTelemetryReader,GyroHeadingEstimator

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--physics-rate',action='store_true')
parser.add_argument('--forward',action='store_true',help='Forward walking instead of turning')
parser.add_argument('--leg-estimate',action='store_true')
args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
report={'status':'started','started_at_utc':datetime.now(timezone.utc).isoformat(),
    'evidence_kind':'actual_mujoco_gyro_heading_turn_diagnostic','hardware_verified':False,
    'sensor_sample_rate_hz':500 if args.physics_rate else 50,
    'gyro_noise_std_rad_s':.005,'gyro_bias_rad_s':[0.,0.,.0015],'seed':8101,
    'initial_world_yaw_rad':.7,'initial_world_yaw_usage':'simulation setup/evaluation only; estimator starts identity',
    'estimator_inputs':['native gyro sensor','timestamps','declared noise variance'],
    'evaluation_only':['absolute free-base orientation'],
    'protocol':{'duration_s':20.,'stand_s':2.,'stop_s':2.,'command_magnitude':.35,'command_axis':'vx' if args.forward else 'wz','max_heading_error_rad':.08},
    'source_hashes':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in
        ['sim/check_k1_imu.py','sim/k1_imu.py','contracts/robot_telemetry.py','sim/run_k1_baseline.py']}}
rows=[];coarse_errors=[];leg_rows=[];odom=np.zeros(2)
try:
    torch.set_num_threads(1);torch.manual_seed(0)
    cfg=K1WalkTaskCfg();cfg.policy.checkpoint_path=str(DEPLOY/'tasks/locomotion/robots/k1/models/k1_walk.pt')
    cfg.mujoco.log_states=None
    report['forward_trial']=args.forward
    report['leg_evaluation_thresholds']={'max_xy_error_m':.3,'height_rmse_m':.03}
    report['checkpoint_sha256']=hashlib.sha256(Path(cfg.policy.checkpoint_path).read_bytes()).hexdigest()
    report['versions']={'mujoco':mujoco.__version__,'torch':torch.__version__}
    controller=ScriptedCommandController(cfg);model,data=controller.mj_model,controller.mj_data
    data.qpos[3:7]=[np.cos(.35),0,0,np.sin(.35)];mujoco.mj_forward(model,data)
    initial_world_position=data.qpos[:3].copy()
    if args.leg_estimate:
        from deployment.k1_leg_estimator import K1LegEstimator
        leg=K1LegEstimator(ROOT/'sim/vendor/booster_assets/robots/K1/K1_22dof.xml')
        report['source_hashes']['deployment/k1_leg_estimator.py']=hashlib.sha256((ROOT/'deployment/k1_leg_estimator.py').read_bytes()).hexdigest()
    reader=MujocoTelemetryReader(model,cfg.robot.joint_names,noise_std_rad_s=.005,bias_rad_s=(0,0,.0015),seed=8101)
    estimator=GyroHeadingEstimator(bias_bound_rad_s=.002)
    first=reader.read(data);estimator.update(first)
    coarse=GyroHeadingEstimator(bias_bound_rad_s=.002);coarse.update(first)
    controller.update_state();controller.start()
    truth_previous=.7;truth_yaw=0.;report['termination']='duration_complete'
    for step in range(1000):
        t=float(data.time);command=.35 if 2<=t<18 else 0.
        controller.vel_command.ang_vel_yaw=0. if args.forward else command
        controller.vel_command.lin_vel_x=command if args.forward else 0.
        controller.update_state()
        target=controller.policy_step()
        if not controller.is_running:report['termination']='actor_fall_fallback';break
        if args.physics_rate:
            targets=target.cpu().numpy()
            for substep in range(controller.decimation):
                data.ctrl[:]=np.clip(controller.robot.joint_stiffness.numpy()*(targets-data.qpos[7:])-controller.robot.joint_damping.numpy()*data.qvel[6:],
                    -controller.robot.effort_limit.numpy(),controller.robot.effort_limit.numpy())
                mujoco.mj_step(model,data);mujoco.mj_forward(model,data)
                telemetry=reader.read(data);estimate=estimator.update(telemetry)
                if args.leg_estimate:
                    motion=leg.estimate(telemetry,estimate)
                    c,s=np.cos(estimate.yaw_rad),np.sin(estimate.yaw_rad)
                    odom+=np.array([[c,-s],[s,c]])@motion.velocity_base_m_s[:2]*float(model.opt.timestep)
        else:
            controller.ctrl_step(target);mujoco.mj_forward(model,data)
            telemetry=reader.read(data);estimate=estimator.update(telemetry)
        coarse_estimate=coarse.update(telemetry)
        w,x,y,z=data.qpos[3:7]  # evaluator only; never given to estimator
        wrapped=float(np.arctan2(2*(w*z+x*y),1-2*(y*y+z*z)))
        truth_yaw+=float(np.arctan2(np.sin(wrapped-truth_previous),np.cos(wrapped-truth_previous)))
        truth_previous=wrapped
        coarse_errors.append(coarse_estimate.yaw_rad-truth_yaw)
        rows.append([float(data.time),estimate.yaw_rad,truth_yaw,estimate.yaw_rad-truth_yaw,
                     estimate.yaw_variance_rad2,command,*telemetry.angular_velocity_body_rad_s])
        if args.leg_estimate:
            motion=leg.estimate(telemetry,estimate)
            R=np.array([[np.cos(wrapped),np.sin(wrapped)],[-np.sin(wrapped),np.cos(wrapped)]])
            truth_velocity=R@data.qvel[:2]  # evaluation only
            c,s=np.cos(estimate.yaw_rad),np.sin(estimate.yaw_rad)
            if not args.physics_rate:odom+=np.array([[c,-s],[s,c]])@motion.velocity_base_m_s[:2]*.02
            c0,s0=np.cos(.7),np.sin(.7)
            truth_displacement=np.array([[c0,s0],[-s0,c0]])@(data.qpos[:2]-initial_world_position[:2])
            leg_rows.append([float(data.time),*motion.velocity_base_m_s[:2],*truth_velocity,
                             motion.trunk_height_m,float(data.qpos[2]),*odom,*truth_displacement])
    if leg_rows:
        l=np.array(leg_rows)
        np.savetxt(args.output/'leg_trajectory.csv',l,delimiter=',',comments='',
                   header='t,estimated_vx,estimated_vy,evaluator_vx,evaluator_vy,estimated_height,evaluator_height,odom_x,odom_y,evaluator_x,evaluator_y')
        report.update(leg_velocity_rmse_m_s=np.sqrt(((l[:,1:3]-l[:,3:5])**2).mean(0)).tolist(),
                      leg_height_rmse_m=float(np.sqrt(((l[:,5]-l[:,6])**2).mean())),
                      leg_final_xy_error_m=float(np.linalg.norm(l[-1,7:9]-l[-1,9:11])),
                      leg_max_xy_error_m=float(np.linalg.norm(l[:,7:9]-l[:,9:11],axis=1).max()))
        report['leg_passed']=report['leg_max_xy_error_m']<.3 and report['leg_height_rmse_m']<.03
    a=np.array(rows)
    np.savetxt(args.output/'imu_trajectory.csv',a,delimiter=',',comments='',
               header='t,estimated_relative_yaw,evaluator_relative_yaw,error,yaw_variance,command_magnitude,gyro_x,gyro_y,gyro_z')
    report.update(status='tested',samples=len(a),simulated_seconds=float(data.time),
        final_relative_yaw_rad=float(a[-1,2]),final_error_rad=float(a[-1,3]),
        max_abs_error_rad=float(abs(a[:,3]).max()),
        same_trajectory_50hz_max_abs_error_rad=float(np.max(np.abs(coarse_errors))),
        passed=report['termination']=='duration_complete' and float(abs(a[:,3]).max())<.08,
        limits=['single unloaded locomotion trial','ideal joint encoders','assumed explicit gyro noise/bias',
                'level initial reference assumption','leg odometry uses provisional stance assumptions; no complete localization'])
except Exception as exc:
    import traceback
    report.update(status='failed',error=str(exc),traceback=traceback.format_exc());raise
finally:
    report['finished_at_utc']=datetime.now(timezone.utc).isoformat()
    report['artifacts']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.output.iterdir() if p.is_file()}
    (args.output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
