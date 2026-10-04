"""Studio setup for single-asset design renders (EEVEE toon)."""
import math
import bpy
from mathutils import Vector
import erlib as E


_SUN = []


def stage(res=(900, 900), sky_top=0x7EC8F8, sky_hor=0xE8F6FF, floor=True, floor_col=0xF3EEE6):
    import os
    quick = os.environ.get("PONGO_QUICK")
    sc = E.setup_eevee(res=res, samples=16 if quick else 48, bloom=True)
    if quick:
        sc.render.resolution_percentage = 50
    E.world_sky(sky_top, sky_hor, 1.0)
    _SUN.clear()
    _SUN.append(E.sun(rot=(48, 12, 38), energy=4.0, color=0xFFF4E2))
    if floor:
        E.mat("studio_floor", floor_col, rim=0.0, spec=0.0, soft=0.2, outline=0)
        m = E.Mesher("floor").mat("studio_floor")
        m.cyl((0, 0, -0.02), r=6, h=0.04, seg=64)
        m.obj()


def aim_sun(yaw, elev=48.0, side=35.0):
    """Key light from the camera side (yaw measured like shoot()), offset by `side` degrees."""
    if not _SUN:
        return
    y = math.radians(yaw + side)
    d = Vector((math.sin(y) * math.cos(math.radians(elev)), -math.cos(y) * math.cos(math.radians(elev)), math.sin(math.radians(elev))))
    _SUN[0].rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()


def shoot(name, target=(0, 0, 0.5), dist=3.0, yaw=35.0, pitch=18.0, lens=50, light=True):
    if light:
        aim_sun(yaw)
    t = Vector(target)
    y, p = math.radians(yaw), math.radians(pitch)
    loc = t + Vector((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p))) * dist
    E.camera(loc, t, lens=lens)
    import os
    os.makedirs(os.path.join(E.OUT_RENDERS, "design"), exist_ok=True)
    E.render(os.path.join(E.OUT_RENDERS, "design", name + ".png"))


# ----------------------------------------------------------------------------- semi-real studio (PBR)

def stage_pbr(res=(1200, 1600), backdrop=0xD9D3E3, floor_col=0xB9B2C6, world_top=0x7C8FB4, world_hor=0xC9C4D6,
              world_strength=0.3, key=260.0, fill=70.0, rim=380.0, look='AgX - Medium High Contrast', samples=96):
    """Three-point area lighting, curved cyclorama, AO, SSR, soft shadows, SSS, bloom, AgX colour.
    PONGO_QUICK=1 in the environment renders previews (half size, few samples)."""
    import os
    quick = os.environ.get("PONGO_QUICK")
    sc = E.setup_eevee(res=res, samples=16 if quick else samples, bloom=True)
    if quick:
        sc.render.resolution_percentage = 50
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = look
    except TypeError:
        pass
    ev = sc.eevee
    ev.use_gtao = True
    ev.gtao_distance = 0.25
    ev.gtao_factor = 1.0
    ev.use_gtao_bent_normals = True
    ev.use_ssr = True
    ev.use_ssr_halfres = False
    ev.ssr_quality = 0.75
    ev.ssr_max_roughness = 0.6
    ev.use_soft_shadows = True
    ev.shadow_cube_size = '2048'
    ev.shadow_cascade_size = '4096'
    ev.use_shadow_high_bitdepth = True
    ev.sss_samples = 15
    ev.bloom_threshold = 0.9
    ev.bloom_intensity = 0.04
    ev.bloom_radius = 5.5
    # world: soft gradient that does light the scene (semi-real needs ambient light)
    w = sc.world or bpy.data.worlds.new("world")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = E.lin4(world_hor)
    ramp.color_ramp.elements[1].color = E.lin4(world_top)
    ramp.color_ramp.elements[0].position = 0.45
    ramp.color_ramp.elements[1].position = 0.8
    nt.links.new(sep.outputs["Z"], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], bg.inputs[0])
    bg.inputs[1].default_value = world_strength
    nt.links.new(bg.outputs[0], out.inputs[0])
    # cyclorama: floor curving up into a back wall
    E.pbr("cyclorama", floor_col, rough=0.85, spec=0.2, outline=0)
    m = E.Mesher("cyclorama").mat("cyclorama")
    # profile runs from the camera side (+Y) back to the wall (-Y): faces point up / towards the subject
    rings = []
    prof = [(0, 9.0, 0.0)] + [(0, -3.5 - 2.0 * math.sin(math.radians(90 * i / 12)),
                                2.0 - 2.0 * math.cos(math.radians(90 * i / 12))) for i in range(13)] + [(0, -5.5, 8.0)]
    for x in (-12.0, 12.0):
        rings.append([(x, y, z) for (_, y, z) in prof])
    m.quad_strip(rings, closed=False)
    m.obj("cyclorama", smooth_angle=80)
    _SUN.clear()
    lights = []

    def area(name, loc, target, power, size, color, shape='RECTANGLE', size_y=None):
        ld = bpy.data.lights.new(name, 'AREA')
        ld.energy = power
        ld.shape = shape
        ld.size = size
        if size_y is not None:
            ld.size_y = size_y
        ld.color = E.hexrgb(color)
        ld.use_contact_shadow = True
        ob = bpy.data.objects.new(name, ld)
        E.link(ob)
        ob.location = Vector(loc)
        d = Vector(target) - Vector(loc)
        ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        lights.append(ob)
        return ob
    # subject faces +Y: key and fill in front (camera-left = +X), rims behind
    area("key", (2.2, 2.6, 3.0), (0, 0, 1.1), key, 1.6, 0xFFF1E4, 'DISK')
    area("fill", (-2.8, 2.2, 1.6), (0, 0, 1.0), fill, 3.0, 0xDCE6FF)
    area("rim_l", (2.0, -2.4, 2.4), (0, 0, 1.2), rim, 1.0, 0xFFE2C4, 'RECTANGLE', 2.0)
    area("rim_r", (-2.2, -2.2, 2.0), (0, 0, 1.1), rim * 0.7, 1.0, 0xC8DCFF, 'RECTANGLE', 2.0)
    area("top", (0.0, 0.4, 4.2), (0, 0, 1.0), key * 0.15, 2.5, 0xFFFFFF, 'DISK')
    return lights


