"""
Greenery in the Genshin-like scenery style: no bare ground anywhere beside the line.

Genshin's towns and fields read lush because every unpaved patch is covered (grass tufts, wildflowers, bushes and
round clumpy trees in layers from the verge out to the hills) and because foliage is shaded as one soft shape, not
as many little facets. Here that means:

  * tufts: a few curved blades per tuft whose normals point straight up, so grass shades like the ground under it
    and the cel terminator never breaks it into noise;
  * flowers: five-petal stars and round heads in a small palette (white, butter yellow, pink, lilac, hydrangea blue);
  * bushes and tree canopies: clusters of lobes whose normals come from one ellipsoid per clump, so each clump has
    one clean light side and one clean shade side, with the ink outline giving the bumpy silhouette;
  * plain colour materials only: the texture atlas cuts triangles at every tiled repeat (see blender/lib/gamelod.py),
    and at these sizes the colour and the outline carry the look.

Every builder takes lod 0, 1 or 2 (near, middle, far tiers of SakuraWorld) and builds that tier directly, since
decimating would throw the soft normals away.
"""
import math, random
import bpy
from mathutils import Vector, Matrix
import erlib as E

V = Vector

LEAF = ("gr_leaf", "gr_leaf_dark", "gr_leaf_light", "gr_leaf_pink", "gr_hydrangea", "gr_hedge")
BLADE = ("gr_blade", "gr_blade_light", "gr_susuki", "gr_ivy", "gr_ivy_light")


def mats():
    M = E.mat
    M("gr_leaf", 0x5DAE55, soft=0.35, rim=0.3, outline=0.7, shadow=0x3F7A6A, flags=E.F_FOLIAGE)
    M("gr_leaf_dark", 0x3F9150, soft=0.35, rim=0.25, outline=0.7, shadow=0x2F5E5E, flags=E.F_FOLIAGE)
    M("gr_leaf_light", 0x8CC965, soft=0.35, rim=0.3, outline=0.7, shadow=0x5E8E6A, flags=E.F_FOLIAGE)
    M("gr_leaf_pink", 0xF5BCD3, soft=0.35, rim=0.3, outline=0.6, shadow=0xC88AB8, flags=E.F_FOLIAGE)
    M("gr_hedge", 0x4C9E52, soft=0.35, rim=0.25, outline=0.7, shadow=0x336B5E, flags=E.F_FOLIAGE)
    M("gr_hydrangea", 0x8DA6EE, soft=0.35, rim=0.3, outline=0.6, shadow=0x6A6AC0, flags=E.F_FOLIAGE)
    M("gr_blade", 0x7CC457, soft=0.4, rim=0.2, outline=0.0, shadow=0x5A9A62, flags=E.F_DOUBLE | E.F_NOCAST | E.F_FOLIAGE)
    M("gr_blade_light", 0xA6D96A, soft=0.4, rim=0.2, outline=0.0, shadow=0x76A866, flags=E.F_DOUBLE | E.F_NOCAST | E.F_FOLIAGE)
    M("gr_susuki", 0xF1E2BE, soft=0.4, rim=0.3, outline=0.0, shadow=0xC4AFA8, flags=E.F_DOUBLE | E.F_NOCAST | E.F_FOLIAGE)
    M("gr_ivy", 0x4E9E4C, soft=0.4, rim=0.2, outline=0.0, shadow=0x3A6E5C, flags=E.F_DOUBLE | E.F_NOCAST | E.F_FOLIAGE)
    M("gr_ivy_light", 0x78BE5A, soft=0.4, rim=0.2, outline=0.0, shadow=0x55886A, flags=E.F_DOUBLE | E.F_NOCAST | E.F_FOLIAGE)
    M("gr_glory", 0x7E8EF2, soft=0.3, rim=0.3, emis=0.05, outline=0.0, flags=E.F_DOUBLE | E.F_NOCAST)
    M("gr_bark", 0x7A5A48, soft=0.15, rim=0.2, outline=0.8, shadow=0x5A4058)
    M("gr_soil", 0x8C6F55, soft=0.2, rim=0.0, outline=0.0)
    M("gr_stone", 0xB8B2A8, soft=0.2, rim=0.2, outline=0.7, shadow=0x8A86A0)
    for nm, col in (("gr_fl_white", 0xFFFDF4), ("gr_fl_yellow", 0xFFE070), ("gr_fl_pink", 0xFF9EC0),
                    ("gr_fl_lilac", 0xC6A8F2), ("gr_fl_red", 0xF2645A), ("gr_fl_center", 0xF7B733)):
        M(nm, col, soft=0.3, rim=0.3, emis=0.05, outline=0.0, flags=E.F_NOCAST)


