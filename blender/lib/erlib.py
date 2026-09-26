"""
erlib — shared Blender (4.0) helpers for the PONGO asset pipeline.

Everything in the game is modelled by Python scripts that use this module:
  * Mesher: a bmesh-based builder with a transform stack, per-primitive
    materials, bevels, lathes, sweeps, extrusions and text.
  * Toon materials: one Blender material per game material. Each carries the
    game parameters (colour, texture tile, specular, rim, emissive, softness,
    outline) as custom properties, plus an EEVEE node tree that reproduces
    the in-game cel shader for design renders.
  * Exporter: writes .erm intermediate files (triangle soup + material table
    + skeleton + animation clips) in game space (Y up, forward = -Z).
  * Render helpers for EEVEE design shots.

Axis convention: Blender is Z-up. The game is Y-up and runs toward -Z.
Model everything with Blender +Y as "forward"; the exporter converts with
game(x, y, z) = blender(x, z, -y).
"""

import bpy, bmesh, math, os, struct, random
from mathutils import Vector, Matrix, Euler, Quaternion

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BUILD = os.path.join(ROOT, "build")
OUT_MODELS = os.path.join(BUILD, "models")
OUT_TEX = os.path.join(BUILD, "tex")
OUT_RENDERS = os.path.join(ROOT, "renders")
for _d in (OUT_MODELS, OUT_TEX, OUT_RENDERS):
    os.makedirs(_d, exist_ok=True)

FONT_LATIN = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_JP = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"


# ----------------------------------------------------------------------------- colours

def hexrgb(h):
    """0xRRGGBB -> (r, g, b) floats in sRGB 0..1."""
    return (((h >> 16) & 255) / 255.0, ((h >> 8) & 255) / 255.0, (h & 255) / 255.0)


def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lin4(h, a=1.0):
    r, g, b = hexrgb(h)
    return (srgb_to_lin(r), srgb_to_lin(g), srgb_to_lin(b), a)


def mix_hex(a, b, t):
    ra, ga, ba = hexrgb(a)
    rb, gb, bb = hexrgb(b)
    r = ra + (rb - ra) * t
    g = ga + (gb - ga) * t
    bl = ba + (bb - ba) * t
    return (int(r * 255 + 0.5) << 16) | (int(g * 255 + 0.5) << 8) | int(bl * 255 + 0.5)


def shade_hex(h, f):
    r, g, b = hexrgb(h)
    r, g, b = min(1, r * f), min(1, g * f), min(1, b * f)
    return (int(r * 255 + 0.5) << 16) | (int(g * 255 + 0.5) << 8) | int(b * 255 + 0.5)


# ----------------------------------------------------------------------------- scene

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.render.fps = 30
    _MATS.clear()
    return sc


