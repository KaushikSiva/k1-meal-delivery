#!/usr/bin/env python3
"""Real K1 RGB-D/gyro navigation development trial; simulator truth only scores it.

One unnumbered table, flat floor, supplied geometric floor plan and operator
initial-pose prior. No payload, VLA or learned carrying residual in this stage.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import mujoco
import torch
from sim.run_k1_baseline import ScriptedCommandController, K1WalkTaskCfg, DEPLOY
from sim.k1_observation import sensor_spec
from sim.k1_imu import MujocoHeadingAdapter
from sim.k1_sensor_observation import SensorObservationAdapter
from autonomy.contracts import DeliveryTask, Observation, OccupancyGrid, Pose2D, Region
from autonomy.grounding import parse_instruction
from autonomy.session import AutonomySession
from autonomy.executive import ExecutiveConfig
from navigation.follower import FollowerLimits
from navigation.localization import ScanMatchLocalizer
from perception.tabletop import TabletopDetector

MODEL = ROOT / 'sim/vendor/booster_assets/robots/K1/K1_22dof.xml'
BOUNDS = (-1., -3., 7., 4.)
TABLE = (4., 0., .4, .5, .75)


def scene_and_map():
    spec = sensor_spec(MODEL)
    wb = spec.worldbody
    wb.add_light(pos=[2, 0, 4], dir=[0, 0, -1], diffuse=[.7, .7, .7])
    x0, y0, x1, y1 = BOUNDS
    objects = [(TABLE[0], TABLE[1], TABLE[2], TABLE[3], TABLE[4])]
    # Physical walls match the supplied floor plan; no fictitious boundary hits.
    objects += [((x0+x1)/2, y0, (x1-x0)/2, .05, 2.),
                ((x0+x1)/2, y1, (x1-x0)/2, .05, 2.),
                (x0, (y0+y1)/2, .05, (y1-y0)/2, 2.),
                (x1, (y0+y1)/2, .05, (y1-y0)/2, 2.)]
    res = .1
    cells = np.zeros((int((y1-y0)/res)+1, int((x1-x0)/res)+1), np.uint8)
    grid = OccupancyGrid(cells, res, (x0,y0))
    for i, (x,y,hx,hy,height) in enumerate(objects):
        wb.add_geom(name=f'room_object_{i}', type=mujoco.mjtGeom.mjGEOM_BOX,
                    pos=[x,y,height/2], size=[hx,hy,height/2], rgba=[.55,.4,.25,1])
        r0,c0 = grid.world_to_cell((x-hx,y-hy)); r1,c1 = grid.world_to_cell((x+hx,y+hy))
        cells[max(0,r0):r1+1,max(0,c0):c1+1] = OccupancyGrid.OCCUPIED
    return spec, grid


class SensorController(ScriptedCommandController):
    def __init__(self, cfg, spec):
        super().__init__(cfg)
        initial = self.mj_data.qpos.copy()
        self.mj_model = spec.compile(); self.mj_model.opt.timestep = cfg.mujoco.physics_dt
        self.mj_data = mujoco.MjData(self.mj_model)
        self.mj_data.qpos[:] = initial
        mujoco.mj_forward(self.mj_model, self.mj_data)
        self._ghost_mj_data = mujoco.MjData(self.mj_model)
        self.imu = MujocoHeadingAdapter(self.mj_model, cfg.robot.joint_names,
                                       noise_std_rad_s=.005, bias_rad_s=(0,0,.0015), seed=8201)
        self.imu.sample(self.mj_data)

    def ctrl_step(self, targets):
        targets = targets.cpu().numpy()
        kp = self.robot.joint_stiffness.numpy(); kd = self.robot.joint_damping.numpy()
        limit = self.robot.effort_limit.numpy(); data = self.mj_data
        for _ in range(self.decimation):
            data.ctrl[:] = np.clip(kp*(targets-data.qpos[7:])-kd*data.qvel[6:], -limit, limit)
            mujoco.mj_step(self.mj_model, data)
            mujoco.mj_forward(self.mj_model, data)
            self.imu.sample(data)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--duration', type=float, default=40.)
    args = ap.parse_args(); out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    report = dict(status='started', started_at_utc=datetime.now(timezone.utc).isoformat(),
        evidence_kind='mujoco_sensor_estimated_navigation_development', payload_present=False,
        markers_present=False, training_performed=False, hardware_verified=False,
        navigation_privileged_inputs=[], evaluation_only=['world pose', 'root speed', 'body tilt'],
        prior='operator floor plan with geometry only; initial pose(0,0,0), sigma(.1,.1,.05)',
        assumptions=['level initial attitude', 'flat floor', 'stance foot for height', 'ideal encoders',
                     'gyro noise .005rad/s and z bias .0015rad/s', 'camera FOV58deg'],
        protocol=dict(duration_s=args.duration, camera_hz=5, policy_hz=50, physics_hz=500,
                      payload='none', destination='single unnumbered table', seed=8201),
        limits=['development trial, not held-out', 'linear prediction uses commanded velocity',
                'scan matching must constrain drift', 'no payload or VLA', 'not hardware tested'])
    files = ['sim/run_k1_sensor_navigation.py','sim/k1_sensor_observation.py','sim/k1_imu.py',
             'sim/k1_observation.py','contracts/robot_telemetry.py','deployment/k1_leg_estimator.py',
             'perception/k1_camera.py','perception/tabletop.py','navigation/localization.py',
             'autonomy/session.py','autonomy/executive.py','navigation/follower.py',
             'navigation/planner.py','navigation/search.py','memory/scene_memory.py']
    report['source_hashes'] = {f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}
    (out/'manifest.json').write_text(json.dumps(report,indent=2))
    torch.set_num_threads(1); torch.manual_seed(0)
    cfg = K1WalkTaskCfg(); cfg.mujoco.log_states = None
    cfg.policy.checkpoint_path = str(DEPLOY/'tasks/locomotion/robots/k1/models/k1_walk.pt')
    report['checkpoint_sha256'] = hashlib.sha256(Path(cfg.policy.checkpoint_path).read_bytes()).hexdigest()
    spec, grid = scene_and_map(); ctrl = SensorController(cfg,spec)
    model,data = ctrl.mj_model,ctrl.mj_data
    adapter = SensorObservationAdapter(model, MODEL)
    evaluator = mujoco.Renderer(model,height=480,width=640)
    localizer = ScanMatchLocalizer(grid, Pose2D(0.,0.,0.), max_points=200)
    task = DeliveryTask('deliver the pizza and drink to the table',
                        parse_instruction('deliver the pizza and drink to the table'), 0., args.duration)
    session = AutonomySession(task,grid,TabletopDetector(),[Region('dining',(3.3,0.),2.,('dining',))],
        config=ExecutiveConfig(final_speed=.35, approach_speed=.35, search_speed=.35),
        limits=FollowerLimits(min_walk_cmd=.35,final_accel=.25),deployable=True)
    import imageio.v2 as iio
    videos={name:iio.get_writer(str(out/(name+'.mp4')),fps=5,codec='libx264')
            for name in ['evaluator','robot_camera']}
    rows=[]; frame_times=[]; observations=[]; next_cam=0.; started=time.monotonic()
    previous_heading=ctrl.imu.latest_heading; command=np.zeros(3); last_pose=None
    ctrl.update_state(); ctrl.start(); termination='duration_complete'
    try:
        while data.time < args.duration-1e-8:
            t=float(data.time); heading=ctrl.imu.latest_heading
            if t > 0:
                # Temporary integration glue: relative gyro increments, never map yaw truth.
                localizer.predict([command[0],command[1],0.],cfg.policy_dt)
                localizer.pose[2] += heading.yaw_rad-previous_heading.yaw_rad
                localizer.cov[2,2] += max(0.,heading.yaw_variance_rad2-previous_heading.yaw_variance_rad2)
            previous_heading=heading
            obs=None
            if t >= next_cam-1e-8:
                frame,height = adapter.capture(data,ctrl.imu.latest_telemetry,heading)
                localizer.correct(Observation(t,frame,localizer.estimate(t)))
                pose=localizer.estimate(t)
                # Finite differences of sensor-estimated map pose, not leg/GT velocity.
                twist=np.zeros(3)
                if last_pose is not None:
                    old,old_t=last_pose; dt=t-old_t
                    delta=(np.array([pose.pose.x,pose.pose.y])-np.array([old.x,old.y]))/dt
                    c,s=np.cos(pose.pose.yaw),np.sin(pose.pose.yaw)
                    twist[:2]=np.array([[c,s],[-s,c]])@delta
                    twist[2]=np.arctan2(np.sin(pose.pose.yaw-old.yaw),np.cos(pose.pose.yaw-old.yaw))/dt
                last_pose=(pose.pose,t)
                obs=adapter.assemble(frame,pose,twist)
                obs.assert_deployable()
                np.savez_compressed(out/f'rgbd-{len(frame_times):04d}.npz',rgb=frame.rgb,
                    depth=frame.depth,T_base_camera=frame.T_base_camera,
                    pose=[pose.pose.x,pose.pose.y,pose.pose.yaw],cov=pose.cov,timestamp=t)
                next_cam+=.2; frame_times.append(t)
                videos['robot_camera'].append_data(frame.rgb)
                camera=mujoco.MjvCamera(); camera.lookat[:]=[2.,0.,.4]
                camera.distance=6.; camera.azimuth=-70.; camera.elevation=-30.
                evaluator.update_scene(data,camera=camera); eval_rgb=evaluator.render().copy()
                videos['evaluator'].append_data(eval_rgb)
                if len(frame_times)%50==1:
                    iio.imwrite(out/f'robot_camera-{len(frame_times):04d}.png',frame.rgb)
                    iio.imwrite(out/f'evaluator-{len(frame_times):04d}.png',eval_rgb)
                observations.append(dict(t=t,pose=[pose.pose.x,pose.pose.y,pose.pose.yaw],
                    sigma=np.sqrt(np.diag(pose.cov)).tolist(),status=pose.status.value,
                    match=localizer.last_match,estimated_twist=twist.tolist(),estimated_height=height))
            command=np.array(session.tick(obs,t,cfg.policy_dt)) if t>=2. else np.zeros(3)
            if obs is not None:
                observations[-1]['tracks']=session.executive.memory.summary()
            ctrl.vel_command.lin_vel_x,ctrl.vel_command.lin_vel_y,ctrl.vel_command.ang_vel_yaw=command
            ctrl.update_state(); target=ctrl.policy_step()
            if not ctrl.is_running:termination='upstream_fall_fallback';break
            # Evaluation-only truth never enters observation, localizer or executive.
            w,x,y,z=data.qpos[3:7]; yaw=np.arctan2(2*(w*z+x*y),1-2*(y*y+z*z))
            tilt=float(np.degrees(np.arccos(np.clip(1-2*(x*x+y*y),-1,1))))
            rows.append([t,*data.qpos[:3],yaw,tilt,*localizer.pose,*command,
                         float(np.linalg.norm(data.qvel[:2]))])
            if data.qpos[2]<.3 or tilt>60:termination='fall';break
            if session.done and t>2:termination='autonomy_terminal';break
            ctrl.ctrl_step(target)
        iio.imwrite(out/'evaluator_final_recorded.png',eval_rgb)
        iio.imwrite(out/'robot_camera_final_recorded.png',frame.rgb)
        report.update(status='tested',termination=termination,
                      outcome=session.outcome.value if session.outcome else None,
                      events=[f'{e.t:.2f} {e.state}: {e.msg}' for e in session.events])
    except Exception as exc:
        import traceback
        report.update(status='failed',error=str(exc),traceback=traceback.format_exc())
        raise
    finally:
        ctrl.stop()
        for video in videos.values():video.close()
        adapter.close();evaluator.close()
        a=np.asarray(rows)
        if len(a):
            np.savetxt(out/'trajectory.csv',a,delimiter=',',comments='',
                header='t,true_x,true_y,true_z,true_yaw,tilt_deg,estimated_x,estimated_y,estimated_yaw,cmd_vx,cmd_vy,cmd_wz,true_speed')
            report.update(max_xy_error_m=float(np.linalg.norm(a[:,1:3]-a[:,6:8],axis=1).max()),
                          final_xy_error_m=float(np.linalg.norm(a[-1,1:3]-a[-1,6:8])),
                          max_yaw_error_rad=float(np.max(np.abs(np.angle(np.exp(1j*(a[:,4]-a[:,8])))))),
                          max_tilt_deg=float(a[:,5].max()),final_true_speed_m_s=float(a[-1,-1]),
                          final_true_xy=a[-1,1:3].tolist())
        np.savetxt(out/'frame_times.csv',frame_times,delimiter=',',header='sim_time_s',comments='')
        (out/'localization.json').write_text(json.dumps(observations,indent=2))
        report.update(simulated_seconds=float(data.time),wall_seconds=time.monotonic()-started,
                      video_fps=5,video_frames=len(frame_times),
                      finished_at_utc=datetime.now(timezone.utc).isoformat())
        report['artifacts']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()
                             if p.is_file() and p.name!='manifest.json'}
        (out/'manifest.json').write_text(json.dumps(report,indent=2))
        print(json.dumps({k:v for k,v in report.items() if k not in ['source_hashes','artifacts']},indent=2))


if __name__=='__main__':main()
