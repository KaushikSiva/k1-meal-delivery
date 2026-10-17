#!/usr/bin/env python3
"""Official K1 URDF import + unfixed-base nominal PD diagnostic in the café.

This tests conversion, joint mapping, contacts and rendered appearance. It does
not execute the walking policy, deliver a payload or train a model.
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
parser.add_argument('--headless', action='store_true', default=True)
args = parser.parse_args()
args.output = args.output.resolve()
args.output.mkdir(parents=True, exist_ok=False)
manifest = args.output/'manifest.json'
urdf = ROOT/'sim/vendor/booster_assets/robots/K1/K1_22dof.urdf'
nominal = json.loads((ROOT/'sim/k1_isaac_nominal.json').read_text())
report = dict(status='started', started_at_utc=datetime.now(timezone.utc).isoformat(),
    evidence_kind='isaac_k1_urdf_import_nominal_pd_diagnostic', fixed_base=False,
    gravity_enabled=True, walking_policy_executed=False, training_performed=False,
    robot_payload_present=False, delivery_success=None,
    source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in [Path(__file__),urdf,ROOT/'sim/k1_isaac_nominal.json',ROOT/'sim/cafe_scene.py']})
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
    from isaaclab.actuators import ImplicitActuatorCfg
    from isaacsim.core.utils.extensions import enable_extension
    enable_extension("isaacsim.sensors.camera")
    from isaacsim.sensors.camera import Camera
    from isaacsim.core.utils.numpy.rotations import euler_angles_to_quats
    from pxr import UsdGeom
    from sim.cafe_scene import build_cafe

    sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(dt=nominal['physics_dt'], device='cuda:0'))
    build_cafe(sim.stage, ROOT/'sim/vendor/cafe-assets')
    joints = nominal['joints']
    cfg = ArticulationCfg(prim_path='/World/K1',
        spawn=sim_utils.UrdfFileCfg(asset_path=str(urdf), usd_dir=str(args.output/'converted'),
            fix_base=False, merge_fixed_joints=False, force_usd_conversion=True,
            replace_cylinders_with_capsules=False,
            rigid_props=sim_utils.RigidBodyPropertiesCfg(disable_gravity=False,max_depenetration_velocity=1),
            articulation_props=sim_utils.ArticulationRootPropertiesCfg(enabled_self_collisions=True,
                solver_position_iteration_count=8,solver_velocity_iteration_count=4),
            joint_drive=sim_utils.UrdfConverterCfg.JointDriveCfg(
                gains=sim_utils.UrdfConverterCfg.JointDriveCfg.PDGainsCfg(stiffness=0,damping=0))),
        init_state=ArticulationCfg.InitialStateCfg(pos=(1.0,0,.57),
            joint_pos={n:float(v['position']) for n,v in joints.items()},joint_vel={'.*':0.0}),
        actuators={'all':ImplicitActuatorCfg(joint_names_expr=['.*'],
            stiffness={n:float(v['stiffness']) for n,v in joints.items()},
            damping={n:float(v['damping']) for n,v in joints.items()},
            effort_limit_sim={n:float(v['effort_limit']) for n,v in joints.items()})})
    robot = Articulation(cfg)
    cam = Camera(prim_path='/World/K1Preview',position=np.array([3.2,-2.0,1.45]),
        orientation=euler_angles_to_quats(np.array([0,15,138]),degrees=True), resolution=(960,720),frequency=30)
    optics=UsdGeom.Camera.Get(sim.stage,cam.prim_path)
    optics.GetHorizontalApertureAttr().Set(32);optics.GetVerticalApertureAttr().Set(24);optics.GetFocalLengthAttr().Set(24)
    sim.reset()
    robot.write_root_pose_to_sim(robot.data.default_root_state[:,:7])
    robot.write_root_velocity_to_sim(robot.data.default_root_state[:,7:])
    robot.write_joint_state_to_sim(robot.data.default_joint_pos,robot.data.default_joint_vel)
    robot.reset();cam.initialize()
    assert len(robot.joint_names)==22 and set(robot.joint_names)==set(joints), robot.joint_names
    camera_links=[str(p.GetPath()) for p in sim.stage.Traverse() if p.GetName()=='head_realsense_rgb_link']
    assert len(camera_links)==1, camera_links
    report.update(joint_names=robot.joint_names,body_names=robot.body_names,camera_links=camera_links,
                  joint_mapping_verified=True,limits=['implicit PhysX PD, not upstream explicit actuator dynamics',
                    'static nominal targets, no actor','no robot payload','URDF fixed sensor joints retained'])
    rows=[]
    for step in range(1000):
        robot.set_joint_position_target(robot.data.default_joint_pos)
        robot.write_data_to_sim()
        sim.step(render=(step%10==0))
        robot.update(nominal['physics_dt'])
        pos=robot.data.root_pos_w[0].cpu().numpy()
        quat=robot.data.root_quat_w[0].cpu().numpy()
        tilt=float(np.degrees(np.arccos(np.clip(1-2*(quat[1]**2+quat[2]**2),-1,1))))
        rows.append([float((step+1)*nominal['physics_dt']),*pos.tolist(),tilt])
        assert np.isfinite(rows[-1]).all()
        if step in (199,999):
            for _ in range(4):sim.render()
            rgb=np.asarray(cam.get_rgba())[:,:,:3].astype(np.uint8)
            assert rgb.shape==(720,960,3) and rgb.std()>2
            Image.fromarray(rgb).save(args.output/f'frame-{step+1:04d}.png')
        if pos[2]<.25 or tilt>60:
            report['termination']='fall';break
    else:
        report['termination']='duration_complete'
    np.savetxt(args.output/'trajectory.csv',np.array(rows),delimiter=',',header='t,x,y,z,tilt_deg',comments='')
    report.update(status='tested',simulated_seconds=rows[-1][0],final_root_xyz=rows[-1][1:4],
                  peak_tilt_deg=max(r[4] for r in rows),nominal_pd_stayed_upright=report['termination']=='duration_complete')
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
