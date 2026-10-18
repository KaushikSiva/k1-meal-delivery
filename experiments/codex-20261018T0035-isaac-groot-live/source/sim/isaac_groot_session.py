"""Live Isaac RGB-D/encoder/gyro bridge to the bounded GR00T delivery stack.

The supplied café floor plan and initial pose are operator priors. No simulator
root position, root velocity, object pose or instance mask enters this adapter.
"""
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen
import numpy as np
from autonomy.contracts import CameraFrame,CameraIntrinsics,DeliveryTask,Observation,OccupancyGrid,Pose2D,Provenance,Region
from autonomy.grounding import parse_instruction
from autonomy.executive import ExecutiveConfig
from contracts.robot_telemetry import RobotTelemetry
from deployment.carrying_depth_filter import filter_known_carrying_volume
from deployment.groot_remote_client import LosslessRemoteVLAClient
from deployment.k1_carry_commands import supported_carry_command
from deployment.vla_session import BoundedVLASession
from navigation.follower import FollowerLimits
from navigation.localization import ScanMatchLocalizer
from perception.tabletop import TabletopDetector
from sim.k1_imu import GyroHeadingEstimator
from sim.k1_sensor_observation import SensorCameraGeometry


def cafe_floor_plan():
    """Declared conservative furniture footprints from the designed café plan."""
    grid=OccupancyGrid(np.zeros((73,105),np.uint8),.1,(-1.,-3.6))
    yy,xx=np.indices(grid.data.shape);x=-1+(xx+.5)*.1;y=-3.6+(yy+.5)*.1
    occupied=(x<-.9)|(x>9.25)|(y<-3.45)|(y>3.45)
    for tx in (2.,4.9,7.8):
        for ty in (-2.05,2.05):
            occupied|=(x-tx)**2+(y-ty)**2<.65**2
            for dx,dy in [(-.88,0),(.88,0),(0,.88 if ty>0 else -.88)]:
                occupied|=(np.abs(x-tx-dx)<.3)&(np.abs(y-ty-dy)<.3)
    occupied|=(np.abs(x+.25)<.52)&(np.abs(y+2)<1.05)
    for px,py in [(8.8,3),(8.8,-3),(-.3,3)]:occupied|=(x-px)**2+(y-py)**2<.22**2
    grid.data[occupied]=OccupancyGrid.OCCUPIED
    return grid


