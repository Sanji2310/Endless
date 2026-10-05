"""
Sky Glide kit. Its own theme and colours, drawn in the Sakura Line art style (soft toon shading,
lilac shadows, thin ink outlines, puffy cloud masses, dense small detail):

  crow_body / crow_wing   Karasu crow; the wing is one side (mirror for the other), hinged at its root
                          -> Ride.H_CROW, H_FLOCK (the game flaps the wings)
  islet         floating rock islet with a tree, flowers, roots and a trickle   -> Ride.H_ISLET
  thundercloud  little storm cloud with a spark and rain (burst through, jolt)   -> Ride.H_STORM
  chime_cable   cable strung across the valley with fuurin wind chimes and flags -> Ride.H_CABLE
  spire         rock spire with a pine and a shrine on top                       -> Ride.H_SPIRE
  cloud         Ghibli cumulus puff (same method as the sakura canopy); the glider bursts through -> Ride.H_CLOUD
  thermal_ring  rising-air ring marker                                           -> Ride.H_THERMAL
  wind_streak   gust ribbon                                                      -> Ride.H_GUST
  terraces      rice-terrace valley tile far below (backdrop)
Origin at the hazard centre; everything faces +Y (she flies +Y).
"""
import math, random
import bpy
from mathutils import Vector, Matrix
import erlib as E

V = Vector


def mats():
    M = E.mat
    M("sk_crow", 0x2C2A3C, rim=0.5, soft=0.1, spec=0.3, shadow=0x1E1A30)
    M("sk_crow_sheen", 0x4A5A8A, rim=0.5, soft=0.1, spec=0.5)
    M("sk_beak", 0x3A3640, rim=0.3, soft=0.1, spec=0.4)
    M("sk_eye", 0xFFE36A, emis=0.4, rim=0.1, soft=0.05, outline=0.5)
    M("sk_paper", 0xFFF4E2, rim=0.25, soft=0.15, flags=E.F_DOUBLE)
    M("sk_paper_red", 0xE8473C, rim=0.25, soft=0.15, flags=E.F_DOUBLE)
    M("sk_paper_blue", 0x3A6FD8, rim=0.25, soft=0.15, flags=E.F_DOUBLE)
    M("sk_paper_pink", 0xF9B8CC, rim=0.25, soft=0.15, flags=E.F_DOUBLE)
    M("sk_ink", 0x22202A, rim=0.0, soft=0.1, outline=0.0)
    M("sk_stick", 0xC9A86A, rim=0.2, soft=0.1)
    M("sk_string", 0xF7F4EC, rim=0.1, soft=0.1, outline=0.0)
    M("sk_glow", 0xFFC46A, emis=1.2, rim=0.1, soft=0.05, flags=E.F_DOUBLE, outline=0.4)
    M("sk_glow_core", 0xFFF2C0, emis=2.0, rim=0.0, soft=0.05, outline=0.0)
    M("sk_cable", 0x3A3E4E, rim=0.1, soft=0.1, outline=0.0)
    M("sk_glass", 0xBFEAFF, spec=1.0, rim=0.5, soft=0.04, flags=E.F_GLASS, outline=0.5)
    M("sk_rock", 0xF2DEB0, rim=0.3, soft=0.14, shadow=0xB8A6B0)
    M("sk_rock_dark", 0xDFC59A, rim=0.25, soft=0.14, shadow=0xA898A8)
    M("sk_rock_band", 0xC9AA80, rim=0.2, soft=0.12, shadow=0x96889C)
    M("sk_pine", 0x5E9A6A, rim=0.25, soft=0.2, flags=E.F_FOLIAGE, sway=0.2, shadow=0x5A6A9A)
    M("sk_bark", 0x6E4A3A, rim=0.2, soft=0.12)
    M("sk_red", 0xE8473C, rim=0.3, soft=0.1)
    M("sk_cloud", 0xFFFFFF, rim=0.4, soft=0.35, flags=E.F_NOCAST | getattr(E, "F_CLOUD", 0), outline=0.0, shadow=0xC9C4EA)
    M("sk_ring", 0xFFF6C8, emis=0.8, rim=0.0, soft=0.1, flags=E.F_NOCAST, outline=0.0)
    M("sk_streak", 0xFFFFFF, emis=0.6, rim=0.0, soft=0.1, flags=E.F_NOCAST | E.F_DOUBLE, outline=0.0)
    M("sk_terrace", 0x9ACD6E, rim=0.1, soft=0.2, shadow=0x9A9AD0)
    M("sk_terrace_water", 0x8FC8D2, rim=0.1, soft=0.2, spec=0.15, shadow=0x7FA0C8)
    M("sk_roof", 0x4A4E66, rim=0.2, soft=0.1)
    M("sk_wall", 0xF2EAD8, rim=0.2, soft=0.1)
    M("sk_grass", 0xA8D46E, rim=0.2, soft=0.2, shadow=0x9A9AD0)
    M("sk_tree", 0x8CCB6A, rim=0.3, soft=0.25, shadow=0x6E9AA8)
    M("sk_tree2", 0x6FB46A, rim=0.3, soft=0.25, shadow=0x5E88A0)
    M("sk_flower", 0xFFD25E, rim=0.3, soft=0.2, emis=0.08)
    M("sk_flower2", 0xFF9E7A, rim=0.3, soft=0.2, emis=0.05)
    M("sk_timber", 0x7A5A48, rim=0.25, soft=0.1, shadow=0x5E4A70)
    M("sk_moss", 0x96C66A, rim=0.2, soft=0.15)
    M("sk_far", 0xA6C4E2, rim=0.1, soft=0.3, outline=0.0, flags=E.F_NOCAST, shadow=0xA6B0E0)
    M("sk_far2", 0xC4CEEC, rim=0.1, soft=0.3, outline=0.0, flags=E.F_NOCAST, shadow=0xBAB8E8)
    M("sk_snow", 0xF6F8FF, rim=0.1, soft=0.3, outline=0.0, flags=E.F_NOCAST)
    M("sk_water", 0xBFEAF6, rim=0.2, soft=0.15, emis=0.15, flags=E.F_WATER | E.F_NOCAST, outline=0.0)
    M("sk_foam", 0xFFFFFF, rim=0.2, soft=0.3, emis=0.2, flags=E.F_NOCAST, outline=0.0)
    M("sk_rope", 0xD8C29A, rim=0.2, soft=0.1)
    M("sk_grass_a", 0x7CC65C, rim=0.2, soft=0.25, flags=E.F_FOLIAGE | E.F_DOUBLE, sway=0.4, outline=0.0, shadow=0x6E9AB0)
    M("sk_grass_b", 0x9AD46A, rim=0.2, soft=0.25, flags=E.F_FOLIAGE | E.F_DOUBLE, sway=0.4, outline=0.0, shadow=0x7EA6B0)
    M("sk_grass_tip", 0xD2E888, rim=0.3, soft=0.25, flags=E.F_FOLIAGE | E.F_DOUBLE, sway=0.5, outline=0.0, shadow=0x92B0A8)
    M("sk_tree_hi", 0xBAE07C, rim=0.35, soft=0.25, shadow=0x7EA6A8)
    M("sk_fl_white", 0xFFFBF0, rim=0.3, soft=0.2, emis=0.05, outline=0.0)
    M("sk_fl_pink", 0xFFB4CC, rim=0.3, soft=0.2, emis=0.05, outline=0.0)
    M("sk_fl_blue", 0x9EC2FF, rim=0.3, soft=0.2, emis=0.05, outline=0.0)
    M("sk_sail", 0xFFF8EC, rim=0.3, soft=0.15, flags=E.F_DOUBLE)
    M("sk_vine", 0x5FA866, rim=0.2, soft=0.25, flags=E.F_FOLIAGE | E.F_DOUBLE, sway=0.5, outline=0.0, shadow=0x5A7AA0)
    M("sk_storm", 0xC9CCE6, rim=0.45, soft=0.35, flags=E.F_NOCAST | getattr(E, "F_CLOUD", 0), outline=0.0, shadow=0x7E78B8)
    M("sk_storm_dark", 0x8E88BC, rim=0.3, soft=0.3, flags=E.F_NOCAST, outline=0.0, shadow=0x5E5694)
    M("sk_bolt", 0xFFF3A8, emis=1.6, rim=0.0, soft=0.05, flags=E.F_NOCAST, outline=0.0)


