"""
Bamboo River kit. Its own theme and colours, drawn in the Sakura Line art style (soft toon shading,
lilac shadows, thin ink outlines, puffy foliage masses, dense small detail):

  river_seg     20 m of river (water strip with painted flow streaks, grassy banks with stone edging,
                bamboo clumps, reeds, a stone lantern); the river is RIVER_HALF wide each side (Ride.java)
  fork_island   the island a Y fork splits around: rocky nose, grass, bamboo, a small torii
  stone         river boulder (tilt around)                       -> Ride.H_STONE
  croc_body / croc_jaw   crocodile in two parts; the jaw hinges at JAW_HINGE   -> Ride.H_CROC
  drift_log     floating log with a broken branch and moss         -> Ride.H_DRIFTLOG
  whirlpool     spiral decal on the water                          -> Ride.H_WHIRL
  small props   lily pads, koi, reeds, drifting bamboo leaves, stone lantern, heron

Everything faces +Y (the canoe travels +Y), origin at the water line.
"""
import math, random
import bpy
from mathutils import Vector, Matrix
import erlib as E

V = Vector
RIVER_HALF = 4.6 / 1.2          # Ride.RIVER_HALF is in game units (x1.2)
JAW_HINGE = V((0.0, 0.62, 0.16))


def mats():
    M = E.mat
    M("rv_water", 0x8FD3E8, rim=0.2, spec=0.6, soft=0.12, flags=E.F_WATER | E.F_NOCAST, outline=0.0, shadow=0x7FA6D6)
    M("rv_water_deep", 0x5FB4D6, rim=0.2, spec=0.6, soft=0.12, flags=E.F_WATER | E.F_NOCAST, outline=0.0, shadow=0x6A8CC8)
    M("rv_foam", 0xF4FBFF, emis=0.25, rim=0.0, soft=0.2, flags=E.F_NOCAST, outline=0.0)
    M("rv_grass", 0x9ACD6E, rim=0.15, soft=0.15, shadow=0x9A9AD0)
    M("rv_grass_dark", 0x78B45A, rim=0.15, soft=0.15, shadow=0x8A8AC8)
    M("rv_bank", 0xCFC3B0, rim=0.2, soft=0.12)
    M("rv_stone", 0xB9B5C4, rim=0.3, soft=0.1, shadow=0x8D86B8)
    M("rv_stone_dark", 0x8E8AA0, rim=0.25, soft=0.1, shadow=0x6E6A98)
    M("rv_moss", 0x8FBF62, rim=0.2, soft=0.12)
    M("rv_bamboo", 0x9CC45A, spec=0.25, rim=0.3, soft=0.08, shadow=0x5E8A6A)
    M("rv_bamboo_node", 0x7DA346, spec=0.2, rim=0.25, soft=0.08)
    M("rv_leaf", 0x7EC46A, rim=0.25, soft=0.25, flags=E.F_FOLIAGE | E.F_NOCAST | E.F_DOUBLE, sway=0.4, outline=0.0,
      shadow=0x6A9A9A)
    M("rv_reed", 0xA8C46A, rim=0.2, soft=0.2, flags=E.F_FOLIAGE | E.F_DOUBLE, sway=0.5, outline=0.0)
    M("rv_lily", 0x6FB25A, rim=0.2, soft=0.15, flags=E.F_DOUBLE, outline=0.6)
    M("rv_lily_flower", 0xFFC6DA, rim=0.3, soft=0.15, emis=0.1)
    M("rv_croc", 0x7FA85A, rim=0.3, soft=0.1, spec=0.15, shadow=0x6A7AA8)
    M("rv_croc_belly", 0xE8E0A8, rim=0.25, soft=0.12)
    M("rv_croc_dark", 0x5E8048, rim=0.25, soft=0.1)
    M("rv_tooth", 0xFFFDF4, rim=0.2, soft=0.1, outline=0.4)
    M("rv_mouth", 0xE0707A, rim=0.1, soft=0.1)
    M("rv_eye", 0xFFE36A, emis=0.35, rim=0.2, soft=0.05, outline=0.6)
    M("rv_pupil", 0x1E1A24, rim=0.0, soft=0.05, outline=0.0)
    M("rv_log", 0x9A6E4E, rim=0.25, soft=0.12, shadow=0x7A5A7A)
    M("rv_log_end", 0xE6C894, rim=0.2, soft=0.12)
    M("rv_lantern", 0xC8C2CE, rim=0.3, soft=0.1)
    M("rv_lantern_glow", 0xFFE2A0, emis=0.9, rim=0.2, soft=0.05, flags=E.F_NIGHT)
    M("rv_torii", 0xE8473C, rim=0.3, soft=0.1)
    M("rv_black", 0x2A2A30, rim=0.2, soft=0.1)
    M("rv_koi_w", 0xFFF6EE, rim=0.3, soft=0.1)
    M("rv_koi_o", 0xFF8A3A, rim=0.3, soft=0.1)
    M("rv_heron", 0xF7F8FC, rim=0.35, soft=0.12)
    M("rv_beak", 0xF2B84A, rim=0.2, soft=0.1)
    M("rv_leaf_float", 0xC8D86A, rim=0.2, soft=0.2, outline=0.0, flags=E.F_NOCAST | E.F_DOUBLE)
    M("rv_whirl", 0xE8F8FF, emis=0.3, rim=0.0, soft=0.2, flags=E.F_NOCAST | E.F_DECAL, outline=0.0)


