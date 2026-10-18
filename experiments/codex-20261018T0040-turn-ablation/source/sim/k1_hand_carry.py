"""Free tray on physical hand contacts. No tray weld, torso bracket or pose replay."""
from pathlib import Path
import xml.etree.ElementTree as ET
import json
ROOT=Path(__file__).resolve().parents[1]
ARM_POSE={
 'aaleft_shoulder_pitch_joint':-.7878273143,'left_shoulder_roll_joint':-1.4451597945,
 'left_elbow_pitch_joint':-.1240584698,'left_elbow_yaw_joint':-.7750652153,
 'aaright_shoulder_pitch_joint':-.7878273143,'right_shoulder_roll_joint':1.4451597945,
 'right_elbow_pitch_joint':-.1240584698,'right_elbow_yaw_joint':.7750652153}

def make_model(destination, handle_seats=False):
    source=ROOT/'sim/vendor/booster_assets/robots/K1/K1_22dof.xml';tree=ET.parse(source);root=tree.getroot()
    compiler=root.find('compiler');compiler.set('meshdir',str(source.parent/'meshes'))
    # Resolve the upstream meshdir rather than assuming its directory spelling.
    original=ET.parse(source).getroot().find('compiler').get('meshdir','.')
    compiler.set('meshdir',str((source.parent/original).resolve()))
    world=root.find('worldbody');root.find('option').set('timestep','.002')
    visual=root.find('visual')
    if visual is None:visual=ET.SubElement(root,'visual')
    global_=visual.find('global')
    if global_ is None:global_=ET.SubElement(visual,'global')
    global_.set('offwidth','960');global_.set('offheight','720')
    for g in root.iter('geom'):
        if g.get('group')=='1':g.set('rgba','.07 .075 .085 1')
    # Both terminal arm meshes are actual colliders in the pinned model. The
    # upward-facing local-X hand surfaces support the tray without added pads.
    config={'tray_center':[.305,0,.699],'tray_size':[.34,.50,.015],
            'tray_mass_kg':.68,'box_mass_kg':.8,'drink_mass_kg':.5,
            'arm_pose':ARM_POSE,'arm_kp':80.,'arm_kd':3.,'arm_effort_limit_Nm':14.,
            'support':'unconstrained contact with original left/right terminal hand meshes',
            'physical_underside_handle_seats':handle_seats,'tray_fixed_joint':False,'torso_bracket':False,'friction':.7}
    tray=ET.SubElement(world,'body',name='free_tray',pos=' '.join(map(str,config['tray_center'])))
    ET.SubElement(tray,'freejoint',name='tray_free')
    def box(body,name,pos,size,mass,rgba):
        return ET.SubElement(body,'geom',name=name,type='box',pos=' '.join(map(str,pos)),size=' '.join(str(v/2) for v in size),mass=str(mass),friction='.7 .005 .0001',rgba=rgba,condim='4')
    box(tray,'tray_base',[0,0,0],config['tray_size'],.48 if handle_seats else .52,'.22 .25 .28 1')
    for side in [-1,1]:
        box(tray,f'tray_rim_x_{side}',[side*.167,0,.014],[.006,.5,.028],.02,'.25 .28 .3 1')
        box(tray,f'tray_rim_y_{side}',[0,side*.247,.014],[.328,.006,.028],.02,'.25 .28 .3 1')
    for i,(pos,size) in enumerate([([0,-.125,.035],[.08,.01,.07]),([0,-.215,.035],[.08,.01,.07]),([.045,-.17,.035],[.01,.1,.07]),([-.045,-.17,.035],[.01,.1,.07])]):
        box(tray,f'cup_wall_{i}',pos,size,.02,'.05 .055 .06 1')
    if handle_seats:
        for sign in [-1,1]:
            box(tray,f'underside_handle_{sign}',[.015,sign*.20,-.02],[.08,.06,.025],.02,'.12 .13 .14 1')
    center=config['tray_center']
    payload=ET.SubElement(world,'body',name='pizza_box',pos=f'{center[0]-.01} .065 {center[2]+.0075+.03+.002}')
    ET.SubElement(payload,'freejoint',name='pizza_free');box(payload,'pizza_box_geom',[0,0,0],[.3,.28,.06],.8,'.88 .84 .72 1')
    drink=ET.SubElement(world,'body',name='drink',pos=f'{center[0]} -.17 {center[2]+.0075+.07+.002}');ET.SubElement(drink,'freejoint',name='drink_free')
    ET.SubElement(drink,'geom',name='drink_geom',type='cylinder',size='.035 .07',mass='.5',friction='.7 .005 .0001',rgba='.8 .015 .03 1',condim='4')
    ET.SubElement(world,'light',name='carry_light',pos='1 -1 3',dir='0 0 -1',diffuse='.8 .8 .8')
    # No equality constraints are introduced, and all payload bodies are free.
    tree.write(destination,encoding='unicode');return config
