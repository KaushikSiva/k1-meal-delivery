"""Real pinned policy/model checks, not hardware or task-success tests."""

import unittest

import numpy as np
import torch

from sim.run_k1_baseline import DEPLOY, K1WalkTaskCfg, ScriptedCommandController


class K1PolicyTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)
        cfg = K1WalkTaskCfg()
        cfg.policy.checkpoint_path = str(DEPLOY / "tasks/locomotion/robots/k1/models/k1_walk.pt")
        self.controller = ScriptedCommandController(cfg)
        self.controller.update_state()
        self.controller.start()
        self.addCleanup(self.controller.stop)

    def test_world_position_and_linear_velocity_do_not_enter_actor(self):
        c = self.controller
        before = c.policy.compute_observation().clone()
        first_action = c.policy_step().clone()
        c.policy.reset()
        c.robot.data.root_pos_w[:] = torch.tensor([99., -7., 30.])
        c.robot.data.root_lin_vel_b[:] = torch.tensor([-10., 7., 8.])
        torch.testing.assert_close(c.policy.compute_observation(), before, rtol=0, atol=0)
        torch.testing.assert_close(c.policy_step(), first_action, rtol=0, atol=0)

    def test_velocity_command_reaches_actor_unchanged(self):
        c = self.controller
        c.vel_command.lin_vel_x = .2
        c.vel_command.lin_vel_y = -.1
        c.vel_command.ang_vel_yaw = .3
        obs = c.policy.compute_observation()
        self.assertEqual(obs.numel(), 69)
        torch.testing.assert_close(obs[6:9], torch.tensor([.2, -.1, .3]))

    def test_policy_advances_real_physics_with_finite_joint_targets(self):
        c = self.controller
        for _ in range(5):
            c.update_state()
            targets = c.policy_step()
            self.assertEqual(tuple(targets.shape), (22,))
            self.assertTrue(torch.isfinite(targets).all())
            c.ctrl_step(targets)
        self.assertAlmostEqual(c.mj_data.time, .1)
        self.assertTrue(np.isfinite(c.mj_data.qpos).all())
        self.assertTrue((np.abs(c.mj_data.ctrl) <= c.robot.effort_limit.numpy() + 1e-6).all())


if __name__ == "__main__":
    unittest.main()
