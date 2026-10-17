"""Sensor-emulated K1 gyro/encoders plus gyro-only relative attitude estimator.

No absolute simulator orientation or position is read. Initial reference is an
explicit level-start assumption. Drift and bias remain; this is not full odometry.
"""
import numpy as np
from contracts.robot_telemetry import RobotTelemetry,RelativeHeading


def _multiply(a,b):
    aw,ax,ay,az=a;bw,bx,by,bz=b
    return np.array([aw*bw-ax*bx-ay*by-az*bz,aw*bx+ax*bw+ay*bz-az*by,
                     aw*by-ax*bz+ay*bw+az*bx,aw*bz+ax*by-ay*bx+az*bw])


class GyroHeadingEstimator:
    """Integrate measured body rates from a declared initial level reference.

    No absolute map yaw is inferred. Users must separately supply/estimate map
    alignment with its own provenance and uncertainty. Covariance is a simple
    declared noise/bias model, not a calibrated hardware confidence guarantee.
    """
    def __init__(self, *, initial_yaw_sigma=.05, bias_bound_rad_s=.002,max_gap_s=.1):
        if min(initial_yaw_sigma,bias_bound_rad_s)<0 or max_gap_s<=0:raise ValueError('Invalid uncertainty/gap')
        self.initial_variance=initial_yaw_sigma**2;self.bias_bound=bias_bound_rad_s;self.max_gap=max_gap_s
        self.q=np.array([1.,0.,0.,0.]);self.last_time=None;self.start_time=None
        self.previous_rate=None;self.noise_variance=0.;self.yaw=0.;self.last_wrapped=0.

    def update(self,sample:RobotTelemetry)->RelativeHeading:
        t=sample.timestamp;rate=sample.angular_velocity_body_rad_s
        if self.last_time is not None:
            dt=t-self.last_time
            if not 0<dt<=self.max_gap:raise ValueError('Nonmonotonic timestamp or gyro gap; explicit estimator reset required')
            omega=.5*(rate+self.previous_rate)
            angle=float(np.linalg.norm(omega)*dt)
            dq=np.r_[np.cos(angle/2),omega*dt*(np.sin(angle/2)/angle if angle>1e-12 else .5)]
            self.q=_multiply(self.q,dq);self.q/=np.linalg.norm(self.q)
            w,x,y,z=self.q
            wrapped=float(np.arctan2(2*(w*z+x*y),1-2*(y*y+z*z)))
            self.yaw+=float(np.arctan2(np.sin(wrapped-self.last_wrapped),np.cos(wrapped-self.last_wrapped)))
            self.last_wrapped=wrapped
            self.noise_variance+=float(sample.gyro_variance_rad2_s2.max())*dt*dt
        else:self.start_time=t
        self.last_time=t;self.previous_rate=rate.copy()
        elapsed=t-self.start_time
        variance=self.initial_variance+self.noise_variance+(self.bias_bound*elapsed)**2
        return RelativeHeading(t,self.yaw,variance,tuple(self.q.tolist()),elapsed)


class MujocoTelemetryReader:
    """Read the pinned native gyro sensor and named hinge encoders only.

    Explicit optional noise is added here; do not assume the XML sensor's noise
    attribute is automatically sampled by the installed MuJoCo runtime.
    """
    def __init__(self,model,joint_names, *, noise_std_rad_s=.005,bias_rad_s=(0.,0.,0.),seed=0):
        import mujoco
        self.names=tuple(joint_names)
        self.qpos_ids=[];self.qvel_ids=[]
        for name in self.names:
            j=model.joint(name)
            if int(j.type[0])!=int(mujoco.mjtJoint.mjJNT_HINGE):raise ValueError('Only named hinge encoders allowed')
            self.qpos_ids.append(int(j.qposadr[0]));self.qvel_ids.append(int(j.dofadr[0]))
        s=model.sensor('angular-velocity')
        if int(s.type[0])!=int(mujoco.mjtSensor.mjSENS_GYRO) or int(s.dim[0])!=3:
            raise ValueError('Expected native three-axis gyro sensor')
        site_id=int(s.objid[0]);site=model.site(site_id)
        if int(site.bodyid[0])!=model.body('trunk').id or not np.allclose(site.quat,[1,0,0,0]):
            raise ValueError('Gyro site must be aligned with trunk body axes')
        self.gyro_adr=int(s.adr[0]);self.noise=float(noise_std_rad_s);self.bias=np.array(bias_rad_s,float)
        if self.noise<0 or self.bias.shape!=(3,) or not np.isfinite(self.bias).all():raise ValueError('Invalid gyro noise/bias')
        self.rng=np.random.default_rng(seed)

    def read(self,data):
        gyro=np.asarray(data.sensordata[self.gyro_adr:self.gyro_adr+3]).copy()
        gyro+=self.bias+self.rng.normal(0,self.noise,3)
        return RobotTelemetry(float(data.time),self.names,np.asarray(data.qpos)[self.qpos_ids],
            np.asarray(data.qvel)[self.qvel_ids],gyro,np.full(3,self.noise**2),
            source='mujoco_native_gyro_and_hinge_encoders_with_explicit_noise')


class MujocoHeadingAdapter:
    """Guard against the verified K1 control-rate gyro aliasing failure.

    Call sample() once initially and after EVERY physics step. Consumers may
    downsample the resulting integrated heading, never the raw endpoint gyro.
    """
    def __init__(self,model,joint_names,**sensor_options):
        self.reader=MujocoTelemetryReader(model,joint_names,**sensor_options)
        self.estimator=GyroHeadingEstimator(max_gap_s=float(model.opt.timestep)*1.01)
        self.latest_telemetry=None;self.latest_heading=None

    def sample(self,data):
        telemetry=self.reader.read(data)
        heading=self.estimator.update(telemetry)
        self.latest_telemetry=telemetry;self.latest_heading=heading
        return heading
