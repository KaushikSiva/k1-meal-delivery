from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from contracts.robot_telemetry import RobotTelemetry,RelativeHeading
from sim.k1_imu import GyroHeadingEstimator,MujocoTelemetryReader,MujocoHeadingAdapter


def packet(t,rate=(0.,0.,.4)):
    return RobotTelemetry(t,('joint',),np.zeros(1),np.zeros(1),np.array(rate),np.full(3,.005**2),'test_fixture')


def test_gyro_heading_crosses_pi_and_grows_uncertainty_without_pose():
    est=GyroHeadingEstimator()
    for i in range(1001):result=est.update(packet(i*.01))
    assert result.yaw_rad==pytest.approx(4.,abs=1e-10)
    assert result.yaw_variance_rad2>.05**2
    with pytest.raises(ValueError,match='timestamp'):est.update(packet(9.))
    with pytest.raises(ValueError,match='gap'):est.update(packet(11.))


def test_full_body_rotation_order_and_validation():
    est=GyroHeadingEstimator()
    # Constant body rotation about x should yield roll, not yaw.
    for i in range(101):r=est.update(packet(i*.01,(.3,0,0)))
    np.testing.assert_allclose(r.quaternion_reference_body,[np.cos(.15),np.sin(.15),0,0],atol=1e-12)
    assert r.yaw_rad==pytest.approx(0.)
    with pytest.raises(ValueError):packet(float('nan'))
    original=np.zeros(1);p=RobotTelemetry(0,('j',),original,original,np.zeros(3),np.zeros(3),'fixture')
    original[0]=10;assert p.joint_position_rad[0]==0
    with pytest.raises(ValueError):p.joint_position_rad[0]=2
    with pytest.raises(ValueError):RelativeHeading(1.,float('nan'),.1,(1,0,0,0),1.)
    with pytest.raises(ValueError):RelativeHeading(1.,0.,.1,(0,0,0,0),1.)
    with pytest.raises(ValueError):RelativeHeading(1.,0.,-.1,(1,0,0,0),1.)


def test_native_k1_gyro_reader_ignores_free_base_pose():
    mujoco=pytest.importorskip('mujoco')
    source=Path(__file__).resolve().parents[2]/'sim/vendor/booster_assets/robots/K1/K1_22dof.xml'
    model=mujoco.MjModel.from_xml_path(str(source));data=mujoco.MjData(model)
    names=[model.joint(i).name for i in range(model.njnt) if int(model.jnt_type[i])==int(mujoco.mjtJoint.mjJNT_HINGE)]
    reader=MujocoTelemetryReader(model,names,noise_std_rad_s=0)
    data.qvel[3:6]=[.1,-.2,.3];mujoco.mj_forward(model,data)
    sensed=reader.read(data)
    np.testing.assert_allclose(sensed.angular_velocity_body_rad_s,[.1,-.2,.3],atol=1e-12)
    # Copy only sensor/joint arrays; poison privileged free-base coordinates.
    limited=SimpleNamespace(time=data.time,sensordata=data.sensordata.copy(),qpos=data.qpos.copy(),qvel=data.qvel.copy())
    limited.qpos[:7]=np.nan;limited.qvel[:6]=np.nan
    again=reader.read(limited)
    np.testing.assert_allclose(again.angular_velocity_body_rad_s,sensed.angular_velocity_body_rad_s)
    assert np.isfinite(again.joint_position_rad).all() and len(again.joint_names)==22


def test_native_adapter_rejects_control_rate_subsampling():
    mujoco=pytest.importorskip('mujoco')
    source=Path(__file__).resolve().parents[2]/'sim/vendor/booster_assets/robots/K1/K1_22dof.xml'
    model=mujoco.MjModel.from_xml_path(str(source));data=mujoco.MjData(model)
    names=[model.joint(i).name for i in range(model.njnt) if int(model.jnt_type[i])==int(mujoco.mjtJoint.mjJNT_HINGE)]
    adapter=MujocoHeadingAdapter(model,names)
    mujoco.mj_forward(model,data);adapter.sample(data)
    mujoco.mj_step(model,data);mujoco.mj_forward(model,data);adapter.sample(data)
    for _ in range(10):mujoco.mj_step(model,data)
    mujoco.mj_forward(model,data)
    with pytest.raises(ValueError,match='gap'):adapter.sample(data)