class IsaacGR00TSession:
    def __init__(self,joint_names,head_camera,endpoint,output,physics_dt=.002):
        parsed=urlsplit(endpoint)
        if parsed.hostname not in ('127.0.0.1','localhost') or parsed.scheme!='http':
            raise ValueError('GR00T endpoint must be localhost')
        with urlopen(endpoint.rsplit('/',1)[0]+'/health',timeout=10) as response:self.health=json.load(response)
        if self.health.get('optimizer_updates')!=500 or self.health.get('model_id')!='groot-c788024b6205':
            raise ValueError('Expected the audited latest 500-update GR00T checkpoint')
        self.names=tuple(joint_names);self.head=head_camera;self.endpoint=endpoint
        self.output=Path(output);self.output.mkdir(parents=True,exist_ok=True)
        self.dt=physics_dt;self.episode=-1
        model=Path(__file__).resolve().parents[1]/'sim/vendor/booster_assets/robots/K1/K1_22dof.xml'
        self.geometry=SensorCameraGeometry(model)
        self.K=CameraIntrinsics.from_fovy(58,640,480)
        self.reset()

    def reset(self):
        self.episode+=1;self.episode_root=self.output/f'episode-{self.episode:03d}'
        self.episode_root.mkdir(exist_ok=False)
        self.estimator=GyroHeadingEstimator(max_gap_s=self.dt*1.1)
        self.rng=np.random.default_rng(9901)
        grid=cafe_floor_plan()
        self.localizer=ScanMatchLocalizer(grid,Pose2D(1.,0.,0.),max_points=200)
        task=DeliveryTask('deliver the pizza and drink to the table',parse_instruction('deliver the pizza and drink to the table'),0.,120.)
        self.session=BoundedVLASession(task,grid,TabletopDetector(),[Region('dining',(4.9,0.),4.,('dining',))],
            config=ExecutiveConfig(final_speed=.4,approach_speed=.4,search_speed=.4),
            limits=FollowerLimits(v_max=.4,min_walk_cmd=.4,final_accel=.25),deployable=True,
            proposal_policy=LosslessRemoteVLAClient(self.endpoint,timeout_s=5.))
        self.latest=None;self.heading=None;self.previous_heading=None
        self.command=np.zeros(3);self.next_camera=0.;self.last_pose=None;self.frames=0
        self.info=dict(model_id=self.health['model_id'],inference_calls=0,accepted_ticks=0,state='ready',command=[0.,0.,0.])
        (self.episode_root/'metadata.json').write_text(json.dumps(dict(health=self.health,
            prior_initial_pose=[1,0,0],floor_plan='operator-supplied conservative cafe design',
            actor_inputs=['head RGB-D','joint encoders','emulated noisy body gyro','estimated map pose and memory'],
            limits=['first Isaac transfer; not delivery validation','MuJoCo-trained checkpoint','synchronous inference with measured delay applied on control clock']),indent=2)+'\n')

    def sample(self,t,data):
        cpu=lambda a:a.detach().cpu().numpy()
        gyro=cpu(data.root_ang_vel_b[0])+np.array([0,0,.0015])+self.rng.normal(0,.005,3)
        self.latest=RobotTelemetry(t,self.names,cpu(data.joint_pos[0]),cpu(data.joint_vel[0]),gyro,
                                  np.full(3,.005**2),'isaac_encoder_and_body_gyro_emulation')
        self.heading=self.estimator.update(self.latest)

    def control(self,t):
        if self.previous_heading is not None:
            self.localizer.predict([*self.command[:2],0.],.02,scale=.5)
            self.localizer.pose[2]+=self.heading.yaw_rad-self.previous_heading.yaw_rad
            self.localizer.cov[2,2]+=max(0,self.heading.yaw_variance_rad2-self.previous_heading.yaw_variance_rad2)
        self.previous_heading=self.heading
        obs=None
        if t>=self.next_camera-1e-8:
            rgb=np.asarray(self.head.get_rgba())[:,:,:3].astype(np.uint8)
            raw_depth=np.asarray(self.head.get_depth(),np.float32)
            if rgb.shape!=(480,640,3) or raw_depth.size!=480*640:
                raise ValueError(f'Isaac RGB-D buffers unavailable: RGB {rgb.shape}, depth {raw_depth.shape}')
            depth=raw_depth.reshape(480,640).copy()
            depth[(depth<=0)|~np.isfinite(depth)]=np.nan
            transform,height=self.geometry.extrinsics(self.latest,self.heading)
            frame=CameraFrame(t,self.K,transform,rgb=rgb,depth=depth,provenance=Provenance.ESTIMATED)
            frame,mask=filter_known_carrying_volume(frame,self.latest)
            self.localizer.correct(Observation(t,frame,self.localizer.estimate(t)))
            pose=self.localizer.estimate(t);twist=np.zeros(3)
            if self.last_pose is not None:
                old,old_t=self.last_pose;elapsed=t-old_t
                delta=(pose.pose.xy()-old.xy())/elapsed;c,s=np.cos(pose.pose.yaw),np.sin(pose.pose.yaw)
                twist[:2]=np.array([[c,s],[-s,c]])@delta
                twist[2]=np.arctan2(np.sin(pose.pose.yaw-old.yaw),np.cos(pose.pose.yaw-old.yaw))/elapsed
            self.last_pose=pose.pose,t
            obs=Observation(t,frame,pose,twist);obs.assert_deployable()
            if self.frames<3:np.savez_compressed(self.episode_root/f'camera-{self.frames:03d}.npz',rgb=rgb,depth=depth,state_pose=self.localizer.pose)
            self.frames+=1;self.next_camera=t+.2
        self.command=supported_carry_command(self.session.tick(obs,t,.02)) if t>=2 else np.zeros(3)
        if self.session.done:self.command=np.zeros(3)
        follower=self.session.follower
        accepted=sum(c['selected_by']=='vla' for c in follower.control)
        self.info.update(inference_calls=len(follower.calls),accepted_ticks=accepted,state=self.session.executive.state.value,
                         command=self.command.tolist(),last_decision=follower.control[-1]['reason'] if follower.control else 'settling',
                         inference_failures=sum('error' in c for c in follower.calls))
        if obs is not None:
            (self.episode_root/'status.json').write_text(json.dumps(self.info,indent=2)+'\n')
            (self.episode_root/'calls.json').write_text(json.dumps(follower.calls,indent=2)+'\n')
            (self.episode_root/'control.json').write_text(json.dumps(follower.control,indent=2)+'\n')
        return tuple(self.command)
