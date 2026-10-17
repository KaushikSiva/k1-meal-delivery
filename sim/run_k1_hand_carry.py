#!/usr/bin/env python3
"""Real MuJoCo hand-contact baseline; simple diagnostic visuals, no success promise."""
import argparse,json,hashlib,sys
from pathlib import Path
from datetime import datetime,timezone
import numpy as np,torch,mujoco,imageio.v2 as imageio
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'sim/vendor/booster_deploy'))
from sim.k1_hand_carry import make_model,ARM_POSE
from booster_deploy.controllers.base_controller import BaseController
from tasks.locomotion.robots.k1 import K1WalkTaskCfg

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--duration',type=float,default=8);ap.add_argument('--speed',type=float,default=0);ap.add_argument('--nominal-arm-observation',action='store_true');ap.add_argument('--handle-seats',action='store_true');ap.add_argument('--gravity-compensation',action='store_true');ap.add_argument('--feet-on-floor',action='store_true');a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    xml=a.output/'scene.xml';setup=make_model(xml,a.handle_seats)
    m=mujoco.MjModel.from_xml_path(str(xml));d=mujoco.MjData(m);d.qpos[2]=.6;d.qpos[3]=1
    cfg=K1WalkTaskCfg();cfg.policy.device='cpu';cfg.policy.checkpoint_path=str(ROOT/'sim/vendor/booster_deploy/tasks/locomotion/robots/k1/models/k1_walk.pt');ctrl=BaseController(cfg)
    names=cfg.robot.joint_names;qi=np.array([m.joint(n).qposadr[0] for n in names]);vi=np.array([m.joint(n).dofadr[0] for n in names]);act=np.arange(m.nu)
    assert [mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_JOINT,int(m.actuator_trnid[i,0])) for i in act]==names
    initial=ctrl.robot.default_joint_pos.numpy().copy();arm=np.array([names.index(n) for n in ARM_POSE]);initial[arm]=[ARM_POSE[names[i]] for i in arm];d.qpos[qi]=initial;mujoco.mj_forward(m,d);ctrl.start()
    kp=ctrl.robot.joint_stiffness.numpy().copy();kd=ctrl.robot.joint_damping.numpy().copy();limit=ctrl.robot.effort_limit.numpy();kp[arm]=setup['arm_kp'];kd[arm]=setup['arm_kd']
    bodies={n:m.body(n).id for n in ['free_tray','pizza_box','drink','left_elbow_yaw_link','right_elbow_yaw_link']};trayid=bodies['free_tray'];handids=[bodies['left_elbow_yaw_link'],bodies['right_elbow_yaw_link']]
    if a.handle_seats:
        payload_q=[m.joint(n).qposadr[0] for n in ['tray_free','pizza_free','drink_free']]
        old=float(d.qpos[payload_q[0]+2]);lo=old-.02;hi=old+.08
        for _ in range(24):
            z=(lo+hi)/2;d.qpos[payload_q[0]+2]=z;mujoco.mj_forward(m,d)
            distances=[]
            for sign,hand in [(-1,handids[1]),(1,handids[0])]:
                pad=m.geom(f'underside_handle_{sign}').id
                for g in range(m.ngeom):
                    if m.geom_bodyid[g]==hand and m.geom_contype[g]:distances.append(mujoco.mj_geomDistance(m,d,pad,g,.2,None))
            if min(distances)<.0005:lo=z
            else:hi=z
        delta=hi-old;d.qpos[payload_q[0]+2]=hi
        for q in payload_q[1:]:d.qpos[q+2]+=delta
        setup['initial_height_adjustment_m']=delta;mujoco.mj_forward(m,d)
    if a.feet_on_floor:
        feet=[g for g in range(m.ngeom) if 'ankle_roll_link' in m.body(int(m.geom_bodyid[g])).name and m.geom_contype[g]]
        floor=[g for g in range(m.ngeom) if m.geom_type[g]==mujoco.mjtGeom.mjGEOM_PLANE][0]
        clearance=min(mujoco.mj_geomDistance(m,d,g,floor,1.,None) for g in feet)
        d.qpos[2]-=clearance-.0005
        for n in ['tray_free','pizza_free','drink_free']:d.qpos[m.joint(n).qposadr[0]+2]-=clearance-.0005
        setup['initial_foot_clearance_corrected_m']=clearance;mujoco.mj_forward(m,d)
    setup['gravity_and_known_load_feedforward']=a.gravity_compensation
    renderer=mujoco.Renderer(m,height=720,width=960);cam=mujoco.MjvCamera();cam.lookat[:]=[.15,0,.65];cam.distance=1.6;cam.azimuth=130;cam.elevation=-20
    report={'requested_speed_m_s':a.speed,'requested_duration_s':a.duration,'command_window_s':[2,a.duration-2],'status':'started','started_at_utc':datetime.now(timezone.utc).isoformat(),'setup':setup,'scope':'hand-supported loaded baseline; scripted velocity; no VLA or PPO residual','gravity':m.opt.gravity.tolist(),'equality_constraints':m.neq,'source_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'sim/k1_hand_carry.py']},'walking_actor_arm_inputs':'nominal position/zero velocity ablation' if a.nominal_arm_observation else 'actual encoders','hand_contact_steps':[0,0],'torso_contact_steps':0,'other_robot_tray_contact_steps':{},'max_payload_relative_xy_m':0.,'max_arm_torque_Nm':0.,'payload_drop':False,'robot_fall':False}
    assert m.neq==0 and m.nq==50 and m.nv==46
    initial_penetration=max([max(0.,-float(c.dist)) for c in d.contact if trayid in [int(m.geom_bodyid[c.geom1]),int(m.geom_bodyid[c.geom2])]] or [0.])
    report['initial_tray_penetration_m']=initial_penetration
    assert initial_penetration<.002, f'Initial tray penetration {initial_penetration}m'
    renderer.update_scene(d,cam);imageio.imwrite(a.output/'initial_before_physics.png',renderer.render())
    import shutil
    for source in [Path(__file__),ROOT/'sim/k1_hand_carry.py']:shutil.copy2(source,a.output/source.name)
    contact_trace=[];contact_gaps=[0,0];report['max_hand_contact_loss_s']=[0.,0.];report['max_tray_tilt_deg']=0.
    rows=[];diagnostics=[];target=initial.copy();torch.set_num_threads(1)
    with imageio.get_writer(a.output/'evaluator.mp4',fps=25,codec='libx264',quality=8) as writer:
      for step in range(round(a.duration/.002)):
        if step%10==0:
            data=ctrl.robot.data;data.joint_pos=torch.from_numpy(d.qpos[qi].astype(np.float32));data.joint_vel=torch.from_numpy(d.qvel[vi].astype(np.float32));data.root_quat_w=torch.from_numpy(d.qpos[3:7].astype(np.float32));data.root_ang_vel_b=torch.from_numpy(d.qvel[3:6].astype(np.float32))
            if a.nominal_arm_observation:
                data.joint_pos[arm]=ctrl.robot.default_joint_pos[arm];data.joint_vel[arm]=0.
            ctrl.vel_command.lin_vel_x=a.speed if 2<d.time<a.duration-2 else 0.
            target=ctrl.policy_step().numpy().copy();target[arm]=initial[arm]
            if not ctrl.is_running:report['robot_fall']=True;break
        tau=kp*(target-d.qpos[qi])-kd*d.qvel[vi]
        if a.gravity_compensation:
            tau[arm]+=d.qfrc_bias[vi[arm]]
            for sign,bid in [(1,handids[0]),(-1,handids[1])]:
                point=d.xpos[bid]+d.xmat[bid].reshape(3,3)@np.array([0,sign*.195,0])
                jp=np.zeros((3,m.nv));jr=np.zeros((3,m.nv));mujoco.mj_jac(m,d,jp,jr,point,bid)
                tau[arm]+=jp[:,vi[arm]].T@np.array([0,0,(.68+.8+.5)*9.81/2])
        d.ctrl[:]=np.clip(tau,-limit,limit)
        mujoco.mj_step(m,d);mujoco.mj_forward(m,d)
        forces=[0.,0.];torso=False;weighted_contact=np.zeros(3);normal_total=0.
        for c in d.contact:
            b1=int(m.geom_bodyid[c.geom1]);b2=int(m.geom_bodyid[c.geom2])
            if trayid not in [b1,b2] or c.dist>0:continue
            other=b2 if b1==trayid else b1
            if other==m.body('trunk').id:torso=True
            if other not in handids and m.body_rootid[other]==m.body('trunk').id:
                name=m.body(other).name;report['other_robot_tray_contact_steps'][name]=report['other_robot_tray_contact_steps'].get(name,0)+1
        # Contact index is explicit: aggregate solved normal contact forces.
        for ci,c in enumerate(d.contact):
            bs=[int(m.geom_bodyid[c.geom1]),int(m.geom_bodyid[c.geom2])]
            if trayid in bs:
                other=bs[1] if bs[0]==trayid else bs[0]
                if other in handids:
                    f=np.zeros(6);mujoco.mj_contactForce(m,d,ci,f);forces[handids.index(other)]+=max(float(f[0]),0);weighted_contact+=max(float(f[0]),0)*c.pos;normal_total+=max(float(f[0]),0)
        for i in range(2):
            report['hand_contact_steps'][i]+=int(forces[i]>.1)
            contact_gaps[i]=0 if forces[i]>.1 else contact_gaps[i]+1
            report['max_hand_contact_loss_s'][i]=max(report['max_hand_contact_loss_s'][i],contact_gaps[i]*.002)
        contact_trace.append([float(d.time),*forces])
        report['torso_contact_steps']+=int(torso);report['max_arm_torque_Nm']=max(report['max_arm_torque_Nm'],float(np.abs(d.ctrl[arm]).max()))
        tpos=d.xpos[trayid];tilt=float(np.rad2deg(np.arccos(np.clip(d.xmat[trayid].reshape(3,3)[2,2],-1,1))))
        report['max_tray_tilt_deg']=max(report['max_tray_tilt_deg'],tilt)
        rtray=d.xmat[trayid].reshape(3,3)
        for name,reference in [('pizza_box',np.array([-.01,.065])),('drink',np.array([0.,-.17]))]:
            relative=rtray.T@(d.xpos[bodies[name]]-tpos);report['max_payload_relative_xy_m']=max(report['max_payload_relative_xy_m'],float(np.linalg.norm(relative[:2]-reference)))
        if step%10==0:diagnostics.append({'t':float(d.time),'command_x_m_s':float(ctrl.vel_command.lin_vel_x),'hand_contact_center':(weighted_contact/normal_total).tolist() if normal_total>0 else None,'arm_error_rad':(target[arm]-d.qpos[qi[arm]]).tolist(),'arm_torque':d.ctrl[arm].tolist(),'hand_normals':[d.xmat[b].reshape(3,3)[:,0].tolist() for b in handids]})
        if step%10==0:rows.append([d.time,*d.qpos[:3],*tpos,tilt,*forces,*d.xpos[bodies['pizza_box']],*d.xpos[bodies['drink']]])
        if step%20==0:
            cam.lookat[:]=[d.qpos[0]+.15,d.qpos[1],.65]
            renderer.update_scene(d,cam);frame=renderer.render();writer.append_data(frame)
            if step==0:imageio.imwrite(a.output/'initial.png',frame)
        if d.qpos[2]<.25:report['robot_fall']=True;break
        if tpos[2]<.35 or min(d.xpos[bodies[n]][2] for n in ['pizza_box','drink'])<tpos[2]-.1:report['payload_drop']=True;break
    renderer.update_scene(d,cam);imageio.imwrite(a.output/'final.png',renderer.render());renderer.close()
    np.savetxt(a.output/'contacts.csv',rows,delimiter=',',header='t,root_x,root_y,root_z,tray_x,tray_y,tray_z,tray_tilt_deg,left_normal_N,right_normal_N,box_x,box_y,box_z,drink_x,drink_y,drink_z',comments='')
    report.update(status='tested',simulated_seconds=float(d.time),physics_steps=step+1,final_tray_xyz=d.xpos[trayid].tolist(),final_root_xyz=d.qpos[:3].tolist(),final_root_speed_m_s=float(np.linalg.norm(d.qvel[:3])),net_forward_m=float(d.qpos[0]))
    np.savetxt(a.output/'contact_forces_500hz.csv',contact_trace,delimiter=',',header='t,left_N,right_N',comments='')
    (a.output/'diagnostics.json').write_text(json.dumps(diagnostics,indent=2))
    report['artifacts']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in a.output.iterdir() if p.is_file()};(a.output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
