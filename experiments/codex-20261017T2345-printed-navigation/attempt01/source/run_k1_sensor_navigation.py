#!/usr/bin/env python3
"""Real K1 RGB-D/gyro navigation development trial; simulator truth only scores it.

One unnumbered table, flat floor, supplied geometric floor plan and operator
initial-pose prior. Optional free hand-supported load and bounded VLA proposals;
no learned carrying residual.
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


def scene_and_map(table=TABLE, model_source=MODEL, cafe_style=False):
    spec = sensor_spec(model_source)
    wb = spec.worldbody
    wb.add_light(pos=[2, 0, 4], dir=[0, 0, -1], diffuse=[.7, .7, .7])
    x0, y0, x1, y1 = BOUNDS
    objects = [tuple(table)]
    # Physical walls match the supplied floor plan; no fictitious boundary hits.
    objects += [((x0+x1)/2, y0, (x1-x0)/2, .05, 2.),
                ((x0+x1)/2, y1, (x1-x0)/2, .05, 2.),
                (x0, (y0+y1)/2, .05, (y1-y0)/2, 2.),
                (x1, (y0+y1)/2, .05, (y1-y0)/2, 2.)]
    res = .1
    cells = np.zeros((int((y1-y0)/res)+1, int((x1-x0)/res)+1), np.uint8)
    grid = OccupancyGrid(cells, res, (x0,y0))
    for i, (x,y,hx,hy,height) in enumerate(objects):
        if cafe_style and i==0:
            # Real tabletop and four physical legs; map conservatively occupies
            # the whole table footprint, including the space between its legs.
            wb.add_geom(name='room_object_0_top',type=mujoco.mjtGeom.mjGEOM_BOX,
                        pos=[x,y,height-.025],size=[hx,hy,.025],rgba=[.43,.25,.12,1])
            for j,(sx,sy) in enumerate([(-1,-1),(-1,1),(1,-1),(1,1)]):
                wb.add_geom(name=f'room_object_0_leg{j}',type=mujoco.mjtGeom.mjGEOM_BOX,
                            pos=[x+sx*(hx-.065),y+sy*(hy-.065),(height-.05)/2],
                            size=[.035,.035,(height-.05)/2],rgba=[.15,.12,.09,1])
        else:
            wb.add_geom(name=f'room_object_{i}', type=mujoco.mjtGeom.mjGEOM_BOX,
                        pos=[x,y,height/2], size=[hx,hy,height/2],
                        rgba=[.85,.82,.75,1] if cafe_style else [.55,.4,.25,1])
        r0,c0 = grid.world_to_cell((x-hx,y-hy)); r1,c1 = grid.world_to_cell((x+hx,y+hy))
        cells[max(0,r0):r1+1,max(0,c0):c1+1] = OccupancyGrid.OCCUPIED
    return spec, grid


class SensorController(ScriptedCommandController):
    def __init__(self, cfg, spec, start=(0.,0.,0.), seed=8201):
        super().__init__(cfg)
        initial = self.mj_data.qpos.copy()
        self.mj_model = spec.compile(); self.mj_model.opt.timestep = cfg.mujoco.physics_dt
        self.mj_data = mujoco.MjData(self.mj_model)
        self.mj_data.qpos[:] = initial
        self.mj_data.qpos[:2] = start[:2]
        self.mj_data.qpos[3:7] = [np.cos(start[2]/2),0,0,np.sin(start[2]/2)]
        self.room_geom_ids = {i for i in range(self.mj_model.ngeom)
            if (mujoco.mj_id2name(self.mj_model,mujoco.mjtObj.mjOBJ_GEOM,i) or "").startswith("room_object_")}
        self.collision_pairs = set()
        self.collision_contact_steps = 0
        mujoco.mj_forward(self.mj_model, self.mj_data)
        self._ghost_mj_data = mujoco.MjData(self.mj_model)
        self.imu = MujocoHeadingAdapter(self.mj_model, cfg.robot.joint_names,
                                       noise_std_rad_s=.005, bias_rad_s=(0,0,.0015), seed=seed)
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
            hit = False
            for contact in data.contact:
                pair = tuple(sorted((int(contact.geom1),int(contact.geom2))))
                if contact.dist < 0 and bool(set(pair) & self.room_geom_ids) and not set(pair) <= self.room_geom_ids:
                    self.collision_pairs.add(pair); hit = True
            self.collision_contact_steps += int(hit)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--duration', type=float, default=40.)
    ap.add_argument('--table', type=float, nargs=5, default=TABLE, metavar=('X','Y','HX','HY','HEIGHT'))
    ap.add_argument('--start', type=float, nargs=3, default=(0.,0.,0.))
    ap.add_argument('--seed', type=int, default=8201)
    ap.add_argument('--record-demo', action='store_true')
    ap.add_argument('--hand-carried', action='store_true')
    ap.add_argument('--printed-payload', action='store_true')
    ap.add_argument('--cafe-style', action='store_true')
    ap.add_argument('--known-load-depth-mask', action='store_true')
    ap.add_argument('--carry-command-guard', action='store_true')
    ap.add_argument('--head-pitch', type=float, default=0.)
    ap.add_argument('--prediction-scale', type=float, default=None)
    ap.add_argument('--video-fps', type=int, choices=[5,25], default=5)
    ap.add_argument('--tracking-evaluator', action='store_true')
    ap.add_argument('--walk-speed', type=float, default=.35)
    ap.add_argument('--settle-seconds', type=float, default=0.)
    ap.add_argument('--vla-checkpoint', type=Path)
    ap.add_argument('--policy-seed', type=int, default=9101)
    args = ap.parse_args()
    assert not (args.known_load_depth_mask or args.printed_payload or args.cafe_style) or args.hand_carried
    assert -.314<=args.head_pitch<=.794
    assert args.prediction_scale is None or 0<=args.prediction_scale<=1.5
    assert 0<args.walk_speed<=.5 and args.settle_seconds>=0
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    report = dict(status='started', started_at_utc=datetime.now(timezone.utc).isoformat(),
        evidence_kind='mujoco_sensor_estimated_navigation_development', payload_present=False,
        markers_present=False, training_performed=False, hardware_verified=False,
        navigation_privileged_inputs=[], evaluation_only=['world pose', 'root speed', 'body tilt'],
        prior={'source':'operator floor plan and initial pose', 'initial_pose':args.start, 'sigma':[.1,.1,.05]},
        assumptions=['level initial attitude', 'flat floor', 'stance foot for height', 'ideal encoders',
                     'gyro noise .005rad/s and z bias .0015rad/s', 'camera FOV58deg'],
        protocol=dict(duration_s=args.duration, camera_hz=5, policy_hz=50, physics_hz=500,
                      payload='free hand-supported tray with box and sealed can' if args.hand_carried else 'none', destination='single unnumbered table', seed=args.seed,
                      table=args.table,start=args.start,record_demo=args.record_demo,
                      video_fps=args.video_fps,tracking_evaluator=args.tracking_evaluator,
                      head_pitch_rad=args.head_pitch,prediction_scale=args.prediction_scale,
                      hand_carried=args.hand_carried,printed_payload=args.printed_payload,cafe_style=args.cafe_style,known_load_depth_mask=args.known_load_depth_mask,carry_command_guard=args.carry_command_guard,walk_speed=args.walk_speed,settle_seconds=args.settle_seconds,
                      policy_mode='smolvla' if args.vla_checkpoint else 'executive',policy_seed=args.policy_seed),
        limits=['development trial, not held-out', 'linear prediction uses commanded velocity',
                'scan matching must constrain drift', 'no payload', 'not hardware tested'])
    report['versions']={'mujoco':mujoco.__version__,'torch':torch.__version__,'numpy':np.__version__}
    files = ['sim/run_k1_sensor_navigation.py','sim/k1_sensor_observation.py','sim/k1_imu.py',
             'sim/k1_observation.py','contracts/robot_telemetry.py','deployment/k1_leg_estimator.py',
             'perception/k1_camera.py','perception/tabletop.py','navigation/localization.py',
             'autonomy/session.py','autonomy/executive.py','navigation/follower.py',
             'navigation/planner.py','navigation/search.py','memory/scene_memory.py',
             'vla/inputs.py','vla/recorder.py','vla/action_space.py']
    if args.hand_carried:
        files += ['sim/k1_hand_controller.py','sim/k1_hand_carry.py']
        report.update(payload_present=True,evidence_kind='mujoco_sensor_guided_hand_carry_development',
            walking_actor_arm_inputs='nominal arm position/zero velocity ablation')
        report['limits']=[v for v in report['limits'] if v!='no payload']+['physical underside tray seats and cup holder','known load arm feedforward','no PPO residual','sealed rigid can, no liquid simulation']
    if args.printed_payload or args.cafe_style:
        files += ['sim/k1_mujoco_appearance.py']
    if args.known_load_depth_mask:
        files += ['deployment/carrying_depth_filter.py']
    if args.carry_command_guard:
        files += ['deployment/k1_carry_commands.py']
    if args.vla_checkpoint:
        files += ['deployment/smolvla_policy.py','deployment/vla_session.py','vla/adapter.py']
    report['source_hashes'] = {f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}
    (out/'manifest.json').write_text(json.dumps(report,indent=2))
    torch.set_num_threads(1); torch.manual_seed(0)
    cfg = K1WalkTaskCfg(); cfg.mujoco.log_states = None
    cfg.policy.checkpoint_path = str(DEPLOY/'tasks/locomotion/robots/k1/models/k1_walk.pt')
    report['checkpoint_sha256'] = hashlib.sha256(Path(cfg.policy.checkpoint_path).read_bytes()).hexdigest()
    if args.hand_carried:
        from sim.k1_hand_carry import make_model
        from sim.k1_hand_controller import HandSensorController
        model_source=out/'hand_scene.xml';report['hand_setup']=make_model(model_source,handle_seats=True)
        if args.printed_payload:
            from sim.k1_mujoco_appearance import decorate_payload
            report['appearance']=decorate_payload(model_source)
        if args.cafe_style:
            from sim.k1_mujoco_appearance import decorate_floor
            report['floor_appearance']=decorate_floor(model_source)
            report['limits']+=['physical tabletop and legs; conservative solid table footprint in supplied map']
        spec,grid=scene_and_map(args.table,model_source,cafe_style=args.cafe_style)
        ctrl=HandSensorController(cfg,spec,args.start,args.seed,head_pitch=args.head_pitch)
    else:
        spec, grid = scene_and_map(args.table); ctrl = SensorController(cfg,spec,args.start,args.seed)
    model,data = ctrl.mj_model,ctrl.mj_data
    adapter = SensorObservationAdapter(model, MODEL)
    evaluator = mujoco.Renderer(model,height=480,width=640)
    localizer = ScanMatchLocalizer(grid, Pose2D(*args.start), max_points=200)
    task = DeliveryTask('deliver the pizza and drink to the table',
                        parse_instruction('deliver the pizza and drink to the table'), 0., args.duration)
    session_cls=AutonomySession;session_kwargs={}
    if args.vla_checkpoint:
        from deployment.smolvla_policy import SmolVLAProposalPolicy
        from deployment.vla_session import BoundedVLASession
        proposal_policy=SmolVLAProposalPolicy(args.vla_checkpoint,args.policy_seed)
        session_cls=BoundedVLASession;session_kwargs['proposal_policy']=proposal_policy
        report['vla_checkpoint_sha256']=proposal_policy.sha256
        report['vla_training_updates']=proposal_policy.manifest['optimizer_updates']
    session = session_cls(task,grid,TabletopDetector(),[Region('dining',((BOUNDS[0]+BOUNDS[2])/2,(BOUNDS[1]+BOUNDS[3])/2),3.,('dining',))],
        config=ExecutiveConfig(final_speed=args.walk_speed, approach_speed=args.walk_speed, search_speed=args.walk_speed),
        limits=FollowerLimits(v_max=args.walk_speed,min_walk_cmd=args.walk_speed,final_accel=.25),deployable=True,**session_kwargs)
    from vla.recorder import DemoRecorder
    recorder = DemoRecorder(out.name, {"source":"mujoco", "detector":"RGB-D tabletop",
        "privileged_inputs":[], "initial_pose_prior":args.start, "floor_plan":"operator supplied",
        "payload_present":args.hand_carried}) if args.record_demo else None
    import imageio.v2 as iio
    videos={name:iio.get_writer(str(out/(name+'.mp4')),fps=args.video_fps,codec='libx264')
            for name in ['evaluator','robot_camera']}
    rows=[]; frame_times=[]; video_times=[]; observations=[]; next_cam=0.; next_video=0.; started=time.monotonic()
    previous_heading=ctrl.imu.latest_heading; command=np.zeros(3); last_pose=None
    ctrl.update_state(); ctrl.start(); termination='duration_complete';terminal_since=None
    try:
        while data.time < args.duration-1e-8:
            t=float(data.time); heading=ctrl.imu.latest_heading
            if t > 0:
                # Temporary integration glue: relative gyro increments, never map yaw truth.
                if args.prediction_scale is None:
                    localizer.predict([command[0],command[1],0.],cfg.policy_dt)
                else:
                    localizer.predict([command[0],command[1],0.],cfg.policy_dt,scale=args.prediction_scale)
                localizer.pose[2] += heading.yaw_rad-previous_heading.yaw_rad
                localizer.cov[2,2] += max(0.,heading.yaw_variance_rad2-previous_heading.yaw_variance_rad2)
            previous_heading=heading
            obs=None
            if t >= next_cam-1e-8:
                frame,height = adapter.capture(data,ctrl.imu.latest_telemetry,heading)
                raw_depth=frame.depth.copy();mask_info=None
                if args.known_load_depth_mask:
                    from deployment.carrying_depth_filter import filter_known_carrying_volume
                    frame,mask_info=filter_known_carrying_volume(frame,ctrl.imu.latest_telemetry)
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
                    depth=frame.depth,raw_depth=raw_depth,T_base_camera=frame.T_base_camera,
                    pose=[pose.pose.x,pose.pose.y,pose.pose.yaw],cov=pose.cov,timestamp=t)
                next_cam+=.2; frame_times.append(t)
                observations.append(dict(t=t,pose=[pose.pose.x,pose.pose.y,pose.pose.yaw],
                    sigma=np.sqrt(np.diag(pose.cov)).tolist(),status=pose.status.value,
                    match=localizer.last_match,estimated_twist=twist.tolist(),estimated_height=height,load_depth_mask=mask_info))
            if t>=next_video-1e-8:
                from sim.k1_observation import CAMERA_NAME
                adapter.renderer.update_scene(data,camera=CAMERA_NAME)
                recorded_rgb=adapter.renderer.render().copy()
                videos['robot_camera'].append_data(recorded_rgb)
                camera=mujoco.MjvCamera()
                if args.tracking_evaluator:
                    camera.lookat[:]=[data.qpos[0]+.1,data.qpos[1],.65]
                    camera.distance=1.9;camera.azimuth=130.;camera.elevation=-15.
                else:
                    camera.lookat[:]=[2.,0.,.4];camera.distance=6.;camera.azimuth=-70.;camera.elevation=-30.
                evaluator.update_scene(data,camera=camera);eval_rgb=evaluator.render().copy()
                videos['evaluator'].append_data(eval_rgb)
                if len(video_times)%(args.video_fps*10)==0:
                    iio.imwrite(out/f'robot_camera-{len(video_times):04d}.png',recorded_rgb)
                    iio.imwrite(out/f'evaluator-{len(video_times):04d}.png',eval_rgb)
                video_times.append(t);next_video+=1./args.video_fps
            command=np.array(session.tick(obs,t,cfg.policy_dt)) if t>=2. else np.zeros(3)
            if session.done:command=np.zeros(3)
            if args.carry_command_guard:
                from deployment.k1_carry_commands import supported_carry_command
                command=supported_carry_command(command)
            if obs is not None:
                observations[-1]['tracks']=session.executive.memory.summary()
                if recorder is not None and session.cmd is not None:
                    recorder.record(obs,session.executive,session.cmd,
                                    image_ref=f'rgbd-{len(frame_times)-1:04d}.npz')
            ctrl.vel_command.lin_vel_x,ctrl.vel_command.lin_vel_y,ctrl.vel_command.ang_vel_yaw=command
            ctrl.update_state(); target=ctrl.policy_step()
            if not ctrl.is_running:termination='upstream_fall_fallback';break
            # Evaluation-only truth never enters observation, localizer or executive.
            w,x,y,z=data.qpos[3:7]; yaw=np.arctan2(2*(w*z+x*y),1-2*(y*y+z*z))
            tilt=float(np.degrees(np.arccos(np.clip(1-2*(x*x+y*y),-1,1))))
            rows.append([t,*data.qpos[:3],yaw,tilt,*localizer.pose,*command,
                         float(np.linalg.norm(data.qvel[:2]))])
            if data.qpos[2]<.3 or tilt>60:termination='fall';break
            if args.hand_carried and ctrl.hand_metrics['payload_drop']:termination='payload_drop';break
            if session.done and t>2:
                if terminal_since is None:terminal_since=t
                if t-terminal_since>=args.settle_seconds-1e-8:termination='autonomy_terminal';break
            ctrl.ctrl_step(target)
        iio.imwrite(out/'evaluator_final_recorded.png',eval_rgb)
        iio.imwrite(out/'robot_camera_final_recorded.png',recorded_rgb)
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
        np.savetxt(out/'video_times.csv',video_times,delimiter=',',header='sim_time_s',comments='')
        (out/'localization.json').write_text(json.dumps(observations,indent=2))
        if args.vla_checkpoint:
            report['vla_summary']=session.follower.summary()
            (out/'vla_calls.json').write_text(json.dumps(session.follower.calls,indent=2))
            (out/'vla_control.json').write_text(json.dumps(session.follower.control,indent=2))
        if args.hand_carried:
            report['hand_metrics']=ctrl.hand_metrics
            np.savetxt(out/'payload_contacts.csv',ctrl.payload_rows,delimiter=',',comments='',header='t,tray_x,tray_y,tray_z,tray_tilt,left_N,right_N,box_shift,drink_shift')
        report['collision_contact_steps'] = ctrl.collision_contact_steps
        report['collision_geom_pairs'] = [list(p) for p in sorted(ctrl.collision_pairs)]
        report['collision_scope'] = 'room-object vs robot and payload at 500Hz' if args.hand_carried else 'room-object vs robot contacts at 500Hz; no self-contact scoring'
        if recorder is not None:
            recorder.finish(out/'demonstrations', report.get('outcome') or report.get('termination','failed'))
            report['demo_frames'] = len(recorder.rows)
            report['demo_files'] = {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in (out/'demonstrations').iterdir() if p.is_file()}
        report.update(simulated_seconds=float(data.time),wall_seconds=time.monotonic()-started,
                      video_fps=args.video_fps,video_frames=len(video_times),camera_observation_frames=len(frame_times),
                      finished_at_utc=datetime.now(timezone.utc).isoformat())
        report['artifacts']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()
                             if p.is_file() and p.name!='manifest.json'}
        (out/'manifest.json').write_text(json.dumps(report,indent=2))
        print(json.dumps({k:v for k,v in report.items() if k not in ['source_hashes','artifacts']},indent=2))


if __name__=='__main__':main()
