"""Transfer the free MuJoCo payload geometry and measured joint controller to PhysX.

MuJoCo here computes inverse dynamics only. PhysX integrates every body's motion.
No body pose is imposed after initialization; only bounded joint torques act.
"""
from pathlib import Path
import numpy as np
import mujoco
from sim.k1_hand_carry import make_model, ARM_POSE


class HandCarryModel:
    def __init__(self, xml):
        self.setup = make_model(xml, handle_seats=True)
        self.model = mujoco.MjModel.from_xml_path(str(xml))
        self.data = mujoco.MjData(self.model)
        self.root_height = .6 - .05238523380879767
        self.tray_height = .699 + .02097352623939508 - .05238523380879767

    def spawn(self, stage, origin=(1., 0., 0.)):
        from pxr import UsdGeom, UsdPhysics, PhysxSchema, Gf
        from isaaclab.assets import RigidObject, RigidObjectCfg
        from sim.cafe_scene import material
        from pxr import UsdShade
        physics = UsdPhysics.MaterialAPI.Apply(stage.DefinePrim('/World/HandCarryFriction', 'Material'))
        physics.CreateStaticFrictionAttr(.7); physics.CreateDynamicFrictionAttr(.7)
        physics.CreateRestitutionAttr(0.)
        physicsmat = UsdShade.Material(physics.GetPrim())
        gray = material(stage, 'HandTrayPhysical', (.15, .17, .19), roughness=.5, metallic=.5)
        objects = {}
        for name, body in [('tray', 'free_tray'), ('box', 'pizza_box'), ('drink', 'drink')]:
            bid = self.model.body(body).id
            path = '/World/Carried_' + name
            xf = UsdGeom.Xform.Define(stage, path)
            offset = self.model.body_pos[bid].copy()
            offset[2] += self.tray_height - .699
            position = offset + np.asarray(origin)
            xf.AddTranslateOp().Set(Gf.Vec3d(*position))
            rb = UsdPhysics.RigidBodyAPI.Apply(xf.GetPrim()); rb.CreateRigidBodyEnabledAttr(True)
            phys = PhysxSchema.PhysxRigidBodyAPI.Apply(xf.GetPrim())
            phys.CreateDisableGravityAttr(False); phys.CreateMaxDepenetrationVelocityAttr(1.)
            phys.CreateSolverPositionIterationCountAttr(16); phys.CreateSolverVelocityIterationCountAttr(8)
            mass = UsdPhysics.MassAPI.Apply(xf.GetPrim())
            mass.CreateMassAttr(float(self.model.body_mass[bid]))
            mass.CreateCenterOfMassAttr(Gf.Vec3f(*self.model.body_ipos[bid]))
            mass.CreateDiagonalInertiaAttr(Gf.Vec3f(*self.model.body_inertia[bid]))
            iq = self.model.body_iquat[bid]
            mass.CreatePrincipalAxesAttr(Gf.Quatf(float(iq[0]), Gf.Vec3f(*iq[1:])))
            for gid in range(self.model.ngeom):
                if self.model.geom_bodyid[gid] != bid: continue
                size = self.model.geom_size[gid]
                child = path + '/' + self.model.geom(gid).name.replace('-', 'minus')
                if self.model.geom_type[gid] == mujoco.mjtGeom.mjGEOM_BOX:
                    shape = UsdGeom.Cube.Define(stage, child); shape.CreateSizeAttr(1.)
                    shape.AddTranslateOp().Set(Gf.Vec3d(*self.model.geom_pos[gid]))
                    shape.AddScaleOp().Set(Gf.Vec3f(*(size * 2)))
                else:
                    shape = UsdGeom.Cylinder.Define(stage, child)
                    shape.CreateRadiusAttr(float(size[0])); shape.CreateHeightAttr(float(size[1] * 2))
                    shape.CreateAxisAttr('Z')
                UsdPhysics.CollisionAPI.Apply(shape.GetPrim())
                cp = PhysxSchema.PhysxCollisionAPI.Apply(shape.GetPrim())
                cp.CreateContactOffsetAttr(.002); cp.CreateRestOffsetAttr(0.)
                UsdShade.MaterialBindingAPI.Apply(shape.GetPrim()).Bind(gray)
                UsdShade.MaterialBindingAPI(shape.GetPrim()).Bind(physicsmat, materialPurpose='physics')
            PhysxSchema.PhysxContactReportAPI.Apply(xf.GetPrim()).CreateThresholdAttr(0.)
            objects[name] = RigidObject(RigidObjectCfg(prim_path=path, spawn=None,
                init_state=RigidObjectCfg.InitialStateCfg(pos=tuple(position))))
        return objects

    def configure_joint_order(self, names):
        self.names = names
        self.qi = np.array([self.model.joint(n).qposadr[0] for n in names])
        self.vi = np.array([self.model.joint(n).dofadr[0] for n in names])
        self.arms = np.array([names.index(n) for n in ARM_POSE])

    def feedforward(self, joint_pos, joint_vel, quaternion, gyro):
        m, d = self.model, self.data
        d.qpos[3:7] = quaternion; d.qpos[self.qi] = joint_pos
        d.qvel[:] = 0.; d.qvel[self.vi] = joint_vel; d.qvel[3:6] = gyro
        mujoco.mj_forward(m, d)
        result = np.zeros(len(self.names))
        result[self.arms] = d.qfrc_bias[self.vi[self.arms]]
        for sign, name in [(1, 'left_elbow_yaw_link'), (-1, 'right_elbow_yaw_link')]:
            bid = m.body(name).id
            point = d.xpos[bid] + d.xmat[bid].reshape(3, 3) @ np.array([0., sign*.195, 0.])
            jp, jr = np.zeros((3, m.nv)), np.zeros((3, m.nv))
            mujoco.mj_jac(m, d, jp, jr, point, bid)
            result[self.arms] += jp[:, self.vi[self.arms]].T @ np.array([0., 0., 1.98*9.81/2])
        return result

    def visual_config(self):
        return dict(tray=dict(center=[0,0,0],size=self.setup['tray_size']),
                    box=dict(size=[.3,.28,.06]),drink=dict(radius=.035,height=.14))
