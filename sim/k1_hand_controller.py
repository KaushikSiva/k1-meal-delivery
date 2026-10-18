"""Free hand-supported load behind the existing sensor navigation controller API."""
import numpy as np
import mujoco
import torch
from sim.run_k1_baseline import ScriptedCommandController
from sim.k1_hand_carry import ARM_POSE
from sim.k1_imu import MujocoHeadingAdapter


class HandSensorController(ScriptedCommandController):
    def __init__(self, cfg, spec, start=(0.,0.,0.), seed=8201, head_pitch=0.,
                 load_mass_kg=1.98, nominal_arm_observation=True):
        if not np.isfinite(load_mass_kg) or load_mass_kg<0:
            raise ValueError('Expected a finite nonnegative supported load mass')
        self.load_mass_kg=float(load_mass_kg)
        self.nominal_arm_observation=bool(nominal_arm_observation)
        super().__init__(cfg)
        self.mj_model = spec.compile()
        m = self.mj_model
        m.opt.timestep = cfg.mujoco.physics_dt
        self.mj_data = d = mujoco.MjData(m)
        names = cfg.robot.joint_names
        self.qi = np.array([m.joint(n).qposadr[0] for n in names])
        self.vi = np.array([m.joint(n).dofadr[0] for n in names])
        assert [m.joint(int(m.actuator_trnid[i,0])).name for i in range(m.nu)] == names
        assert m.neq == 0 and m.nq == 50
        self.head_pitch=float(head_pitch);self.head_index=names.index('aahead_pitch_joint')
        self.arm = np.array([names.index(n) for n in ARM_POSE])
        self.arm_targets = np.array([ARM_POSE[names[i]] for i in self.arm])
        d.qpos[self.qi] = self.robot.default_joint_pos.numpy()
        d.qpos[self.qi[self.arm]] = self.arm_targets
        d.qpos[self.qi[self.head_index]]=self.head_pitch
        d.qpos[:3] = [*start[:2], .6-.05238523380879767]
        d.qpos[3:7] = [np.cos(start[2]/2),0,0,np.sin(start[2]/2)]
        c,s = np.cos(start[2]),np.sin(start[2]); R = np.array([[c,-s],[s,c]])
        for joint in ['tray_free','pizza_free','drink_free']:
            q = m.joint(joint).qposadr[0]
            d.qpos[q:q+2] = R @ d.qpos[q:q+2] + start[:2]
            d.qpos[q+2] += .02097352623939508-.05238523380879767
            d.qpos[q+3:q+7] = d.qpos[3:7]
        self.kp = self.robot.joint_stiffness.numpy().copy()
        self.kd = self.robot.joint_damping.numpy().copy()
        self.kp[self.arm] = 80.; self.kd[self.arm] = 3.
        self.limit = self.robot.effort_limit.numpy()
        self.tray = m.body('free_tray').id
        self.hands = [m.body(side+'_elbow_yaw_link').id for side in ['left','right']]
        self.room_geom_ids = {i for i in range(m.ngeom) if m.geom(i).name.startswith('room_object_')}
        self.collision_pairs = set(); self.collision_contact_steps = 0
        self.hand_metrics = dict(physics_steps=0, hand_contact_steps=[0,0],
            max_hand_contact_loss_s=[0.,0.], other_robot_contact_steps={},
            max_arm_torque_Nm=0., max_tray_tilt_deg=0., max_payload_shift_m=0.,
            payload_drop=False, equality_constraints=0, torque_limit_Nm=14.)
        self.gaps = [0,0]; self.payload_rows = []
        mujoco.mj_forward(m,d)
        self.imu = MujocoHeadingAdapter(m,names,noise_std_rad_s=.005,bias_rad_s=(0,0,.0015),seed=seed)
        self.imu.sample(d)

    def update_state(self):
        # Called by the parent constructor before our payload model is installed.
        if not hasattr(self,'qi'):return super().update_state()
        d = self.mj_data; dst = self.robot.data
        dst.joint_pos = torch.from_numpy(d.qpos[self.qi].astype(np.float32))
        dst.joint_vel = torch.from_numpy(d.qvel[self.vi].astype(np.float32))
        dst.root_quat_w = torch.from_numpy(d.qpos[3:7].astype(np.float32))
        dst.root_ang_vel_b = torch.from_numpy(d.qvel[3:6].astype(np.float32))
        # This explicit actor ablation never changes physical encoder telemetry.
        if self.nominal_arm_observation:
            dst.joint_pos[self.arm] = self.robot.default_joint_pos[self.arm]
            dst.joint_vel[self.arm] = 0.

    def ctrl_step(self, targets):
        target = targets.detach().cpu().numpy().copy(); target[self.arm] = self.arm_targets;target[self.head_index]=self.head_pitch
        m,d = self.mj_model,self.mj_data
        for _ in range(self.decimation):
            tau = self.kp*(target-d.qpos[self.qi])-self.kd*d.qvel[self.vi]
            tau[self.arm] += d.qfrc_bias[self.vi[self.arm]]
            for sign,bid in [(1,self.hands[0]),(-1,self.hands[1])]:
                point = d.xpos[bid]+d.xmat[bid].reshape(3,3)@np.array([0.,sign*.195,0.])
                jp,jr = np.zeros((3,m.nv)),np.zeros((3,m.nv))
                mujoco.mj_jac(m,d,jp,jr,point,bid)
                tau[self.arm] += jp[:,self.vi[self.arm]].T@np.array([0.,0.,self.load_mass_kg*9.81/2])
            d.ctrl[:] = np.clip(tau,-self.limit,self.limit)
            mujoco.mj_step(m,d); mujoco.mj_forward(m,d); self.imu.sample(d)
            forces = [0.,0.]; hit = False; others = set()
            for ci,contact in enumerate(d.contact):
                if contact.dist>0:continue
                gs = {int(contact.geom1),int(contact.geom2)}
                if gs & self.room_geom_ids and not gs <= self.room_geom_ids:
                    self.collision_pairs.add(tuple(sorted(gs))); hit=True
                bs = [int(m.geom_bodyid[g]) for g in [contact.geom1,contact.geom2]]
                if self.tray not in bs:continue
                other = bs[1] if bs[0]==self.tray else bs[0]
                if other in self.hands:
                    force=np.zeros(6);mujoco.mj_contactForce(m,d,ci,force)
                    forces[self.hands.index(other)] += max(float(force[0]),0.)
                elif m.body_rootid[other]==m.body('trunk').id:others.add(m.body(other).name)
            self.collision_contact_steps += int(hit)
            h=self.hand_metrics;h['physics_steps']+=1
            for name in others:h['other_robot_contact_steps'][name]=h['other_robot_contact_steps'].get(name,0)+1
            for i in range(2):
                h['hand_contact_steps'][i]+=int(forces[i]>.1)
                self.gaps[i]=0 if forces[i]>.1 else self.gaps[i]+1
                h['max_hand_contact_loss_s'][i]=max(h['max_hand_contact_loss_s'][i],self.gaps[i]*m.opt.timestep)
            h['max_arm_torque_Nm']=max(h['max_arm_torque_Nm'],float(np.abs(d.ctrl[self.arm]).max()))
            tp=d.xpos[self.tray];tr=d.xmat[self.tray].reshape(3,3)
            tilt=float(np.degrees(np.arccos(np.clip(tr[2,2],-1,1))))
            h['max_tray_tilt_deg']=max(h['max_tray_tilt_deg'],tilt)
            shifts=[]
            for name,reference in [('pizza_box',[-.01,.065]),('drink',[0.,-.17])]:
                rel=tr.T@(d.xpos[m.body(name).id]-tp)
                shift=float(np.linalg.norm(rel[:2]-reference));shifts.append(shift)
                h['max_payload_shift_m']=max(h['max_payload_shift_m'],shift)
                h['payload_drop'] |= bool(rel[2]<-.1)
            h['payload_drop'] |= bool(tp[2]<.35)
            if h['physics_steps']%10==0:self.payload_rows.append([float(d.time),*tp,tilt,*forces,*shifts])
