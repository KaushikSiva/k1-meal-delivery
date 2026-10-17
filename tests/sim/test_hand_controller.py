import numpy as np
import mujoco
from sim.k1_hand_carry import make_model, ARM_POSE
from sim.k1_hand_controller import HandSensorController
from sim.run_k1_baseline import K1WalkTaskCfg, DEPLOY
from sim.k1_observation import sensor_spec


def test_free_payload_never_enters_actor_joint_vector(tmp_path):
    path=tmp_path/'hand.xml';make_model(path,handle_seats=True)
    cfg=K1WalkTaskCfg();cfg.mujoco.log_states=None;cfg.policy.device='cpu'
    cfg.policy.checkpoint_path=str(DEPLOY/'tasks/locomotion/robots/k1/models/k1_walk.pt')
    ctrl=HandSensorController(cfg,sensor_spec(path))
    ctrl.update_state()
    assert ctrl.robot.data.joint_pos.shape == (22,)
    assert ctrl.robot.data.joint_vel.shape == (22,)
    before=ctrl.robot.data.joint_pos.clone()
    q=ctrl.mj_model.joint('pizza_free').qposadr[0]
    ctrl.mj_data.qpos[q:q+3] += [4.,2.,1.]
    mujoco.mj_forward(ctrl.mj_model,ctrl.mj_data);ctrl.update_state()
    assert (before==ctrl.robot.data.joint_pos).all()
    # The nominal-arm actor features do not rewrite actual sensor telemetry.
    for n,v in ARM_POSE.items():
        i=cfg.robot.joint_names.index(n)
        assert np.isclose(ctrl.imu.latest_telemetry.joint_position_rad[i],v)
        assert np.isclose(ctrl.robot.data.joint_pos[i],ctrl.robot.default_joint_pos[i])
