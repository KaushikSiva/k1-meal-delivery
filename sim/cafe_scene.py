"""Metric, textured café USD scene for Isaac Sim; all physical priors are provisional.

Furniture/HDRI/floor maps: Poly Haven CC0, exact hashes in cafe_assets.json.
This constructs an environment, not a delivery policy or a successful trial.
"""
from pathlib import Path
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdPhysics, UsdShade

TABLES = [(x, y) for x in (2.0, 4.9, 7.8) for y in (-2.05, 2.05)]


def material(stage, name, color, roughness=0.6, metallic=0.0):
    mat = UsdShade.Material.Define(stage, f"/World/Materials/{name}")
    shader = UsdShade.Shader.Define(stage, str(mat.GetPath()) + "/Surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(roughness)
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(metallic)
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return mat


def bind(prim, mat):
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(mat)


def pbr_material(stage, assets, asset, part=""):
    """Explicit PreviewSurface avoids imported MaterialX graph compatibility failures."""
    key = asset + ("_" + part if part else "")
    existing = UsdShade.Material.Get(stage, f"/World/Materials/{key}")
    if existing:
        return existing
    mat = material(stage, key, (0.5, 0.5, 0.5))
    root = str(mat.GetPath())
    shader = UsdShade.Shader.Get(stage, root + "/Surface")
    uv = UsdShade.Shader.Define(stage, root + "/UV")
    uv.CreateIdAttr("UsdPrimvarReader_float2")
    uv.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
    uv.CreateOutput("result", Sdf.ValueTypeNames.Float2)
    maps = [("diffuseColor", "diff", "rgb", Sdf.ValueTypeNames.Color3f),
            ("roughness", "rough", "r", Sdf.ValueTypeNames.Float),
            ("normal", "nor_gl", "rgb", Sdf.ValueTypeNames.Normal3f)]
    if part == "leaves":
        maps.append(("opacity", "alpha", "r", Sdf.ValueTypeNames.Float))
        shader.CreateInput("opacityThreshold", Sdf.ValueTypeNames.Float).Set(0.5)
    for channel, suffix, output, kind in maps:
        stem = f"{key}_{suffix}_2k"
        candidates = [assets / asset / "textures" / (stem + ext) for ext in (".png", ".jpg", ".exr")]
        path = next(p for p in candidates if p.exists())
        tex = UsdShade.Shader.Define(stage, root + "/" + channel)
        tex.CreateIdAttr("UsdUVTexture")
        tex.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(str(path.resolve()))
        tex.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB" if suffix == "diff" else "raw")
        tex.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(uv.ConnectableAPI(), "result")
        tex.CreateOutput(output, Sdf.ValueTypeNames.Float3 if output == "rgb" else Sdf.ValueTypeNames.Float)
        if channel == "normal":
            tex.CreateInput("scale", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(2, 2, 2, 1))
            tex.CreateInput("bias", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(-1, -1, -1, 0))
        shader.CreateInput(channel, kind).ConnectToSource(tex.ConnectableAPI(), output)
    return mat


def collision(prim, physics_mat):
    UsdPhysics.CollisionAPI.Apply(prim)
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(physics_mat, materialPurpose="physics")


def box(stage, name, center, size, mat, physics_mat=None):
    cube = UsdGeom.Cube.Define(stage, "/World/Cafe/" + name)
    cube.CreateSizeAttr(1)
    cube.AddTranslateOp().Set(Gf.Vec3d(*center))
    cube.AddScaleOp().Set(Gf.Vec3f(*size))
    bind(cube.GetPrim(), mat)
    if physics_mat:
        collision(cube.GetPrim(), physics_mat)
    return cube.GetPrim()


def cylinder(stage, name, center, radius, height, mat, physics_mat=None):
    cyl = UsdGeom.Cylinder.Define(stage, "/World/Cafe/" + name)
    cyl.CreateRadiusAttr(radius)
    cyl.CreateHeightAttr(height)
    cyl.CreateAxisAttr("Z")
    cyl.AddTranslateOp().Set(Gf.Vec3d(*center))
    bind(cyl.GetPrim(), mat)
    if physics_mat:
        collision(cyl.GetPrim(), physics_mat)
    return cyl.GetPrim()


def imported(stage, assets, asset, name, position, scale=1.0, yaw=0.0, physics_mat=None):
    source = assets / asset / f"{asset}_2k.usdc"
    if not source.is_file():
        raise FileNotFoundError(f"Fetch locked café assets first: {source}")
    parent = UsdGeom.Xform.Define(stage, "/World/Cafe/" + name)
    parent.AddTranslateOp().Set(Gf.Vec3d(*position))
    parent.AddRotateZOp().Set(yaw)
    parent.AddScaleOp().Set(Gf.Vec3f(scale))
    visual = stage.DefinePrim(str(parent.GetPath()) + "/Visual", "Xform")
    visual.GetReferences().AddReference(str(source.resolve()))
    for prim in Usd.PrimRange(visual):
        if prim.IsA(UsdGeom.Mesh):
            original, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
            part = ("leaves" if "leaves" in str(original.GetPath()) else "pot") if asset == "potted_plant_01" else ""
            bind(prim, pbr_material(stage, assets, asset, part))
            if part == "leaves":
                UsdGeom.Mesh(prim).CreateDoubleSidedAttr(True)
            if physics_mat:
                collision(prim, physics_mat)
                UsdPhysics.MeshCollisionAPI.Apply(prim).CreateApproximationAttr("none")
    return parent


def wood_floor(stage, assets):
    mat = material(stage, "OakFloor", (0.45, 0.27, 0.13), roughness=0.6)
    root = str(mat.GetPath())
    shader = UsdShade.Shader.Get(stage, root + "/Surface")
    uv = UsdShade.Shader.Define(stage, root + "/UV")
    uv.CreateIdAttr("UsdPrimvarReader_float2")
    uv.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
    for channel, suffix, output in [("diffuseColor", "diff", "rgb"), ("roughness", "rough", "r"),
                                     ("normal", "nor_gl", "rgb")]:
        tex = UsdShade.Shader.Define(stage, root + "/" + channel)
        tex.CreateIdAttr("UsdUVTexture")
        tex.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(
            str((assets / "wood_floor" / f"wood_floor_{suffix}_2k.jpg").resolve()))
        tex.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB" if suffix == "diff" else "raw")
        tex.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(uv.ConnectableAPI(), "result")
        tex.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("repeat")
        tex.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("repeat")
        if channel == "normal":
            tex.CreateInput("scale", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(2, 2, 2, 1))
            tex.CreateInput("bias", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(-1, -1, -1, 0))
        shader.GetInput(channel) if channel != "normal" else shader.CreateInput("normal", Sdf.ValueTypeNames.Normal3f)
        shader.GetInput(channel).ConnectToSource(tex.ConnectableAPI(), output)
    mesh = UsdGeom.Mesh.Define(stage, "/World/Cafe/FloorFinish")
    mesh.CreatePointsAttr([(-1, -3.6, 0.002), (9.4, -3.6, 0.002), (9.4, 3.6, 0.002), (-1, 3.6, 0.002)])
    mesh.CreateFaceVertexCountsAttr([4])
    mesh.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    mesh.CreateSubdivisionSchemeAttr("none")
    uvdata = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, "vertex")
    uvdata.Set([(0, 0), (5.2, 0), (5.2, 3.6), (0, 3.6)])
    bind(mesh.GetPrim(), mat)