FLOWERS = ("gr_fl_white", "gr_fl_yellow", "gr_fl_pink", "gr_fl_lilac", "gr_fl_white", "gr_fl_red")


# ----------------------------------------------------------------------------- small pieces (on a Mesher)

def tuft(m, x, y, z, rnd, h=0.24, blades=6, light=False):
    """A soft clump of thin curved grass blades (two triangles each), fanned out from one root."""
    m.mat("gr_blade_light" if light else "gr_blade")
    a0 = rnd.uniform(0, 2 * math.pi)
    for k in range(blades):
        a = a0 + k * 2 * math.pi / blades + rnd.uniform(-0.3, 0.3)
        lean = rnd.uniform(0.2, 0.45)
        hh = h * rnd.uniform(0.65, 1.15)
        w = rnd.uniform(0.018, 0.028)
        ca, sa = math.cos(a), math.sin(a)
        px, py = -sa * w, ca * w                       # blade width across its lean
        bx, by = x + ca * 0.02, y + sa * 0.02
        mid = (bx + ca * lean * hh * 0.35, by + sa * lean * hh * 0.35, z + hh * 0.6)
        tip = (bx + ca * lean * hh, by + sa * lean * hh, z + hh)
        m.poly([(bx - px, by - py, z), (bx + px, by + py, z), (mid[0] + px * 0.7, mid[1] + py * 0.7, mid[2]),
                (mid[0] - px * 0.7, mid[1] - py * 0.7, mid[2])])
        m.poly([(mid[0] - px * 0.7, mid[1] - py * 0.7, mid[2]), (mid[0] + px * 0.7, mid[1] + py * 0.7, mid[2]), tip])


def flower(m, x, y, z, rnd, kind=None, r=None):
    """A five-petal star on a short stem, facing up."""
    kind = kind or rnd.choice(FLOWERS)
    r = r or rnd.uniform(0.06, 0.09)
    zz = z + rnd.uniform(0.14, 0.3)
    m.mat("gr_blade")
    m.poly([(x - 0.01, y, z), (x + 0.01, y, z), (x, y, zz)])
    m.mat(kind)
    rot = rnd.uniform(0, 1.3)
    pts = []
    for k in range(10):
        a = rot + k * math.pi / 5
        rr = r if k % 2 == 0 else r * 0.5
        pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr, zz))
    m.poly(pts)
    m.poly(pts[::-1])
    m.mat("gr_fl_center")
    m.poly([(x + math.cos(a) * r * 0.3, y + math.sin(a) * r * 0.3, zz + 0.004) for a in (0, 2.1, 4.2)])


def flowers(m, x, y, z, rnd, n=None):
    """A little patch of one kind of flower among a couple of tufts."""
    kind = rnd.choice(FLOWERS)
    for k in range(n or rnd.randint(3, 5)):
        flower(m, x + rnd.uniform(-0.18, 0.18), y + rnd.uniform(-0.18, 0.18), z, rnd, kind=kind)
    tuft(m, x, y, z, rnd, blades=5)


def susuki(m, x, y, z, rnd, h=None, lod=0):
    """Japanese pampas grass: a fountain of long blades with a few cream seed plumes nodding over the top."""
    h = h or rnd.uniform(0.85, 1.15)
    tuft(m, x, y, z, rnd, h=h * 0.75, blades=(9, 5)[min(lod, 1)], light=rnd.random() < 0.4)
    m.mat("gr_susuki")
    for k in range((4, 2)[min(lod, 1)]):
        a = rnd.uniform(0, 2 * math.pi)
        lean = rnd.uniform(0.15, 0.35)
        ca, sa = math.cos(a), math.sin(a)
        base = V((x + ca * 0.03, y + sa * 0.03, z + h * 0.55))
        tip = V((x + ca * lean * h, y + sa * lean * h, z + h * rnd.uniform(0.95, 1.1)))
        side = V((-sa, ca, 0)) * 0.035
        mid = base.lerp(tip, 0.55) + V((0, 0, 0.04))
        m.poly([tuple(base - side * 0.3), tuple(base + side * 0.3), tuple(mid + side), tuple(mid - side)])
        m.poly([tuple(mid - side), tuple(mid + side), tuple(tip)])


