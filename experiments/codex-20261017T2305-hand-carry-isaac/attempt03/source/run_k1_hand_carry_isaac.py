#!/usr/bin/env python3
"""Free tray carried by physical hand contacts in Isaac café physics.

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
parser.add_argument('--wide-evaluator', action='store_true', help='Wider fixed view covering the full straight route')
parser.add_argument('--payload-config', type=Path, default=ROOT/'sim/k1_payload.json')
parser.add_argument('--reference-colors', action='store_true', help='Approximate official-photo surface colors only')
parser.add_argument('--realistic-payload', action='store_true', help='Render-only branded payload shells')
args = parser.parse_args()
args.loaded=False;args.residual_checkpoint=None;args.reference_colors=True;args.realistic_payload=True
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
    from sim.k1_hand_isaac import HandCarryModel, ARM_POSE
    handmodel=HandCarryModel(args.output/'hand-model.xml')
    joints = nominal['joints']
    for n,v in ARM_POSE.items():joints[n].update(position=v,stiffness=80.,damping=3.)
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
        init_state=ArticulationCfg.InitialStateCfg(pos=(1.0,0,handmodel.root_height),
            joint_pos={n:float(v['position']) for n,v in joints.items()},joint_vel={'.*':0.0}),
        actuators={'all':IdealPDActuatorCfg(joint_names_expr=['.*'],armature=armature,
            effort_limit={n:float(v['effort_limit']) for n,v in joints.items()},
            stiffness={n:float(v['stiffness']) for n,v in joints.items()},
            damping={n:float(v['damping']) for n,v in joints.items()},
            effort_limit_sim={n:float(v['effort_limit']) for n,v in joints.items()})})
    robot = Articulation(cfg)
    if args.reference_colors:
        from sim.k1_appearance import apply_k1_appearance
        report['appearance']=apply_k1_appearance(sim.stage)
        report['source_hashes']['sim/k1_appearance.py']=hashlib.sha256((ROOT/'sim/k1_appearance.py').read_bytes()).hexdigest()
    payload=handmodel.spawn(sim.stage)
    from isaaclab.sensors import ContactSensor, ContactSensorCfg
    robot_paths=[str(p.GetPath()) for p in sim.stage.Traverse() if p.HasAPI(__import__('pxr',fromlist=['UsdPhysics']).UsdPhysics.RigidBodyAPI) and str(p.GetPath()).startswith('/World/K1/')]
    contact=ContactSensor(ContactSensorCfg(prim_path='/World/Carried_tray', update_period=0., filter_prim_paths_expr=robot_paths))
    payload_config=handmodel.visual_config()
    if args.realistic_payload:
        from sim.k1_payload_visuals import apply_payload_visuals
        report['payload_appearance']=apply_payload_visuals(sim.stage,payload_config,tray_root='/World/Carried_tray')
        for source in [ROOT/'sim/k1_payload_visuals.py', *sorted((ROOT/'sim/assets/payload').glob('*.png'))]:
            report['source_hashes'][str(source.relative_to(ROOT))]=hashlib.sha256(source.read_bytes()).hexdigest()
    evaluator_position=[5.5,-3.2,2.0] if args.wide_evaluator else [3.2,-2.0,1.45]
    evaluator_angles=[0,18,133] if args.wide_evaluator else [0,15,138]
    report['evaluator_camera']=dict(position_m=evaluator_position,euler_degrees=evaluator_angles,
                                    purpose='evaluation only; excluded from actor')
    cam = Camera(prim_path='/World/K1Preview',position=np.array(evaluator_position),
        orientation=euler_angles_to_quats(np.array(evaluator_angles),degrees=True), resolution=(960,720))
    optics=UsdGeom.Camera.Get(sim.stage,cam.prim_path)
    optics.GetHorizontalApertureAttr().Set(32);optics.GetVerticalApertureAttr().Set(24);optics.GetFocalLengthAttr().Set(24)
    sim.reset()
    robot.write_root_pose_to_sim(robot.data.default_root_state[:,:7])
    robot.write_root_velocity_to_sim(robot.data.default_root_state[:,7:])
    robot.write_joint_state_to_sim(robot.data.default_joint_pos,robot.data.default_joint_vel)
    robot.reset();cam.initialize()
    handmodel.configure_joint_order(robot.joint_names)
    arm_indices=handmodel.arms.tolist()
    hand_targets=torch.tensor([ARM_POSE[robot.joint_names[i]] for i in arm_indices],device='cuda:0')
    report.update(evidence_kind='isaac_free_tray_hand_contact_development',robot_payload_present=True,hand_setup=handmodel.setup,walking_actor_arm_inputs='nominal arm position/zero velocity ablation',contact_filter_paths=robot_paths,hand_contact_steps=[0,0],max_hand_contact_loss_s=[0.,0.],other_robot_contact_steps={},max_arm_torque_Nm=0.,max_tray_tilt_deg=0.)
    contact_gaps=[0,0]
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
    closeup=None
    if args.realistic_payload:
        closeup=Camera(prim_path='/World/PayloadCloseup',position=np.array([2.,-.75,1.4]),
            orientation=euler_angles_to_quats(np.array([0,30,135]),degrees=True),resolution=(1280,960))
        closeup.initialize()
        closeopt=UsdGeom.Camera.Get(sim.stage,closeup.prim_path)
        closeopt.GetHorizontalApertureAttr().Set(32);closeopt.GetVerticalApertureAttr().Set(24);closeopt.GetFocalLengthAttr().Set(35)
    # Populate RTX sensor buffers before time-indexed recording begins.
    for _ in range(20):sim.render()
    if closeup is not None:
        Image.fromarray(closeup.get_rgba()[:,:,:3]).save(args.output/'payload_closeup_initial.png')
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
        original_observation=bridge.controller.policy.compute_observation
        def nominal_arm_observation():
            dst=bridge.controller.robot.data
            arm=[bridge.controller.cfg.robot.joint_names.index(n) for n in ARM_POSE]
            dst.joint_pos[arm]=bridge.controller.robot.default_joint_pos[arm].to(dst.joint_pos.device)
            dst.joint_vel[arm]=0.
            return original_observation()
        bridge.controller.policy.compute_observation=nominal_arm_observation
    report['actor_steps']=0
    rows=[];frame_times=[];last_frames={};max_tilt=0.;targets=robot.data.default_joint_pos.clone()
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
            targets[:,arm_indices]=hand_targets
            ff=handmodel.feedforward(robot.data.joint_pos[0].cpu().numpy(),robot.data.joint_vel[0].cpu().numpy(),robot.data.root_quat_w[0].cpu().numpy(),robot.data.root_ang_vel_b[0].cpu().numpy())
            robot.set_joint_effort_target(torch.tensor(ff,device='cuda:0',dtype=torch.float32).unsqueeze(0))
            robot.set_joint_position_target(targets)
            robot.write_data_to_sim()
            sim.step(render=(step%20==19))
            robot.update(nominal['physics_dt'])
            for obj in payload.values():obj.update(nominal['physics_dt'])
            contact.update(nominal['physics_dt'],force_recompute=True)
            forces=torch.linalg.vector_norm(contact.data.force_matrix_w[0,0],dim=-1).cpu().numpy()
            for i,side in enumerate(['left','right']):
                f=sum(float(forces[j]) for j,path in enumerate(robot_paths) if path.endswith('/'+side+'_elbow_yaw_link'))
                report['hand_contact_steps'][i]+=int(f>.1)
                contact_gaps[i]=0 if f>.1 else contact_gaps[i]+1
                report['max_hand_contact_loss_s'][i]=max(report['max_hand_contact_loss_s'][i],contact_gaps[i]*nominal['physics_dt'])
            for j,path in enumerate(robot_paths):
                if forces[j]>.1 and not path.endswith(('/left_elbow_yaw_link','/right_elbow_yaw_link')):report['other_robot_contact_steps'][path]=report['other_robot_contact_steps'].get(path,0)+1
            report['max_arm_torque_Nm']=max(report['max_arm_torque_Nm'],float(robot.data.applied_torque[0,arm_indices].abs().max()))
            pos=robot.data.root_pos_w[0].cpu().numpy()
            quat=robot.data.root_quat_w[0].cpu().numpy()
            tilt=float(np.degrees(np.arccos(np.clip(1-2*(quat[1]**2+quat[2]**2),-1,1))))
            max_tilt=max(max_tilt,tilt)
            from isaaclab.utils.math import quat_apply_inverse
            tq=payload['tray'].data.root_quat_w[0]
            tp=payload['tray'].data.root_pos_w[0]
            traytilt=float(torch.rad2deg(torch.acos(torch.clamp(1-2*(tq[1]**2+tq[2]**2),-1,1))))
            report['max_tray_tilt_deg']=max(report['max_tray_tilt_deg'],traytilt)
            payload_values=[]
            for name,reference in [('box',[-.01,.065]),('drink',[0.,-.17])]:
                relative=quat_apply_inverse(tq.unsqueeze(0),(payload[name].data.root_pos_w[0]-tp).unsqueeze(0))[0]
                displacement=float(torch.linalg.vector_norm(relative[:2]-torch.tensor(reference,device='cuda:0')))
                max_payload_displacement=max(max_payload_displacement,displacement)
                if float(relative[2])<-.1:payload_drop=True
                payload_values.extend([*relative.cpu().tolist(),displacement])
            if float(tp[2])<.35:payload_drop=True
            if step%10==9:payload_rows.append([(step+1)*nominal['physics_dt'],*tp.cpu().tolist(),traytilt,*payload_values,*forces.tolist()])
            if step%10==9:
                rows.append([(step+1)*nominal['physics_dt'],*pos.tolist(),tilt,*command])
                assert np.isfinite(rows[-1]).all()
            if step%20==19:
                capture_t=(step+1)*nominal['physics_dt']
                for name,c in [('evaluator',cam),('robot_camera',head)]:
                    rgb=np.asarray(c.get_rgba())[:,:,:3].astype(np.uint8)
                    assert rgb.ndim==3 and rgb.shape[2]==3 and rgb.std()>2
                    writers[name].append_data(rgb)
                    last_frames[name]=rgb.copy()
                    if len(frame_times)%125==0:
                        Image.fromarray(rgb).save(args.output/f'{name}-{len(frame_times):04d}.png')
                frame_times.append(capture_t)
            if pos[2]<.25 or tilt>60:
                report['termination']='fall';break
            if payload_drop:
                report['termination']='payload_drop';break
    finally:
        for writer in writers.values():writer.close()
    for name,rgb in last_frames.items():
        Image.fromarray(rgb).save(args.output/f'{name}_final_recorded.png')
    report['last_recorded_frame_time_s']=frame_times[-1] if frame_times else None
    np.savetxt(args.output/'trajectory.csv',np.array(rows),delimiter=',',header='t,x,y,z,tilt_deg,cmd_vx,cmd_vy,cmd_wz',comments='')
    np.savetxt(args.output/'frame_times.csv',np.array(frame_times),delimiter=',',header='sim_time_s',comments='')
    report.update(status='tested',simulated_seconds=(step+1)*nominal['physics_dt'],final_root_xyz=pos.tolist(),
                  peak_tilt_deg=max_tilt,net_x_m=float(pos[0]-1),video_fps=25,video_frames=len(frame_times))
    np.savetxt(args.output/'payload_contacts.csv',np.array(payload_rows),delimiter=',',header='t,tray_x,tray_y,tray_z,tray_tilt,box_x,box_y,box_z,box_shift,drink_x,drink_y,drink_z,drink_shift,'+','.join(robot_paths),comments='')
    report.update(max_payload_displacement_xy_m=max_payload_displacement,payload_drop=payload_drop,final_root_speed_m_s=float(torch.linalg.vector_norm(robot.data.root_lin_vel_w[0])))
    report['limits']=['scripted velocity, not vision-guided delivery','no PPO residual or VLA in this trial','preloaded tray with physical underside seats and cup holder','sealed rigid drink, no fluid simulation','model-based arm gravity/load compensation via joint torques','material/geometry assumptions, no hardware verification']
    report['source_hashes'].update({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'sim/k1_hand_isaac.py',ROOT/'sim/k1_hand_carry.py']})

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