# ----------------------------------------------------------------------------- crow

def crow():
    """Body (head, beak, eyes, tail fan, tucked feet) and one wing (+X side, root at origin, span along +X)."""
    mats()
    b = E.Mesher("crow_body")
    b.mat("sk_crow")
    b.sphere((0, 0, 0), 1.0, 16, 10, s=(0.13, 0.26, 0.13))
    b.sphere((0, 0.24, 0.06), 0.1, 14, 10)
    b.mat("sk_crow_sheen")
    b.sphere((0, 0.05, 0.08), 1.0, 12, 8, s=(0.09, 0.18, 0.06))
    b.mat("sk_beak")
    b.cyl((0, 0.37, 0.05), r=0.035, h=0.16, seg=8, r2=0.004, axis='Y')
    b.mat("sk_eye")
    for sx in (-1, 1):
        b.sphere((sx * 0.065, 0.29, 0.09), 0.022, 8, 6)
    b.mat("sk_crow")
    for k in range(5):
        a = math.radians(-30 + 15 * k)
        b.push(Matrix.Translation((0, -0.22, 0.0)) @ Matrix.Rotation(a, 4, 'Z'))
        b.box((0, -0.12, 0), (0.06, 0.24, 0.015), smooth=False)
        b.pop()
    bo = b.obj("crow_body", smooth_angle=60)
    w = E.Mesher("crow_wing")
    # broad wing with real thickness so it reads head-on too: covert panel, then fingered primaries fanning out
    w.mat("sk_crow")
    w.box((0.17, 0.0, 0.0), (0.34, 0.22, 0.045), smooth=False)
    w.ico((0.04, 0.02, 0.0), 0.09, 1, s=(1.2, 1.3, 0.6))             # shoulder, blends into the body
    for k in range(6):                                                  # primaries, each a tapered thick feather
        a = math.radians(-8 - 13 * k)
        w.push(Matrix.Translation((0.32, 0.06 - 0.03 * k, 0.0)) @ Matrix.Rotation(a, 4, 'Z') @
               Matrix.Rotation(math.radians(4 * k), 4, 'X'))
        w.cyl((0.17, 0, 0), r=0.035, h=0.36 - 0.025 * k, seg=6, r2=0.012, axis='X')
        w.pop()
    w.mat("sk_crow_sheen")
    w.box((0.16, 0.03, 0.026), (0.28, 0.12, 0.012), smooth=False)       # blue-black sheen on the coverts
    wo = w.obj("crow_wing", smooth_angle=0)
    return bo, wo