def ivy(m, x, y, z0, rnd, face=1, h=1.2, leaves=12):
    """A vine climbing a fence panel in the plane x: pairs of leaves up a wandering stem, now and then a morning
    glory. face (+1/-1) is the side of the panel it grows on."""
    yy, zz = y, z0
    for k in range(leaves):
        zz += h / leaves
        yy += rnd.uniform(-0.1, 0.1)
        for sd in (-1, 1):
            if rnd.random() < 0.15:
                continue
            sz = rnd.uniform(0.06, 0.1)
            cy, cz = yy + sd * sz * 0.6, zz + rnd.uniform(-0.03, 0.03)
            xx = x + face * rnd.uniform(0.025, 0.06)
            m.mat("gr_ivy" if rnd.random() < 0.65 else "gr_ivy_light")
            m.poly([(xx, cy - sz * 0.55, cz), (xx + face * 0.02, cy, cz - sz * 0.55), (xx, cy + sz * 0.55, cz),
                    (xx - face * 0.01, cy, cz + sz * 0.6)])
        if rnd.random() < 0.18:
            r = rnd.uniform(0.045, 0.06)
            xx = x + face * 0.07
            m.mat("gr_glory")
            m.poly([(xx, yy + math.cos(a) * r, zz + math.sin(a) * r) for a in [k2 * 2 * math.pi / 5 for k2 in range(5)]])
            m.mat("gr_fl_white")
            m.poly([(xx + face * 0.004, yy + math.cos(a) * r * 0.35, zz + math.sin(a) * r * 0.35) for a in (0, 2.1, 4.2)])


def meadow(m, x0, x1, y0, y1, z, rnd, density=2.0, bloom=0.35, lod=0, light=0.3, h=0.24):
    """Tufts (and flowers) scattered over a rectangle; density = tufts per square metre at LOD0."""
    area = abs(x1 - x0) * abs(y1 - y0)
    n = int(area * density * (1.0, 0.35, 0.0)[lod])
    for _ in range(n):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        if rnd.random() < bloom * 0.3:
            flowers(m, x, y, z, rnd, n=3 if lod == 0 else 2)
        else:
            tuft(m, x, y, z, rnd, h=h, blades=6 if lod == 0 else 4, light=rnd.random() < light)


# ----------------------------------------------------------------------------- clumps with soft normals

class Clumps:
    """Collects the ellipsoids that give foliage its normals (call soften(ob) once the object exists)."""

    def __init__(self):
        self.blobs = []

    def add(self, c, r):
        self.blobs.append((V(c), V(r)))

    def lobes(self, m, mat, c, r, n, rnd, lod=0, spread=0.62, squash=0.9, core=True):
        """A clump inside the ellipsoid (c, r): a core plus n smaller lobes bulging out of its surface, so the
        silhouette is cloud-like while the shading (soften) stays one smooth shape."""
        m.mat(mat)
        c, r = V(c), V(r)
        self.add(c, r)
        seg, rings = ((11, 7), (8, 5), (6, 4))[lod]
        if core:
            m.sphere(tuple(c), 1.0, seg, rings, s=(r.x * 0.82, r.y * 0.82, r.z * 0.82 * squash))
        for k in range(n):
            a = rnd.uniform(0, 2 * math.pi) if k == 0 else a + 2 * math.pi / n * rnd.uniform(0.7, 1.3)
            b = rnd.uniform(-0.15, 0.85)
            o = V((math.cos(a) * math.cos(b), math.sin(a) * math.cos(b), math.sin(b))) * spread
            lr = rnd.uniform(0.42, 0.58)
            cc = c + V((o.x * r.x, o.y * r.y, o.z * r.z))
            m.sphere(tuple(cc), 1.0, seg, rings, s=(r.x * lr, r.y * lr, r.z * lr * squash))

    def soften(self, ob):
        """Foliage loops take the normal of the ellipsoid they sit in, grass blades point up, the rest is kept."""
        me = ob.data
        E.set_smooth(ob, 35.0)
        if hasattr(me, "calc_normals_split"):
            me.calc_normals_split()
        names = [s.material.name if s.material else "" for s in ob.material_slots]
        out = []
        for poly in me.polygons:
            mn = names[poly.material_index] if poly.material_index < len(names) else ""
            leaf, blade = mn in LEAF, mn in BLADE or mn.startswith("gr_fl_")
            for li in poly.loop_indices:
                if blade:
                    out.append((0.0, 0.0, 1.0))
                elif leaf and self.blobs:
                    p = me.vertices[me.loops[li].vertex_index].co
                    best, bd = None, 1e9
                    for c, r in self.blobs:
                        d = V(((p.x - c.x) / r.x, (p.y - c.y) / r.y, (p.z - c.z) / r.z))
                        if d.length < bd:
                            bd, best = d.length, (c, r)
                    c, r = best
                    n = V(((p.x - c.x) / (r.x * r.x), (p.y - c.y) / (r.y * r.y), (p.z - c.z) / (r.z * r.z)))
                    n = n.normalized() if n.length > 1e-9 else V((0, 0, 1))
                    # a little upward bias: the tops catch the sun like Genshin canopies
                    n = (n + V((0, 0, 0.25))).normalized()
                    out.append(tuple(n))
                else:
                    out.append(tuple(me.loops[li].normal))
        me.normals_split_custom_set(out)
        return ob