# ----------------------------------------------------------------------------- props

def bamboo_clump(m, c, rnd, n=7, h=6.5):
    """A clump of culms leaning out, node rings, leaf sprays near the tops."""
    x0, y0, z0 = c
    for i in range(n):
        a = rnd.uniform(0, 2 * math.pi)
        r0 = rnd.uniform(0.05, 0.35)
        base = V((x0 + math.cos(a) * r0, y0 + math.sin(a) * r0, z0))
        lean = V((math.cos(a) * rnd.uniform(0.15, 0.4), math.sin(a) * rnd.uniform(0.15, 0.4), 1)).normalized()
        hh = h * rnd.uniform(0.7, 1.1)
        top = base + lean * hh + V((0, 0, 0)) + V((math.cos(a), math.sin(a), 0)) * hh * 0.08
        pts = [base.lerp(top, k / 6) + V((math.cos(a), math.sin(a), 0)) * 0.12 * hh * (k / 6) ** 2 for k in range(7)]
        m.mat("rv_bamboo")
        m.tube([tuple(p) for p in pts], r=0.055, seg=8, taper=0.65)
        m.mat("rv_bamboo_node")
        for k in range(1, 6):
            p = pts[k]
            m.torus(tuple(p), R=0.05 * (1 - 0.06 * k), r=0.012, seg=10, sides=4)
        m.mat("rv_leaf")
        for k in range(5):
            p = pts[6].lerp(pts[3], k / 5) + V((rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2), 0))
            for j in range(4):
                aa = rnd.uniform(0, 2 * math.pi)
                d = V((math.cos(aa), math.sin(aa), -0.35)).normalized()
                tip = p + d * 0.55
                side = d.cross(V((0, 0, 1))).normalized() * 0.07
                m.poly([tuple(p), tuple(p + d * 0.27 + side), tuple(tip), tuple(p + d * 0.27 - side)])


def reeds(m, c, rnd, n=12):
    m.mat("rv_reed")
    for i in range(n):
        p = V(c) + V((rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5), 0))
        h = rnd.uniform(0.6, 1.3)
        bend = V((rnd.uniform(-0.25, 0.25), rnd.uniform(-0.25, 0.25), 0))
        m.poly([tuple(p + V((-0.025, 0, 0))), tuple(p + V((0.025, 0, 0))), tuple(p + bend + V((0, 0, h)))])
        m.poly([tuple(p + V((0, -0.025, 0))), tuple(p + V((0, 0.025, 0))), tuple(p + bend * 0.8 + V((0, 0, h * 0.9)))])
    m.mat("rv_log")
    for i in range(3):
        p = V(c) + V((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), 0))
        h = rnd.uniform(1.0, 1.4)
        m.cyl(tuple(p + V((0, 0, h / 2))), r=0.008, h=h, seg=5)
        m.sphere(tuple(p + V((0, 0, h + 0.08))), 1.0, 8, 5, s=(0.035, 0.035, 0.11))   # cattail head