def chime_cable(name="chime_cable", span=24.0, rnd_seed=4, pylon=24.0):
    """Cable across the gorge with glass wind chimes (fuurin), paper strips and small flags. Each end is tied off
    on a braced timber pylon that stands on the valley floor (`pylon` m tall below the cable), so the cable is
    held up wherever the game strings it; the pylons stand outside the glide (Ride: SKY_HALF + 3)."""
    mats()
    rnd = random.Random(rnd_seed)
    m = E.Mesher(name)
    for sx in (-1, 1):
        x = sx * span / 2
        m.mat("sk_timber")
        for dy in (-0.35, 0.35):
            m.box((x, dy, 0.9 - pylon / 2), (0.2, 0.2, pylon + 0.6), smooth=False)
        z = 0.2
        while z > -pylon + 1.5:
            m.box((x, 0, z), (0.16, 0.85, 0.12), smooth=False)                           # rungs
            for sg in (-1, 1):
                m.push(Matrix.Translation((x, 0, z - 1.0)) @ Matrix.Rotation(math.radians(20 * sg), 4, 'X'))
                m.box((0, 0, 0), (0.09, 0.09, 2.1), smooth=False)                        # X brace
                m.pop()
            z -= 2.0
        m.mat("sk_roof")                                                                 # little gabled cap
        m.poly([(x - 0.35, -0.6, 1.2), (x - 0.35, 0.6, 1.2), (x, 0.6, 1.5), (x, -0.6, 1.5)])
        m.poly([(x + 0.35, 0.6, 1.2), (x + 0.35, -0.6, 1.2), (x, -0.6, 1.5), (x, 0.6, 1.5)])
        m.mat("sk_red")
        m.box((x, 0, 1.17), (0.3, 0.95, 0.08), smooth=False)
        m.mat("sk_glow")
        m.sphere((x - sx * 0.25, 0, 0.95), 1.0, 10, 6, s=(0.1, 0.1, 0.13))               # lantern under the cap
        m.mat("sk_rope")
        m.torus((x, 0, 0.62), R=0.16, r=0.035, seg=12, sides=5, axis='Y')               # tie-off wrap
    m.mat("sk_cable")
    pts = E.catenary(V((-span / 2, 0, 0.6)), V((span / 2, 0, 0.6)), sag=0.6, n=24)
    m.sweep(pts, [(math.cos(2 * math.pi * k / 6), math.sin(2 * math.pi * k / 6)) for k in range(6)], closed=True, cap=True,
            scale=lambda t: 0.02)
    for k in range(13):
        t = (k + 0.5) / 13
        p = V(pts[int(t * (len(pts) - 1))])
        if k % 2 == 0:
            m.mat("sk_cable")
            m.cyl(tuple(p + V((0, 0, -0.08))), r=0.004, h=0.16, seg=4)
            m.mat("sk_glass")
            m.sphere(tuple(p + V((0, 0, -0.2))), 1.0, 12, 8, s=(0.09, 0.09, 0.08))
            m.mat(rnd.choice(("sk_paper_blue", "sk_paper_pink", "sk_paper_red")))
            m.box(tuple(p + V((0, 0, -0.42))), (0.06, 0.004, 0.25), smooth=False)
        else:
            m.mat(rnd.choice(("sk_paper_red", "sk_paper", "sk_paper_blue")))
            m.poly([tuple(p + V((-0.15, 0, -0.02))), tuple(p + V((0.15, 0, -0.02))), tuple(p + V((0, 0, -0.32)))])
    return m.obj(name, smooth_angle=40)


# ----------------------------------------------------------------------------- spire

def spire(name="spire", h=14.0, seed=3):
    """Rock spire from the valley (same layered sandstone as the gorge): a grassy cap with ivy, a black pine leaning
    out and a little hokora shrine with a torii in front."""
    import scenery as SC
    mats()
    rnd = random.Random(seed)
    m = E.Mesher(name)
    top, rt = _cliff_column(m, rnd, 0.0, 0.0, 0.0, h, 1.6)
    _cap(m, rnd, top, rt, dense=True)
    SC.pine(m, PAL, tuple(top + V((rt * 0.35, 0.1, 0.25))), rnd, h=2.6)
    sx, sy, sz = top.x - rt * 0.3, top.y, top.z + 0.3
    m.mat("sk_rock_dark")
    m.box((sx, sy, sz), (0.6, 0.5, 0.12), smooth=False)
    m.mat("sk_timber")
    m.box((sx, sy, sz + 0.25), (0.42, 0.34, 0.38), smooth=False)
    m.mat("sk_red")
    m.box((sx, sy - 0.175, sz + 0.25), (0.3, 0.02, 0.26), smooth=False)
    m.mat("sk_roof")
    m.push(Matrix.Translation((sx, sy, sz + 0.5)))
    m.poly([(-0.32, -0.3, 0), (0.32, -0.3, 0), (0.32, 0, 0.2), (-0.32, 0, 0.2)])
    m.poly([(0.32, 0.3, 0), (-0.32, 0.3, 0), (-0.32, 0, 0.2), (0.32, 0, 0.2)])
    m.pop()
    m.mat("sk_red")
    for dx in (-0.2, 0.2):
        m.cyl((sx + dx, sy - 0.6, sz + 0.25), r=0.025, h=0.5, seg=6)
    m.box((sx, sy - 0.6, sz + 0.5), (0.58, 0.05, 0.05), smooth=False)
    m.box((sx, sy - 0.6, sz + 0.4), (0.46, 0.04, 0.035), smooth=False)
    return m.obj(name, smooth_angle=30)