def tree(m, cl, x, y, z, rnd, h=None, lod=0, mat="gr_leaf", pink=False):
    """A round garden tree: tapered trunk with two limbs and a canopy of two or three cloud-like clumps."""
    h = h or rnd.uniform(4.5, 7.0)
    m.mat("gr_bark")
    tr = 0.12 + h * 0.018
    m.cyl((x, y, z + h * 0.3), r=tr, r2=tr * 0.7, h=h * 0.6, seg=(10, 7, 5)[lod])
    if lod < 2:
        for s in (-1, 1):
            m.tube([V((x, y, z + h * 0.45)), V((x + s * h * 0.12, y + rnd.uniform(-0.3, 0.3), z + h * 0.62))],
                   r=tr * 0.45, seg=6)
    crown = V((x, y, z + h * 0.7))
    R = h * 0.34
    mat = "gr_leaf_pink" if pink else mat
    cl.lobes(m, mat, crown, (R, R, R * 0.85), (7, 4, 0)[lod], rnd, lod=lod)
    if lod < 2:
        for k in range(2):
            a = rnd.uniform(0, 2 * math.pi)
            c = crown + V((math.cos(a) * R * 0.8, math.sin(a) * R * 0.8, -R * 0.3))
            cl.lobes(m, mat if (pink or rnd.random() < 0.5) else "gr_leaf_light", c, (R * 0.6, R * 0.6, R * 0.5),
                     (4, 2, 0)[lod], rnd, lod=lod)


def bush(m, cl, x, y, z, rnd, r=0.6, lod=0, mat=None):
    """A round shrub; hydrangeas carry clusters of blue-lilac flower balls on the green."""
    hyd = mat == "gr_hydrangea" or (mat is None and rnd.random() < 0.25)
    mat = "gr_leaf_dark" if hyd else (mat or rnd.choice(("gr_leaf", "gr_leaf_dark", "gr_leaf")))
    cl.lobes(m, mat, (x, y, z + r * 0.62), (r * 1.2, r, r * 0.8), (4, 2, 0)[lod], rnd, lod=lod)
    if hyd and lod < 2:
        for k in range((5, 3)[lod]):
            a = rnd.uniform(0, 2 * math.pi)
            b = rnd.uniform(0.2, 0.9)
            p = V((x + math.cos(a) * math.cos(b) * r * 1.1, y + math.sin(a) * math.cos(b) * r * 0.9,
                   z + r * 0.62 + math.sin(b) * r * 0.75))
            cl.lobes(m, "gr_hydrangea", tuple(p), (0.2, 0.2, 0.18), 2 if lod == 0 else 0, rnd, lod=max(lod, 1))


def hedge(m, cl, x0, x1, y, z, rnd, h=1.0, w=0.8, lod=0):
    """A clipped hedge along x from x0 to x1: a row of overlapping clumps."""
    n = max(1, int(abs(x1 - x0) / (1.4 if lod == 0 else 2.8)))
    for k in range(n):
        x = x0 + (x1 - x0) * (k + 0.5) / n
        L = abs(x1 - x0) / n
        cl.lobes(m, "gr_hedge", (x, y, z + h * 0.55), (L * 0.72, w * 0.55, h * 0.55), (3, 2, 0)[lod], rnd,
                 lod=lod, spread=0.45, squash=1.0)


# ----------------------------------------------------------------------------- design render

def design_greenery():
    import studio, city
    E.reset()
    studio.stage(res=(1400, 900), floor=True, floor_col=0x8FC46A)
    mats()
    rnd = random.Random(3)
    m = E.Mesher("greens")
    cl = Clumps()
    meadow(m, -4, 4, -2, 3, 0.0, rnd, density=7.0, bloom=0.35)
    for k, x in enumerate((-3.0, 0.0, 3.0)):
        tree(m, cl, x, 6.0, 0.0, rnd, h=5.5 + k * 0.6, pink=(k == 1))
    for k, x in enumerate((-3.5, -1.8, 1.6, 3.4)):
        bush(m, cl, x, 2.8, 0.0, rnd, r=0.6, mat="gr_hydrangea" if k == 1 else None)
    hedge(m, cl, -4, 4, 4.2, 0.0, rnd)
    ob = cl.soften(m.obj("greens", smooth_angle=35))
    E.add_outline(ob, 0.01)
    studio.aim_sun(20)
    studio.shoot("greenery", target=(0, 3.0, 1.6), dist=11, yaw=10, pitch=12, lens=32)
