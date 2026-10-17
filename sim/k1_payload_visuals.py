"""Reference-inspired render shells. All mass/collision proxies remain unchanged.

Printed box design is an approximation, not an exact current Domino's SKU.
Can dimensions follow the existing assumed payload, not a measured retail can.
Raised tray lip is cosmetic and provides NO additional physical retention.
"""
from pathlib import Path
import math

def apply_payload_visuals(stage, config, tray_root=None):
    from pxr import Usd,UsdGeom,UsdShade,Sdf,Gf
    from sim.cafe_scene import material
    assets=Path(__file__).parent/'assets/payload'
    def mat(name,color,roughness=.5,metallic=0,texture=None):
        m=material(stage,name,color,roughness=roughness,metallic=metallic)
        if texture:
            shader=UsdShade.Shader.Get(stage,str(m.GetPath())+'/Shader')
            if not shader:
                shader=UsdShade.Shader(m.ComputeSurfaceSource()[0])
            uv=UsdShade.Shader.Define(stage,str(m.GetPath())+'/UV');uv.CreateIdAttr('UsdPrimvarReader_float2');uv.CreateInput('varname',Sdf.ValueTypeNames.Token).Set('st')
            tex=UsdShade.Shader.Define(stage,str(m.GetPath())+'/Texture');tex.CreateIdAttr('UsdUVTexture');tex.CreateInput('file',Sdf.ValueTypeNames.Asset).Set(str((assets/texture).resolve()));tex.CreateInput('sourceColorSpace',Sdf.ValueTypeNames.Token).Set('sRGB');tex.CreateInput('st',Sdf.ValueTypeNames.Float2).ConnectToSource(uv.ConnectableAPI(),'result')
            shader.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).ConnectToSource(tex.ConnectableAPI(),'rgb')
        return m
    card=mat('PayloadKraft',(.54,.39,.23),.85)
    lid=mat('PayloadPrintedLid',(1,1,1),.78,texture='pizza-lid.png')
    side=mat('PayloadPrintedSide',(1,1,1),.8,texture='pizza-side.png')
    red=mat('PayloadCokeRed',(.64,.006,.018),.24,.4)
    label=mat('PayloadCokeLabel',(1,1,1),.26,.22,texture='coke-wrap.png')
    aluminum=mat('PayloadAluminum',(.66,.69,.72),.23,.88)
    dark=mat('PayloadOpening',(.028,.028,.03),.5,.1)
    traymat=mat('PayloadTrayBrushedSteel',(.34,.37,.40),.32,.8)
    rubber=mat('PayloadTrayGrip',(.045,.05,.055),.9)
    def mesh(path,points,faces,material,uv=None,smooth=False):
        m=UsdGeom.Mesh.Define(stage,path);m.CreatePointsAttr(points);m.CreateFaceVertexCountsAttr([len(f) for f in faces]);m.CreateFaceVertexIndicesAttr([i for f in faces for i in f]);m.CreateSubdivisionSchemeAttr('none');m.CreateDoubleSidedAttr(True)
        if uv:UsdGeom.PrimvarsAPI(m).CreatePrimvar('st',Sdf.ValueTypeNames.TexCoord2fArray,UsdGeom.Tokens.faceVarying).Set(uv)
        UsdShade.MaterialBindingAPI.Apply(m.GetPrim()).Bind(material)
        return m
    def rect(x,y,cut=.008):return [(-x/2+cut,-y/2),(x/2-cut,-y/2),(x/2,-y/2+cut),(x/2,y/2-cut),(x/2-cut,y/2),(-x/2+cut,y/2),(-x/2,y/2-cut),(-x/2,-y/2+cut)]
    def loft(path,rings,material,cap=False):
        points=[(x,y,z) for contour,z in rings for x,y in contour];n=len(rings[0][0]);faces=[]
        for j in range(len(rings)-1):
            for i in range(n):faces.append([j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i])
        if cap:faces.extend([list(reversed(range(n))),list(range((len(rings)-1)*n,len(rings)*n))])
        return mesh(path,points,faces,material)
    def quad(path,points,material):return mesh(path,points,[[0,1,2,3]],material,[(0,0),(1,0),(1,1),(0,1)])
    def lathe(path,profile,material,label_uv=False):
        n=96;points=[];faces=[];uv=[]
        for r,z in profile:
            points.extend([(r*math.cos(2*math.pi*i/n),r*math.sin(2*math.pi*i/n),z) for i in range(n)])
        for j in range(len(profile)-1):
            for i in range(n):
                faces.append([j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i]);a=i/n;b=(i+1)/n;c=j/(len(profile)-1);d=(j+1)/(len(profile)-1);uv.extend([(a,c),(b,c),(b,d),(a,d)])
        return mesh(path,points,faces,material,uv if label_uv else None)
    hidden=[]
    for name in ('box','drink'):
        root=stage.GetPrimAtPath('/World/Carried_'+name)
        for p in list(Usd.PrimRange(root)):
            if p.IsA(UsdGeom.Gprim):UsdGeom.Imageable(p).MakeInvisible();hidden.append(str(p.GetPath()))
    # Imported fixed tray visuals are merged into trunk, with authored local transforms.
    trunks=[p for p in stage.Traverse() if p.GetName()=='trunk' and str(p.GetPath()).startswith('/World/K1/')]
    assert len(trunks)==1
    trunk=trunks[0]
    for p in list(Usd.PrimRange(trunk)):
        path=str(p.GetPath())
        if '/visuals/' in path and 'carry_tray' in path:
            UsdGeom.Imageable(p).MakeInvisible();hidden.append(path)
    box='/World/Carried_box/Packaging';UsdGeom.Xform.Define(stage,box)
    x,y,z=config['box']['size'];lo=-z/2;hi=z/2
    loft(box+'/CorrugatedBase',[(rect(x,y),lo),(rect(x,y),hi-.004)],card,True)
    loft(box+'/FoldedLidEdge',[(rect(x+.001,y+.001),hi-.004),(rect(x+.001,y+.001),hi)],side,True)
    quad(box+'/PrintedTop',[(-x/2+.004,-y/2+.004,hi+.0001),(x/2-.004,-y/2+.004,hi+.0001),(x/2-.004,y/2-.004,hi+.0001),(-x/2+.004,y/2-.004,hi+.0001)],lid)
    quad(box+'/PrintedFront',[(-x/2+.008,-y/2-.0002,lo+.003),(x/2-.008,-y/2-.0002,lo+.003),(x/2-.008,-y/2-.0002,hi-.005),(-x/2+.008,-y/2-.0002,hi-.005)],side)
    quad(box+'/PrintedRight',[(x/2+.0002,-y/2+.008,lo+.003),(x/2+.0002,y/2-.008,lo+.003),(x/2+.0002,y/2-.008,hi-.005),(x/2+.0002,-y/2+.008,hi-.005)],side)
    # Front folded latch, exposed kraft seam and tiny corrugation flute ends.
    quad(box+'/LidTab',[(-.03,-y/2-.0006,hi-.015),(.03,-y/2-.0006,hi-.015),(.03,-y/2-.0006,hi-.003),(-.03,-y/2-.0006,hi-.003)],card)
    for i in range(45):
        a=-x/2+.009+i*(x-.018)/45
        quad(box+f'/Flute{i}',[(a,-y/2-.0003,lo+.0004),(a+.0015,-y/2-.0003,lo+.0004),(a+.0015,-y/2-.0003,lo+.0026),(a,-y/2-.0003,lo+.0026)],dark)
    can='/World/Carried_drink/Can';UsdGeom.Xform.Define(stage,can)
    r=config['drink']['radius'];h=config['drink']['height'];bottom=-h/2;top=h/2
    lathe(can+'/Body',[(r*.84,bottom+.002),(r*.94,bottom+.006),(r,bottom+.013),(r,top-.017),(r*.88,top-.007),(r*.86,top-.003)],red)
    lathe(can+'/PrintedWrap',[(r+.00005,bottom+.014),(r+.00005,top-.018)],label,True)
    lathe(can+'/LowerRim',[(r*.84,bottom+.004),(r*.88,bottom+.001),(r*.90,bottom+.002),(r*.90,bottom+.004),(r*.86,bottom+.006)],aluminum)
    lathe(can+'/RolledTopRim',[(r*.84,top-.005),(r*.90,top-.004),(r*.91,top-.001),(r*.88,top+.0001),(r*.83,top-.001),(r*.82,top-.004)],aluminum)
    lathe(can+'/Lid',[(0,top-.004),(r*.73,top-.004),(r*.80,top-.006),(r*.84,top-.004)],aluminum)
    def oval(cx,cy,rx,ry,n=48):return [(cx+rx*math.cos(i*2*math.pi/n),cy+ry*math.sin(i*2*math.pi/n)) for i in range(n)]
    loft(can+'/ScoredOpening',[(oval(0,.010,.011,.009),top-.0037),(oval(0,.010,.0095,.0075),top-.0035)],dark)
    loft(can+'/PullTab',[(oval(0,-.004,.008,.014),top-.002),(oval(0,-.004,.007,.012),top-.0007),(oval(0,-.006,.0035,.006),top-.0007),(oval(0,-.006,.0035,.006),top-.002)],aluminum)
    tray=(tray_root or str(trunk.GetPath()))+'/RealisticTray';xf=UsdGeom.Xform.Define(stage,tray);xf.AddTranslateOp().Set(Gf.Vec3d(*config['tray']['center']))
    tx,ty,tz=config['tray']['size']
    loft(tray+'/PressedSteel',[(rect(tx-.012,ty-.012,.02),-tz/2),(rect(tx,ty,.025),tz/2),(rect(tx,ty,.025),tz/2+.015),(rect(tx-.008,ty-.008,.023),tz/2+.017),(rect(tx-.018,ty-.018,.02),tz/2+.003)],traymat,True)
    # Thin rubber liner above the collision surface is cosmetic.
    loft(tray+'/GripLiner',[(rect(tx-.025,ty-.025,.018),tz/2+.0002),(rect(tx-.025,ty-.025,.018),tz/2+.0005)],rubber,True)
    return {'scope':'render-only shells; approximate branded packaging','physics_changed':False,'rgb_changed':True,'hidden_proxy_visuals':hidden,'raised_lip_collision':False,'attachment':'free hand-contact tray' if tray_root else 'existing torso bracket and cup holder unchanged','references':['https://media.dominos.com/stories/recycling-pizza-boxes/','https://www.coca-cola.com/us/en/brands/coca-cola/products/original']}