def collection(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def link(obj, coll=None):
    (coll or bpy.context.scene.collection).objects.link(obj)
    return obj


def activate(obj):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def apply_modifiers(obj, skip=()):
    activate(obj)
    for m in list(obj.modifiers):
        if m.type in skip:
            continue
        try:
            bpy.ops.object.modifier_apply(modifier=m.name)
        except RuntimeError as e:
            print("modifier apply failed", obj.name, m.name, e)
            obj.modifiers.remove(m)


def join(objs, name=None):
    objs = [o for o in objs if o is not None]
    if not objs:
        return None
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    if name:
        ob.name = name
        ob.data.name = name
    return ob


def set_smooth(obj, angle=40.0):
    me = obj.data
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    if hasattr(me, "use_auto_smooth"):
        me.use_auto_smooth = True
        me.auto_smooth_angle = math.radians(angle)
    me.update()


def delete(obj):
    bpy.data.objects.remove(obj, do_unlink=True)


# ----------------------------------------------------------------------------- materials

class GameMat:
    """Game material description (also becomes a Blender material)."""

    def __init__(self, name, color=0xFFFFFF, tex="", spec=0.0, rim=0.35, emis=0.0, soft=0.12,
                 outline=1.0, skin=0.0, sway=0.0, flags=0, shadow=0xB3ACDC):
        self.name, self.color, self.tex = name, color, tex
        self.spec, self.rim, self.emis, self.soft = spec, rim, emis, soft
        self.outline, self.skin, self.sway, self.flags = outline, skin, sway, flags
        self.shadow = shadow


# material flags (shared with the Java builder / shaders)
F_DOUBLE = 1      # render both faces
F_UNLIT = 2       # sky / emissive-only
F_WATER = 4       # water shader
F_NOCAST = 8      # does not cast shadows
F_HAIR = 16       # anisotropic hair highlight band
F_ALPHA = 32      # uses texture alpha as cutout
F_GLASS = 64      # glossy window glass (sky reflection)
F_METAL = 128     # sharp metallic highlight, deeper shadows
F_FOLIAGE = 256   # wind sway + soft translucency
F_NIGHT = 512     # emissive only after dusk (windows, lamps)
F_DECAL = 1024    # alpha-blended decal drawn over opaque surfaces (eyes, mouths, signs)

_MATS = {}
TOON_GROUP = "PongoToon"


def mat(name, color=0xFFFFFF, tex="", **kw):
    """Get or create a game material and its Blender material."""
    if name in _MATS:
        return _MATS[name]
    gm = GameMat(name, color, tex, **kw)
    bm = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    bm["pongo"] = 1
    bm["color"] = color
    bm["tex"] = tex
    for k in ("spec", "rim", "emis", "soft", "outline", "skin", "sway", "flags", "shadow"):
        bm[k] = getattr(gm, k)
    _build_toon_nodes(bm, gm)
    gm.bmat = bm
    _MATS[name] = gm
    return gm


def tex_path(tile):
    return os.path.join(OUT_TEX, tile + ".png")


def _toon_group():
    g = bpy.data.node_groups.get(TOON_GROUP)
    if g:
        return g
    g = bpy.data.node_groups.new(TOON_GROUP, 'ShaderNodeTree')
    iface = g.interface
    def inp(n, t, d=None):
        s = iface.new_socket(n, in_out='INPUT', socket_type=t)
        if d is not None:
            s.default_value = d
        return s
    inp("Albedo", 'NodeSocketColor', (1, 1, 1, 1))
    inp("ShadowTint", 'NodeSocketColor', (0.45, 0.41, 0.72, 1))
    inp("LightTint", 'NodeSocketColor', (1.0, 0.97, 0.92, 1))
    inp("Softness", 'NodeSocketFloat', 0.12)
    inp("Rim", 'NodeSocketFloat', 0.35)
    inp("RimColor", 'NodeSocketColor', (1.0, 0.95, 0.85, 1))
    inp("Spec", 'NodeSocketFloat', 0.0)
    inp("Emission", 'NodeSocketFloat', 0.0)
    inp("AO", 'NodeSocketFloat', 1.0)
    inp("Skin", 'NodeSocketFloat', 0.0)
    iface.new_socket("Shader", in_out='OUTPUT', socket_type='NodeSocketShader')
    N, L = g.nodes, g.links
    gi = N.new('NodeGroupInput'); go = N.new('NodeGroupOutput')
    diff = N.new('ShaderNodeBsdfDiffuse')
    s2r = N.new('ShaderNodeShaderToRGB')
    bw = N.new('ShaderNodeRGBToBW')
    L.new(diff.outputs[0], s2r.inputs[0]); L.new(s2r.outputs[0], bw.inputs[0])
    # smooth step around 0.5 * softness -> light factor
    lo = N.new('ShaderNodeMath'); lo.operation = 'SUBTRACT'; lo.inputs[0].default_value = 0.18
    L.new(gi.outputs["Softness"], lo.inputs[1])
    hi = N.new('ShaderNodeMath'); hi.operation = 'ADD'; hi.inputs[0].default_value = 0.18
    L.new(gi.outputs["Softness"], hi.inputs[1])
    mr = N.new('ShaderNodeMapRange'); mr.interpolation_type = 'SMOOTHSTEP'; mr.clamp = True
    L.new(bw.outputs[0], mr.inputs["Value"]); L.new(lo.outputs[0], mr.inputs["From Min"]); L.new(hi.outputs[0], mr.inputs["From Max"])
    # ambient occlusion pulls toward the shadow side
    aom = N.new('ShaderNodeMath'); aom.operation = 'MULTIPLY'
    L.new(mr.outputs[0], aom.inputs[0]); L.new(gi.outputs["AO"], aom.inputs[1])
    # shadow colour: albedo * tint (skin shifts warmer)
    skinTint = N.new('ShaderNodeMix'); skinTint.data_type = 'RGBA'
    skinTint.inputs[7].default_value = (0.86, 0.52, 0.55, 1)
    L.new(gi.outputs["Skin"], skinTint.inputs[0]); L.new(gi.outputs["ShadowTint"], skinTint.inputs[6])
    shadowCol = N.new('ShaderNodeMix'); shadowCol.data_type = 'RGBA'; shadowCol.blend_type = 'MULTIPLY'
    shadowCol.inputs[0].default_value = 1.0
    L.new(gi.outputs["Albedo"], shadowCol.inputs[6]); L.new(skinTint.outputs[2], shadowCol.inputs[7])
    litCol = N.new('ShaderNodeMix'); litCol.data_type = 'RGBA'; litCol.blend_type = 'MULTIPLY'
    litCol.inputs[0].default_value = 1.0
    L.new(gi.outputs["Albedo"], litCol.inputs[6]); L.new(gi.outputs["LightTint"], litCol.inputs[7])
    base = N.new('ShaderNodeMix'); base.data_type = 'RGBA'
    L.new(aom.outputs[0], base.inputs[0]); L.new(shadowCol.outputs[2], base.inputs[6]); L.new(litCol.outputs[2], base.inputs[7])
    # rim light (fresnel, hard edged)
    lw = N.new('ShaderNodeLayerWeight'); lw.inputs[0].default_value = 0.35
    rr = N.new('ShaderNodeMapRange'); rr.clamp = True
    rr.inputs["From Min"].default_value = 0.55; rr.inputs["From Max"].default_value = 0.62
    L.new(lw.outputs["Facing"], rr.inputs["Value"])
    rimk = N.new('ShaderNodeMath'); rimk.operation = 'MULTIPLY'
    L.new(rr.outputs[0], rimk.inputs[0]); L.new(gi.outputs["Rim"], rimk.inputs[1])
    rimk2 = N.new('ShaderNodeMath'); rimk2.operation = 'MULTIPLY'
    L.new(rimk.outputs[0], rimk2.inputs[0]); L.new(mr.outputs[0], rimk2.inputs[1])
    rim = N.new('ShaderNodeMix'); rim.data_type = 'RGBA'; rim.blend_type = 'ADD'
    L.new(rimk2.outputs[0], rim.inputs[0]); L.new(base.outputs[2], rim.inputs[6]); L.new(gi.outputs["RimColor"], rim.inputs[7])
    # toon specular band
    gl = N.new('ShaderNodeBsdfGlossy'); gl.inputs["Roughness"].default_value = 0.32
    s2r2 = N.new('ShaderNodeShaderToRGB'); bw2 = N.new('ShaderNodeRGBToBW')
    L.new(gl.outputs[0], s2r2.inputs[0]); L.new(s2r2.outputs[0], bw2.inputs[0])
    sr = N.new('ShaderNodeMapRange'); sr.clamp = True
    sr.inputs["From Min"].default_value = 0.55; sr.inputs["From Max"].default_value = 0.6
    L.new(bw2.outputs[0], sr.inputs["Value"])
    spk = N.new('ShaderNodeMath'); spk.operation = 'MULTIPLY'
    L.new(sr.outputs[0], spk.inputs[0]); L.new(gi.outputs["Spec"], spk.inputs[1])
    spec = N.new('ShaderNodeMix'); spec.data_type = 'RGBA'; spec.blend_type = 'ADD'
    spec.inputs[7].default_value = (1, 1, 1, 1)
    L.new(spk.outputs[0], spec.inputs[0]); L.new(rim.outputs[2], spec.inputs[6])
    # emission
    emk = N.new('ShaderNodeMath'); emk.operation = 'MULTIPLY'; emk.inputs[1].default_value = 3.0
    L.new(gi.outputs["Emission"], emk.inputs[0])
    emc = N.new('ShaderNodeMix'); emc.data_type = 'RGBA'; emc.blend_type = 'MULTIPLY'; emc.inputs[0].default_value = 1
    L.new(gi.outputs["Albedo"], emc.inputs[6])
    emv = N.new('ShaderNodeCombineColor')
    L.new(emk.outputs[0], emv.inputs[0]); L.new(emk.outputs[0], emv.inputs[1]); L.new(emk.outputs[0], emv.inputs[2])
    L.new(emv.outputs[0], emc.inputs[7])
    tot = N.new('ShaderNodeMix'); tot.data_type = 'RGBA'; tot.blend_type = 'ADD'; tot.inputs[0].default_value = 1
    L.new(spec.outputs[2], tot.inputs[6]); L.new(emc.outputs[2], tot.inputs[7])
    em = N.new('ShaderNodeEmission')
    L.new(tot.outputs[2], em.inputs[0])
    L.new(em.outputs[0], go.inputs[0])
    return g


def _build_toon_nodes(bmat, gm):
    bmat.use_nodes = True
    nt = bmat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    grp = nt.nodes.new('ShaderNodeGroup')
    grp.node_tree = _toon_group()
    nt.links.new(grp.outputs[0], out.inputs[0])
    r, g, b = hexrgb(gm.color)
    base = nt.nodes.new('ShaderNodeMix'); base.data_type = 'RGBA'; base.blend_type = 'MULTIPLY'
    base.inputs[0].default_value = 1.0
    base.inputs[6].default_value = lin4(gm.color)
    base.inputs[7].default_value = (1.0, 1.0, 1.0, 1.0)
    vc = nt.nodes.new('ShaderNodeVertexColor'); vc.layer_name = "Col"
    m2 = nt.nodes.new('ShaderNodeMix'); m2.data_type = 'RGBA'; m2.blend_type = 'MULTIPLY'; m2.inputs[0].default_value = 1
    nt.links.new(base.outputs[2], m2.inputs[6]); nt.links.new(vc.outputs["Color"], m2.inputs[7])
    albedo = m2.outputs[2]
    if gm.tex:
        p = tex_path(gm.tex)
        img = bpy.data.images.get(gm.tex)
        if img is None and os.path.exists(p):
            img = bpy.data.images.load(p)
            img.name = gm.tex
        if img is not None:
            ti = nt.nodes.new('ShaderNodeTexImage'); ti.image = img
            ti.interpolation = 'Linear'
            nt.links.new(ti.outputs["Color"], base.inputs[7])
    ao = nt.nodes.new('ShaderNodeAttribute'); ao.attribute_name = "AO"
    nt.links.new(albedo, grp.inputs["Albedo"])
    grp.inputs["ShadowTint"].default_value = lin4(gm.shadow)
    grp.inputs["Softness"].default_value = gm.soft
    grp.inputs["Rim"].default_value = gm.rim
    grp.inputs["Spec"].default_value = gm.spec
    grp.inputs["Emission"].default_value = gm.emis
    grp.inputs["Skin"].default_value = gm.skin
    nt.links.new(ao.outputs["Fac"], grp.inputs["AO"])
    if gm.flags & (F_ALPHA | F_DECAL) and gm.tex and bpy.data.images.get(gm.tex):
        tnode = [n for n in nt.nodes if n.type == 'TEX_IMAGE'][0]
        tr = nt.nodes.new('ShaderNodeBsdfTransparent')
        mx = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(tnode.outputs["Alpha"], mx.inputs[0])
        nt.links.new(tr.outputs[0], mx.inputs[1])
        nt.links.new(grp.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out.inputs[0])
        bmat.blend_method = 'CLIP' if gm.flags & F_ALPHA else 'BLEND'
        bmat.shadow_method = 'CLIP' if gm.flags & F_ALPHA else 'NONE'
        bmat.show_transparent_back = False
    if gm.flags & F_DOUBLE:
        bmat.use_backface_culling = False


def outline_material():
    m = bpy.data.materials.get("_outline")
    if m:
        return m
    m = bpy.data.materials.new("_outline")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs[0].default_value = lin4(0x2A2233)
    nt.links.new(em.outputs[0], out.inputs[0])
    m.use_backface_culling = True
    m["pongo_outline"] = 1
    return m


def add_outline(obj, width=0.012):
    """Inverted-hull outline for design renders (the game draws its own)."""
    om = outline_material()
    if om.name not in [m.name for m in obj.data.materials if m]:
        obj.data.materials.append(om)
    idx = [m.name if m else "" for m in obj.data.materials].index(om.name)
    sm = obj.modifiers.new("_outline", 'SOLIDIFY')
    sm.thickness = width
    sm.offset = 1.0
    sm.use_flip_normals = True
    sm.use_rim = False
    sm.material_offset = idx
    sm.material_offset_rim = idx
    return sm


# ----------------------------------------------------------------------------- mesher

def _circle(n, r=1.0, start=0.0):
    return [(r * math.cos(start + 2 * math.pi * i / n), r * math.sin(start + 2 * math.pi * i / n)) for i in range(n)]


class Mesher:
    """bmesh builder with transform stack, material slots, UV and colour layers."""

    def __init__(self, name="mesh"):
        self.name = name
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.col = self.bm.loops.layers.color.new("Col")
        self.stack = [Matrix.Identity(4)]
        self.mats = []
        self.mi = 0
        self.tint = (1.0, 1.0, 1.0, 1.0)
        self.uvscale = 1.0

    # --- state
    @property
    def M(self):
        return self.stack[-1]

    def mat(self, gm, tint=None, uvscale=None):
        if isinstance(gm, str):
            gm = _MATS[gm]
        if gm.name not in self.mats:
            self.mats.append(gm.name)
        self.mi = self.mats.index(gm.name)
        self.tint = (1, 1, 1, 1) if tint is None else ((*hexrgb(tint), 1.0) if isinstance(tint, int) else tint)
        if uvscale is not None:
            self.uvscale = uvscale
        return self

    def push(self, m=None):
        self.stack.append(self.M @ (m if m is not None else Matrix.Identity(4)))
        return self

    def pop(self):
        self.stack.pop()
        return self

    def tr(self, x=0, y=0, z=0):
        self.stack[-1] = self.M @ Matrix.Translation((x, y, z))
        return self

    def rot(self, deg, axis='Z'):
        self.stack[-1] = self.M @ Matrix.Rotation(math.radians(deg), 4, axis)
        return self

    def rotv(self, deg, axis_vec):
        self.stack[-1] = self.M @ Matrix.Rotation(math.radians(deg), 4, Vector(axis_vec))
        return self

    def scl(self, x, y=None, z=None):
        y = x if y is None else y
        z = x if z is None else z
        self.stack[-1] = self.M @ Matrix.Diagonal((x, y, z, 1))
        return self

    # --- low level
    def _finish(self, verts, bevel=None, uv='box', smooth=True):
        """Assign material/tint/UV to faces of freshly created verts, bevel if requested."""
        verts = [v for v in verts if v.is_valid]
        faces = set()
        for v in verts:
            faces.update(v.link_faces)
        if bevel and bevel[0] > 0:
            edges = set()
            for f in faces:
                edges.update(f.edges)
            res = bmesh.ops.bevel(self.bm, geom=list(edges) + verts, offset=bevel[0], segments=bevel[1] if len(bevel) > 1 else 2,
                                  profile=0.5, affect='EDGES', clamp_overlap=True)
            faces.update(res.get("faces", []))
            vs = set(verts)
            for f in list(faces):
                if not f.is_valid:
                    faces.discard(f)
            # re-collect all faces connected to the island
            island = set()
            todo = [next(iter(faces))] if faces else []
            while todo:
                f = todo.pop()
                if f in island:
                    continue
                island.add(f)
                for e in f.edges:
                    for g in e.link_faces:
                        if g not in island:
                            todo.append(g)
            faces = island
        for f in faces:
            f.material_index = self.mi
            f.smooth = smooth
            for l in f.loops:
                l[self.col] = self.tint
        if uv == 'box':
            self._box_uv(faces)
        return faces

    def _box_uv(self, faces):
        s = 1.0 / max(self.uvscale, 1e-6)
        for f in faces:
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for l in f.loops:
                p = l.vert.co
                if ax == 0:
                    u, v = (p.y if n.x > 0 else -p.y), p.z
                elif ax == 1:
                    u, v = (-p.x if n.y > 0 else p.x), p.z
                else:
                    u, v = p.x, (p.y if n.z > 0 else -p.y)
                l[self.uv].uv = (u * s, v * s)

    def uv_rect(self, faces, u0, v0, u1, v1, axis=None):
        """Planar-map faces into a UV rectangle (for decals)."""
        faces = list(faces)
        if not faces:
            return
        n = Vector((0, 0, 0))
        for f in faces:
            n += f.normal
        n.normalize()
        if axis is None:
            up = Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((0, 1, 0))
            ua = up.cross(n).normalized()
            va = n.cross(ua).normalized()
        else:
            ua, va = Vector(axis[0]), Vector(axis[1])
        pts = [l.vert.co for f in faces for l in f.loops]
        us = [p.dot(ua) for p in pts]
        vs = [p.dot(va) for p in pts]
        umin, umax, vmin, vmax = min(us), max(us), min(vs), max(vs)
        du = max(umax - umin, 1e-9)
        dv = max(vmax - vmin, 1e-9)
        for f in faces:
            for l in f.loops:
                p = l.vert.co
                l[self.uv].uv = (u0 + (p.dot(ua) - umin) / du * (u1 - u0), v0 + (p.dot(va) - vmin) / dv * (v1 - v0))

    def poly(self, pts, bevel=None, uv='box', smooth=False):
        """Single polygon from 3D points (local space)."""
        vs = [self.bm.verts.new(self.M @ Vector(p)) for p in pts]
        f = self.bm.faces.new(vs)
        f.normal_update()
        return self._finish(vs, bevel, uv, smooth)

    def quad_strip(self, rings, closed=True, cap0=False, cap1=False, uv='box', smooth=True, bevel=None):
        """Loft through rings of 3D points (all rings same length)."""
        bm = self.bm
        M = self.M
        vr = [[bm.verts.new(M @ Vector(p)) for p in ring] for ring in rings]
        n = len(rings[0])
        allv = [v for r in vr for v in r]
        for i in range(len(vr) - 1):
            a, b = vr[i], vr[i + 1]
            rng = range(n) if closed else range(n - 1)
            for j in rng:
                k = (j + 1) % n
                try:
                    bm.faces.new((a[j], a[k], b[k], b[j]))
                except ValueError:
                    pass
        if cap0 and closed:
            try:
                bm.faces.new(list(reversed(vr[0])))
            except ValueError:
                pass
        if cap1 and closed:
            try:
                bm.faces.new(vr[-1])
            except ValueError:
                pass
        bmesh.ops.recalc_face_normals(bm, faces=list({f for v in allv for f in v.link_faces}))
        return self._finish(allv, bevel, uv, smooth)

    # --- primitives
    def box(self, c=(0, 0, 0), s=(1, 1, 1), bevel=None, uv='box', smooth=True):
        M = self.M @ Matrix.Translation(c) @ Matrix.Diagonal((s[0], s[1], s[2], 1))
        r = bmesh.ops.create_cube(self.bm, size=1.0, matrix=M)
        return self._finish(r["verts"], bevel, uv, smooth)

    def rbox(self, c=(0, 0, 0), s=(1, 1, 1), r=0.03, seg=3, uv='box'):
        """Box with rounded (bevelled) edges."""
        r = min(r, min(s) * 0.49)
        return self.box(c, s, bevel=(r, seg), uv=uv)

    def cyl(self, c=(0, 0, 0), r=0.5, h=1.0, seg=24, r2=None, caps=True, bevel=None, uv='box', smooth=True, axis='Z'):
        M = self.M @ Matrix.Translation(c) @ _axis_mat(axis)
        res = bmesh.ops.create_cone(self.bm, cap_ends=caps, cap_tris=False, segments=seg,
                                    radius1=r, radius2=r if r2 is None else r2, depth=h, matrix=M)
        return self._finish(res["verts"], bevel, uv, smooth)

    def sphere(self, c=(0, 0, 0), r=0.5, seg=24, rings=12, s=(1, 1, 1), uv='box'):
        M = self.M @ Matrix.Translation(c) @ Matrix.Diagonal((s[0], s[1], s[2], 1))
        res = bmesh.ops.create_uvsphere(self.bm, u_segments=seg, v_segments=rings, radius=r, matrix=M)
        return self._finish(res["verts"], None, uv, True)

    def ico(self, c=(0, 0, 0), r=0.5, sub=2, s=(1, 1, 1), uv='box', smooth=True):
        M = self.M @ Matrix.Translation(c) @ Matrix.Diagonal((s[0], s[1], s[2], 1))
        res = bmesh.ops.create_icosphere(self.bm, subdivisions=sub, radius=r, matrix=M)
        return self._finish(res["verts"], None, uv, smooth)

    def torus(self, c=(0, 0, 0), R=0.5, r=0.1, seg=32, sides=12, arc=360.0, uv='box', axis='Z'):
        rings = []
        full = abs(arc - 360.0) < 1e-3
        n = seg if full else seg + 1
        for i in range(n):
            a = math.radians(arc) * i / seg
            ca, sa = math.cos(a), math.sin(a)
            ring = []
            for j in range(sides):
                b = 2 * math.pi * j / sides
                d = R + r * math.cos(b)
                ring.append((d * ca, d * sa, r * math.sin(b)))
            rings.append(ring)
        if full:
            rings.append(rings[0])
        self.push(Matrix.Translation(c) @ _axis_mat(axis))
        f = self.quad_strip(rings, closed=True, cap0=not full, cap1=not full, uv=uv)
        self.pop()
        if full:
            bmesh.ops.remove_doubles(self.bm, verts=list({v for fa in f for v in fa.verts}), dist=1e-6)
        return f

    def lathe(self, prof, seg=32, c=(0, 0, 0), axis='Z', uv='box', smooth=True, arc=360.0, bevel=None):
        """Surface of revolution. prof = [(radius, height), ...] from bottom to top."""
        rings = []
        full = abs(arc - 360.0) < 1e-3
        for (r, z) in prof:
            ring = []
            cnt = seg if full else seg + 1
            for i in range(cnt):
                a = math.radians(arc) * i / seg
                ring.append((r * math.cos(a), r * math.sin(a), z))
            rings.append(ring)
        self.push(Matrix.Translation(c) @ _axis_mat(axis))
        # close the ends if the profile starts/ends on the axis
        faces = self.quad_strip(rings, closed=full, uv=uv, smooth=smooth, bevel=bevel)
        self.pop()
        vs = list({v for f in faces for v in f.verts})
        bmesh.ops.remove_doubles(self.bm, verts=vs, dist=1e-6)
        return {f for f in faces if f.is_valid}

    def sweep(self, path, prof, closed=True, cap=True, scale=None, twist=0.0, up=(0, 0, 1), uv='box', smooth=True, rings_out=None):
        """Sweep 2D profile (list of (x, y)) along a 3D path using rotation-minimising frames.
        scale: callable t->(sx, sy) or float list per path point."""
        path = [Vector(p) for p in path]
        n = len(path)
        tang = []
        for i in range(n):
            a = path[max(i - 1, 0)]
            b = path[min(i + 1, n - 1)]
            t = (b - a)
            tang.append(t.normalized() if t.length > 1e-9 else Vector((0, 0, 1)))
        upv = Vector(up)
        if abs(tang[0].dot(upv)) > 0.95:
            upv = Vector((1, 0, 0)) if abs(tang[0].x) < 0.9 else Vector((0, 1, 0))
        nrm = tang[0].cross(upv).normalized()
        binv = tang[0].cross(nrm).normalized()
        frames = [(nrm, binv)]
        for i in range(1, n):
            # double reflection RMF
            v1 = path[i] - path[i - 1]
            c1 = v1.dot(v1)
            if c1 < 1e-12:
                frames.append(frames[-1])
                continue
            rL = frames[-1][0] - (2.0 / c1) * v1.dot(frames[-1][0]) * v1
            tL = tang[i - 1] - (2.0 / c1) * v1.dot(tang[i - 1]) * v1
            v2 = tang[i] - tL
            c2 = v2.dot(v2)
            r = rL - (2.0 / c2) * v2.dot(rL) * v2 if c2 > 1e-12 else rL
            r.normalize()
            b = tang[i].cross(r).normalized()
            frames.append((r, b))
        rings = []
        for i in range(n):
            t = i / max(n - 1, 1)
            sx, sy = (1.0, 1.0)
            if callable(scale):
                s = scale(t)
                sx, sy = (s, s) if isinstance(s, (int, float)) else s
            elif scale is not None:
                s = scale[i]
                sx, sy = (s, s) if isinstance(s, (int, float)) else s
            ang = twist * t
            ca, sa = math.cos(ang), math.sin(ang)
            r, b = frames[i]
            ring = []
            for (px, py) in prof:
                x = (px * ca - py * sa) * sx
                y = (px * sa + py * ca) * sy
                ring.append(tuple(path[i] + r * x + b * y))
            rings.append(ring)
        if rings_out is not None:
            rings_out.extend(rings)
        return self.quad_strip(rings, closed=closed, cap0=cap, cap1=cap, uv=uv, smooth=smooth)

    def tube(self, path, r=0.05, seg=10, cap=True, taper=None, uv='box'):
        prof = _circle(seg, 1.0)
        if taper is None:
            sc = lambda t: r
        elif callable(taper):
            sc = lambda t: r * taper(t)
        else:
            sc = lambda t: r * (1 + (taper - 1) * t)
        return self.sweep(path, prof, closed=True, cap=cap, scale=sc, uv=uv)

    def extrude(self, outline, depth, holes=(), bevel=None, c=(0, 0, 0), uv='box', smooth=False):
        """Extrude a 2D polygon (XY plane) along +Z by depth, centred on Z."""
        bm = self.bm
        M = self.M @ Matrix.Translation(c)
        loops = [outline] + list(holes)
        edges = []
        allv = []
        for lp in loops:
            vs = [bm.verts.new(M @ Vector((x, y, -depth / 2))) for (x, y) in lp]
            allv += vs
            for i in range(len(vs)):
                edges.append(bm.edges.new((vs[i], vs[(i + 1) % len(vs)])))
        res = bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=True, edges=edges)
        faces = [g for g in res["geom"] if isinstance(g, bmesh.types.BMFace)]
        ext = bmesh.ops.extrude_face_region(bm, geom=faces)
        newv = [g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)]
        d = (M.to_3x3() @ Vector((0, 0, depth)))
        bmesh.ops.translate(bm, verts=newv, vec=d)
        bmesh.ops.recalc_face_normals(bm, faces=list({f for v in allv + newv for f in v.link_faces}))
        return self._finish(allv + newv, bevel, uv, smooth)

    def text(self, body, size=1.0, depth=0.1, bevel=0.0, font=FONT_LATIN, c=(0, 0, 0), align='CENTER', res=4, spacing=1.0):
        """3D text in the XY plane (reading along +X, up +Y), extruded along Z."""
        cu = bpy.data.curves.new("_txt", 'FONT')
        cu.body = body
        cu.font = _font(font)
        cu.size = size
        cu.extrude = depth / 2
        cu.bevel_depth = bevel
        cu.bevel_resolution = 2
        cu.resolution_u = res
        cu.align_x = align
        cu.align_y = 'CENTER'
        cu.space_character = spacing
        ob = bpy.data.objects.new("_txt", cu)
        bpy.context.scene.collection.objects.link(ob)
        dg = bpy.context.evaluated_depsgraph_get()
        me = ob.evaluated_get(dg).to_mesh()
        before = set(self.bm.verts)
        tmp = bmesh.new()
        tmp.from_mesh(me)
        bmesh.ops.transform(tmp, matrix=self.M @ Matrix.Translation(c), verts=tmp.verts)
        m2 = bpy.data.meshes.new("_tmp")
        tmp.to_mesh(m2)
        tmp.free()
        self.bm.from_mesh(m2)
        bpy.data.meshes.remove(m2)
        ob.evaluated_get(dg).to_mesh_clear()
        bpy.data.objects.remove(ob)
        bpy.data.curves.remove(cu)
        newv = [v for v in self.bm.verts if v not in before]
        return self._finish(newv, None, 'box', False)

    def merge_object(self, ob, apply_world=True):
        """Append another object's evaluated mesh (keeps its own material slots)."""
        dg = bpy.context.evaluated_depsgraph_get()
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        tmp = bmesh.new()
        tmp.from_mesh(me)
        M = self.M @ (ob.matrix_world if apply_world else Matrix.Identity(4))
        bmesh.ops.transform(tmp, matrix=M, verts=tmp.verts)
        # remap materials
        remap = {}
        for i, m in enumerate(me.materials):
            if m is None:
                continue
            if m.name not in self.mats:
                self.mats.append(m.name)
            remap[i] = self.mats.index(m.name)
        for f in tmp.faces:
            f.material_index = remap.get(f.material_index, self.mi)
        m2 = bpy.data.meshes.new("_tmp")
        tmp.to_mesh(m2)
        tmp.free()
        self.bm.from_mesh(m2)
        bpy.data.meshes.remove(m2)
        ev.to_mesh_clear()

    # --- output
    def obj(self, name=None, coll=None, smooth_angle=40.0, subsurf=0, outline=None):
        name = name or self.name
        me = bpy.data.meshes.new(name)
        self.bm.normal_update()
        self.bm.to_mesh(me)
        self.bm.free()
        for mn in self.mats:
            me.materials.append(_MATS[mn].bmat if mn in _MATS else bpy.data.materials[mn])
        ob = bpy.data.objects.new(name, me)
        link(ob, coll)
        ensure_ao(ob)
        set_smooth(ob, smooth_angle)
        if subsurf:
            sm = ob.modifiers.new("subsurf", 'SUBSURF')
            sm.levels = subsurf
            sm.render_levels = subsurf
            sm.quality = 3
        if outline:
            add_outline(ob, outline)
        return ob