def lily_pads(m, c, rnd, n=5):
    for i in range(n):
        p = V(c) + V((rnd.uniform(-0.8, 0.8), rnd.uniform(-0.8, 0.8), 0.015))
        r = rnd.uniform(0.18, 0.32)
        a0 = rnd.uniform(0, 2 * math.pi)
        pts = []
        for k in range(18):
            a = a0 + 0.35 + (2 * math.pi - 0.7) * k / 17
            pts.append((p.x + math.cos(a) * r, p.y + math.sin(a) * r, p.z))
        pts.append(tuple(p))
        m.mat("rv_lily")
        m.poly(pts)
        if rnd.random() < 0.4:
            m.mat("rv_lily_flower")
            for k in range(6):
                a = k * math.pi / 3
                m.sphere((p.x + math.cos(a) * 0.05, p.y + math.sin(a) * 0.05, p.z + 0.05), 1.0, 8, 5, s=(0.05, 0.025, 0.04))


def stone_lantern(m, c):
    """Kasuga-style toro on the bank: base, post, firebox with glowing windows, roof, jewel."""
    x, y, z = c
    m.mat("rv_lantern")
    m.cyl((x, y, z + 0.08), r=0.28, h=0.16, seg=6)
    m.cyl((x, y, z + 0.55), r=0.09, h=0.8, seg=8)
    m.cyl((x, y, z + 0.98), r=0.22, h=0.08, seg=6)
    m.box((x, y, z + 1.17), (0.32, 0.32, 0.3), smooth=False)
    m.mat("rv_lantern_glow")
    for sx, sy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        m.box((x + sx * 0.161, y + sy * 0.161, z + 1.17), (0.12 if sy else 0.01, 0.01 if sy else 0.12, 0.15), smooth=False)
    m.mat("rv_lantern")
    m.cyl((x, y, z + 1.4), r=0.36, h=0.08, seg=6, r2=0.12)
    m.cyl((x, y, z + 1.5), r=0.12, h=0.12, seg=6, r2=0.03)
    m.sphere((x, y, z + 1.6), 0.06, 10, 6)


def torii(m, c, w=1.6, h=1.9, s=1.0):
    x, y, z = c
    m.mat("rv_torii")
    for sx in (-1, 1):
        m.cyl((x + sx * w / 2, y, z + h / 2), r=0.07 * s, h=h, seg=12)
    m.box((x, y, z + h * 0.78), (w + 0.3, 0.1, 0.1), smooth=False)
    m.mat("rv_black")
    m.sweep([V((x - w / 2 - 0.35, y, z + h + 0.05)), V((x, y, z + h - 0.02)), V((x + w / 2 + 0.35, y, z + h + 0.05))],
            [(-0.07, -0.07), (0.07, -0.07), (0.07, 0.07), (-0.07, 0.07)], closed=True, cap=True)


def leaf_drift(m, c, rnd, n=14, r=0.9):
    """Fallen bamboo leaves drifting on the current."""
    m.mat("rv_leaf_float")
    for i in range(n):
        a = rnd.uniform(0, 2 * math.pi)
        rr = r * math.sqrt(rnd.random())
        p = V(c) + V((math.cos(a) * rr, math.sin(a) * rr, 0.02))
        b = rnd.uniform(0, math.pi)
        d1, d2 = V((math.cos(b), math.sin(b), 0)) * 0.12, V((-math.sin(b), math.cos(b), 0)) * 0.025
        m.poly([tuple(p - d1), tuple(p + d2), tuple(p + d1), tuple(p - d2)])


# ----------------------------------------------------------------------------- river segment

def _bank_profile(side):
    """Cross-section of one bank from the water's edge outward (x, z)."""
    e = RIVER_HALF
    return [(side * (e - 0.1), -0.25), (side * e, 0.12), (side * (e + 0.5), 0.3), (side * (e + 1.6), 0.55),
            (side * (e + 4.0), 0.75), (side * (e + 9.0), 1.0)]