# ----------------------------------------------------------------------------- cloud, thermal, gust

def cloud(name="cloud", seed=1, size=4.0):
    """Ghibli cumulus: a cluster of puffs whose normals come from a smooth hull, flat bottom."""
    mats()
    rnd = random.Random(seed)
    m = E.Mesher(name)
    m.mat("sk_cloud")
    for k in range(14):
        a = rnd.uniform(0, 2 * math.pi)
        rr = size * 0.45 * math.sqrt(rnd.random())
        c = V((math.cos(a) * rr, math.sin(a) * rr * 0.6, size * 0.15 + rnd.uniform(0, size * 0.25) * (1 - rr / size)))
        m.ico(tuple(c), size * rnd.uniform(0.18, 0.3), 2, s=(1, 1, 0.8))
    ob = m.obj(name, smooth_angle=180)
    prox = E.proxy_ellipsoid(name + "_px", (0, 0, size * 0.25), (size * 0.6, size * 0.4, size * 0.35))
    E.transfer_normals(ob, prox, 0.85)
    E.delete(prox)
    return ob


def thermal_ring(name="thermal_ring"):
    mats()
    m = E.Mesher(name)
    m.mat("sk_ring")
    m.torus((0, 0, 0), R=1.3, r=0.04, seg=36, sides=6)
    for k in range(8):
        a = 2 * math.pi * k / 8
        m.box((math.cos(a) * 1.3, math.sin(a) * 1.3, 0.12), (0.03, 0.03, 0.22), smooth=False)
    return m.obj(name, smooth_angle=60)


def wind_streak(name="wind_streak"):
    mats()
    m = E.Mesher(name)
    m.mat("sk_streak")
    for j, (y0, z0) in enumerate(((0, 0), (0.6, 0.35), (-0.5, -0.3))):
        pts = [V((-2.5 + 5 * k / 20, y0, z0 + 0.25 * math.sin(k * 0.6 + j))) for k in range(21)]
        m.sweep(pts, [(-0.5, 0), (0.5, 0)], closed=False, cap=False, scale=lambda t: 0.06 * math.sin(math.pi * t) + 0.005)
    return m.obj(name, smooth_angle=60)


def terraces(name="terraces", seed=2, w=60.0, d=60.0):
    """Rice terraces and a hamlet far below the glide line (backdrop tile)."""
    mats()
    rnd = random.Random(seed)
    m = E.Mesher(name)
    for k in range(10):
        z = k * 0.9
        y0 = -d / 2 + k * d / 10
        m.mat("sk_terrace")
        m.box((0, y0 + d / 20, z - 0.4), (w, d / 10, 0.8), smooth=False)
        m.mat("sk_terrace_water")
        for j in range(5):
            m.box((-w / 2 + (j + 0.5) * w / 5, y0 + d / 20, z + 0.02), (w / 5 - 0.6, d / 10 - 0.6, 0.02), smooth=False)
    for k in range(6):
        x, y = rnd.uniform(-w / 2 + 4, w / 2 - 4), rnd.uniform(-d / 2 + 4, d / 2 - 4)
        z = int((y + d / 2) / (d / 10)) * 0.9
        m.mat("sk_wall")
        m.box((x, y, z + 0.6), (2.0, 1.6, 1.2), smooth=False)
        m.mat("sk_roof")
        m.cyl((x, y, z + 1.5), r=1.6, h=0.7, seg=4, r2=0.1)
    return m.obj(name, smooth_angle=30)


# ----------------------------------------------------------------------------- the gorge either side of the glide

PAL = {"trunk": "sk_bark", "leaf": "sk_tree", "leaf2": "sk_tree2", "leaf3": "sk_pine", "flower": "sk_flower",
       "flower2": "sk_flower2", "wall": "sk_wall", "timber": "sk_timber", "roof": "sk_roof", "stone": "sk_rock",
       "stone2": "sk_rock_dark", "moss": "sk_moss", "far": "sk_far", "far2": "sk_far2", "snow": "sk_snow",
       "water": "sk_water", "foam": "sk_foam", "rope": "sk_rope", "red": "sk_red", "glow": "sk_glow", "culm": "sk_stick",
       "grass_a": "sk_grass_a", "grass_b": "sk_grass_b", "grass_tip": "sk_grass_tip", "leaf_hi": "sk_tree_hi",
       "fl_white": "sk_fl_white", "fl_yellow": "sk_flower", "fl_pink": "sk_fl_pink", "sail": "sk_sail"}