def shoot_pbr(name, target=(0, 0, 1.0), dist=3.0, yaw=0.0, pitch=8.0, lens=50, dof=None):
    """Camera only (lights stay fixed); yaw 0 = in front of a character facing +Y."""
    t = Vector(target)
    y, p = math.radians(yaw), math.radians(pitch)
    loc = t + Vector((math.sin(y) * math.cos(p), math.cos(y) * math.cos(p), math.sin(p))) * dist
    cam = E.camera(loc, t, lens=lens)
    if dof:
        cam.data.dof.use_dof = True
        cam.data.dof.focus_distance = (loc - t).length
        cam.data.dof.aperture_fstop = dof
    import os
    os.makedirs(os.path.join(E.OUT_RENDERS, "design"), exist_ok=True)
    E.render(os.path.join(E.OUT_RENDERS, "design", name + ".png"))


def haze(col=0xDDEBF5, start=25.0, depth=160.0, amount=0.75):
    """Aerial perspective for scenery shots: blends toward `col` with distance (mist pass in the compositor), the
    soft blue distance of Genshin landscapes; the game does the same with RenderFrame fog."""
    sc = bpy.context.scene
    vl = bpy.context.view_layer
    vl.use_pass_mist = True
    w = sc.world
    w.mist_settings.start = start
    w.mist_settings.depth = depth
    w.mist_settings.falloff = 'QUADRATIC'
    sc.use_nodes = True
    nt = sc.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    rl = nt.nodes.new("CompositorNodeRLayers")
    mul = nt.nodes.new("CompositorNodeMath")
    mul.operation = 'MULTIPLY'
    mul.inputs[1].default_value = amount
    mul.use_clamp = True
    mix = nt.nodes.new("CompositorNodeMixRGB")
    mix.inputs[2].default_value = E.lin4(col)
    out = nt.nodes.new("CompositorNodeComposite")
    vl.use_pass_z = True
    geo = nt.nodes.new("CompositorNodeMath")          # 1 on geometry, 0 on the sky (keep the sky's own gradient)
    geo.operation = 'LESS_THAN'
    geo.inputs[1].default_value = 1.0e5
    m2 = nt.nodes.new("CompositorNodeMath")
    m2.operation = 'MULTIPLY'
    nt.links.new(rl.outputs["Mist"], mul.inputs[0])
    nt.links.new(rl.outputs["Depth"], geo.inputs[0])
    nt.links.new(mul.outputs[0], m2.inputs[0])
    nt.links.new(geo.outputs[0], m2.inputs[1])
    nt.links.new(m2.outputs[0], mix.inputs[0])
    nt.links.new(rl.outputs["Image"], mix.inputs[1])
    nt.links.new(mix.outputs[0], out.inputs[0])
