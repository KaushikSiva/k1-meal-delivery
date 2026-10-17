"""Check real saved Isaac RGB-D against independent metric room geometry.

Requires the ignored capture data. This is sensor/transform evidence, not robot
localization, calibrated hardware, general detector accuracy or delivery evidence.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
import pytest

CAPTURE = Path(__file__).resolve().parents[2] / 'experiments/codex-20261017T2019-cafe-rgbd'
NAMES = ['table1_1p5', 'table1_2p5', 'table3_2p0', 'table6_2p8', 'counter_head_height']


@pytest.mark.parametrize('name', NAMES)
def test_real_depth_and_cv_transform_reconstruct_known_surfaces(name):
    p = CAPTURE/(name+'.npz')
    if not p.exists():
        pytest.skip('real GPU capture artifact not available')
    manifest = json.loads((CAPTURE/'manifest.json').read_text())
    assert hashlib.sha256(p.read_bytes()).hexdigest() == manifest['artifacts'][p.name]['sha256']
    with np.load(p, allow_pickle=False) as obs:
        K, T, d = obs['K'], obs['T_world_camera'], obs['depth']
        assert str(obs['provenance']) == 'sim_privileged'
        assert str(obs['depth_convention']) == 'optical_z'
        assert obs['rgb'].shape == (480, 640, 3) and d.shape == (480, 640)
        np.testing.assert_allclose(T[:3,:3].T @ T[:3,:3], np.eye(3), atol=1e-6)
        assert np.linalg.det(T[:3,:3]) == pytest.approx(1, abs=1e-6)
        assert T[2,3] == pytest.approx(.9, abs=1e-6)
        assert T[2,2] == pytest.approx(-np.sin(np.deg2rad(15)), abs=1e-6)
        # Independent ray intersection against modeled surfaces. Counter view
        # straddles its lower front face and floor; do not call both floor.
        v,u=np.mgrid[440:461:5,310:331:5]
        pixels=np.stack([u.ravel(),v.ravel(),np.ones(u.size)])
        points=T[:3,:3] @ (np.linalg.solve(K,pixels)*d[v,u].ravel()) + T[:3,3,None]
        assert np.isfinite(points).all()
        rays=T[:3,:3] @ np.linalg.solve(K,pixels)
        origin=T[:3,3,None]
        distance=(.002-origin[2,0])/rays[2]
        if name=='counter_head_height':
            front_distance=(.2-origin[0,0])/rays[0]
            front=origin+rays*front_distance
            hit=(front_distance>0)&(front[2]>=0)&(front[2]<=.96)&(front[1]>=-3)&(front[1]<=-1)
            distance=np.where(hit,np.minimum(distance,front_distance),distance)
        expected=origin+rays*distance
        assert np.max(np.linalg.norm(points-expected,axis=0)) < .01