def _cap(m, rnd, top, rt, sd=1, dense=True):
    """Pillar top: grassy dome, then a carpet of grass and flowers over it, bushes round the rim, ivy curtains
    hanging down the faces so the stone edge never reads bare."""
    import scenery as SC
    P = PAL
    m.mat("sk_grass")
    m.ico(tuple(top + V((0, 0, 0.1))), rt * 1.05, 2, s=(1, 1, 0.22))
    zc = top.z + 0.1 + rt * 1.05 * 0.22
    zf = lambda px, py: zc - min(1.0, ((px - top.x) ** 2 + (py - top.y) ** 2) / (rt * rt * 1.1)) * rt * 0.23
    if dense:
        SC.grass_carpet(m, P, top.x - rt * 0.7, top.x + rt * 0.7, top.y - rt * 0.7, top.y + rt * 0.7, zf, rnd,
                        density=2.0, h=0.4, flowers=0.1)
    for k in range(rnd.randint(3, 5)):
        a = rnd.uniform(0, 2 * math.pi)
        p = top + V((math.cos(a) * rt * 0.85, math.sin(a) * rt * 0.85, 0.12))
        SC.shrub(m, P, tuple(p), rnd, r=rnd.uniform(0.35, 0.6), flowers=rnd.choice((None, "sk_fl_pink", "sk_flower", "sk_fl_blue")))
    for k in range(rnd.randint(4, 7)):                  # ivy: irregular tapering strands of leaf tufts
        a = rnd.uniform(0, 2 * math.pi)
        d = V((math.cos(a), math.sin(a), 0))
        sdv = d.cross(V((0, 0, 1)))
        for j in range(rnd.randint(1, 3)):
            p = top + d * (rt * 0.98) + sdv * rnd.uniform(-0.6, 0.6) + V((0, 0, 0.05))
            ln = rnd.uniform(0.8, 3.8)
            zz = 0.0
            while zz < ln:
                f = zz / ln
                p = p + sdv * rnd.uniform(-0.09, 0.09) + d * rnd.uniform(-0.02, 0.03)
                q = p + V((0, 0, -zz))
                m.mat(("sk_vine", "sk_grass_b", "sk_tree2")[rnd.randrange(3)])
                m.ico(tuple(q + sdv * rnd.uniform(-0.08, 0.08)), (0.16 + rnd.uniform(-0.05, 0.06)) * (1 - 0.6 * f), 1,
                      s=(rnd.uniform(0.45, 0.7), rnd.uniform(0.8, 1.2), rnd.uniform(0.6, 1.0)))
                zz += rnd.uniform(0.18, 0.4)


GORGE = 10.5        # cliff faces start this far either side of the glide line (Ride.SKY_HALF is 6 game m = 5 here)
FLOOR = -14.0       # valley floor below the glide line


def _cliff_column(m, rnd, x, y, z0, z1, r):
    """Stacked eroded rock drums from z0 up to z1; returns the top centre."""
    z = z0
    while z < z1:
        dh = rnd.uniform(1.6, 3.0)
        ox, oy = x + rnd.uniform(-0.25, 0.25), y + rnd.uniform(-0.25, 0.25)
        m.mat("sk_rock" if rnd.random() < 0.65 else "sk_rock_dark")
        m.cyl((ox, oy, z + dh / 2), r=r, h=dh, seg=16, r2=r * rnd.uniform(0.86, 0.98))
        if rnd.random() < 0.45:
            m.mat("sk_rock_band")                   # eroded stratum lip where two layers meet
            m.cyl((ox, oy, z + dh * 0.9), r=r * 1.03, h=0.12, seg=16, r2=r * 0.98)
        m.mat("sk_rock_dark")
        for j in range(rnd.randint(1, 3)):         # weathered chunks breaking the silhouette
            a = rnd.uniform(0, 2 * math.pi)
            m.ico((ox + math.cos(a) * r * 0.86, oy + math.sin(a) * r * 0.86, z + rnd.uniform(0.2, dh * 0.8)),
                  rnd.uniform(0.35, 0.7), 2, s=(1.0, 1.0, 0.6))
        z += dh * 0.9
        r *= rnd.uniform(0.94, 1.0)
    return V((x, y, z)), r