def _axis_mat(axis):
    if axis == 'Z':
        return Matrix.Identity(4)
    if axis == 'X':
        return Matrix.Rotation(math.radians(90), 4, 'Y')
    if axis == 'Y':
        return Matrix.Rotation(math.radians(-90), 4, 'X')
    raise ValueError(axis)


_FONTS = {}


def _font(path):
    if path not in _FONTS:
        _FONTS[path] = bpy.data.fonts.load(path)
    return _FONTS[path]


# ----------------------------------------------------------------------------- curves

def bezier(p0, p1, p2, p3, n=12):
    out = []
    for i in range(n + 1):
        t = i / n
        a = (1 - t) ** 3
        b = 3 * (1 - t) ** 2 * t
        c = 3 * (1 - t) * t * t
        d = t ** 3
        out.append(tuple(a * Vector(p0) + b * Vector(p1) + c * Vector(p2) + d * Vector(p3)))
    return out


def catenary(p0, p1, sag=0.5, n=16):
    p0, p1 = Vector(p0), Vector(p1)
    out = []
    for i in range(n + 1):
        t = i / n
        p = p0.lerp(p1, t)
        p.z -= sag * 4 * t * (1 - t)
        out.append(tuple(p))
    return out


def rounded_rect(w, h, r, seg=4):
    r = min(r, w / 2 - 1e-4, h / 2 - 1e-4)
    pts = []
    for (cx, cy, a0) in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def star_pts(n=5, r0=1.0, r1=0.45, rot=90.0):
    pts = []
    for i in range(2 * n):
        a = math.radians(rot + 180.0 * i / n)
        r = r0 if i % 2 == 0 else r1
        pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


