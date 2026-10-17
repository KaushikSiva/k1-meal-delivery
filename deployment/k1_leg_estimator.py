"""Provisional K1 leg kinematics estimator from encoders and integrated IMU.

Dedicated FK model only: no simulator pose, velocity or contact state is accepted.
Assumes a level floor and at least one non-slipping stance foot. Not hardware
validated; flight, stairs, slip and inaccurate geometry invalidate the estimate.
"""
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from autonomy.contracts import Provenance
from contracts.robot_telemetry import RobotTelemetry,RelativeHeading


@dataclass(frozen=True)
class LegEstimate:
    timestamp: float
    velocity_base_m_s: np.ndarray  # gravity-aligned, yaw-relative base
    trunk_height_m: float
    trunk_roll_rad: float
    trunk_pitch_rad: float
    stance_candidates: tuple[str,...]
    velocity_sigma_m_s: float = .15  # provisional floor, not a calibration result
    height_sigma_m: float = .03
    provenance: Provenance = Provenance.ESTIMATED


class K1LegEstimator:
    def __init__(self,model_path:Path):
        import mujoco
        self.mujoco=mujoco
        self.model=mujoco.MjModel.from_xml_path(str(model_path));self.data=mujoco.MjData(self.model)
        self.names=tuple(self.model.joint(i).name for i in range(self.model.njnt)
                         if int(self.model.jnt_type[i])==int(mujoco.mjtJoint.mjJNT_HINGE))
        self.qpos=np.array([int(self.model.joint(n).qposadr[0]) for n in self.names])
        self.dofs=np.array([int(self.model.joint(n).dofadr[0]) for n in self.names])
        self.feet=[]
        for side in ('left','right'):
            body=self.model.body(side+'_ankle_roll_link').id
            ids=[i for i in range(self.model.ngeom) if self.model.geom_bodyid[i]==body
                 and self.model.geom_type[i]==mujoco.mjtGeom.mjGEOM_BOX and self.model.geom_contype[i]!=0]
            if len(ids)!=1:raise ValueError('Expected one collision sole box per foot')
            self.feet.append((side,body,ids[0]))

    def estimate(self,telemetry:RobotTelemetry,heading:RelativeHeading)->LegEstimate:
        if abs(telemetry.timestamp-heading.timestamp)>1e-6:raise ValueError('Unsynchronized telemetry/attitude')
        if set(telemetry.joint_names)!=set(self.names):raise ValueError('Expected complete K1 joint encoders')
        order=[telemetry.joint_names.index(n) for n in self.names]
        q=np.asarray(heading.quaternion_reference_body,float);q/=np.linalg.norm(q)
        w,x,y,z=q
        yaw=np.arctan2(2*(w*z+x*y),1-2*(y*y+z*z))
        # Remove relative yaw: height/contact geometry uses a gravity-aligned frame.
        from sim.k1_imu import _multiply
        q=_multiply([np.cos(-yaw/2),0,0,np.sin(-yaw/2)],q)
        self.data.qpos[:3]=0.;self.data.qpos[3:7]=q
        self.data.qpos[self.qpos]=telemetry.joint_position_rad[order]
        self.mujoco.mj_kinematics(self.model,self.data);self.mujoco.mj_comPos(self.model,self.data)
        trunk=self.model.body('trunk').id;R=self.data.xmat[trunk].reshape(3,3)
        roll=float(np.arctan2(R[2,1],R[2,2]));pitch=float(np.arcsin(np.clip(-R[2,0],-1,1)))
        omega=R@telemetry.angular_velocity_body_rad_s
        candidates=[]
        for side,body,geom in self.feet:
            half=self.model.geom_size[geom]
            corners=np.array([[a*half[0],b*half[1],-half[2]] for a in (-1,1) for b in (-1,1)])
            world=corners@self.data.geom_xmat[geom].reshape(3,3).T+self.data.geom_xpos[geom]
            low=world[:,2].min();point=world[world[:,2]<=low+.002].mean(0)
            J=np.zeros((3,self.model.nv));Jr=np.zeros_like(J)
            self.mujoco.mj_jac(self.model,self.data,J,Jr,point,body)
            velocity=-(np.cross(omega,point)+J[:,self.dofs]@telemetry.joint_velocity_rad_s[order])
            candidates.append((side,float(low),velocity))
        lowest=min(c[1] for c in candidates)
        stance=[c for c in candidates if c[1]<=lowest+.01]
        velocity=np.mean([c[2] for c in stance],axis=0)
        height=-lowest
        if not np.isfinite(velocity).all() or not .2<height<.9:raise ValueError('Implausible leg estimate')
        return LegEstimate(telemetry.timestamp,velocity,height,roll,pitch,tuple(c[0] for c in stance))
