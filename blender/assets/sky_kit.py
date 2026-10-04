"""
Sky Glide kit. Its own theme and colours, drawn in the Sakura Line art style (soft toon shading,
lilac shadows, thin ink outlines, puffy cloud masses, dense small detail):

  crow_body / crow_wing   Karasu crow; the wing is one side (mirror for the other), hinged at its root
                          -> Ride.H_CROW, H_FLOCK (the game flaps the wings)
  kite          paper diamond kite with a painted face, ribbon tail and string  -> Ride.H_KITE
  sky_lantern   glowing paper sky lantern drifting up                            -> Ride.H_LANTERN
  chime_cable   cable strung across the valley with fuurin wind chimes and flags -> Ride.H_CABLE
  spire         rock spire with a pine and a shrine on top                       -> Ride.H_SPIRE
  cloud         Ghibli cumulus puff (same method as the sakura canopy)
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
    M("sk_rock", 0xC6B8C8, rim=0.3, soft=0.12, shadow=0x8D86B8)
    M("sk_rock_dark", 0x9A8EA8, rim=0.25, soft=0.12, shadow=0x6E6A98)
    M("sk_pine", 0x5E9A6A, rim=0.25, soft=0.2, flags=E.F_FOLIAGE, sway=0.2, shadow=0x5A6A9A)
    M("sk_bark", 0x6E4A3A, rim=0.2, soft=0.12)
    M("sk_red", 0xE8473C, rim=0.3, soft=0.1)
    M("sk_cloud", 0xFFFFFF, rim=0.4, soft=0.35, flags=E.F_NOCAST, outline=0.0, shadow=0xC9C4EA)
    M("sk_ring", 0xFFF6C8, emis=0.8, rim=0.0, soft=0.1, flags=E.F_NOCAST, outline=0.0)
    M("sk_streak", 0xFFFFFF, emis=0.6, rim=0.0, soft=0.1, flags=E.F_NOCAST | E.F_DOUBLE, outline=0.0)
    M("sk_terrace", 0x9ACD6E, rim=0.1, soft=0.2, shadow=0x9A9AD0)
    M("sk_terrace_water", 0xB9E4F0, rim=0.1, soft=0.2, spec=0.5)
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
    w.mat("sk_crow")
    w.poly([(0, 0.08, 0), (0.25, 0.1, 0.01), (0.45, 0.05, 0.0), (0.45, -0.08, 0), (0.0, -0.1, 0)])
    for k in range(6):
        x0 = 0.3 + k * 0.06
        w.poly([(x0, 0.06 - k * 0.02, 0.0), (x0 + 0.2, 0.02 - k * 0.035, 0.0), (x0 + 0.16, -0.06 - k * 0.03, 0.0),
                (x0 - 0.02, -0.06, 0.0)])
    w.mat("sk_crow_sheen")
    w.poly([(0.05, 0.06, 0.005), (0.3, 0.07, 0.005), (0.3, 0.0, 0.005), (0.05, -0.02, 0.005)])
    wo = w.obj("crow_wing", smooth_angle=0)
    return bo, wo


# ----------------------------------------------------------------------------- kite

def kite(name="kite"):
    """Edo-style rectangular kite (tako) with a painted face, bamboo spars, ribbon tail and the string bridle.
    Faces -Y toward her; the string leaves from the bridle point downward/back."""
    mats()
    m = E.Mesher(name)
    W, H = 1.2, 1.6
    m.mat("sk_paper")
    m.box((0, 0, 0), (W, 0.01, H), smooth=False)
    m.mat("sk_paper_red")
    m.box((0, -0.008, -H * 0.38), (W * 0.98, 0.004, H * 0.2), smooth=False)
    m.box((0, -0.008, H * 0.42), (W * 0.98, 0.004, H * 0.12), smooth=False)
    # painted kabuki-ish face: brows, eyes, mouth
    m.mat("sk_ink")
    for sx in (-1, 1):
        m.push(Matrix.Translation((sx * 0.25, -0.01, 0.25)) @ Matrix.Rotation(math.radians(sx * 15), 4, 'Y'))
        m.box((0, 0, 0), (0.3, 0.004, 0.05), smooth=False)
        m.pop()
        m.cyl((sx * 0.24, -0.01, 0.07), r=0.08, h=0.004, seg=16, axis='Y')
    m.mat("sk_paper_red")
    m.cyl((0, -0.012, -0.12), r=0.12, h=0.004, seg=16, axis='Y')
    m.mat("sk_stick")
    for x in (-W / 2, 0, W / 2):
        m.cyl((x, 0.01, 0), r=0.012, h=H, seg=6)
    m.cyl((0, 0.01, H * 0.3), r=0.012, h=W, seg=6, axis='X')
    # tail ribbons
    for sx, mt in ((-0.3, "sk_paper_blue"), (0.3, "sk_paper_pink")):
        m.mat(mt)
        pts = [V((sx, 0.0, -H / 2 - 0.05 - k * 0.25)) + V((0.12 * math.sin(k * 0.9), 0, 0)) for k in range(9)]
        m.sweep(pts, [(-0.05, -0.002), (0.05, -0.002), (0.05, 0.002), (-0.05, 0.002)], closed=True, cap=True,
                scale=lambda t: 1 - 0.5 * t)
    # bridle and string (down and back toward the ground, ~8 m drawn)
    m.mat("sk_string")
    br = V((0, 0.15, -0.1))
    for p in (V((-W / 2, 0.01, H / 2)), V((W / 2, 0.01, H / 2)), V((0, 0.01, -H / 2))):
        m.sweep([p, br], [(math.cos(2 * math.pi * k / 4), math.sin(2 * math.pi * k / 4)) for k in range(4)], closed=True,
                cap=False, scale=lambda t: 0.006)
    m.sweep([br, br + V((-1.0, 2.0, -4.0)), br + V((-2.0, 4.5, -9.0))],
            [(math.cos(2 * math.pi * k / 4), math.sin(2 * math.pi * k / 4)) for k in range(4)], closed=True, cap=False,
            scale=lambda t: 0.012)
    return m.obj(name, smooth_angle=0)


# ----------------------------------------------------------------------------- sky lantern

def sky_lantern(name="sky_lantern"):
    mats()
    m = E.Mesher(name)
    m.mat("sk_glow")
    prof = [(0.0, 0.0), (0.2, 0.02), (0.27, 0.25), (0.28, 0.5), (0.24, 0.66), (0.0, 0.7)]
    m.lathe(prof, seg=16)
    m.mat("sk_stick")
    m.torus((0, 0, 0.02), R=0.2, r=0.01, seg=16, sides=4)
    m.mat("sk_glow_core")
    m.sphere((0, 0, 0.08), 0.06, 10, 6)
    m.mat("sk_ink")
    m.push(Matrix.Translation((0, -0.272, 0.35)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
    m.text("願", size=0.2, depth=0.004, font=E.FONT_JP, c=(0, 0, 0))
    m.pop()
    return m.obj(name, smooth_angle=60)


# ----------------------------------------------------------------------------- chime cable

def chime_cable(name="chime_cable", span=18.0, rnd_seed=4):
    """Cable across the valley with glass wind chimes (fuurin) with paper strips and small flags."""
    mats()
    rnd = random.Random(rnd_seed)
    m = E.Mesher(name)
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
    """Rock spire from the valley: stacked eroded drums, a pine leaning off the top, a tiny red shrine."""
    mats()
    rnd = random.Random(seed)
    m = E.Mesher(name)
    z = 0.0
    r = 1.6
    while z < h:
        dh = rnd.uniform(1.4, 2.4)
        m.mat("sk_rock" if rnd.random() < 0.65 else "sk_rock_dark")
        m.cyl((rnd.uniform(-0.1, 0.1), rnd.uniform(-0.1, 0.1), z + dh / 2), r=r, h=dh, seg=9, r2=r * rnd.uniform(0.8, 0.95))
        z += dh * 0.92
        r *= rnd.uniform(0.86, 0.96)
    m.mat("sk_bark")
    m.tube([(0, 0, z), (0.4, 0.1, z + 0.8), (1.1, 0.2, z + 1.3)], r=0.12, seg=8, taper=0.6)
    m.mat("sk_pine")
    for (x, zz, s) in ((1.1, 1.4, 0.8), (0.6, 1.0, 0.6), (1.5, 1.2, 0.5)):
        m.ico((x, 0.2, z + zz), s, 2, s=(1.3, 1.0, 0.45))
    m.mat("sk_red")
    m.box((-0.4, 0, z + 0.25), (0.35, 0.3, 0.3), smooth=False)
    m.mat("sk_roof")
    m.cyl((-0.4, 0, z + 0.48), r=0.32, h=0.16, seg=4, r2=0.02)
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
       "water": "sk_water", "foam": "sk_foam", "rope": "sk_rope", "red": "sk_red", "glow": "sk_glow", "culm": "sk_stick"}
GORGE = 9.0         # cliff faces start this far either side of the glide line (Ride.SKY_HALF is 6 game m = 5 here)
FLOOR = -14.0       # valley floor below the glide line


def _cliff_column(m, rnd, x, y, z0, z1, r):
    """Stacked eroded rock drums from z0 up to z1; returns the top centre."""
    z = z0
    while z < z1:
        dh = rnd.uniform(1.6, 3.0)
        m.mat("sk_rock" if rnd.random() < 0.6 else "sk_rock_dark")
        m.cyl((x + rnd.uniform(-0.15, 0.15), y + rnd.uniform(-0.15, 0.15), z + dh / 2), r=r, h=dh, seg=9,
              r2=r * rnd.uniform(0.86, 0.98))
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
    for sd in (-1, 1):
        y = 0.0
        while y < L:
            r = rnd.uniform(2.0, 3.4)
            x = sd * (GORGE + r + rnd.uniform(0.0, 2.5))
            top_z = rnd.uniform(-2.0, 12.0)
            top, rt = _cliff_column(m, rnd, x, y + r, FLOOR, top_z, r)
            # grassy cap with dressing
            m.mat("sk_grass")
            m.ico(tuple(top + V((0, 0, 0.1))), rt * 1.05, 2, s=(1, 1, 0.22))
            k = rnd.random()
            if k < 0.35:
                SC.pine(m, P, tuple(top + V((-sd * rt * 0.4, 0, 0.2))), rnd, h=rnd.uniform(2.5, 4.0))
                SC.shrub(m, P, tuple(top + V((sd * rt * 0.3, 0.6, 0.2))), rnd, r=0.5, flowers=P["flower"])
            elif k < 0.55:
                SC.house(m, P, top + V((0, 0, 0.1)), rnd, rot=math.radians(90 * sd), w=2.0, d=1.6, h=1.2)
                SC.round_tree(m, P, tuple(top + V((0, rt * 0.6, 0.2))), rnd, h=2.4, r=1.0)
            elif k < 0.7:
                SC.pagoda(m, P, tuple(top + V((0, 0, 0.1))), tiers=3, s=0.6)
            else:
                for j in range(3):
                    SC.round_tree(m, P, tuple(top + V((rnd.uniform(-1, 1) * rt * 0.5, rnd.uniform(-1, 1) * rt * 0.5, 0.2))),
                                  rnd, h=rnd.uniform(2.0, 3.2), r=rnd.uniform(0.8, 1.2))
            SC.grass_tufts(m, P, tuple(top + V((0, 0, 0.25))), rnd, n=5, spread=rt * 0.6, h=0.4)
            # ledge pines and moss clinging to the cliff face on the gorge side
            for j in range(2):
                zz = rnd.uniform(FLOOR + 4, top_z - 1)
                p = V((x - sd * r * 0.95, y + r + rnd.uniform(-r, r) * 0.6, zz))
                SC.rock(m, P, tuple(p), rnd, r=0.6)
                if rnd.random() < 0.5:
                    SC.pine(m, P, tuple(p + V((-sd * 0.2, 0, 0.3))), rnd, h=1.8)
            if rnd.random() < 0.2:
                SC.waterfall(m, P, (x - sd * r * 0.98, y + r, top_z - 0.5), drop=top_z - FLOOR - 1, w=1.0)
            y += 2 * r + rnd.uniform(-0.5, 0.8)
        # second rank behind: taller, simpler
        y = rnd.uniform(-4, 0)
        while y < L:
            r = rnd.uniform(3.0, 4.5)
            x = sd * (GORGE + 7 + r + rnd.uniform(0, 4))
            top, rt = _cliff_column(m, rnd, x, y + r, FLOOR, rnd.uniform(8, 20), r)
            m.mat("sk_grass")
            m.ico(tuple(top + V((0, 0, 0.1))), rt * 1.05, 1, s=(1, 1, 0.25))
            for j in range(2):
                SC.round_tree(m, P, tuple(top + V((rnd.uniform(-1, 1) * rt * 0.5, rnd.uniform(-1, 1) * rt * 0.5, 0.2))),
                              rnd, h=rnd.uniform(2.4, 3.6), r=rnd.uniform(1.0, 1.5))
            y += 2 * r
    # rope bridge across, well above the glide ceiling (ALT_MAX 12 game = 10 here) so it is scenery, not a hazard
    if rnd.random() < 0.6:
        y = rnd.uniform(8, L - 8)
        a, b = V((-GORGE - 1.5, y, 13.0)), V((GORGE + 1.5, y, 13.0))
        n = 24
        pts = [a.lerp(b, k / n) + V((0, 0, -1.6 * math.sin(math.pi * k / n))) for k in range(n + 1)]
        m.mat("sk_timber")
        for p in pts[1:-1]:
            m.box(tuple(p), (0.5, 1.0, 0.06), smooth=False)
        m.mat("sk_rope")
        for dy in (-0.5, 0.5):
            m.tube([tuple(p + V((0, dy, 0.7))) for p in pts], r=0.025, seg=5)
        m.mat("sk_paper_red")
        for k in range(2, n - 1, 3):
            m.box(tuple(pts[k] + V((0, 0.5, 0.45))), (0.03, 0.2, 0.32), smooth=False)
    # valley floor: terrace bands and a stream
    m.mat("sk_terrace")
    m.box((0, L / 2, FLOOR - 0.2), (2 * GORGE + 8, L, 0.4), smooth=False)
    m.mat("sk_terrace_water")
    for k in range(8):
        for sd in (-1, 1):
            m.box((sd * rnd.uniform(2.5, 7), rnd.uniform(0, L), FLOOR + 0.02), (rnd.uniform(2, 4), rnd.uniform(2, 4), 0.02),
                  smooth=False)
    m.mat("sk_water")
    m.box((rnd.uniform(-1, 1), L / 2, FLOOR + 0.03), (1.2, L, 0.02), smooth=False)
    return m.obj(name, smooth_angle=30)


def sky_backdrop(name="sky_far", seed=9):
    import scenery as SC
    mats()
    rnd = random.Random(seed)
    m = E.Mesher(name)
    SC.mountains(m, PAL, (0, 150, FLOOR), rnd, n=7, w=200, h=(26, 46), depth=18)
    return m.obj(name, smooth_angle=30)


def design_sky_gorge():
    import studio
    E.reset()
    studio.stage(res=(1280, 720), floor=False, sky_top=0x8FC8F4, sky_hor=0xEAF6FF)
    outl = []
    for k in range(4):
        g = sky_gorge("sky_gorge_%d" % k, seed=3 + k)
        g.location = (0, k * 40.0, 0)
        outl.append(g)
    sky_backdrop()
    for k, (x, y, z, sz) in enumerate(((-4, 30, -6, 6), (5, 55, -5, 7), (-6, 80, 4, 5), (3, 18, 13, 4), (8, 100, -3, 8))):
        c = cloud("cloud_%d" % k, seed=k + 2, size=sz)
        c.location = (x, y, z)
    bo, wo = crow()
    bo.location = (1.5, 22, 6.0)
    wo.location = (1.6, 22, 6.02)
    sl = sky_lantern()
    sl.location = (-2.0, 30, 5.0)
    k = kite()
    k.location = (3.0, 38, 8.0)
    for o in outl + [bo, wo, sl, k]:
        E.add_outline(o, 0.012)
    studio.aim_sun(150)
    studio.shoot("sky_gorge_runner", target=(0, 30, 5.0), dist=14, yaw=0, pitch=10, lens=30, light=False)
    studio.shoot("sky_gorge_overview", target=(0, 50, 0.0), dist=48, yaw=330, pitch=28, lens=30, light=False)


# ----------------------------------------------------------------------------- design render

def design_sky():
    import studio
    E.reset()
    studio.stage(res=(1280, 720), floor=False, sky_top=0x8FC8F4, sky_hor=0xEAF6FF)
    bo, wo = crow()
    bo.location = (-3.2, 0, 2.0)
    wl = wo.copy()
    wl.data = wo.data.copy()
    E.link(wl)
    wo.location = (-3.2 + 0.1, 0, 2.02)
    wo.rotation_euler = (0, math.radians(-25), 0)
    wl.location = (-3.2 - 0.1, 0, 2.02)
    wl.scale = (-1, 1, 1)
    wl.rotation_euler = (0, math.radians(25), 0)
    for o in (bo, wo, wl):
        o.scale = (o.scale[0] * 2, 2, 2)
    k = kite()
    k.location = (-0.4, 0, 2.2)
    k.rotation_euler = (math.radians(-10), 0, math.radians(10))
    sl = sky_lantern()
    sl.location = (2.0, 0, 1.4)
    sl.scale = (2, 2, 2)
    cc = chime_cable(span=10)
    cc.location = (0.5, 2.5, 3.6)
    sp = spire(h=6.0)
    sp.location = (5.5, 4.0, -3.0)
    cl = cloud(size=4.0)
    cl.location = (-6.0, 8.0, 2.0)
    tr = thermal_ring()
    tr.location = (3.6, -0.5, 0.3)
    ws = wind_streak()
    ws.location = (0.5, -1.0, 0.6)
    for o in (bo, wo, wl, k, sl, cc, sp):
        E.add_outline(o, 0.01)
    studio.shoot("sky_hazards", target=(0.2, 1.0, 2.0), dist=13, yaw=8, pitch=20, lens=35)
