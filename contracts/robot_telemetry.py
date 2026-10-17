"""Sensor-only telemetry proposal for the existing autonomy integration.

No simulator pose, world velocity, contact IDs or payload truth belongs here.
MEASURED includes explicitly labeled sensor emulation, not hardware evidence.
"""
from dataclasses import dataclass
import numpy as np
from autonomy.contracts import Provenance


@dataclass(frozen=True)
class RobotTelemetry:
    timestamp: float
    joint_names: tuple[str, ...]
    joint_position_rad: np.ndarray
    joint_velocity_rad_s: np.ndarray
    angular_velocity_body_rad_s: np.ndarray
    gyro_variance_rad2_s2: np.ndarray
    source: str
    provenance: Provenance = Provenance.MEASURED

    def __post_init__(self):
        object.__setattr__(self, 'joint_names', tuple(self.joint_names))
        if not np.isfinite(self.timestamp) or self.timestamp < 0:
            raise ValueError('Telemetry timestamp must be finite and nonnegative')
        if len(set(self.joint_names))!=len(self.joint_names) or not self.joint_names:
            raise ValueError('Joint names must be unique and nonempty')
        if self.provenance!=Provenance.MEASURED:
            raise ValueError('Raw telemetry requires measured sensor provenance')
        for name,shape in [('joint_position_rad',(len(self.joint_names),)),
                           ('joint_velocity_rad_s',(len(self.joint_names),)),
                           ('angular_velocity_body_rad_s',(3,)),('gyro_variance_rad2_s2',(3,))]:
            a=np.array(getattr(self,name),dtype=float,copy=True)
            if a.shape!=shape or not np.isfinite(a).all():raise ValueError(f'Invalid {name}')
            if name=='gyro_variance_rad2_s2' and np.any(a<0):raise ValueError('Negative gyro variance')
            a.setflags(write=False);object.__setattr__(self,name,a)


@dataclass(frozen=True)
class RelativeHeading:
    timestamp: float
    yaw_rad: float  # unwrapped; zero is initial reference, not map north
    yaw_variance_rad2: float
    quaternion_reference_body: tuple[float,float,float,float]  # wxyz
    elapsed_s: float
    source: str = 'body_gyro_integration'
    provenance: Provenance = Provenance.ESTIMATED

    def __post_init__(self):
        values = [self.timestamp, self.yaw_rad, self.yaw_variance_rad2, self.elapsed_s]
        if not np.isfinite(values).all() or min(self.timestamp,self.yaw_variance_rad2,self.elapsed_s)<0:
            raise ValueError('Invalid heading timestamp, angle or uncertainty')
        q = np.asarray(self.quaternion_reference_body, float)
        if q.shape != (4,) or not np.isfinite(q).all() or abs(np.linalg.norm(q)-1.) > 1e-6:
            raise ValueError('Heading quaternion must be finite and normalized')
        if self.provenance != Provenance.ESTIMATED:
            raise ValueError('Relative heading requires estimated provenance')
        object.__setattr__(self, 'quaternion_reference_body', tuple(float(v) for v in q))
