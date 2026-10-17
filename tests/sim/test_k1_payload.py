"""Check attachment mass/inertia and independent placement clearances."""
from pathlib import Path
import xml.etree.ElementTree as ET
import pytest
from sim.k1_payload import load_config, make_supported_urdf


def test_supports_add_physical_mass_without_changing_joint_topology(tmp_path):
    source=Path(__file__).resolve().parents[2]/'sim/vendor/booster_assets/robots/K1/K1_22dof.urdf'
    if not source.exists():pytest.skip('pinned K1 assets absent')
    before=source.read_bytes()
    root=ET.parse(make_supported_urdf(source,tmp_path/'loaded.urdf')).getroot()
    assert source.read_bytes()==before
    assert len([j for j in root.findall('joint') if j.attrib['type']!='fixed'])==22
    assert sum(float(m.attrib['value']) for m in root.findall('link/inertial/mass'))==pytest.approx(20.616)
    for name in ('carry_tray','carry_bracket'):
        i=root.find(f"link[@name='{name}']/inertial/inertia").attrib
        assert all(float(i[k])>0 for k in ('ixx','iyy','izz'))
        assert float(i['ixx'])+float(i['iyy'])>=float(i['izz'])
    assert all(Path(m.attrib['filename']).is_file() for m in root.iter('mesh'))


def test_payload_starts_above_tray_with_clearance_and_no_overlap():
    c=load_config();t=c['tray'];b=c['box'];d=c['drink']
    surface=t['center'][2]+t['size'][2]/2
    assert b['center'][2]-b['size'][2]/2-surface==pytest.approx(c['initial_surface_gap_m'])
    assert d['center'][2]-d['height']/2-surface==pytest.approx(c['initial_surface_gap_m'])
    for axis in (0,1):
        lo=t['center'][axis]-t['size'][axis]/2;hi=t['center'][axis]+t['size'][axis]/2
        assert lo<b['center'][axis]-b['size'][axis]/2<b['center'][axis]+b['size'][axis]/2<hi
        assert lo<d['center'][axis]-d['radius']<d['center'][axis]+d['radius']<hi
    assert d['center'][1]+d['radius']<b['center'][1]-b['size'][1]/2