# ----------------------------------------------------------------------------- vertex colours & AO

def ensure_ao(obj, value=1.0):
    me = obj.data
    if "AO" not in me.color_attributes:
        a = me.color_attributes.new("AO", 'FLOAT_COLOR', 'POINT')
        a.data.foreach_set("color", [value] * (4 * len(a.data)))
    return me.color_attributes["AO"]


def bake_ao(objs, samples=64, distance=0.6, ground=True):
    """Bake ambient occlusion into a POINT float attribute 'AO' using Cycles."""
    sc = bpy.context.scene
    prev = sc.render.engine
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = samples
    sc.cycles.device = 'CPU'
    if sc.world is None:
        sc.world = bpy.data.worlds.new("w")
    sc.world.light_settings.distance = distance
    gp = None
    if ground:
        bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.001))
        gp = bpy.context.active_object
    for ob in objs:
        me = ob.data
        if "AO" not in me.color_attributes:
            me.color_attributes.new("AO", 'FLOAT_COLOR', 'POINT')
        me.color_attributes.active_color = me.color_attributes["AO"]
        sc.render.bake.target = 'VERTEX_COLORS'
        activate(ob)
        try:
            bpy.ops.object.bake(type='AO')
        except RuntimeError as e:
            print("AO bake failed", ob.name, e)
    if gp:
        delete(gp)
    sc.render.engine = prev