def river_seg(name="river_seg", L=20.0, seed=3, details=True):
    mats()
    rnd = random.Random(seed)
    m = E.Mesher(name)
    # water: lighter shallows at the edges, deeper channel, flow streaks
    m.mat("rv_water_deep")
    m.box((0, L / 2, -0.03), (RIVER_HALF * 1.2, L, 0.02), smooth=False)
    m.mat("rv_water")
    for sx in (-1, 1):
        m.box((sx * RIVER_HALF * 0.82, L / 2, -0.025), (RIVER_HALF * 0.5, L, 0.02), smooth=False)
    m.mat("rv_foam")
    for k in range(16):
        x = rnd.uniform(-RIVER_HALF + 0.3, RIVER_HALF - 0.3)
        y = rnd.uniform(0, L)
        ln = rnd.uniform(0.6, 1.8)
        m.box((x, y, -0.012), (0.04, ln, 0.005), smooth=False)
    # banks: grass slope with a stone edging course along the water
    for sd in (-1, 1):
        prof = _bank_profile(sd)
        rings = []
        for k in range(5):
            y = L * k / 4
            rings.append([(px, y, pz) for (px, pz) in (prof if sd > 0 else prof[::-1])])
        m.mat("rv_grass")
        m.quad_strip(rings, closed=False, smooth=True)
        m.mat("rv_stone")
        y = 0.2
        while y < L:
            w = rnd.uniform(0.45, 0.8)
            m.rbox((sd * (RIVER_HALF + 0.05), y + w / 2, 0.08), (0.35, w - 0.04, 0.3), 0.05, 1)
            y += w
    if details:
        for sd in (-1, 1):
            for k in range(2):
                bamboo_clump(m, (sd * (RIVER_HALF + rnd.uniform(2.2, 4.5)), rnd.uniform(2, L - 2), 0.7), rnd,
                             n=rnd.randint(5, 9))
            reeds(m, (sd * (RIVER_HALF - 0.35), rnd.uniform(1, L - 1), -0.02), rnd)
            lily_pads(m, (sd * (RIVER_HALF - 0.9), rnd.uniform(2, L - 2), 0), rnd)
            m.mat("rv_grass_dark")
            for k in range(6):
                m.ico((sd * (RIVER_HALF + rnd.uniform(0.8, 3.5)), rnd.uniform(0, L), 0.45), rnd.uniform(0.25, 0.5), 1,
                      s=(1, 1, 0.6))
        stone_lantern(m, (rnd.choice((-1, 1)) * (RIVER_HALF + 1.0), rnd.uniform(4, L - 4), 0.3))
        leaf_drift(m, (rnd.uniform(-2, 2), rnd.uniform(3, L - 3), 0), rnd)
    ob = m.obj(name, smooth_angle=40)
    return ob


def fork_island(name="fork_island", L=50.0, half=1.4 / 1.2, seed=5):
    """Island for a Y fork: pointed rocky nose upstream (y=0), grassy body with bamboo, a small torii."""
    mats()
    rnd = random.Random(seed)
    m = E.Mesher(name)
    def w(y):
        u = y / L
        return half * min(1.0, (u / 0.12) ** 0.6) * min(1.0, ((1 - u) / 0.12) ** 0.6)
    rings = []
    for k in range(21):
        y = L * k / 20
        ww = max(0.02, w(y))
        rings.append([(-ww - 0.15, y, -0.2), (-ww, y, 0.25), (-ww * 0.4, y, 0.45), (ww * 0.4, y, 0.45), (ww, y, 0.25),
                      (ww + 0.15, y, -0.2)])
    m.mat("rv_grass")
    m.quad_strip(rings, closed=False, smooth=True)
    m.mat("rv_stone")
    for k in range(6):
        m.ico((rnd.uniform(-0.3, 0.3), rnd.uniform(0.0, 2.0), 0.15), rnd.uniform(0.25, 0.45), 1, s=(1, 1.3, 0.7))
    for k in range(int(L / 4)):
        y = rnd.uniform(2, L - 2)
        sd = rnd.choice((-1, 1))
        m.rbox((sd * (w(y) + 0.05), y, 0.05), (0.3, 0.5, 0.25), 0.05, 1)
    for k in range(3):
        bamboo_clump(m, (rnd.uniform(-0.3, 0.3), L * (0.3 + 0.2 * k), 0.4), rnd, n=5, h=5)
    torii(m, (0, 4.0, 0.42), w=0.9, h=1.2)
    stone_lantern(m, (0.3, 7.0, 0.42))
    reeds(m, (half * 0.8, L * 0.6, 0.0), rnd)
    reeds(m, (-half * 0.8, L * 0.45, 0.0), rnd)
    return m.obj(name, smooth_angle=40)


