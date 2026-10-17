#!/usr/bin/env python3
"""Official K1 actor in Isaac café physics, optional supported load and learned residual.

Explicit PD + MJCF armature; evaluation only, no vision guidance or delivery claim.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--duration', type=float, default=15)
parser.add_argument('--speed', type=float, default=.35)
parser.add_argument('--loaded', action='store_true', help='Explicit supported tray and free box/drink')
parser.add_argument('--residual-checkpoint', type=Path, help='Trusted project-trained residual checkpoint for evaluation')
args = parser.parse_args()
assert 5 <= args.duration <= 60 and 0 <= args.speed <= .5
assert args.residual_checkpoint is None or args.loaded, 'Residual evaluation requires declared supported payload'
args.output = args.output.resolve()
args.output.mkdir(parents=True, exist_ok=False)
manifest = args.output/'manifest.json'
urdf = ROOT/'sim/vendor/booster_assets/robots/K1/K1_22dof.urdf'
nominal = json.loads((ROOT/'sim/k1_isaac_nominal.json').read_text())
report = dict(status='started', started_at_utc=datetime.now(timezone.utc).isoformat(),
    evidence_kind='isaac_k1_unloaded_scripted_velocity_diagnostic', fixed_base=False,
    gravity_enabled=True, walking_policy_executed=False, training_performed=False,
    robot_payload_present=False, delivery_success=None,
    source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in [Path(__file__),urdf,ROOT/'sim/k1_isaac_nominal.json',ROOT/'sim/cafe_scene.py',ROOT/'sim/k1_isaac_policy.py']})
report.update(duration_requested_s=args.duration,speed_command_m_s=args.speed,
    checkpoint_sha256=hashlib.sha256((ROOT/'sim/vendor/booster_deploy/tasks/locomotion/robots/k1/models/k1_walk.pt').read_bytes()).hexdigest(),
    actor_inputs=['joint_positions','joint_velocities','body_gyro','quaternion_projected_gravity','velocity_command','last_action'],
    evaluation_only=['world_position','height','tilt'])
if args.loaded:
    from sim.k1_payload import load_config, make_supported_urdf, spawn_payload
    payload_config=load_config()
    report.update(evidence_kind='isaac_k1_supported_payload_scripted_velocity_diagnostic',
                  robot_payload_present=True,payload_config=payload_config,
                  payload_observations='evaluation/reward only; never walking actor inputs')
    for name in ('sim/k1_payload.py','sim/k1_payload.json'):
        report['source_hashes'][name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    urdf=make_supported_urdf(urdf,args.output/'loaded.urdf',payload_config)
manifest.write_text(json.dumps(report,indent=2))
app = None
try:
    from isaaclab.app import AppLauncher
    app = AppLauncher(headless=True, enable_cameras=True).app
    import numpy as np
    import torch
    from PIL import Image
    import isaaclab.sim as sim_utils
    from isaaclab.assets import Articulation, ArticulationCfg
    from isaaclab.actuators import IdealPDActuatorCfg
    from isaacsim.core.utils.extensions import enable_extension
    enable_extension("isaacsim.sensors.camera")
    from isaacsim.sensors.camera import Camera
    from isaacsim.core.utils.numpy.rotations import euler_angles_to_quats
    from pxr import UsdGeom, Gf
    import imageio.v2 as imageio
    import xml.etree.ElementTree as ET
    from sim.k1_isaac_policy import IsaacK1Policy
    from sim.cafe_scene import build_cafe

    sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(dt=nominal['physics_dt'], device='cuda:0'))
    build_cafe(sim.stage, ROOT/'sim/vendor/cafe-assets')
    joints = nominal['joints']
    armature={j.attrib['name']:float(j.attrib['armature']) for j in ET.parse(ROOT/'sim/vendor/booster_assets/robots/K1/K1_22dof.xml').iter('joint') if 'armature' in j.attrib}
    assert set(armature)==set(joints)
    cfg = ArticulationCfg(prim_path='/World/K1',
        spawn=sim_utils.UrdfFileCfg(asset_path=str(urdf), usd_dir=str(args.output/'converted'),
            fix_base=False, merge_fixed_joints=True, force_usd_conversion=True,
            replace_cylinders_with_capsules=False,
            rigid_props=sim_utils.RigidBodyPropertiesCfg(disable_gravity=False,max_depenetration_velocity=1),
            articulation_props=sim_utils.ArticulationRootPropertiesCfg(enabled_self_collisions=True,
                solver_position_iteration_count=8,solver_velocity_iteration_count=4),
            joint_drive=sim_utils.UrdfConverterCfg.JointDriveCfg(
                gains=sim_utils.UrdfConverterCfg.JointDriveCfg.PDGainsCfg(stiffness=0,damping=0))),
        init_state=ArticulationCfg.InitialStateCfg(pos=(1.0,0,.6),
            joint_pos={n:float(v['position']) for n,v in joints.items()},joint_vel={'.*':0.0}),
        actuators={'all':IdealPDActuatorCfg(joint_names_expr=['.*'],armature=armature,
            effort_limit={n:float(v['effort_limit']) for n,v in joints.items()},
            stiffness={n:float(v['stiffness']) for n,v in joints.items()},
            damping={n:float(v['damping']) for n,v in joints.items()},
            effort_limit_sim={n:float(v['effort_limit']) for n,v in joints.items()})})
    robot = Articulation(cfg)
    payload=spawn_payload((1.,0.,.6),payload_config) if args.loaded else {}
    cam = Camera(prim_path='/World/K1Preview',position=np.array([3.2,-2.0,1.45]),
        orientation=euler_angles_to_quats(np.array([0,15,138]),degrees=True), resolution=(960,720))
    optics=UsdGeom.Camera.Get(sim.stage,cam.prim_path)
    optics.GetHorizontalApertureAttr().Set(32);optics.GetVerticalApertureAttr().Set(24);optics.GetFocalLengthAttr().Set(24)
    sim.reset()
    robot.write_root_pose_to_sim(robot.data.default_root_state[:,:7])
    robot.write_root_velocity_to_sim(robot.data.default_root_state[:,7:])
    robot.write_joint_state_to_sim(robot.data.default_joint_pos,robot.data.default_joint_vel)
    robot.reset();cam.initialize()
    for obj in payload.values():
        obj.write_root_pose_to_sim(obj.data.default_root_state[:,:7])
        obj.write_root_velocity_to_sim(obj.data.default_root_state[:,7:])
        obj.reset()
    assert len(robot.joint_names)==22 and set(robot.joint_names)==set(joints), robot.joint_names
    camera_links=[str(p.GetPath()) for p in sim.stage.Traverse() if p.GetName()=='head_realsense_rgb_link']
    if not camera_links:
        # Merging massless fixed sensor links avoids PhysX's implicit1kg bodies.
        # Restore only their optical frame under the real articulated head link.
        parents=[p for p in sim.stage.Traverse() if p.GetName()=='aahead_pitch_link']
        assert len(parents)==1
        joint=ET.parse(urdf).find("joint[@name='head_realsense_rgb_joint']")
        origin=joint.find('origin')
        optical=UsdGeom.Xform.Define(sim.stage,str(parents[0].GetPath())+'/head_realsense_rgb_link')
        optical.AddTranslateOp().Set(Gf.Vec3d(*map(float,origin.attrib['xyz'].split())))
        optical.AddRotateXYZOp().Set(Gf.Vec3f(*np.rad2deg(list(map(float,origin.attrib['rpy'].split())))))
        camera_links=[str(optical.GetPath())]
    assert len(camera_links)==1, camera_links
    report.update(joint_names=robot.joint_names,body_names=robot.body_names,camera_links=camera_links,
                  joint_mapping_verified=True,limits=['PhysX contacts differ from MuJoCo',
                    'unloaded, no vision guidance','massless fixed sensor joints merged; optical frame restored from URDF'],armature=armature)
    # Native camera under the articulated optical link. URDF link uses CV axes;
    # the USD camera needs +Yup/-Zforward, so rotate180deg about optical x.
    head=Camera(prim_path=camera_links[0]+'/DiagnosticRGBD',resolution=(640,480))
    xf=UsdGeom.Xformable(sim.stage.GetPrimAtPath(head.prim_path))
    xf.ClearXformOpOrder();xf.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(0,Gf.Vec3d(1,0,0)))
    lens=UsdGeom.Camera.Get(sim.stage,head.prim_path)
    lens.GetHorizontalApertureAttr().Set(32);lens.GetVerticalApertureAttr().Set(24)
    lens.GetFocalLengthAttr().Set(float(24/(2*np.tan(np.deg2rad(58)/2))))
    head.initialize();head.add_distance_to_image_plane_to_frame()
    # Populate RTX sensor buffers before time-indexed recording begins.
    for _ in range(20):sim.render()
    report['body_masses_kg']=robot.root_physx_view.get_masses()[0].cpu().tolist()
    report['total_mass_kg']=sum(report['body_masses_kg'])
    expected_mass=sum(float(x.attrib['value']) for x in ET.parse(urdf).findall('link/inertial/mass'))
    report['expected_urdf_mass_kg']=expected_mass
    assert abs(report['total_mass_kg']-expected_mass)<1e-4, 'Importer changed robot mass'
    if args.loaded:
        report['payload_masses_kg']={name:float(obj.root_physx_view.get_masses()[0].sum()) for name,obj in payload.items()}
        for name,mass in report['payload_masses_kg'].items():
            assert abs(mass-payload_config[name]['mass_kg'])<1e-5
        from isaaclab.utils.math import quat_apply_inverse
    payload_rows=[];max_payload_displacement=0.;max_payload_tilt=0.;payload_drop=False
    residual_model=None
    if args.residual_checkpoint:
        from sim.k1_batch_policy import BatchedK1Policy
        from training.ppo_core import ResidualActorCritic
        checkpoint=torch.load(args.residual_checkpoint,map_location='cuda:0',weights_only=False)
        bridge=BatchedK1Policy(robot.joint_names,1,'cuda:0')
        assert checkpoint['policy_joint_names']==bridge.cfg.policy.policy_joint_names
        assert checkpoint['report']['base_actor_sha256']==report['checkpoint_sha256']
        assert checkpoint['report']['residual_bound_rad']==.08
        residual_model=ResidualActorCritic().to('cuda:0').eval()
        residual_model.load_state_dict(checkpoint['model'])
        previous_residual=torch.zeros(1,20,device='cuda:0')
        report.update(residual_checkpoint_sha256=hashlib.sha256(args.residual_checkpoint.read_bytes()).hexdigest(),
            residual_training_environment_steps=checkpoint['report']['environment_steps'],
            residual_training_optimizer_steps=checkpoint['report']['optimizer_steps'],
            residual_bound_rad=.08,base_actor_finetuned=False)
        for name in ('sim/k1_batch_policy.py','training/ppo_core.py'):
            report['source_hashes'][name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
        report['actor_inputs'].append('previous_residual')
    else:
        bridge=IsaacK1Policy(robot,device='cuda:0')
    report['actor_steps']=0
    rows=[];frame_times=[];max_tilt=0.;targets=robot.data.default_joint_pos.clone()
    writers={name:imageio.get_writer(str(args.output/(name+'.mp4')),fps=25,codec='libx264')
             for name in ('evaluator','robot_camera')}
    report['termination']='duration_complete'
    try:
        for step in range(int(round(args.duration/nominal['physics_dt']))):
            t=step*nominal['physics_dt']
            command=(args.speed if 2<=t<args.duration-2 else 0.,0.,0.)
            if step%10==0:
                try:
                    if residual_model is None:
                        targets=bridge.step(command)
                    else:
                        with torch.no_grad():
                            commands=torch.tensor([command],device='cuda:0')
                            observation=torch.cat((bridge.observe(robot.data,commands),previous_residual),-1)
                            residual=.08*torch.tanh(residual_model.actor(observation))
                            targets=bridge.step(robot.data,commands)
                            targets[:,bridge.policy_indices]+=residual
                            previous_residual.copy_(residual)
                    report['walking_policy_executed']=True
                    report['actor_steps']+=1
                except RuntimeError as exc:
                    report['termination']='actor_fallback';report['actor_error']=str(exc);break
            robot.set_joint_position_target(targets)
            robot.write_data_to_sim()
            sim.step(render=(step%20==19))
            robot.update(nominal['physics_dt'])
            for obj in payload.values():obj.update(nominal['physics_dt'])
            pos=robot.data.root_pos_w[0].cpu().numpy()
            quat=robot.data.root_quat_w[0].cpu().numpy()
            tilt=float(np.degrees(np.arccos(np.clip(1-2*(quat[1]**2+quat[2]**2),-1,1))))
            max_tilt=max(max_tilt,tilt)
            if args.loaded:
                payload_values=[]
                for name,obj in payload.items():
                    relative=quat_apply_inverse(robot.data.root_quat_w,
                        obj.data.root_pos_w-robot.data.root_pos_w)[0]
                    reference=torch.tensor(payload_config[name]['center'],device=relative.device)
                    displacement=float(torch.linalg.vector_norm((relative-reference)[:2]))
                    pq=obj.data.root_quat_w[0]
                    payload_tilt=float(torch.rad2deg(torch.acos(torch.clamp(1-2*(pq[1]**2+pq[2]**2),-1,1))))
                    max_payload_displacement=max(max_payload_displacement,displacement)
                    max_payload_tilt=max(max_payload_tilt,payload_tilt)
                    surface=payload_config['tray']['center'][2]+payload_config['tray']['size'][2]/2
                    if float(relative[2]) < surface-payload_config['development_thresholds']['drop_below_tray_m']:
                        payload_drop=True
                    payload_values.extend([*relative.cpu().tolist(),displacement,payload_tilt])
                if step%10==9:payload_rows.append([(step+1)*nominal['physics_dt'],*payload_values])
            if step%10==9:
                rows.append([(step+1)*nominal['physics_dt'],*pos.tolist(),tilt,*command])
                assert np.isfinite(rows[-1]).all()
            if step%20==19:
                capture_t=(step+1)*nominal['physics_dt']
                for name,c in [('evaluator',cam),('robot_camera',head)]:
                    rgb=np.asarray(c.get_rgba())[:,:,:3].astype(np.uint8)
                    assert rgb.ndim==3 and rgb.shape[2]==3 and rgb.std()>2
                    writers[name].append_data(rgb)
                    if len(frame_times)%125==0:
                        Image.fromarray(rgb).save(args.output/f'{name}-{len(frame_times):04d}.png')
                frame_times.append(capture_t)
            if pos[2]<.25 or tilt>60:
                report['termination']='fall';break
            if payload_drop:
                report['termination']='payload_drop';break
    finally:
        for writer in writers.values():writer.close()
    np.savetxt(args.output/'trajectory.csv',np.array(rows),delimiter=',',header='t,x,y,z,tilt_deg,cmd_vx,cmd_vy,cmd_wz',comments='')
    np.savetxt(args.output/'frame_times.csv',np.array(frame_times),delimiter=',',header='sim_time_s',comments='')
    report.update(status='tested',simulated_seconds=(step+1)*nominal['physics_dt'],final_root_xyz=pos.tolist(),
                  peak_tilt_deg=max_tilt,net_x_m=float(pos[0]-1),video_fps=25,video_frames=len(frame_times))
    if args.loaded:
        np.savetxt(args.output/'payload_trajectory.csv',np.array(payload_rows),delimiter=',',
            header='t,box_x,box_y,box_z,box_displacement_xy,box_tilt_deg,drink_x,drink_y,drink_z,drink_displacement_xy,drink_tilt_deg',comments='')
        limits=payload_config['development_thresholds']
        final_speed=float(torch.linalg.vector_norm(robot.data.root_lin_vel_w[0]))
        stable=(report['termination']=='duration_complete' and not payload_drop
                and max_tilt<limits['max_tray_tilt_deg']
                and max_payload_displacement<limits['max_payload_displacement_m']
                and final_speed<limits['max_final_root_speed_m_s'])
        report.update(max_payload_displacement_xy_m=max_payload_displacement,
            max_payload_tilt_deg=max_payload_tilt,payload_drop=payload_drop,
            final_root_speed_m_s=final_speed,development_stability_pass=stable)
        report['limits']=[x for x in report['limits'] if x!='unloaded, no vision guidance']+[
            'supported torso bracket; not hand carrying','scripted command, no vision guidance',
            'sealed rigid drink; no liquid or spilling simulation','development thresholds, not hardware validation']

except Exception as exc:
    import traceback
    report.update(status='failed',error=f'{type(exc).__name__}: {exc}',traceback=traceback.format_exc())
    raise
finally:
    report['finished_at_utc']=datetime.now(timezone.utc).isoformat()
    report['artifacts']={str(p.relative_to(args.output)):dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
                         for p in args.output.rglob('*') if p.is_file() and p!=manifest}
    manifest.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)
    if app is not None:app.close(wait_for_replicator=False, skip_cleanup=True)