def build_cafe(stage, assets: Path):
    assets = assets.resolve()
    UsdGeom.SetStageUpAxis(stage, "Z")
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    UsdGeom.Xform.Define(stage, "/World/Cafe")
    stone = material(stage, "WarmPlaster", (0.73, 0.69, 0.59), 0.9)
    green = material(stage, "DeepSage", (0.09, 0.18, 0.13), 0.65)
    dark = material(stage, "CharcoalMetal", (0.025, 0.03, 0.028), 0.3, 0.7)
    brass = material(stage, "BrushedBrass", (0.56, 0.35, 0.12), 0.3, 0.8)
    marble = material(stage, "CounterStone", (0.65, 0.62, 0.54), 0.32)
    cardboard = material(stage, "KraftCardboard", (0.42, 0.25, 0.11), 0.9)
    white = material(stage, "Ceramic", (0.85, 0.82, 0.73), 0.23)
    physics = UsdShade.Material.Define(stage, "/World/Materials/ProvisionalFriction")
    pmat = UsdPhysics.MaterialAPI.Apply(physics.GetPrim())
    pmat.CreateStaticFrictionAttr(0.7)
    pmat.CreateDynamicFrictionAttr(0.6)
    pmat.CreateRestitutionAttr(0.0)
    box(stage, "FloorCollision", (4.2, 0, -0.06), (10.4, 7.2, 0.12), stone, physics)
    wood_floor(stage, assets)
    box(stage, "Ceiling", (4.2, 0, 3.24), (10.4, 7.2, 0.12), stone, physics)
    box(stage, "OutsideTerrace", (4.2, -8.0, -0.08), (20, 9.0, 0.12), marble, physics)
    for i, x in enumerate((1.0, 4.2, 7.4)):
        box(stage, f"CeilingBeam{i}", (x, 0, 3.13), (0.10, 7.2, 0.16), dark)
    box(stage, "BackWall", (9.4, 0, 1.6), (0.16, 7.2, 3.2), stone, physics)
    box(stage, "RightWall", (4.2, 3.6, 1.6), (10.4, 0.16, 3.2), stone, physics)
    box(stage, "RightWainscot", (4.2, 3.50, 0.48), (10.4, 0.05, 0.96), green, physics)
    box(stage, "BackWainscot", (9.30, 0, 0.48), (0.05, 7.2, 0.96), green, physics)
    box(stage, "WindowSill", (4.2, -3.6, 0.40), (10.4, 0.20, 0.80), stone, physics)
    box(stage, "WindowHeader", (4.2, -3.6, 3.0), (10.4, 0.22, 0.4), stone, physics)
    for i, x in enumerate((-0.9, 1.15, 3.2, 5.25, 7.3, 9.35)):
        box(stage, f"WindowMullion{i}", (x, -3.6, 1.8), (0.065, 0.10, 2.1), dark, physics)
    # Invisible structural pane retains wall contact while an open glazed visual
    # avoids multiple alpha layers in head-camera depth. Glazing model is provisional.
    pane = box(stage, "WindowCollision", (4.2, -3.6, 1.8), (10.4, 0.025, 2.0), stone, physics)
    UsdGeom.Imageable(pane).MakeInvisible()
    for i, (x, y) in enumerate(TABLES):
        imported(stage, assets, "round_wooden_table_01", f"Table{i+1}", (x, y, 0.001),
                 scale=0.75, physics_mat=physics)
        for j, (dx, dy, yaw) in enumerate([(-0.88, 0, -90), (0.88, 0, 90), (0, 0.88 if y > 0 else -0.88, 0 if y > 0 else 180)]):
            imported(stage, assets, "dining_chair_02", f"Chair{i+1}_{j}", (x+dx, y+dy, 0),
                     yaw=yaw, physics_mat=physics)
        cylinder(stage, f"TableVase{i}", (x, y, 0.81), 0.045, 0.10, white, physics)
        cylinder(stage, f"PendantShade{i}", (x, y, 2.53), 0.23, 0.10, dark)
        cylinder(stage, f"PendantStem{i}", (x, y, 2.89), 0.008, 0.62, dark)
        lamp = UsdLux.DiskLight.Define(stage, f"/World/Cafe/PendantLight{i}")
        lamp.AddTranslateOp().Set(Gf.Vec3d(x, y, 2.46))
        lamp.CreateRadiusAttr(0.18)
        lamp.CreateIntensityAttr(30000)
        lamp.CreateEnableColorTemperatureAttr(True)
        lamp.CreateColorTemperatureAttr(2900)
    for i, pos in enumerate(((8.8, 3.0, 0), (8.8, -3.0, 0), (-0.3, 3.0, 0))):
        imported(stage, assets, "potted_plant_01", f"Plant{i}", pos)
        proxy = cylinder(stage, f"PlantPotCollision{i}", (pos[0], pos[1], 0.18), 0.22, 0.36, stone, physics)
        UsdGeom.Imageable(proxy).MakeInvisible()
    # Service counter, tray and loaded payload staging; nothing is attached to a robot.
    box(stage, "CounterBase", (-0.25, -2.0, 0.48), (0.9, 2.0, 0.96), green, physics)
    box(stage, "CounterTop", (-0.25, -2.0, 0.99), (1.04, 2.1, 0.06), marble, physics)
    box(stage, "TrayBase", (-0.20, -1.8, 1.035), (0.56, 0.42, 0.025), brass, physics)
    for name, pos, size in [
        ("front", (-0.20, -2.005, 1.065), (0.56, 0.012, 0.06)),
        ("back", (-0.20, -1.595, 1.065), (0.56, 0.012, 0.06)),
        ("left", (-0.475, -1.8, 1.065), (0.012, 0.42, 0.06)),
        ("right", (0.075, -1.8, 1.065), (0.012, 0.42, 0.06))]:
        box(stage, "TrayRim_"+name, pos, size, brass, physics)
    pizza = box(stage, "PizzaBox", (-0.28, -1.8, 1.075), (0.34, 0.34, 0.055), cardboard, physics)
    UsdPhysics.RigidBodyAPI.Apply(pizza)
    UsdPhysics.MassAPI.Apply(pizza).CreateMassAttr(0.8)
    drink = cylinder(stage, "SealedDrink", (0.005, -1.8, 1.14), 0.043, 0.18, white, physics)
    UsdPhysics.RigidBodyAPI.Apply(drink)
    UsdPhysics.MassAPI.Apply(drink).CreateMassAttr(0.5)
    # Lid is part of the same rigid body, so it cannot falsely float in a trial.
    lid = UsdGeom.Cylinder.Define(stage, str(drink.GetPath()) + "/Lid")
    lid.CreateRadiusAttr(0.045); lid.CreateHeightAttr(0.012)
    lid.AddTranslateOp().Set(Gf.Vec3d(0, 0, 0.096)); bind(lid.GetPrim(), dark)
    dome = UsdLux.DomeLight.Define(stage, "/World/Daylight")
    dome.CreateTextureFileAttr(str(assets / "kloofendal_48d_partly_cloudy_puresky/kloofendal_48d_partly_cloudy_puresky_2k.hdr"))
    dome.CreateIntensityAttr(600)
    sun = UsdLux.DistantLight.Define(stage, "/World/Sun")
    sun.AddRotateXYZOp().Set(Gf.Vec3f(-35, 20, -30))
    sun.CreateIntensityAttr(1200); sun.CreateAngleAttr(1.0)
    window_fill = UsdLux.RectLight.Define(stage, "/World/WindowDaylight")
    window_fill.AddTranslateOp().Set(Gf.Vec3d(4.2, -3.48, 1.85))
    window_fill.AddRotateXOp().Set(90)
    window_fill.CreateWidthAttr(9.8)
    window_fill.CreateHeightAttr(1.9)
    window_fill.CreateIntensityAttr(1500)
    window_fill.CreateEnableColorTemperatureAttr(True)
    window_fill.CreateColorTemperatureAttr(6500)
    return {"scene": "Common Table cafe", "units": "meters", "table_count": len(TABLES),
            "chair_count": len(TABLES)*3, "asset_provider": "Poly Haven / CC0",
            "physics": "static triangle mesh furniture; provisional friction 0.7/0.6",
            "payload": "0.8kg box + 0.5kg sealed drink, staged on counter tray; masses assumed",
            "robot_present": False, "delivery_tested": False,
            "limitations": ["room dimensions invented", "no calibrated material friction",
                            "lighting intensities selected for visibility, not measured photometry",
                            "window collision pane invisible; glass sensor response not modeled",
                            "plant collision approximates pot only", "no robot or learned controller yet"]}