# ----------------------------------------------------------------------------- armatures & animation

def make_armature(name, bones, coll=None):
    """bones: list of (name, head, tail, parent_name or None, roll_deg)."""
    ad = bpy.data.armatures.new(name)
    ob = bpy.data.objects.new(name, ad)
    link(ob, coll)
    activate(ob)
    bpy.ops.object.mode_set(mode='EDIT')
    ebs = {}
    for (bn, h, t, par, roll) in bones:
        eb = ad.edit_bones.new(bn)
        eb.head = Vector(h)
        eb.tail = Vector(t)
        eb.roll = math.radians(roll)
        ebs[bn] = eb
    for (bn, h, t, par, roll) in bones:
        if par:
            ebs[bn].parent = ebs[par]
            ebs[bn].use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in ob.pose.bones:
        pb.rotation_mode = 'XYZ'
    return ob


def bind_auto(mesh_objs, arm):
    """Parent meshes to the armature with automatic (heat) weights."""
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for m in mesh_objs:
        m.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')


def bind_rigid(mesh_obj, arm, bone):
    """Weight every vertex of mesh_obj fully to one bone."""
    vg = mesh_obj.vertex_groups.get(bone) or mesh_obj.vertex_groups.new(name=bone)
    vg.add(list(range(len(mesh_obj.data.vertices))), 1.0, 'REPLACE')
    if not any(m.type == 'ARMATURE' for m in mesh_obj.modifiers):
        am = mesh_obj.modifiers.new("Armature", 'ARMATURE')
        am.object = arm
    mesh_obj.parent = arm


