"""Sensor boundary checks for the Isaac GR00T bridge; not delivery evidence."""
from types import SimpleNamespace as NS
import numpy as np
import torch
from sim.isaac_groot_session import IsaacGR00TSession,cafe_floor_plan
from sim.k1_imu import GyroHeadingEstimator


def test_isaac_telemetry_reads_only_encoders_and_body_gyro():
    class Sensors:
        joint_pos=torch.zeros(1,22)
        joint_vel=torch.zeros(1,22)
        root_ang_vel_b=torch.zeros(1,3)
        def __getattr__(self,name):raise AssertionError('Unexpected sensor access: '+name)
    bridge=IsaacGR00TSession.__new__(IsaacGR00TSession)
    bridge.names=tuple('joint'+str(i) for i in range(22))
    bridge.rng=np.random.default_rng(0);bridge.estimator=GyroHeadingEstimator(max_gap_s=.0021)
    bridge.sample(0.,Sensors());bridge.sample(.002,Sensors())
    assert bridge.latest.timestamp==.002 and bridge.heading.elapsed_s==.002
    assert bridge.latest.joint_position_rad.shape==(22,)


def test_declared_floor_plan_keeps_initial_aisle_free_and_furniture_occupied():
    grid=cafe_floor_plan()
    assert grid.data[grid.world_to_cell((1,0))]==grid.FREE
    assert grid.data[grid.world_to_cell((4.9,2.05))]==grid.OCCUPIED
    assert grid.data[grid.world_to_cell((-.25,-2.))]==grid.OCCUPIED
