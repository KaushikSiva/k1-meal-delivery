"""USD asset/collision integrity checks; requires fetched assets, no GPU."""
from pathlib import Path

import pytest
pytest.importorskip("pxr")
from pxr import Sdf, Usd, UsdGeom, UsdPhysics
from sim.cafe_scene import build_cafe

ASSETS = Path(__file__).resolve().parents[2] / "sim/vendor/cafe-assets"
pytestmark = pytest.mark.skipif(not ASSETS.exists(), reason="cafe assets not fetched")


@pytest.fixture(scope="module")
def cafe():
    stage = Usd.Stage.CreateInMemory()
    build_cafe(stage, ASSETS)
    return stage


def test_furniture_is_metric_and_grounded(cafe):
    assert UsdGeom.GetStageMetersPerUnit(cafe) == 1.0
    assert UsdGeom.GetStageUpAxis(cafe) == "Z"
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    table = cache.ComputeWorldBound(cafe.GetPrimAtPath("/World/Cafe/Table1")).ComputeAlignedRange()
    assert -0.01 < table.GetMin()[2] < 0.01
    assert 0.74 < table.GetMax()[2] < 0.77
    assert 1.0 < table.GetSize()[0] < 1.1


def test_all_texture_dependencies_resolve(cafe):
    missing = []
    for prim in cafe.Traverse():
        for attr in prim.GetAttributes():
            if attr.GetTypeName() != Sdf.ValueTypeNames.Asset:
                continue
            value = attr.Get()
            if value and value.path and not value.resolvedPath:
                missing.append((str(prim.GetPath()), value.path))
    assert not missing


def test_furniture_has_contacts_and_payload_has_mass(cafe):
    count = 0
    for prim in cafe.Traverse():
        path = str(prim.GetPath())
        if prim.IsA(UsdGeom.Mesh) and ("/Table" in path or "/Chair" in path):
            assert prim.HasAPI(UsdPhysics.CollisionAPI), path
            assert not prim.HasAPI(UsdPhysics.RigidBodyAPI), path
            count += 1
    assert count >= 24
    for name, expected_mass in [("PizzaBox", 0.8), ("SealedDrink", 0.5)]:
        prim = cafe.GetPrimAtPath("/World/Cafe/" + name)
        assert prim.HasAPI(UsdPhysics.RigidBodyAPI)
        assert UsdPhysics.MassAPI(prim).GetMassAttr().Get() == pytest.approx(expected_mass)
