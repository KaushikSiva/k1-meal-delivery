"""Approximate K1 link colors from inspected official product photos.

Cosmetic USD surface materials only. No mesh edits, masses, collisions or sensor
placement changes. The STL meshes do not separate every housing/accent, so this
is not an exact textured replica. RGB observations will naturally change.
"""
REFERENCE = 'https://www.booster.tech/booster-k1/'
PHOTO = 'https://fe-cdn.booster.tech/booster-official-website/release-0.1.4/_astro/robot.CSH3ZJyt.webp'


def apply_k1_appearance(stage, root='/World/K1'):
    from pxr import Usd, UsdGeom, UsdShade
    from sim.cafe_scene import material
    light = material(stage, 'K1SilverHousing', (.64,.66,.69), roughness=.35, metallic=.22)
    dark = material(stage, 'K1DarkHousing', (.045,.048,.055), roughness=.42, metallic=.12)
    assigned = []
    # URDF importer instances each visual subtree. Make only those render
    # subtrees editable; collision subtrees and their instances stay untouched.
    for prim in list(Usd.PrimRange(stage.GetPrimAtPath(root))):
        if prim.GetName() == 'visuals' and prim.IsInstance():
            prim.SetInstanceable(False)
    for prim in Usd.PrimRange(stage.GetPrimAtPath(root)):
        if not prim.IsA(UsdGeom.Mesh): continue
        parts = str(prim.GetPath()).split('/')
        if 'visuals' not in parts: continue
        link = parts[parts.index('visuals')-1]
        # Merged attachment geometry may share the trunk: keep its own materials.
        if any('carry_' in p for p in parts): continue
        if any('logo' in p.lower() for p in parts): continue
        chosen = light if link == 'trunk' else dark
        # The imported object's parent binding is stronger than descendants;
        # rebinding only the leaf mesh silently leaves the original gray active.
        object_path = '/'.join(parts[:parts.index('visuals')+2])
        object_prim = stage.GetPrimAtPath(object_path)
        UsdShade.MaterialBindingAPI.Apply(object_prim).Bind(
            chosen, bindingStrength=UsdShade.Tokens.strongerThanDescendants)
        effective, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
        if effective.GetPath() != chosen.GetPath():
            raise RuntimeError(f'Material override ineffective at {prim.GetPath()}')
        assigned.append({'path':str(prim.GetPath()),'material':'silver' if link=='trunk' else 'dark'})
    if len(assigned)<20:
        raise RuntimeError(f'Unexpected imported visual hierarchy: only {len(assigned)} meshes matched')
    return {'reference_page':REFERENCE,'reference_photo':PHOTO,'scope':'approximate per-link surface colors',
            'physics_changed':False,'rgb_changed':True,'assigned':assigned,
            'limits':['no exact surface segmentation','no orange accents or new logo textures']}