def new_action(arm, name):
    if arm.animation_data is None:
        arm.animation_data_create()
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data.action = act
    return act


def key(arm, frame, pose, loc=None):
    """pose: {bone: (rx, ry, rz) degrees}; loc: {bone: (x, y, z)} local offsets."""
    for bn, e in pose.items():
        pb = arm.pose.bones[bn]
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = Euler([math.radians(a) for a in e], 'XYZ')
        pb.keyframe_insert("rotation_euler", frame=frame)
    if loc:
        for bn, p in loc.items():
            pb = arm.pose.bones[bn]
            pb.location = Vector(p)
            pb.keyframe_insert("location", frame=frame)


def clear_pose(arm):
    for pb in arm.pose.bones:
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = Euler((0, 0, 0))
        pb.location = Vector((0, 0, 0))
        pb.scale = Vector((1, 1, 1))


# ----------------------------------------------------------------------------- export

C_B2G = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))  # blender -> game
C_G2B = C_B2G.inverted()


def _wstr(f, s):
    b = s.encode("utf-8")
    f.write(struct.pack("<i", len(b)))
    f.write(b)


def export_erm(objs, name, arm=None, clips=(), extra=None):
    """Write build/models/<name>.erm. objs: mesh objects (modifiers applied virtually)."""
    if isinstance(objs, bpy.types.Object):
        objs = [objs]
    dg = bpy.context.evaluated_depsgraph_get()
    if arm is not None:
        arm.data.pose_position = 'REST'
        dg.update()
    bone_names = [b.name for b in arm.data.bones] if arm is not None else []
    mat_names = []
    P, N, UV, COL, MI, BI, BW = [], [], [], [], [], [], []
    for ob in objs:
        hidden = []
        for m in ob.modifiers:
            if m.name == "_outline" and m.show_viewport:
                m.show_viewport = False
                hidden.append(m)
        dg.update()
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        if hasattr(me, "calc_normals_split"):
            me.calc_normals_split()
        nt = len(me.loop_triangles)
        if nt == 0:
            ev.to_mesh_clear()
            continue
        tri_loops = np.empty(nt * 3, np.int32)
        me.loop_triangles.foreach_get("loops", tri_loops)
        tri_mat = np.empty(nt, np.int32)
        me.loop_triangles.foreach_get("material_index", tri_mat)
        loop_vert = np.empty(len(me.loops), np.int32)
        me.loops.foreach_get("vertex_index", loop_vert)
        co = np.empty(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        ln = np.empty(len(me.loops) * 3, np.float32)
        me.loops.foreach_get("normal", ln)
        ln = ln.reshape(-1, 3)
        if me.uv_layers.active:
            uv = np.empty(len(me.loops) * 2, np.float32)
            me.uv_layers.active.data.foreach_get("uv", uv)
            uv = uv.reshape(-1, 2)
        else:
            uv = np.zeros((len(me.loops), 2), np.float32)
        col = np.ones((len(me.loops), 4), np.float32)
        ca = me.color_attributes.get("Col")
        if ca is not None:
            tmp = np.empty(len(ca.data) * 4, np.float32)
            ca.data.foreach_get("color_srgb", tmp)
            tmp = tmp.reshape(-1, 4)
            if ca.domain == 'CORNER':
                col[:, :3] = tmp[:, :3]
            else:
                col[:, :3] = tmp[loop_vert, :3]
        ao = me.color_attributes.get("AO")
        if ao is not None:
            tmp = np.empty(len(ao.data) * 4, np.float32)
            ao.data.foreach_get("color", tmp)
            tmp = tmp.reshape(-1, 4)
            a = tmp[:, 0] if ao.domain == 'CORNER' else tmp[loop_vert, 0]
            col[:, 3] = np.clip(a, 0, 1)
        mw = np.array(ob.matrix_world, dtype=np.float64)
        G = np.array(C_B2G, dtype=np.float64) @ mw
        L = tri_loops
        V = loop_vert[L]
        p = co[V].astype(np.float64)
        p = (np.c_[p, np.ones(len(p))] @ G.T)[:, :3]
        nm = np.linalg.inv(G[:3, :3]).T
        n = ln[L].astype(np.float64) @ nm.T
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        P.append(p.astype(np.float32)); N.append(n.astype(np.float32))
        UV.append(uv[L]); COL.append(col[L])
        # material remap
        local = []
        for m in me.materials:
            nm_ = m.name if m else "_default"
            if nm_ not in mat_names:
                mat_names.append(nm_)
            local.append(mat_names.index(nm_))
        if not local:
            if "_default" not in mat_names:
                mat_names.append("_default")
            local = [mat_names.index("_default")]
        lm = np.array(local, np.int32)
        MI.append(lm[np.clip(tri_mat, 0, len(lm) - 1)])
        if arm is not None:
            nv = len(me.vertices)
            bi = np.zeros((nv, 4), np.uint8)
            bw = np.zeros((nv, 4), np.float32)
            gidx = {g.index: g.name for g in ob.vertex_groups}
            for v in me.vertices:
                ws = []
                for g in v.groups:
                    gn = gidx.get(g.group)
                    if gn in bone_names and g.weight > 1e-4:
                        ws.append((g.weight, bone_names.index(gn)))
                ws.sort(reverse=True)
                ws = ws[:4]
                s = sum(w for w, _ in ws)
                if s <= 0:
                    ws, s = [(1.0, 0)], 1.0
                for k, (w, b) in enumerate(ws):
                    bi[v.index, k] = b
                    bw[v.index, k] = w / s
            BI.append(bi[V]); BW.append(bw[V])
        ev.to_mesh_clear()
        for m in hidden:
            m.show_viewport = True
    if arm is not None:
        arm.data.pose_position = 'POSE'
    P = np.concatenate(P); N = np.concatenate(N); UV = np.concatenate(UV); COL = np.concatenate(COL); MI = np.concatenate(MI)
    path = os.path.join(OUT_MODELS, name + ".erm")
    with open(path, "wb") as f:
        f.write(b"ERM1")
        f.write(struct.pack("<i", 1))
        _wstr(f, name)
        f.write(struct.pack("<i", 1 if arm is not None else 0))
        f.write(struct.pack("<i", len(mat_names)))
        for mn in mat_names:
            bmx = bpy.data.materials.get(mn)
            g = _MATS.get(mn)
            _wstr(f, mn)
            if g is None:
                g = GameMat(mn)
            _wstr(f, g.tex)
            r, gg, b = hexrgb(g.color)
            sr, sg, sb = hexrgb(g.shadow)
            f.write(struct.pack("<3f", r, gg, b))
            f.write(struct.pack("<7f", g.spec, g.rim, g.emis, g.soft, g.outline, g.skin, g.sway))
            f.write(struct.pack("<3f", sr, sg, sb))
            f.write(struct.pack("<i", g.flags))
        nt = len(MI)
        f.write(struct.pack("<i", nt))
        f.write(P.astype("<f4").tobytes())
        f.write(N.astype("<f4").tobytes())
        f.write(UV.astype("<f4").tobytes())
        f.write(COL.astype("<f4").tobytes())
        f.write(MI.astype("<i4").tobytes())
        if arm is not None:
            f.write(np.concatenate(BI).astype(np.uint8).tobytes())
            f.write(np.concatenate(BW).astype("<f4").tobytes())
            _write_skeleton(f, arm)
            _write_clips(f, arm, clips)
        ex = extra or {}
        f.write(struct.pack("<i", len(ex)))
        for k, v in ex.items():
            _wstr(f, k)
            vals = list(v) if hasattr(v, "__iter__") else [v]
            f.write(struct.pack("<i", len(vals)))
            f.write(struct.pack("<%df" % len(vals), *vals))
    print("exported", name, "tris", len(MI), "mats", len(mat_names))
    return path


def _mat_g(m):
    """Blender armature-space matrix -> game space (conjugation)."""
    return C_B2G @ m @ C_G2B


def _write_skeleton(f, arm):
    bones = arm.data.bones
    names = [b.name for b in bones]
    f.write(struct.pack("<i", len(bones)))
    for b in bones:
        _wstr(f, b.name)
        f.write(struct.pack("<i", names.index(b.parent.name) if b.parent else -1))
        rest = _mat_g(b.matrix_local)
        f.write(struct.pack("<16f", *[rest[r][c] for c in range(4) for r in range(4)]))
        f.write(struct.pack("<i", 1 if b.name.startswith("dyn") else 0))


def _write_clips(f, arm, clips):
    """clips: list of (action_name, loop_bool). Samples armature-space poses per frame."""
    sc = bpy.context.scene
    bones = arm.data.bones
    names = [b.name for b in bones]
    f.write(struct.pack("<i", len(clips)))
    for (an, loop) in clips:
        act = bpy.data.actions[an]
        arm.animation_data.action = act
        f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
        if loop:
            f1 -= 1  # last key repeats the first
        nf = f1 - f0 + 1
        _wstr(f, an)
        f.write(struct.pack("<fii", float(sc.render.fps), nf, 1 if loop else 0))
        for fr in range(f0, f1 + 1):
            sc.frame_set(fr)
            dgm = {}
            for pb in arm.pose.bones:
                dgm[pb.name] = _mat_g(pb.matrix)
            for b in bones:
                Mw = dgm[b.name]
                if b.parent:
                    Ml = dgm[b.parent.name].inverted() @ Mw
                else:
                    Ml = Mw
                loc, rot, _s = Ml.decompose()
                f.write(struct.pack("<7f", rot.x, rot.y, rot.z, rot.w, loc.x, loc.y, loc.z))
    sc.frame_set(0)


# ----------------------------------------------------------------------------- design renders

def setup_eevee(res=(1080, 1920), samples=32, bloom=True, film_transparent=False):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.eevee.taa_render_samples = samples
    sc.eevee.use_bloom = bloom
    sc.eevee.bloom_threshold = 1.0
    sc.eevee.bloom_intensity = 0.08
    sc.eevee.bloom_radius = 5.0
    sc.eevee.use_soft_shadows = True
    sc.eevee.shadow_cascade_size = '4096'
    sc.eevee.shadow_cube_size = '1024'
    sc.eevee.use_gtao = False
    sc.render.film_transparent = film_transparent
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.render.image_settings.file_format = 'PNG'
    return sc


def world_sky(top=0x5CA8F0, horizon=0xCDEBFF, strength=1.0):
    sc = bpy.context.scene
    w = sc.world or bpy.data.worlds.new("world")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    grad = nt.nodes.new('ShaderNodeTexGradient'); grad.gradient_type = 'LINEAR'
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = lin4(horizon)
    ramp.color_ramp.elements[1].color = lin4(top)
    ramp.color_ramp.elements[0].position = 0.5
    ramp.color_ramp.elements[1].position = 0.75
    nt.links.new(sep.outputs["Z"], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], bg.inputs[0])
    bg.inputs[1].default_value = strength
    # visible to the camera but contributes no lighting: the toon shader owns ambient
    lp = nt.nodes.new('ShaderNodeLightPath')
    dark = nt.nodes.new('ShaderNodeBackground')
    dark.inputs[0].default_value = (0, 0, 0, 1)
    dark.inputs[1].default_value = 0.0
    mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(lp.outputs["Is Camera Ray"], mx.inputs[0])
    nt.links.new(dark.outputs[0], mx.inputs[1])
    nt.links.new(bg.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs[0])
    return w


