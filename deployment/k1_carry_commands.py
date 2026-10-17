"""Conservative carrying limits around a walking actor with a measured deadband."""
import numpy as np


def supported_carry_command(command, min_translation=.30, max_yaw_rate=.25):
    """Never increase requested speed. Hold translations the actor cannot track.

    These are development priors from the declared K1 simulator tests, not a
    hardware calibration. The executive's lower speed caps remain authoritative:
    an uncertainty-limited request below the walking band results in a hold.
    """
    value=np.asarray(command,float).copy()
    if value.shape!=(3,) or not np.isfinite(value).all():raise ValueError('Expected finite vx/vy/wz')
    if min_translation<0 or max_yaw_rate<0:raise ValueError('Invalid carrying limits')
    if np.linalg.norm(value[:2])<min_translation:value[:2]=0.
    value[2]=np.clip(value[2],-max_yaw_rate,max_yaw_rate)
    return value
