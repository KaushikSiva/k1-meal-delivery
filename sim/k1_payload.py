"""Explicit supported-tray fixture and free rigid payload for development.

Mass, dimensions and attachment are assumptions; no hardware grasp claim.
The source URDF is never edited. Fixed supports merge into the articulation.
"""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

CONFIG_PATH = Path(__file__).with_name('k1_payload.json')


def load_config(path=None):
    return json.loads(Path(path or CONFIG_PATH).read_text())


def make_supported_urdf(source, destination, config=None):
    source, destination = Path(source), Path(destination)
    config = config or load_config()
    tree = ET.parse(source)
    root = tree.getroot()
    for mesh in root.iter('mesh'):
        path = Path(mesh.attrib['filename'])
        if not path.is_absolute():
            mesh.set('filename', str((source.parent / path).resolve()))
    supports={kind:config[kind] for kind in ('tray','bracket')}
    supports.update(config.get('extra_supports',{}))
    for kind,spec in supports.items():
        name = 'carry_' + kind
        link = ET.SubElement(root, 'link', name=name)
        inertial = ET.SubElement(link, 'inertial')
        ET.SubElement(inertial, 'origin', xyz='0 0 0', rpy='0 0 0')
        mass = spec['mass_kg']
        ET.SubElement(inertial, 'mass', value=str(mass))
        x,y,z = spec['size']
        ET.SubElement(inertial, 'inertia', ixx=str(mass*(y*y+z*z)/12),
                      iyy=str(mass*(x*x+z*z)/12), izz=str(mass*(x*x+y*y)/12),
                      ixy='0', ixz='0', iyz='0')
        for role in ('visual', 'collision'):
            node = ET.SubElement(link, role)
            ET.SubElement(node, 'origin', xyz='0 0 0', rpy='0 0 0')
            ET.SubElement(ET.SubElement(node, 'geometry'), 'box', size=' '.join(map(str,spec['size'])))
            if role == 'visual':
                mat = ET.SubElement(node, 'material', name='CarrySupport')
                ET.SubElement(mat, 'color', rgba='0.18 0.20 0.22 1')
        joint = ET.SubElement(root, 'joint', name=name+'_fixed', type='fixed')
        ET.SubElement(joint, 'parent', link='trunk')
        ET.SubElement(joint, 'child', link=name)
        ET.SubElement(joint, 'origin', xyz=' '.join(map(str,spec['center'])), rpy='0 0 0')
    tree.write(destination, encoding='utf-8', xml_declaration=True)
    return destination


def spawn_payload(root_position, config=None, prim_prefix='/World'):
    """Create free PhysX objects before SimulationContext.reset()."""
    import isaaclab.sim as sim_utils
    from isaaclab.assets import RigidObject, RigidObjectCfg
    config = config or load_config()
    material = sim_utils.RigidBodyMaterialCfg(
        static_friction=config['payload_static_friction'],
        dynamic_friction=config['payload_dynamic_friction'],
        restitution=config['payload_restitution'])
    objects = {}
    for name in ('box', 'drink'):
        spec = config[name]
        common = dict(rigid_props=sim_utils.RigidBodyPropertiesCfg(max_depenetration_velocity=1),
                      mass_props=sim_utils.MassPropertiesCfg(mass=spec['mass_kg']),
                      collision_props=sim_utils.CollisionPropertiesCfg(), physics_material=material,
                      visual_material=sim_utils.PreviewSurfaceCfg(
                          diffuse_color=(.65,.38,.17) if name=='box' else (.12,.38,.20)))
        shape = (sim_utils.CuboidCfg(size=tuple(spec['size']), **common) if name=='box' else
                 sim_utils.CylinderCfg(radius=spec['radius'], height=spec['height'], axis='Z', **common))
        objects[name] = RigidObject(RigidObjectCfg(prim_path=prim_prefix+'/Carried_'+name, spawn=shape,
            init_state=RigidObjectCfg.InitialStateCfg(
                pos=tuple(float(a+b) for a,b in zip(root_position,spec['center'])))))
    return objects
