from pathlib import Path
import numpy as np
import pytest
from contracts.robot_telemetry import RobotTelemetry,RelativeHeading
from deployment.k1_leg_estimator import K1LegEstimator


def test_leg_height_and_motion_use_only_named_encoders_and_imu():
    pytest.importorskip('mujoco')
    root=Path(__file__).resolve().parents[2]
    est=K1LegEstimator(root/'sim/vendor/booster_assets/robots/K1/K1_22dof.xml')
    import json
    cfg=json.loads((root/'sim/k1_isaac_nominal.json').read_text())['joints']
    names=tuple(reversed(est.names));q=np.array([cfg[n]['position'] for n in names])
    p=RobotTelemetry(1.,names,q,np.zeros(22),np.zeros(3),np.zeros(3),'synthetic_encoders')
    h=RelativeHeading(1.,0.,.01,(1.,0.,0.,0.),1.)
    result=est.estimate(p,h)
    assert .5<result.trunk_height_m<.65
    np.testing.assert_allclose(result.velocity_base_m_s,0.,atol=1e-12)
    assert set(result.stance_candidates)=={'left','right'}
    # Absolute/global yaw is immaterial to local height and velocity.
    h2=RelativeHeading(1.,2.,.01,(np.cos(1),0,0,np.sin(1)),1.)
    r2=est.estimate(p,h2)
    assert r2.trunk_height_m==pytest.approx(result.trunk_height_m)
    np.testing.assert_allclose(r2.velocity_base_m_s,result.velocity_base_m_s,atol=1e-10)
    with pytest.raises(ValueError,match='Unsynchronized'):
        est.estimate(p,RelativeHeading(2.,0.,.01,(1.,0.,0.,0.),1.))