# ----------------------------------------------------------------------------- hazards

def stone(name="rv_stone", seed=1, r=0.7):
    mats()
    rnd = random.Random(seed)
    m = E.Mesher(name)
    m.mat("rv_stone")
    m.ico((0, 0, 0.15), r, 3, s=(1.0, 1.1, 0.75))
    m.mat("rv_stone_dark")
    m.ico((r * 0.6, -r * 0.3, 0.0), r * 0.5, 1, s=(1, 1, 0.6))
    m.mat("rv_moss")
    m.ico((-r * 0.2, r * 0.1, r * 0.62), r * 0.45, 1, s=(1.2, 1.1, 0.35))
    m.mat("rv_foam")
    m.torus((0, 0, -0.01), R=r * 1.05, r=0.05, seg=24, sides=4)
    m.box((r * 0.4, -r * 1.3, -0.01), (0.04, 0.8, 0.01), smooth=False)
    m.box((-r * 0.4, -r * 1.4, -0.01), (0.04, 1.0, 0.01), smooth=False)
    return m.obj(name, smooth_angle=50)


def croc(name="croc"):
    """Cute-but-dangerous toon crocodile, swimming toward -Y (at the canoe). Two objects: body (with the
    lower jaw) and the upper jaw/head, hinged at JAW_HINGE so the game can open it."""
    mats()
    body = E.Mesher(name + "_body")
    L0, L1 = -1.6, 0.62           # tail tip .. jaw hinge (head points -Y? no: head at +Y side toward hinge)
    # the croc's head points toward -Y (facing the canoe); build along +Y then rotate at the end
    def sec(y):
        u = (y - L0) / (L1 - L0)
        return 0.06 + 0.32 * math.sin(math.pi * min(1.0, u * 1.1)) ** 0.7, 0.05 + 0.2 * math.sin(math.pi * min(1.0, u)) ** 0.8
    rings = []
    for k in range(19):
        y = L0 + (L1 - L0) * k / 18
        w, h = sec(y)
        rings.append([(w * math.cos(a), y, 0.08 + h * math.sin(a) * (0.55 if math.sin(a) < 0 else 1.0))
                      for a in [2 * math.pi * j / 14 for j in range(14)]])
    body.mat("rv_croc")
    body.quad_strip(rings, closed=True, cap0=True)
    # back scutes
    body.mat("rv_croc_dark")
    for k in range(10):
        y = L0 + 0.25 + k * 0.17
        w, h = sec(y)
        for sx in (-1, 1):
            body.cyl((sx * w * 0.35, y, 0.08 + h + 0.01), r=0.035, h=0.045, seg=6, r2=0.01)
    # legs paddling
    for sx in (-1, 1):
        for y in (-0.6, 0.25):
            body.mat("rv_croc")
            body.sphere((sx * 0.36, y, 0.0), 1.0, 10, 6, s=(0.16, 0.09, 0.06))
    # lower jaw (part of the body): flat, belly coloured, teeth along the edge
    body.mat("rv_croc_belly")
    body.rbox((0, L1 + 0.33, 0.06), (0.36, 0.66, 0.07), 0.03, 1)
    body.mat("rv_mouth")
    body.box((0, L1 + 0.33, 0.1), (0.28, 0.58, 0.01), smooth=False)
    body.mat("rv_tooth")
    for k in range(5):
        for sx in (-1, 1):
            body.cyl((sx * 0.15, L1 + 0.1 + k * 0.12, 0.13), r=0.022, h=0.06, seg=5, r2=0.0)
    bo = body.obj(name + "_body", smooth_angle=50)
    # upper jaw / head: snout, eye bumps with big yellow eyes, nostrils, teeth pointing down
    jaw = E.Mesher(name + "_jaw")
    jaw.mat("rv_croc")
    jaw.rbox((0, 0.36, 0.08), (0.38, 0.72, 0.12), 0.05, 2)
    jaw.sphere((0, 0.02, 0.1), 1.0, 14, 8, s=(0.3, 0.22, 0.16))
    for sx in (-1, 1):
        jaw.mat("rv_croc")
        jaw.sphere((sx * 0.11, 0.05, 0.22), 0.09, 12, 8)
        jaw.mat("rv_eye")
        jaw.sphere((sx * 0.12, 0.1, 0.25), 0.06, 12, 8)
        jaw.mat("rv_pupil")
        jaw.box((sx * 0.12, 0.155, 0.255), (0.012, 0.01, 0.07), smooth=False)
        jaw.mat("rv_croc_dark")
        jaw.sphere((sx * 0.06, 0.7, 0.15), 0.025, 8, 5)
    jaw.mat("rv_tooth")
    for k in range(5):
        for sx in (-1, 1):
            jaw.cyl((sx * 0.16, 0.12 + k * 0.12, 0.0), r=0.022, h=0.06, seg=5, r2=0.0, )
    jo = jaw.obj(name + "_jaw", smooth_angle=50)
    # face the croc toward -Y (at the canoe coming up +Y): rotate both 180 deg about Z
    for o in (bo, jo):
        o.data.transform(Matrix.Rotation(math.pi, 4, 'Z'))
    return bo, jo


