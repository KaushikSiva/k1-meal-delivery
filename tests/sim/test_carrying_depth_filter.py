import numpy as np
from types import SimpleNamespace
from deployment.carrying_depth_filter import mask_depth_in_volume


def test_only_observed_points_inside_load_volume_are_invalidated():
    # Optical forward -> trunk forward. Camera is at torso-relative height .2m.
    T=np.array([[0,0,1,0],[-1,0,0,0],[0,-1,0,.2],[0,0,0,1]],float)
    K=SimpleNamespace(cx=1.,cy=0.,fx=10.,fy=10.)
    raw=np.array([[.3,2.,np.nan]],np.float32)
    filtered,mask=mask_depth_in_volume(raw,K,T)
    assert mask.tolist()==[[True,False,False]]
    assert np.isnan(filtered[0,0]) and filtered[0,1]==2. and np.isnan(filtered[0,2])
    assert raw[0,0]==np.float32(.3)  # preserve raw evidence; never synthesize background


def test_no_blanket_near_range_mask():
    T=np.eye(4);T[2,3]=.2
    K=SimpleNamespace(cx=0.,cy=0.,fx=1.,fy=1.)
    # Point directly above the trunk, outside the forward load profile.
    depth,mask=mask_depth_in_volume(np.array([[.1]],np.float32),K,T)
    assert not mask.any() and np.isfinite(depth).all()