def sun(rot=(50, 0, 35), energy=3.0, color=0xFFF4E0, angle=0.02):
    ld = bpy.data.lights.new("sun", 'SUN')
    ld.energy = energy
    ld.color = hexrgb(color)
    ld.angle = angle
    ob = bpy.data.objects.new("sun", ld)
    link(ob)
    ob.rotation_euler = Euler([math.radians(a) for a in rot])
    return ob


def camera(loc, target, lens=35.0, ortho=None):
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    if ortho:
        cd.type = 'ORTHO'
        cd.ortho_scale = ortho
    cd.clip_start = 0.05
    cd.clip_end = 2000
    ob = bpy.data.objects.new("cam", cd)
    link(ob)
    ob.location = Vector(loc)
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = ob
    return ob


def render(path, engine=None):
    sc = bpy.context.scene
    if engine:
        sc.render.engine = engine
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("rendered", path)


def set_light_tint(light=0xFFF6E8, shadow=0x6A5FA8, rimc=0xFFF1D8):
    """Set time-of-day tints on every toon material instance."""
    g = _toon_group()
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        for n in m.node_tree.nodes:
            if n.type == 'GROUP' and n.node_tree == g:
                n.inputs["LightTint"].default_value = lin4(light)
                n.inputs["ShadowTint"].default_value = lin4(shadow)
                n.inputs["RimColor"].default_value = lin4(rimc)