def drift_log(name="drift_log", seed=2, L=3.2):
    mats()
    rnd = random.Random(seed)
    m = E.Mesher(name)
    m.mat("rv_log")
    m.cyl((0, 0, 0.05), r=0.28, h=L, seg=14, axis='X')
    m.mat("rv_log_end")
    for sx in (-1, 1):
        m.cyl((sx * L / 2, 0, 0.05), r=0.24, h=0.02, seg=14, axis='X')
    m.mat("rv_log")
    m.push(Matrix.Translation((0.5, 0, 0.2)) @ Matrix.Rotation(math.radians(-35), 4, 'Y'))
    m.cyl((0, 0, 0.3), r=0.07, h=0.6, seg=8, r2=0.03)
    m.pop()
    m.mat("rv_moss")
    m.ico((-0.6, 0, 0.27), 0.25, 1, s=(1.4, 1, 0.3))
    m.mat("rv_leaf")
    m.poly([(-0.2, 0.2, 0.3), (0.0, 0.4, 0.3), (0.1, 0.2, 0.32)])
    m.mat("rv_foam")
    m.torus((0, 0, -0.01), R=0.5, r=0.04, seg=20, sides=4)
    ob = m.obj(name, smooth_angle=40)
    ob.data.transform(Matrix.Diagonal((1, 1, 1, 1)))
    return ob


def whirlpool(name="whirlpool", r=1.8):
    mats()
    m = E.Mesher(name)
    m.mat("rv_whirl")
    for arm in range(3):
        pts = []
        for k in range(40):
            t = k / 39
            a = arm * 2 * math.pi / 3 + t * 2.6 * math.pi
            rr = r * (1 - t * 0.9)
            pts.append(V((math.cos(a) * rr, math.sin(a) * rr, 0.01 - 0.12 * t)))
        m.sweep(pts, [(-0.06, -0.005), (0.06, -0.005), (0.06, 0.005), (-0.06, 0.005)], closed=True, cap=True,
                scale=lambda t: 1.0 - 0.6 * t)
    m.mat("rv_water_deep")
    m.cyl((0, 0, -0.1), r=0.25, h=0.02, seg=16)
    return m.obj(name, smooth_angle=60)


# ----------------------------------------------------------------------------- ambient life

def koi(name="koi"):
    mats()
    m = E.Mesher(name)
    rings = []
    for k in range(9):
        y = -0.25 + 0.5 * k / 8
        u = k / 8
        w = 0.07 * math.sin(math.pi * min(1, u * 1.2 + 0.05)) + 0.01
        rings.append([(w * math.cos(a), y, w * 1.1 * math.sin(a)) for a in [2 * math.pi * j / 10 for j in range(10)]])
    m.mat("rv_koi_w")
    m.quad_strip(rings, closed=True, cap0=True, cap1=True)
    m.mat("rv_koi_o")
    m.sphere((0, 0.05, 0.05), 1.0, 10, 6, s=(0.06, 0.1, 0.03))
    m.sphere((0, -0.1, 0.045), 1.0, 10, 6, s=(0.05, 0.06, 0.03))
    m.poly([(0, -0.24, 0), (0.09, -0.36, 0.03), (0.0, -0.31, 0), (-0.09, -0.36, 0.03)])
    return m.obj(name, smooth_angle=60)


