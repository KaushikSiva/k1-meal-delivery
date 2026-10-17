"""Printed payload render meshes; collision geometry and body inertia stay intact.

Uses the same reference-inspired packaging textures as the Isaac scene. The can
is sealed and rigid. Decorative seams, aluminum rims and labels carry no mass.
"""
from pathlib import Path
import math
import xml.etree.ElementTree as ET
import hashlib

ASSETS = Path(__file__).parent / 'assets/payload'


def decorate_floor(xml_path):
    from PIL import Image
    source = Path(__file__).parent / 'vendor/cafe-assets/wood_floor/wood_floor_diff_2k.jpg'
    png = Path(xml_path).parent / 'wood_floor.png'
    Image.open(source).convert('RGB').save(png)
    tree = ET.parse(xml_path)
    asset = tree.getroot().find('asset')
    texture = asset.find("texture[@name='texplane']")
    texture.attrib.clear()
    texture.attrib.update(name='texplane', type='2d', file=str(png.resolve()))
    mat = asset.find("material[@name='matplane']")
    mat.set('reflectance', '.015')
    mat.set('specular', '.12')
    mat.set('texrepeat', '.5 .5')
    tree.write(xml_path, encoding='unicode')
    return dict(source='Poly Haven wood_floor CC0; pinned in cafe_assets.json',
                source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                png_sha256=hashlib.sha256(png.read_bytes()).hexdigest())


def decorate_payload(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    asset = root.find('asset')
    report = dict(physics_changed=False, rgb_changed=True, decorative_mass_kg=0,
                  decorative_contacts=False, texture_sha256={})

    def material(name, rgba, texture=None, specular=.2, shininess=.2):
        attrs = dict(name=name, rgba=rgba, specular=str(specular), shininess=str(shininess))
        if texture:
            path = (ASSETS / texture).resolve()
            ET.SubElement(asset, 'texture', name=name+'_tex', type='2d', file=str(path))
            attrs['texture'] = name+'_tex'
            report['texture_sha256'][texture] = hashlib.sha256(path.read_bytes()).hexdigest()
        ET.SubElement(asset, 'material', **attrs)

    material('carry_cardboard', '.57 .42 .27 1', specular=.05)
    material('carry_lid', '1 1 1 1', 'pizza-lid.png', .05)
    material('carry_side', '1 1 1 1', 'pizza-side.png', .05)
    material('carry_coke', '1 1 1 1', 'coke-wrap.png', .45, .5)
    material('carry_red', '.68 .008 .02 1', specular=.45, shininess=.5)
    material('carry_aluminum', '.68 .71 .74 1', specular=.8, shininess=.7)
    material('carry_steel', '.28 .31 .34 1', specular=.65, shininess=.5)
    material('carry_dark', '.035 .04 .045 1', specular=.08)

    def mesh(body, name, vertices, faces, uv, mat):
        # Duplicate face vertices to give the cylindrical seam and box corners
        # independent UVs. Closed meshes avoid degenerate planar convex hulls.
        points, coords, triangles = [], [], []
        for face, tex in zip(faces, uv):
            offset = len(points)
            points.extend(vertices[i] for i in face)
            coords.extend(tex)
            triangles.extend((offset, offset+i, offset+i+1) for i in range(1, len(face)-1))
        def flat(values):
            return ' '.join(str(v) for row in values for v in row)
        ET.SubElement(asset, 'mesh', name=name, vertex=flat(points), face=flat(triangles),
                      texcoord=flat(coords))
        ET.SubElement(body, 'geom', name=name+'_visual', type='mesh', mesh=name,
                      material=mat, mass='0', contype='0', conaffinity='0', group='2')

    def box(body, name, center, size, mat):
        x,y,z = (v/2 for v in size)
        vertices = [(center[0]+a, center[1]+b, center[2]+c)
                    for a,b,c in [(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),
                                  (-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]]
        faces = [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
        mesh(body,name,vertices,faces,[[(0,0),(1,0),(1,1),(0,1)]]*6,mat)

    def lathe(body, name, profile, mat):
        n = 64
        vertices = [(r*math.cos(2*math.pi*i/n), r*math.sin(2*math.pi*i/n), z)
                    for r,z in profile for i in range(n)]
        faces, uv = [], []
        for j in range(len(profile)-1):
            for i in range(n):
                faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
                uv.append([(i/n,j/(len(profile)-1)),((i+1)/n,j/(len(profile)-1)),
                           ((i+1)/n,(j+1)/(len(profile)-1)),(i/n,(j+1)/(len(profile)-1))])
        faces.extend([tuple(reversed(range(n))),tuple(range((len(profile)-1)*n,len(profile)*n))])
        uv.extend([[(.5,.5)]*n,[(.5,.5)]*n])
        mesh(body,name,vertices,faces,uv,mat)

    pizza = root.find(".//body[@name='pizza_box']")
    drink = root.find(".//body[@name='drink']")
    tray = root.find(".//body[@name='free_tray']")
    assert pizza is not None and drink is not None and tray is not None
    pizza.find('geom').set('rgba', '.57 .42 .27 1')
    box(pizza,'printed_lid',(0,0,.0301),(.298,.278,.0003),'carry_lid')
    box(pizza,'printed_front',(0,-.1401,.001),(.284,.0003,.049),'carry_side')
    box(pizza,'printed_back',(0,.1401,.001),(.284,.0003,.049),'carry_side')
    box(pizza,'lid_fold',(0,-.1404,.017),(.052,.0003,.012),'carry_cardboard')
    drink.find('geom').set('rgba', '0 0 0 0')
    lathe(drink,'can_body',[(.029,-.07),(.033,-.065),(.035,-.056),(.035,.052),(.030,.063),(.03,.069)],'carry_red')
    lathe(drink,'can_label',[(.03505,-.056),(.03505,.052)],'carry_coke')
    lathe(drink,'can_top',[(.030,.065),(.032,.068),(.032,.070),(.029,.0705)],'carry_aluminum')
    lathe(drink,'can_bottom',[(.030,-.070),(.032,-.069),(.032,-.066)],'carry_aluminum')
    box(drink,'can_tab',(0,-.005,.0708),(.013,.024,.001),'carry_aluminum')
    box(drink,'can_opening',(0,.012,.0707),(.012,.012,.0003),'carry_dark')
    for geom in tray.findall('geom'):
        if geom.get('name','').startswith('tray_'):
            geom.set('material','carry_steel')
            geom.set('rgba','1 1 1 1')
    tree.write(xml_path,encoding='unicode')
    return report
