import numpy as np
from deployment.k1_carry_commands import supported_carry_command


def test_uncertainty_speed_cap_is_never_overridden():
    assert np.allclose(supported_carry_command([.15,0,.1]),[0,0,.1])
    assert np.allclose(supported_carry_command([.4,0,.6]),[.4,0,.25])
    for cmd in np.random.default_rng(42).uniform(-.5,.5,(100,3)):
        out=supported_carry_command(cmd)
        assert np.linalg.norm(out[:2])<=np.linalg.norm(cmd[:2])+1e-12
        assert abs(out[2])<=abs(cmd[2])+1e-12