def heron(name="heron"):
    """White heron standing in the shallows (ambient)."""
    mats()
    m = E.Mesher(name)
    m.mat("rv_heron")
    m.sphere((0, 0, 0.75), 1.0, 14, 10, s=(0.14, 0.26, 0.15))
    m.tube([(0, 0.18, 0.82), (0, 0.24, 1.0), (0, 0.2, 1.15), (0, 0.26, 1.22)], r=0.03, seg=8, taper=0.8)
    m.sphere((0, 0.27, 1.23), 0.05, 10, 8)
    m.mat("rv_beak")
    m.cyl((0, 0.38, 1.22), r=0.015, h=0.2, seg=6, r2=0.0, axis='Y')
    m.mat("rv_black")
    for sx in (-1, 1):
        m.cyl((sx * 0.04, 0, 0.32), r=0.01, h=0.64, seg=5)
    m.sphere((0.03, 0.29, 1.25), 0.008, 6, 4)
    return m.obj(name, smooth_angle=50)


# ----------------------------------------------------------------------------- design renders

def design_river():
    import studio
    E.reset()
    studio.stage(res=(1280, 720), floor=False)
    for k in range(3):
        seg = river_seg("river_seg_%d" % k, seed=3 + k)
        seg.location = (0, k * 20.0, 0)
    isl = fork_island()
    isl.location = (0, 62.0, 0)
    s1 = stone(seed=1)
    s1.location = (-1.6, 14, 0)
    s2 = stone("rv_stone2", seed=2, r=0.55)
    s2.location = (2.2, 22, 0)
    bo, jo = croc()
    for o in (bo, jo):
        o.location = (1.0, 30, 0)
    jo.rotation_euler = (math.radians(-28), 0, 0)
    jo.location = (1.0, 30 - 0.62, 0.16)
    lg = drift_log()
    lg.location = (-1.2, 38, 0)
    lg.rotation_euler = (0, 0, math.radians(20))
    wp = whirlpool()
    wp.location = (1.5, 46, 0)
    hr = heron()
    hr.location = (-RIVER_HALF + 0.6, 26, 0)
    for o in [s1, s2, bo, jo, lg, hr, isl]:
        E.add_outline(o, 0.012)
    studio.aim_sun(160)
    studio.shoot("river_overview", target=(0, 34, 0.0), dist=22, yaw=180 + 160, pitch=26, lens=30, light=False)
    studio.shoot("river_runner", target=(0, 30, 0.8), dist=12, yaw=0, pitch=14, lens=32, light=False)


def design_river_hazards():
    import studio
    E.reset()
    studio.stage(res=(1280, 640), floor_col=0x8FD3E8)
    s1 = stone(seed=1)
    s1.location = (-3.2, 0, 0)
    bo, jo = croc()
    bo.location = (0, 0, 0)
    jo.location = (0, -0.62, 0.16)
    jo.rotation_euler = (math.radians(-32), 0, 0)
    # the jaw is modelled around the hinge at its origin side: place it at the hinge
    lg = drift_log()
    lg.location = (3.4, 0, 0)
    wp = whirlpool()
    wp.location = (6.6, 0, 0.02)
    k = koi()
    k.location = (-5.4, 0.5, 0.1)
    for o in (s1, bo, jo, lg, k):
        E.add_outline(o, 0.01)
    studio.shoot("river_hazards", target=(0.6, 0, 0.3), dist=11, yaw=200, pitch=22, lens=40)


def design_croc(open_deg="30"):
    import studio
    E.reset()
    studio.stage(res=(900, 600), floor_col=0x8FD3E8)
    bo, jo = croc()
    jo.location = (0, -JAW_HINGE.y, JAW_HINGE.z - 0.06)
    jo.rotation_euler = (math.radians(-float(open_deg)), 0, 0)
    for o in (bo, jo):
        E.add_outline(o, 0.01)
    studio.shoot("croc_%s" % open_deg, target=(0, -0.5, 0.2), dist=3.4, yaw=325, pitch=20, lens=45)
