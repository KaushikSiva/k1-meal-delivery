import numpy as np
import pytest
from deployment.hand_residual import hand_observation
from training.hand_carry_env import HandCarryEnv


def test_gravity_observation_has_no_absolute_yaw():
    args=[np.zeros(3),np.array([1.,0,0,0]),np.zeros(22),np.zeros(22),np.zeros(22),np.zeros(3),np.zeros(12)]
    a=hand_observation(*args)
    args[1]=np.array([np.cos(.7),0,0,np.sin(.7)])
    np.testing.assert_allclose(hand_observation(*args),a,atol=1e-7)
    args[1]=np.zeros(4)
    with pytest.raises(ValueError):hand_observation(*args)


def test_world_translation_and_linear_velocity_do_not_enter_residual(tmp_path):
    env=HandCarryEnv(tmp_path)
    a=env.reset(command=[0,0,.15],yaw=.12)
    env.ctrl.mj_data.qpos[:2]+=[20.,-40.]
    env.ctrl.mj_data.qvel[:3]=[99.,-88.,77.]
    np.testing.assert_array_equal(env.observe(),a)
    with pytest.raises(ValueError):env.step(np.full(12,.5))