def sky_gorge(name="sky_gorge", L=40.0, seed=3):
    """One tile of the gorge the glider flies along: cliff columns either side with grassy tops, pines, shrines,
    a waterfall, fences and hamlets on the ledges, a rope bridge high across now and then, terraces on the floor."""
    import scenery as SC
    mats()
    rnd = random.Random(seed)
    m = E.Mesher(name)
    P = PAL
    # a rope bridge between two tall pillars, its lowest plank above the canopy at the glide ceiling
    # (ALT_MAX 12 + 2.6 m of lines and wing)
    bridge_y = rnd.uniform(8, L - 8) if rnd.random() < 0.6 else None
    ends = {}
    for sd in (-1, 1):
        y = 0.0
        while y < L:
            r = rnd.uniform(2.0, 3.4)
            x = sd * (GORGE + r + rnd.uniform(0.0, 2.5))
            top_z = rnd.uniform(-6.0, 9.0)
            holds = bridge_y is not None and sd not in ends and y <= bridge_y <= y + 2 * r
            if holds:
                top_z = 18.0
            top, rt = _cliff_column(m, rnd, x, y + r, FLOOR, top_z, r)
            if holds:
                ends[sd] = top + V((-sd * rt * 0.55, 0, 0.15))
            # grassy cap with dressing
            _cap(m, rnd, top, rt, sd)
            k = rnd.random()
            if k < 0.35:
                SC.pine(m, P, tuple(top + V((-sd * rt * 0.4, 0, 0.2))), rnd, h=rnd.uniform(2.5, 4.0))
                SC.shrub(m, P, tuple(top + V((sd * rt * 0.3, 0.6, 0.2))), rnd, r=0.5, flowers=P["flower"])
            elif k < 0.55:
                SC.house(m, P, top + V((0, 0, 0.1)), rnd, rot=math.radians(90 * sd), w=2.0, d=1.6, h=1.2)
                SC.round_tree(m, P, tuple(top + V((0, rt * 0.6, 0.2))), rnd, h=2.4, r=1.0)
            elif k < 0.62:
                SC.pagoda(m, P, tuple(top + V((0, 0, 0.1))), tiers=3, s=0.6)
            elif k < 0.75:
                SC.windmill(m, P, top + V((0, 0, 0.15)), rnd, rot=math.radians(rnd.uniform(-30, 30)), h=3.2)
            else:
                for j in range(3):
                    SC.round_tree(m, P, tuple(top + V((rnd.uniform(-1, 1) * rt * 0.5, rnd.uniform(-1, 1) * rt * 0.5, 0.2))),
                                  rnd, h=rnd.uniform(2.0, 3.2), r=rnd.uniform(0.8, 1.2))
            # ledge pines and moss clinging to the cliff face on the gorge side
            m.mat("sk_moss")
            for j in range(7):                      # bushes rooted in cracks on the gorge face
                zz = rnd.uniform(FLOOR + 2, top_z - 0.5)
                a = math.radians(rnd.uniform(-50, 50)) + (math.pi if sd > 0 else 0.0)
                p = V((x + math.cos(a) * r * 1.0, y + r + math.sin(a) * r * 1.0, zz))
                for q in range(3):
                    m.mat(("sk_tree", "sk_tree2", "sk_tree_hi")[q])
                    m.ico(tuple(p + V((math.cos(a) * 0.15, math.sin(a) * 0.15, 0)) +
                                V((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), q * 0.18))), rnd.uniform(0.28, 0.42), 2,
                          s=(1, 1, 0.8))
            for j in range(2):
                zz = rnd.uniform(FLOOR + 4, top_z - 1)
                p = V((x - sd * r * 0.95, y + r + rnd.uniform(-r, r) * 0.6, zz))
                SC.rock(m, P, tuple(p), rnd, r=0.6)
                if rnd.random() < 0.5:
                    SC.pine(m, P, tuple(p + V((-sd * 0.2, 0, 0.3))), rnd, h=1.8)
            if rnd.random() < 0.3:          # falls on the face toward her, so they read head-on
                SC.waterfall(m, P, (x - sd * r * 0.3, y + r - r * 0.97, top_z - 0.3), drop=top_z - FLOOR - 1,
                             w=rnd.uniform(1.4, 2.2), out=(0, -1, 0))
            y += 2 * r + rnd.uniform(-0.5, 0.8)
        # second rank behind: taller, simpler
        y = rnd.uniform(-4, 0)
        while y < L:
            r = rnd.uniform(3.0, 4.5)
            x = sd * (GORGE + 7 + r + rnd.uniform(0, 4))
            top, rt = _cliff_column(m, rnd, x, y + r, FLOOR, rnd.uniform(8, 20), r)
            _cap(m, rnd, top, rt, sd, dense=False)
            for j in range(2):
                SC.round_tree(m, P, tuple(top + V((rnd.uniform(-1, 1) * rt * 0.5, rnd.uniform(-1, 1) * rt * 0.5, 0.2))),
                              rnd, h=rnd.uniform(2.4, 3.6), r=rnd.uniform(1.0, 1.5))
            y += 2 * r
    if len(ends) == 2:
        a, b = ends[-1], ends[1]
        n = 24
        pts = [a.lerp(b, k / n) + V((0, 0, -1.4 * math.sin(math.pi * k / n))) for k in range(n + 1)]
        side = (b - a).cross(V((0, 0, 1))).normalized()
        m.mat("sk_timber")
        for p in pts[1:-1]:
            m.push(Matrix.Translation(p) @ (b - a).to_track_quat('X', 'Z').to_matrix().to_4x4())
            m.box((0, 0, 0), (0.42, 1.0, 0.06), smooth=False)
            m.pop()
        for p in (a, b):                                 # anchor posts standing on the pillar tops
            for dy in (-0.55, 0.55):
                m.cyl(tuple(p + side * dy + V((0, 0, 0.5))), r=0.08, h=1.3, seg=6)
        m.mat("sk_rope")
        for dy in (-0.55, 0.55):
            m.tube([tuple(p + side * dy + V((0, 0, 0.75 + 0.35 * (1 - math.sin(math.pi * k / n))))) for k, p in enumerate(pts)],
                   r=0.025, seg=5)
            for p in pts[2:-2:2]:
                m.cyl(tuple(p + side * dy + V((0, 0, 0.38))), r=0.01, h=0.75, seg=4)
        m.mat("sk_paper_red")
        for k in range(2, n - 1, 3):
            m.box(tuple(pts[k] + side * 0.6 + V((0, 0, 0.4))), (0.03, 0.2, 0.32), smooth=False)
    # valley floor far below: fully covered by forest canopy and stepped rice terraces, a winding stream
    m.mat("sk_terrace")
    m.box((0, L / 2, FLOOR - 0.2), (2 * GORGE + 8, L, 0.4), smooth=False)
    sx = lambda yy: 1.6 * math.sin(yy * 0.16 + seed)
    for sd in (-1, 1):
        y = 0.0
        while y < L:                                    # terraces: stepped paddies with grass lips and water tops
            ln = rnd.uniform(5.0, 8.0)
            for st in range(3):
                x0 = sx(y) + sd * (1.6 + st * 1.6)
                zt = FLOOR + 0.25 * st
                m.mat("sk_terrace")
                m.box((x0 + sd * 0.8, y + ln / 2, zt + 0.06), (1.6, ln, 0.3), smooth=False)
                m.mat("sk_terrace_water")
                m.box((x0 + sd * 0.8, y + ln / 2, zt + 0.22), (1.3, ln - 0.3, 0.02), smooth=False)
            y += ln + 0.2
        SC.canopy_mass(m, P, sd * 7.0, sd * (GORGE + 4), 0, L, lambda px, py: FLOOR, rnd, n=26, r=(1.4, 2.4))
    m.mat("sk_water")
    pts = [(sx(k * L / 16), k * L / 16, FLOOR + 0.06) for k in range(17)]
    for a_, b_ in zip(pts, pts[1:]):
        m.push(Matrix.Translation(((a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2, FLOOR + 0.06)) @
               Matrix.Rotation(-math.atan2(b_[0] - a_[0], b_[1] - a_[1]), 4, 'Z'))
        m.box((0, 0, 0), (1.3, L / 16 + 0.3, 0.04), smooth=False)
        m.mat("sk_rock_dark")
        for sd_ in (-1, 1):
            m.ico((sd_ * 0.75, rnd.uniform(-1, 1), 0.05), rnd.uniform(0.15, 0.3), 1, s=(1, 1, 0.5))
        m.mat("sk_water")
        m.pop()
    return m.obj(name, smooth_angle=30)


def sky_backdrop(name="sky_far", seed=9):
    import scenery as SC
    mats()
    rnd = random.Random(seed)
    m = E.Mesher(name)
    SC.mountains(m, PAL, (0, 150, FLOOR), rnd, n=7, w=200, h=(26, 46), depth=18)
    return m.obj(name, smooth_angle=30)


def design_sky_gorge():
    """The gorge from behind the glider at mid altitude, and a high overview."""
    import studio
    E.reset()
    studio.stage(res=(1280, 720), floor=False, sky_top=0x7FC0F2, sky_hor=0xEAF6FF)
    outl = []
    for k in range(4):
        g = sky_gorge("sky_gorge_%d" % k, seed=3 + k)
        g.location = (0, k * 40.0, 0)
        outl.append(g)
    sky_backdrop()
    rnd = random.Random(12)
    for k in range(14):                     # cloud banks: below in the gorge, in the lane, and big ones far off
        if k < 5:
            loc, sz = (rnd.uniform(-8, 8), rnd.uniform(15, 150), rnd.uniform(-11, -6)), rnd.uniform(6, 9)
        elif k < 9:
            loc, sz = (rnd.uniform(-5, 5), rnd.uniform(25, 120), rnd.uniform(4, 10)), rnd.uniform(3, 4.5)
        else:
            loc, sz = (rnd.uniform(-60, 60), rnd.uniform(160, 220), rnd.uniform(14, 36)), rnd.uniform(18, 30)
        c = cloud("cloud_%d" % k, seed=k + 2, size=sz)
        c.location = loc
    for k, (x, y, z, sc) in enumerate(((-26, 120, 18, 2.4), (30, 150, 22, 3.0), (-40, 180, 10, 3.4), (22, 95, 26, 1.8))):
        d = islet("far_islet_%d" % k, seed=40 + k)          # distant floating islets
        d.location = (x, y, z)
        d.scale = (sc, sc, sc)
    il = islet("islet_a", seed=6)
    il.location = (-2.5, 46, 6.5)
    tc = thundercloud()
    tc.location = (3.5, 58, 8.0)
    cab = chime_cable("gorge_cable", span=2 * GORGE + 6, pylon=10.0 - FLOOR)
    cab.location = (0, 76, 10.0)
    outl += [il, cab]
    outl += crow_flight("crow_a", (1.2, 28, 6.6), flap=34)
    for i, k in enumerate(range(-2, 3)):
        outl += crow_flight("flock_%d" % i, (-1.5 + k * 1.3, 36 + abs(k) * 1.6, 8.2 + abs(k) * 0.45), flap=22 + 16 * (i % 2))
    for o in outl:
        if o.type == 'MESH':
            E.add_outline(o, 0.012)
    studio.haze(0xE4F0FA, start=20.0, depth=170.0, amount=0.7)
    studio.aim_sun(150)
    studio.shoot("sky_gorge_runner", target=(0, 30, 6.0), dist=14, yaw=0, pitch=8, lens=30, light=False)
    studio.shoot("sky_gorge_overview", target=(0, 60, 0.0), dist=44, yaw=8, pitch=34, lens=30, light=False)


def islet(name="islet", seed=5, r=2.2):
    """Floating rock islet (H_ISLET): an upturned craggy cone of layered sandstone, a grassy top with a tree, bushes
    and flowers, roots and vines trailing from its underside, and a thread of water spilling off one edge."""
    import scenery as SC
    mats()
    rnd = random.Random(seed)
    m = E.Mesher(name)
    P = PAL
    z = 0.0
    rr = r
    for k in range(4):                       # stacked drums tapering downward
        dh = rnd.uniform(0.45, 0.7)
        m.mat("sk_rock" if k % 2 == 0 else "sk_rock_dark")
        m.cyl((rnd.uniform(-0.1, 0.1), rnd.uniform(-0.1, 0.1), z - dh / 2), r=rr, h=dh, seg=10, r2=rr * 0.97)
        z -= dh * 0.92
        rr *= 0.7
    m.mat("sk_rock_dark")
    m.cyl((0, 0, z - 0.4), r=rr, h=0.8, seg=8, r2=0.05)
    top = V((0, 0, 0.0))
    _cap(m, rnd, top, r * 0.95)
    SC.round_tree(m, P, (r * 0.2, 0.1, 0.25), rnd, h=2.0, r=0.9)
    m.mat("sk_bark")                        # roots
    for k in range(7):
        a = 2 * math.pi * k / 7 + rnd.uniform(-0.2, 0.2)
        p0 = V((math.cos(a) * r * 0.6, math.sin(a) * r * 0.6, -0.6))
        pts = [p0, p0 + V((math.cos(a) * 0.3, math.sin(a) * 0.3, -0.7)), p0 + V((math.cos(a) * 0.2, math.sin(a) * 0.2, -1.5))]
        m.tube([tuple(p) for p in pts], r=0.05, seg=5, taper=0.2)
    SC.waterfall(m, P, (r * 0.75, -r * 0.45, -0.05), drop=2.6, w=0.45, out=(0.6, -0.8, 0))
    return m.obj(name, smooth_angle=40)


def thundercloud(name="thundercloud", seed=3, size=3.0):
    """Little storm cloud (H_STORM): a soft lilac-grey puff with a darker belly, a zig-zag spark and rain streaks.
    She bursts through it (no crash), with a jolt."""
    mats()
    rnd = random.Random(seed)
    m = E.Mesher(name)
    for k in range(11):
        a = rnd.uniform(0, 2 * math.pi)
        rr = size * 0.42 * math.sqrt(rnd.random())
        c = V((math.cos(a) * rr, math.sin(a) * rr * 0.55, rnd.uniform(0, size * 0.25)))
        m.mat("sk_cloud" if c.z > size * 0.17 else "sk_storm" if c.z > size * 0.06 else "sk_storm_dark")
        m.ico(tuple(c), size * rnd.uniform(0.2, 0.32), 2, s=(1, 1, 0.8))
    m.mat("sk_storm_dark")
    m.ico((0, 0, -size * 0.05), size * 0.5, 2, s=(1.1, 0.6, 0.25))
    m.mat("sk_bolt")
    pts = [V((0.25, -0.25, -0.2)), V((-0.2, -0.3, -0.75)), V((0.2, -0.3, -0.95)), V((-0.15, -0.35, -1.6))]
    m.sweep(pts, [(-0.07, -0.03), (0.07, -0.03), (0.07, 0.03), (-0.07, 0.03)], closed=True, cap=True,
            scale=lambda t: 1.0 - 0.6 * t)
    m.sweep([pts[1], pts[1] + V((-0.3, 0, -0.35))], [(-0.04, -0.02), (0.04, -0.02), (0.04, 0.02), (-0.04, 0.02)],
            closed=True, cap=True, scale=lambda t: 1.0 - 0.7 * t)
    m.mat("sk_water")
    for k in range(9):
        x = rnd.uniform(-size * 0.4, size * 0.4)
        y = rnd.uniform(-size * 0.2, size * 0.2)
        m.box((x, y, -size * 0.25 - 0.5), (0.02, 0.02, 0.6 + rnd.uniform(0, 0.4)), smooth=False)
    return m.obj(name, smooth_angle=180)


def crow_flight(prefix, loc, flap=20.0, face=-1):
    """Crow with both wings set at `flap` degrees, facing -Y (head-on toward the player) when face = -1."""
    bo, wo = crow()
    bo.name = prefix
    wl = wo.copy()
    wl.data = wo.data.copy()
    E.link(wl)
    rz = math.pi if face < 0 else 0.0
    for o in (wo, wl):
        o.parent = bo
    wo.location = (0.1, 0, 0.02)
    wo.rotation_euler = (0, math.radians(-flap), 0)
    wl.location = (-0.1, 0, 0.02)
    wl.scale = (-1, 1, 1)
    wl.rotation_euler = (0, math.radians(flap), 0)
    bo.location = loc
    bo.rotation_euler = (0, 0, rz)
    bo.scale = (2, 2, 2)
    return [bo, wo, wl]


def design_sky():
    """Sheet of the sky-glide obstacles, from where she sees them (they come at her down the gorge)."""
    import studio
    E.reset()
    studio.stage(res=(1280, 720), floor=False, sky_top=0x8FC8F4, sky_hor=0xEAF6FF)
    outl = []
    outl += crow_flight("crow_a", (-4.0, 0, 2.4), flap=28)
    for i, k in enumerate(range(-2, 3)):                  # V flock, head-on
        outl += crow_flight("flock_%d" % i, (-4.0 + k * 0.9, 4.0 + abs(k) * 0.8, 3.6 + abs(k) * 0.3), flap=10 + 12 * (i % 2))
    il = islet()
    il.location = (1.0, 3.0, 1.6)
    outl.append(il)
    tc = thundercloud()
    tc.location = (5.6, 2.0, 3.0)
    cc = chime_cable(span=10, pylon=4.5)
    cc.location = (0.5, 7.0, 4.6)
    outl.append(cc)
    cl = cloud(size=4.0)
    cl.location = (-7.0, 9.0, 0.6)
    tr = thermal_ring()
    tr.location = (4.8, -1.5, 0.3)
    ws = wind_streak()
    ws.location = (-1.0, -1.0, 0.4)
    for o in outl:
        if o.type == 'MESH':
            E.add_outline(o, 0.01)
    studio.shoot("sky_hazards", target=(0.2, 2.0, 2.4), dist=13, yaw=8, pitch=12, lens=35)
