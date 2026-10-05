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
RIVER_HALF = 4.6                # = Ride.RIVER_HALF (the kits are built at game size, Ride.K = 1)
JAW_HINGE = V((0.0, 0.62, 0.06))        # after the croc is sunk SINK into the water


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
    M("rv_trunk", 0x8A6A58, rim=0.25, soft=0.12, shadow=0x6E5A86)
    M("rv_tree", 0x86C870, rim=0.3, soft=0.25, shadow=0x6E9AA8)
    M("rv_tree2", 0x6CB466, rim=0.3, soft=0.25, shadow=0x5E88A0)
    M("rv_pine", 0x4E9A72, rim=0.3, soft=0.25, shadow=0x4E7698)
    M("rv_hydrangea", 0x9DB6F2, rim=0.3, soft=0.2, emis=0.05)
    M("rv_hydrangea2", 0xC9A8EE, rim=0.3, soft=0.2, emis=0.05)
    M("rv_wall", 0xF6EEDC, rim=0.25, soft=0.1, shadow=0xB8B0D8)
    M("rv_timber", 0x7A5A48, rim=0.25, soft=0.1, shadow=0x5E4A70)
    M("rv_roof", 0x5E6A8E, rim=0.3, soft=0.1, shadow=0x4A4E7E)
    M("rv_far", 0x9CC6C8, rim=0.1, soft=0.3, outline=0.0, flags=E.F_NOCAST, shadow=0x9CB0D8)
    M("rv_far2", 0xB8C8E4, rim=0.1, soft=0.3, outline=0.0, flags=E.F_NOCAST, shadow=0xB0B4E0)
    M("rv_snow", 0xF4F6FF, rim=0.1, soft=0.3, outline=0.0, flags=E.F_NOCAST)
    M("rv_rope", 0xD8C29A, rim=0.2, soft=0.1)
    M("rv_grass_a", 0x6FBF58, rim=0.2, soft=0.25, flags=E.F_FOLIAGE | E.F_DOUBLE, sway=0.35, outline=0.0, shadow=0x6A9AA8)
    M("rv_grass_b", 0x8ED066, rim=0.2, soft=0.25, flags=E.F_FOLIAGE | E.F_DOUBLE, sway=0.35, outline=0.0, shadow=0x7AA6A8)
    M("rv_grass_tip", 0xC2E27C, rim=0.3, soft=0.25, flags=E.F_FOLIAGE | E.F_DOUBLE, sway=0.45, outline=0.0, shadow=0x8EB0A0)
    M("rv_tree_hi", 0xB2DC78, rim=0.35, soft=0.25, shadow=0x7EA6A0)
    M("rv_fl_white", 0xFFFBF0, rim=0.3, soft=0.2, emis=0.05, outline=0.0)
    M("rv_fl_yellow", 0xFFD65A, rim=0.3, soft=0.2, emis=0.05, outline=0.0)
    M("rv_fl_pink", 0xFFB4CC, rim=0.3, soft=0.2, emis=0.05, outline=0.0)
    M("rv_whirl", 0xE8F8FF, emis=0.3, rim=0.0, soft=0.2, flags=E.F_NOCAST | E.F_DECAL, outline=0.0)


# ----------------------------------------------------------------------------- props

def _leaf_blade(m, p, d, L, w):
    """Lanceolate bamboo/grass leaf: 5-point blade from p along d (drooping), width w."""
    d = d.normalized()
    side = d.cross(V((0, 0, 1)))
    if side.length < 1e-4:
        side = V((1, 0, 0))
    side = side.normalized() * w
    sag = V((0, 0, -0.18 * L))
    m.poly([tuple(p), tuple(p + d * L * 0.3 + side + sag * 0.2), tuple(p + d * L * 0.65 + side * 0.7 + sag * 0.6),
            tuple(p + d * L + sag), tuple(p + d * L * 0.65 - side * 0.7 + sag * 0.6), tuple(p + d * L * 0.3 - side + sag * 0.2)])


def bamboo_clump(m, c, rnd, n=7, h=6.5):
    """A clump of culms leaning out, node rings, and leaf sprays: soft lumpy foliage clusters at the crown with
    drooping lance-shaped blades round them, so a grove reads full and feathery (no flat leaf plates)."""
    x0, y0, z0 = c
    k_h = h / 6.5
    for i in range(n):
        a = rnd.uniform(0, 2 * math.pi)
        r0 = rnd.uniform(0.05, 0.35)
        base = V((x0 + math.cos(a) * r0, y0 + math.sin(a) * r0, z0))
        lean = V((math.cos(a) * rnd.uniform(0.15, 0.4), math.sin(a) * rnd.uniform(0.15, 0.4), 1)).normalized()
        hh = h * rnd.uniform(0.7, 1.1)
        top = base + lean * hh + V((math.cos(a), math.sin(a), 0)) * hh * 0.08
        pts = [base.lerp(top, k / 6) + V((math.cos(a), math.sin(a), 0)) * 0.12 * hh * (k / 6) ** 2 for k in range(7)]
        m.mat("rv_bamboo")
        m.tube([tuple(p) for p in pts], r=0.055, seg=8, taper=0.65)
        m.mat("rv_bamboo_node")
        for k in range(1, 6):
            m.torus(tuple(pts[k]), R=0.05 * (1 - 0.06 * k), r=0.012, seg=10, sides=4)
        out = V((math.cos(a), math.sin(a), 0))
        for k in range(4):                                  # foliage clusters along the upper culm
            p = pts[6].lerp(pts[3], k / 4) + out * rnd.uniform(0.2, 0.45)
            for j in range(3):
                m.mat(("rv_tree", "rv_tree2", "rv_tree_hi")[(i + j + k) % 3])
                q = p + V((rnd.uniform(-0.25, 0.25), rnd.uniform(-0.25, 0.25), rnd.uniform(-0.1, 0.15))) * k_h
                m.ico(tuple(q), rnd.uniform(0.22, 0.34) * k_h, 2, s=(1.25, 1.1, 0.7))
            m.mat("rv_leaf")
            for j in range(6):                              # drooping blades sticking out of the cluster
                aa = rnd.uniform(0, 2 * math.pi)
                d = V((math.cos(aa), math.sin(aa), rnd.uniform(-0.6, -0.1)))
                _leaf_blade(m, p + d.normalized() * 0.2 * k_h, d, rnd.uniform(0.35, 0.5) * k_h, 0.045 * k_h)
        for k in range(3):                                  # side twigs with blades lower down
            p = pts[2 + k]
            tw = p + out.cross(V((0, 0, 1))) * rnd.choice((-1, 1)) * 0.35 * k_h + V((0, 0, 0.1))
            m.mat("rv_bamboo_node")
            m.tube([tuple(p), tuple(tw)], r=0.01, seg=4)
            m.mat("rv_leaf")
            for j in range(4):
                aa = rnd.uniform(0, 2 * math.pi)
                _leaf_blade(m, tw, V((math.cos(aa), math.sin(aa), -0.4)), 0.32 * k_h, 0.04 * k_h)


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
    """Kasuga-style toro: hexagonal footing with lotus petals, banded post, platform, firebox with glowing windows
    (round moon and lattice), a broad hexagonal roof with curled-up corners, and the jewel on a lotus cup.
    Moss on the roof and footing so it reads as old stone."""
    x, y, z = c
    m.push(Matrix.Translation((x, y, z)))
    m.mat("rv_lantern")
    m.cyl((0, 0, 0.06), r=0.32, h=0.12, seg=6)                          # kiso footing
    m.cyl((0, 0, 0.16), r=0.27, h=0.08, seg=6, r2=0.2)
    for k in range(6):                                                  # lotus petals
        a = math.radians(30 + 60 * k)
        m.ico((math.cos(a) * 0.17, math.sin(a) * 0.17, 0.2), 0.07, 1, s=(1.0, 0.7, 0.45))
    m.cyl((0, 0, 0.58), r=0.08, h=0.78, seg=12, r2=0.07)                 # sao post
    for zz in (0.32, 0.6, 0.86):
        m.cyl((0, 0, zz), r=0.095, h=0.035, seg=12)
    m.cyl((0, 0, 0.98), r=0.13, h=0.06, seg=6, r2=0.25)                  # chudai platform
    m.cyl((0, 0, 1.04), r=0.25, h=0.06, seg=6)
    m.mat("rv_stone_dark")
    m.cyl((0, 0, 1.24), r=0.19, h=0.34, seg=6)                          # hibukuro firebox
    m.mat("rv_lantern")
    for k in range(6):                                                  # corner posts
        a = math.radians(60 * k)
        m.box((math.cos(a) * 0.185, math.sin(a) * 0.185, 1.24), (0.05, 0.05, 0.34), smooth=False)
    m.mat("rv_lantern_glow")
    for k in range(6):
        a = math.radians(30 + 60 * k)
        m.push(Matrix.Translation((math.cos(a) * 0.168, math.sin(a) * 0.168, 1.24)) @ Matrix.Rotation(a + math.pi / 2, 4, 'Z'))
        if k % 3 == 0:
            m.cyl((0, 0, 0), r=0.055, h=0.012, seg=14, axis='Y')        # moon window
        else:
            m.box((0, 0, 0), (0.11, 0.012, 0.16), smooth=False)
        m.pop()
    m.mat("rv_lantern")
    m.cyl((0, 0, 1.43), r=0.24, h=0.05, seg=6)
    m.cyl((0, 0, 1.53), r=0.46, h=0.16, seg=6, r2=0.14)                 # kasa roof
    for k in range(6):                                                  # warabite curls on the roof corners
        a = math.radians(60 * k)
        m.sphere((math.cos(a) * 0.45, math.sin(a) * 0.45, 1.5), 0.045, 8, 6)
    m.cyl((0, 0, 1.65), r=0.09, h=0.06, seg=12)
    m.sphere((0, 0, 1.71), 1.0, 12, 8, s=(0.11, 0.11, 0.06))           # ukebana cup
    m.sphere((0, 0, 1.79), 1.0, 12, 8, s=(0.075, 0.075, 0.1))          # hoju jewel
    m.cyl((0, 0, 1.88), r=0.0, h=0.06, seg=8, r2=0.02)
    m.mat("rv_moss")
    m.ico((0.12, 0.08, 1.58), 0.16, 2, s=(1.3, 1.0, 0.3))
    m.ico((-0.1, -0.16, 1.56), 0.12, 2, s=(1.2, 1.0, 0.3))
    m.ico((0.2, -0.1, 0.13), 0.14, 2, s=(1.2, 1.0, 0.35))
    m.pop()


def torii(m, c, w=1.6, h=1.9, s=1.0):
    """Myojin torii: slightly leaning pillars on stone footings with black sleeves, a through tie-beam with wedges,
    a centre strut carrying a plaque, and the double top lintel (red shimaki under a black kasagi) curving up at
    both ends."""
    x, y, z = c
    r = 0.075 * s
    m.push(Matrix.Translation((x, y, z)))
    for sx in (-1, 1):
        bx = sx * w / 2
        m.mat("rv_stone")
        m.cyl((bx, 0, 0.05 * s), r=r * 1.9, h=0.1 * s, seg=12, r2=r * 1.6)
        m.mat("rv_torii")
        m.cyl((bx - sx * 0.02 * s, 0, h / 2), r=r * 1.05, h=h, seg=14, r2=r * 0.92)
        m.mat("rv_black")
        m.cyl((bx, 0, 0.2 * s), r=r * 1.18, h=0.2 * s, seg=14)
        m.cyl((bx - sx * 0.018 * s, 0, h * 0.74), r=r * 1.12, h=0.035 * s, seg=14)
    zt = h * 0.74                                                           # nuki tie-beam, through the pillars
    m.mat("rv_torii")
    m.box((0, 0, zt), (w + 0.36 * s, 0.09 * s, 0.11 * s), smooth=False)
    m.mat("rv_black")
    for sx in (-1, 1):
        m.box((sx * (w / 2 + 0.1 * s), 0.06 * s, zt), (0.04 * s, 0.03 * s, 0.13 * s), smooth=False)   # kusabi wedges
    m.mat("rv_torii")
    m.box((0, 0, (zt + h) / 2), (0.08 * s, 0.08 * s, h - zt), smooth=False)   # gakuzuka strut
    m.mat("rv_black")
    m.box((0, -0.05 * s, (zt + h) / 2 + 0.02), (0.22 * s, 0.025 * s, 0.26 * s), smooth=False)   # plaque
    m.mat("rv_lantern_glow")
    m.box((0, -0.064 * s, (zt + h) / 2 + 0.02), (0.15 * s, 0.006, 0.19 * s), smooth=False)
    ext = w / 2 + 0.38 * s

    def lintel(z0, th, dep, up):
        n = 12
        path = [V((-ext + 2 * ext * k / n, 0, z0 + up * (abs(-1 + 2 * k / n) ** 2.4))) for k in range(n + 1)]
        m.sweep(path, [(-dep / 2, -th / 2), (dep / 2, -th / 2), (dep / 2, th / 2), (-dep / 2, th / 2)], closed=True, cap=True)
    m.mat("rv_torii")
    lintel(h + 0.06 * s, 0.1 * s, 0.13 * s, 0.1 * s)                    # shimaki
    m.mat("rv_black")
    lintel(h + 0.15 * s, 0.09 * s, 0.17 * s, 0.16 * s)                   # kasagi
    m.pop()


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

PAL = {"trunk": "rv_trunk", "leaf": "rv_tree", "leaf2": "rv_tree2", "leaf3": "rv_pine", "flower": "rv_hydrangea",
       "flower2": "rv_hydrangea2", "wall": "rv_wall", "timber": "rv_timber", "roof": "rv_roof", "stone": "rv_stone",
       "stone2": "rv_stone_dark", "moss": "rv_moss", "far": "rv_far", "far2": "rv_far2", "snow": "rv_snow",
       "water": "rv_water", "foam": "rv_foam", "rope": "rv_rope", "red": "rv_torii", "glow": "rv_lantern_glow",
       "culm": "rv_bamboo", "grass_a": "rv_grass_a", "grass_b": "rv_grass_b", "grass_tip": "rv_grass_tip",
       "leaf_hi": "rv_tree_hi", "fl_white": "rv_fl_white", "fl_yellow": "rv_fl_yellow", "fl_pink": "rv_fl_pink"}


def _bank_profile(side):
    """Cross-section of one bank from the water's edge outward (x, z): low grassy bank, then the valley side
    rising into wooded hills so the frame is full either side of the river."""
    e = RIVER_HALF
    return [(side * (e - 0.1), -0.25), (side * e, 0.12), (side * (e + 0.5), 0.3), (side * (e + 1.6), 0.55),
            (side * (e + 4.0), 0.75), (side * (e + 9.0), 1.2), (side * (e + 14.0), 2.6), (side * (e + 22.0), 6.0),
            (side * (e + 34.0), 13.0)]


def _bank_z(d):
    """Ground height at distance d outward from the river's edge (matches _bank_profile)."""
    prof = [(-0.1, -0.25), (0, 0.12), (0.5, 0.3), (1.6, 0.55), (4.0, 0.75), (9.0, 1.2), (14.0, 2.6), (22.0, 6.0),
            (34.0, 13.0)]
    for (a, za), (b, zb) in zip(prof, prof[1:]):
        if d <= b:
            return za + (zb - za) * (d - a) / (b - a)
    return prof[-1][1]


def river_sides(m, L, rnd, sd):
    """Dense dressing for one bank: water's edge, the near bank, the bamboo grove, the hillside village."""
    import scenery as SC
    e = RIVER_HALF
    P = PAL
    at = lambda d, y: (sd * (e + d), y, _bank_z(d))
    # water's edge: reed beds, lily pads, mossy boulders, stepping stones
    for k in range(4):
        reeds(m, (sd * (e - 0.35), rnd.uniform(0.5, L - 0.5), -0.02), rnd, n=9)
    for k in range(2):
        lily_pads(m, (sd * (e - 1.0), rnd.uniform(1, L - 1), 0), rnd, n=4)
    for k in range(5):
        SC.rock(m, P, at(rnd.uniform(-0.2, 0.6), rnd.uniform(0, L)), rnd, r=rnd.uniform(0.2, 0.45))
    # the whole bank under a carpet of grass and wildflowers (no bare ground), ferns along the edge
    zf = lambda px, py: _bank_z(abs(px) - e)
    lo, hi = sorted((sd * (e + 0.35), sd * (e + 16.0)))
    SC.grass_carpet(m, P, lo, hi, 0.0, L, zf, rnd, density=2.2, h=0.42, flowers=0.07)
    for k in range(6):
        d = rnd.uniform(0.6, 3.0)
        SC.fern(m, P, at(d, rnd.uniform(0, L)), rnd, r=rnd.uniform(0.45, 0.7))
    for k in range(12):
        y = rnd.uniform(0.5, L - 0.5)
        SC.shrub(m, P, at(rnd.uniform(1.2, 3.8), y), rnd, r=rnd.uniform(0.35, 0.6),
                 flowers=rnd.choice((P["flower"], P["flower2"])))
    y0 = rnd.uniform(1, 6)
    SC.bamboo_fence(m, P, at(2.2, y0), at(2.2, y0 + rnd.uniform(5, 9)))
    # bamboo grove behind, thick
    for k in range(6):
        bamboo_clump(m, at(rnd.uniform(4.0, 8.5), rnd.uniform(0.5, L - 0.5)), rnd, n=rnd.randint(6, 10),
                     h=rnd.uniform(5.5, 8.0))
    # hillside: broadleaf trees and pines, with a house or a mill now and then
    for k in range(7):
        d = rnd.uniform(8.5, 20.0)
        SC.round_tree(m, P, at(d, rnd.uniform(0, L)), rnd, h=rnd.uniform(2.8, 4.5), r=rnd.uniform(1.1, 1.8))
    for k in range(3):
        SC.pine(m, P, at(rnd.uniform(10, 21), rnd.uniform(0, L)), rnd, h=rnd.uniform(3.5, 5.5))
    for k in range(8):
        SC.shrub(m, P, at(rnd.uniform(5, 16), rnd.uniform(0, L)), rnd, r=rnd.uniform(0.6, 1.1),
                 flowers=rnd.choice((None, P["flower"], P["flower2"], P["fl_white"])))
    # forest on the upper slope: a continuous canopy so the hillside is fully covered
    SC.canopy_mass(m, P, *sorted((sd * (e + 15.0), sd * (e + 33.0))), 0.0, L, zf, rnd, n=26, r=(1.8, 3.0))
    r = rnd.random()
    if r < 0.45:
        SC.house(m, P, at(rnd.uniform(9, 13), rnd.uniform(4, L - 4)), rnd, rot=math.radians(90 if sd > 0 else -90))
    elif r < 0.7:
        y = rnd.uniform(4, L - 4)
        # the wheel stands in the shallows, its axle running into the mill on the bank
        SC.water_wheel(m, P, (sd * (e - 0.55), y, 0.5), rot=0.0 if sd > 0 else math.pi, axle=2.4)
        SC.house(m, P, at(1.6, y), rnd, rot=math.radians(90 if sd > 0 else -90), w=2.2, d=1.8, h=1.3)
    else:
        SC.dock(m, P, (sd * (e - 0.2), rnd.uniform(4, L - 4), 0.0), rot=0.0)


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
            river_sides(m, L, rnd, sd)
        stone_lantern(m, (rnd.choice((-1, 1)) * (RIVER_HALF + 1.0), rnd.uniform(4, L - 4), 0.3))
        leaf_drift(m, (rnd.uniform(-2, 2), rnd.uniform(3, L - 3), 0), rnd)
    ob = m.obj(name, smooth_angle=40)
    return ob


def fork_island(name="fork_island", L=50.0, half=1.4, seed=5):
    """Island for a Y fork: pointed rocky nose upstream (y=0), grassy body fully carpeted, mossy shore rocks
    sitting in the water, bamboo groves, a small torii and a lantern."""
    import scenery as SC
    mats()
    rnd = random.Random(seed)
    m = E.Mesher(name)

    def w(y):
        u = y / L
        return half * min(1.0, (u / 0.12) ** 0.6) * min(1.0, ((1 - u) / 0.12) ** 0.6)
    rings = []
    for k in range(41):
        y = L * k / 40
        ww = max(0.02, w(y))
        rings.append([(-ww - 0.25, y, -0.35), (-ww, y, 0.2), (-ww * 0.6, y, 0.38), (0, y, 0.45), (ww * 0.6, y, 0.38),
                      (ww, y, 0.2), (ww + 0.25, y, -0.35)])
    m.mat("rv_grass")
    m.quad_strip(rings, closed=False, smooth=True)

    def zf(px, py):
        ww = max(0.05, w(py))
        return 0.45 - 0.25 * min(1.0, (px / ww) ** 2)
    SC.grass_carpet(m, PAL, -half * 0.85, half * 0.85, 1.5, L - 1.5, lambda px, py: zf(px, py) if abs(px) < w(py) * 0.9 else -9,
                    rnd, density=2.4, h=0.4, flowers=0.08)
    m.mat("rv_stone")                                                    # rocky nose that splits the current
    for k in range(7):
        m.ico((rnd.uniform(-0.35, 0.35), rnd.uniform(-0.2, 2.0), rnd.uniform(-0.05, 0.12)), rnd.uniform(0.25, 0.45), 2,
              s=(1, 1.3, 0.7))
    for k in range(int(L / 2.2)):                                        # shore rocks half in the water, mossy tops
        y = rnd.uniform(2, L - 2)
        sd = rnd.choice((-1, 1))
        r = rnd.uniform(0.18, 0.34)
        p = (sd * (w(y) + 0.08), y, 0.0)
        m.mat("rv_stone" if k % 3 else "rv_stone_dark")
        m.ico(p, r, 2, s=(1.1, 1.4, 0.7))
        m.mat("rv_moss")
        m.ico((p[0], p[1], r * 0.45), r * 0.75, 2, s=(1.1, 1.3, 0.3))
    for k in range(4):
        bamboo_clump(m, (rnd.uniform(-0.3, 0.3), L * (0.22 + 0.18 * k), 0.4), rnd, n=5, h=5)
    for k in range(6):
        y = rnd.uniform(4, L - 4)
        SC.shrub(m, PAL, (rnd.uniform(-0.5, 0.5) * w(y), y, 0.38), rnd, r=rnd.uniform(0.35, 0.55),
                 flowers=rnd.choice((None, "rv_hydrangea", "rv_hydrangea2")))
    torii(m, (0, 4.0, 0.42), w=0.9, h=1.2, s=0.65)
    stone_lantern(m, (0.3, 7.0, 0.42))
    reeds(m, (half * 0.9, L * 0.6, 0.0), rnd)
    reeds(m, (-half * 0.9, L * 0.45, 0.0), rnd)
    return m.obj(name, smooth_angle=40)


# ----------------------------------------------------------------------------- hazards

def stone(name="rv_stone", seed=1, r=0.7):
    """River boulder: a cluster of rounded rocks with a dark wet band at the waterline, a moss cap with grass and a
    fern, pebbles at its foot, a foam pillow on the upstream side and a wake trailing downstream (-Y)."""
    mats()
    rnd = random.Random(seed)
    m = E.Mesher(name)
    m.mat("rv_stone")
    m.push(Matrix.Rotation(math.radians(9), 4, 'Y') @ Matrix.Rotation(math.radians(-6), 4, 'X'))
    m.ico((-r * 0.12, 0.05, 0.1), r * 0.9, 2, s=(1.0, 1.15, 0.85))
    m.pop()
    m.mat("rv_stone_dark")
    m.ico((r * 0.6, -r * 0.3, 0.12), r * 0.62, 2, s=(1.0, 1.1, 0.8))
    m.mat("rv_stone")
    m.ico((-r * 0.65, r * 0.3, 0.02), r * 0.48, 2, s=(1.1, 1.0, 0.7))
    m.ico((r * 0.2, r * 0.55, 0.0), r * 0.35, 2, s=(1.0, 1.0, 0.6))
    m.mat("rv_stone_dark")                                               # wet band where the water laps
    m.ico((0, 0, -0.02), r * 1.03, 3, s=(1.0, 1.1, 0.16))
    m.ico((r * 0.55, -r * 0.35, -0.03), r * 0.57, 2, s=(1.0, 1.1, 0.14))
    m.ico((-r * 0.6, r * 0.2, -0.03), r * 0.47, 2, s=(1.1, 1.0, 0.14))
    m.mat("rv_stone")                                                    # chips and cracks
    for k in range(4):
        a = rnd.uniform(0, 2 * math.pi)
        m.ico((math.cos(a) * r * 0.75, math.sin(a) * r * 0.8, r * rnd.uniform(0.15, 0.4)), r * rnd.uniform(0.2, 0.3), 2,
              s=(1, 1, 0.7))
    m.mat("rv_moss")
    for (mx, my, mz, mr) in ((-0.2, 0.1, 0.78, 0.42), (0.05, -0.15, 0.74, 0.3), (-0.4, 0.3, 0.62, 0.26),
                             (0.6, -0.3, 0.55, 0.28)):
        m.ico((r * mx, r * my, r * mz), r * mr, 2, s=(1.15, 1.05, 0.45))
    m.mat("rv_grass_b")
    for k in range(7):
        a = rnd.uniform(0, 2 * math.pi)
        p = V((-r * 0.15 + math.cos(a) * r * 0.3, r * 0.1 + math.sin(a) * r * 0.3, r * 0.78))
        d = V((math.cos(a) * 0.3, math.sin(a) * 0.3, 1)).normalized()
        sd = d.cross(V((0, 0, 1))).normalized() * 0.02 if abs(d.z) < 0.999 else V((0.02, 0, 0))
        m.poly([tuple(p - sd), tuple(p + sd), tuple(p + d * rnd.uniform(0.15, 0.25))])
    m.mat("rv_stone_dark")
    for k in range(6):                                                   # pebbles at the foot
        a = rnd.uniform(0, 2 * math.pi)
        m.ico((math.cos(a) * r * 1.15, math.sin(a) * r * 1.2, 0.0), rnd.uniform(0.05, 0.1), 1, s=(1.2, 1, 0.5))
    m.mat("rv_foam")
    m.torus((0, 0, 0.0), R=r * 1.08, r=0.03, seg=28, sides=5)
    m.ico((0, r * 1.05, 0.0), r * 0.4, 2, s=(1.6, 0.5, 0.12))          # pillow upstream
    for sx in (-1, 1):                                                   # wake streaks downstream
        for k in range(3):
            m.box((sx * (r * 0.45 + k * 0.08), -r * (1.3 + k * 0.45), 0.0), (0.05, 0.5 - k * 0.1, 0.012), smooth=False)
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
    # waterline: foam collar round the back and a V of ripples off the snout (the part under z=0 is hidden by water)
    wl = E.Mesher(name + "_wake")
    wl.mat("rv_foam")
    for k in range(17):
        y = L0 + 0.1 + (L1 - L0 - 0.1) * k / 16
        w, h = sec(y)
        for sx in (-1, 1):
            wl.box((sx * (w + 0.02), y, 0.1), (0.05, 0.14, 0.012), smooth=False)
    for sx in (-1, 1):
        wl.push(Matrix.Translation((0, L1 + 0.75, 0.0)) @ Matrix.Rotation(math.radians(sx * 28), 4, 'Z'))
        for k in range(3):
            wl.box((0, -0.5 - k * 0.5, 0.1), (0.04, 0.34, 0.012), smooth=False)
        wl.pop()
    wo = wl.obj(name + "_wake", smooth_angle=50)
    bo = E.join([bo, wo], name + "_body")
    # sink it 0.1 m so only the back, the scutes, the eyes and the snout ride above the water, and face -Y
    bo.data.transform(Matrix.Rotation(math.pi, 4, 'Z') @ Matrix.Translation((0, 0, -0.1)))
    jo.data.transform(Matrix.Rotation(math.pi, 4, 'Z'))       # origin = hinge; place it at JAW_HINGE
    return bo, jo


def drift_log(name="drift_log", seed=2, L=3.2):
    """Floating log a little over half sunk: knobbly trunk with bark ridges, ringed end grain on the sawn end and a
    splintered break on the other, a branch stub with a leafy twig, moss, shelf fungus, and waterline foam."""
    mats()
    rnd = random.Random(seed)
    m = E.Mesher(name)
    zc = -0.06
    R = 0.28
    bulge = [rnd.uniform(0.92, 1.06) for _ in range(9)]
    rad = lambda t: R * bulge[min(8, int(t * 8))] * (1 - 0.08 * t)
    path = [(-L / 2 + L * k / 16, 0, zc) for k in range(17)]
    m.mat("rv_log")
    m.tube(path, r=1.0, seg=16, taper=lambda t: rad(t), cap=False)
    m.mat("rv_trunk")                                                    # bark ridges along the trunk
    for k in range(14):
        a = 2 * math.pi * k / 14 + rnd.uniform(-0.1, 0.1)
        if math.sin(a) < -0.35:
            continue
        x0 = rnd.uniform(-L / 2 + 0.1, 0)
        x1 = rnd.uniform(0.2, L / 2 - 0.15)
        rr = R * 1.0
        m.tube([(x, math.cos(a) * rr * (1 - 0.04 * (x + L / 2) / L), zc + math.sin(a) * rr) for x in (x0, (x0 + x1) / 2, x1)],
               r=0.022, seg=4)
    m.mat("rv_log_end")                                                  # sawn end: pale end grain with rings
    m.cyl((-L / 2, 0, zc), r=rad(0) * 0.97, h=0.03, seg=16, axis='X')
    m.mat("rv_log")
    for rr in (0.3, 0.55, 0.8):
        m.torus((-L / 2 - 0.016, 0, zc), R=rad(0) * rr, r=0.008, seg=20, sides=4, axis='X')
    m.mat("rv_log_end")                                                  # broken end: jagged splinters
    for k in range(9):
        a = 2 * math.pi * k / 9
        p = V((L / 2, math.cos(a) * rad(1) * 0.6, zc + math.sin(a) * rad(1) * 0.6))
        m.push(Matrix.Translation(p) @ Matrix.Rotation(math.radians(90), 4, 'Y'))
        m.cyl((0, 0, 0.0), r=0.07, h=rnd.uniform(0.15, 0.35), seg=4, r2=0.0)
        m.pop()
    m.cyl((L / 2 - 0.01, 0, zc), r=rad(1) * 0.9, h=0.03, seg=16, axis='X')
    m.mat("rv_log")                                                      # branch stub with a twig
    m.push(Matrix.Translation((0.5, 0.05, zc + R * 0.85)) @ Matrix.Rotation(math.radians(-35), 4, 'Y'))
    m.cyl((0, 0, 0.28), r=0.075, h=0.56, seg=8, r2=0.045)
    m.tube([(0, 0, 0.45), (0.12, 0.08, 0.62), (0.18, 0.2, 0.72)], r=0.02, seg=5, taper=0.5)
    m.mat("rv_leaf")
    for k in range(5):
        a = rnd.uniform(0, 2 * math.pi)
        _leaf_blade(m, V((0.15, 0.16, 0.68)), V((math.cos(a), math.sin(a), -0.3)), 0.2, 0.05)
    m.pop()
    m.mat("rv_moss")
    for (mx, my, mr) in ((-0.75, 0.0, 0.22), (-0.55, 0.08, 0.17), (-0.9, -0.06, 0.15), (0.9, -0.05, 0.16), (1.05, 0.04, 0.12)):
        m.ico((mx, my, zc + R * 0.9), mr, 2, s=(1.3, 1.0, 0.5))
    m.mat("rv_log_end")                                                  # shelf fungus on the side
    for k in range(3):
        m.sphere((-0.2 + k * 0.16, -R * 0.95, zc + 0.08 + 0.05 * (k % 2)), 1.0, 10, 5, s=(0.08, 0.06, 0.02))
    m.mat("rv_foam")
    for sy in (-1, 1):
        m.box((0, sy * (R * 0.92), 0.0), (L - 0.1, 0.06 if sy < 0 else 0.1, 0.012), smooth=False)
    for k in range(5):
        x = -L / 2 + 0.3 + k * (L - 0.6) / 4
        m.box((x, 0.45, 0.0), (0.3, 0.04, 0.012), smooth=False)
    return m.obj(name, smooth_angle=40)


def whirlpool(name="whirlpool", r=1.8):
    """Whirlpool read from the canoe: a darker swirl of deep water, four thick foam arms spiralling into a dark eye,
    and a broken ring of foam bubbles at the rim."""
    mats()
    m = E.Mesher(name)
    m.mat("rv_water_deep")
    m.cyl((0, 0, 0.004), r=r * 0.95, h=0.006, seg=40)
    m.mat("rv_black")
    m.cyl((0, 0, 0.012), r=0.28, h=0.006, seg=24)
    m.mat("rv_whirl")
    for arm in range(4):
        pts = []
        for k in range(48):
            t = k / 47
            a = arm * math.pi / 2 + t * 2.4 * math.pi
            rr = r * (1 - t * 0.85)
            pts.append(V((math.cos(a) * rr, math.sin(a) * rr, 0.02 + 0.01 * t)))
        m.sweep(pts, [(-0.11, -0.008), (0.11, -0.008), (0.11, 0.012), (-0.11, 0.012)], closed=True, cap=True,
                scale=lambda t: 1.0 - 0.7 * t)
    m.mat("rv_foam")
    for k in range(26):
        a = 2 * math.pi * k / 26
        if k % 7 == 3:
            continue
        m.sphere((math.cos(a) * r, math.sin(a) * r, 0.02), 1.0, 8, 5, s=(0.09, 0.09, 0.04))
    return m.obj(name, smooth_angle=60)


# ----------------------------------------------------------------------------- ambient life

def koi(name="koi"):
    """Kohaku koi: lofted body (deep in front, slim tail stock), red patches, dorsal and pectoral fins, a flowing
    forked tail, eyes and barbels. Head toward +Y."""
    mats()
    m = E.Mesher(name)
    rings = []
    N = 14
    for k in range(N + 1):
        u = k / N
        y = -0.26 + 0.52 * u
        w = 0.012 + 0.07 * math.sin(math.pi * min(1.0, 0.08 + u * 0.98)) ** 0.8
        hh = w * 1.25
        rings.append([(w * math.cos(a), y, hh * math.sin(a) * (0.8 if math.sin(a) < 0 else 1.0))
                      for a in [2 * math.pi * j / 14 for j in range(14)]])
    m.mat("rv_koi_w")
    m.quad_strip(rings, closed=True, cap0=True, cap1=True)
    m.mat("rv_koi_o")
    for (yy, sx, s_) in ((0.15, 0.008, 0.05), (0.02, -0.01, 0.058), (-0.12, 0.01, 0.04)):   # red saddles on the back
        m.sphere((sx, yy, 0.05), 1.0, 14, 7, s=(s_ * 1.1, s_ * 1.5, 0.05))
    m.mat("rv_koi_w")
    m.poly([(0, 0.08, 0.075), (0, -0.12, 0.07), (0, -0.16, 0.05), (0, 0.0, 0.12), (0, 0.08, 0.095)])     # dorsal
    for sx in (-1, 1):
        m.poly([(sx * 0.06, 0.12, -0.01), (sx * 0.12, 0.07, -0.02), (sx * 0.09, 0.05, -0.015)])          # pectorals
    m.mat("rv_koi_o")
    m.poly([(0, -0.24, 0.01), (0.06, -0.33, 0.02), (0.16, -0.46, 0.03), (0.07, -0.44, 0.0), (0, -0.35, 0.0)])
    m.poly([(0, -0.24, 0.01), (0, -0.35, 0.0), (-0.07, -0.44, 0.0), (-0.16, -0.46, 0.03), (-0.06, -0.33, 0.02)])
    m.mat("rv_pupil")
    for sx in (-1, 1):
        m.sphere((sx * 0.032, 0.21, 0.02), 0.012, 8, 5)
    m.mat("rv_koi_w")
    for sx in (-1, 1):
        m.tube([(sx * 0.015, 0.25, -0.01), (sx * 0.04, 0.27, -0.02)], r=0.004, seg=4)
    return m.obj(name, smooth_angle=60)


def heron(name="heron"):
    """Grey heron standing in the shallows: teardrop body with folded wings (dark flight feathers), tail, an
    S-curved neck, a head with a black crest plume and a long dagger bill, and backward-kneed legs with toes."""
    mats()
    m = E.Mesher(name)
    rings = []
    for k in range(13):                                                  # body, tilted nose-up
        u = k / 12
        y = -0.3 + 0.55 * u
        w = 0.02 + 0.13 * math.sin(math.pi * min(1.0, 0.05 + u)) ** 0.7
        rings.append([(w * math.cos(a), y, 0.78 + 0.25 * (y + 0.05) + w * 1.1 * math.sin(a))
                      for a in [2 * math.pi * j / 14 for j in range(14)]])
    m.mat("rv_heron")
    m.quad_strip(rings, closed=True, cap0=True, cap1=True)
    for sx in (-1, 1):                                                   # folded wings hugging the body
        m.mat("rv_lantern")
        m.push(Matrix.Translation((sx * 0.085, -0.06, 0.82)) @ Matrix.Rotation(math.radians(-14), 4, 'X'))
        m.sphere((0, 0, 0), 1.0, 14, 8, s=(0.06, 0.27, 0.11))
        m.mat("rv_stone_dark")
        m.sphere((-sx * 0.01, -0.2, -0.03), 1.0, 12, 6, s=(0.045, 0.17, 0.06))      # dark flight feathers
        m.pop()
    m.mat("rv_heron")
    neck = [(0, 0.2, 0.9), (0, 0.27, 1.0), (0, 0.22, 1.12), (0, 0.2, 1.22), (0, 0.27, 1.32)]
    m.tube(neck, r=0.05, seg=10, taper=0.65)
    m.sphere((0, 0.29, 1.34), 1.0, 12, 8, s=(0.05, 0.075, 0.05))
    m.mat("rv_black")
    m.tube([(0, 0.26, 1.37), (0, 0.17, 1.39), (0, 0.08, 1.35)], r=0.012, seg=5, taper=0.2)   # crest plume
    for sx in (-1, 1):
        m.box((sx * 0.04, 0.3, 1.355), (0.004, 0.06, 0.012), smooth=False)               # eye stripe
    m.mat("rv_beak")
    m.cyl((0, 0.45, 1.335), r=0.02, h=0.24, seg=8, r2=0.002, axis='Y')
    m.mat("rv_eye")
    for sx in (-1, 1):
        m.sphere((sx * 0.042, 0.33, 1.35), 0.011, 6, 4)
    m.mat("rv_beak")                                                     # legs: thigh, backward knee, shank, toes
    for sx in (-1, 1):
        hip, knee, ank = V((sx * 0.05, 0.0, 0.72)), V((sx * 0.055, -0.04, 0.42)), V((sx * 0.05, 0.02, 0.03))
        m.tube([tuple(hip), tuple(knee)], r=0.016, seg=6)
        m.sphere(tuple(knee), 0.02, 8, 5)
        m.tube([tuple(knee), tuple(ank)], r=0.012, seg=6)
        for a in (-35, 0, 35, 180):
            d = V((math.sin(math.radians(a)), math.cos(math.radians(a)), 0)) * (0.1 if a != 180 else 0.05)
            m.tube([tuple(ank), tuple(ank + d + V((0, 0, -0.02)))], r=0.007, seg=4)
    return m.obj(name, smooth_angle=50)


# ----------------------------------------------------------------------------- design renders

def backdrop(name="river_far", seed=7):
    """Far valley: two rows of soft peaks ahead and down both sides (no outlines, fogged by distance)."""
    import scenery as SC
    mats()
    rnd = random.Random(seed)
    m = E.Mesher(name)
    SC.mountains(m, PAL, (0, 120, -1.0), rnd, n=7, w=160, h=(14, 30), depth=14)
    for sd in (-1, 1):
        m.push(Matrix.Translation((sd * 62, 50, 4.0)) @ Matrix.Rotation(math.radians(90 * sd), 4, 'Z'))
        SC.mountains(m, PAL, (0, 0, 0), rnd, n=6, w=130, h=(10, 20), depth=12)
        m.pop()
    return m.obj(name, smooth_angle=30)


def design_river():
    import studio
    E.reset()
    studio.stage(res=(1280, 720), floor=False)
    for k in range(3):
        seg = river_seg("river_seg_%d" % k, seed=3 + k)
        seg.location = (0, k * 20.0, 0)
    isl = fork_island()
    isl.location = (0, 62.0, 0)
    for k in range(3, 5):
        seg = river_seg("river_seg_%d" % k, seed=3 + k)
        seg.location = (0, k * 20.0, 0)
    backdrop("river_far")
    s1 = stone(seed=1)
    s1.location = (-1.6, 14, 0)
    s2 = stone("rv_stone2", seed=2, r=0.55)
    s2.location = (2.2, 22, 0)
    bo, jo = croc()
    for o in (bo, jo):
        o.location = (1.0, 30, 0)
    jo.rotation_euler = (math.radians(-28), 0, 0)
    jo.location = (1.0, 30 - JAW_HINGE.y, JAW_HINGE.z)
    lg = drift_log()
    lg.location = (-1.2, 38, 0)
    lg.rotation_euler = (0, 0, math.radians(20))
    wp = whirlpool()
    wp.location = (1.5, 46, 0)
    hr = heron()
    hr.location = (-RIVER_HALF + 0.6, 26, 0)
    for o in [s1, s2, bo, jo, lg, hr, isl]:
        E.add_outline(o, 0.012)
    import sky_kit as SK
    rnd = random.Random(21)
    for k in range(7):                       # big painterly cumulus over the valley
        c = SK.cloud("river_cloud_%d" % k, seed=30 + k, size=rnd.uniform(16, 28))
        c.location = (rnd.uniform(-70, 70), rnd.uniform(90, 170), rnd.uniform(22, 40))
    studio.haze(0xDCEBF4, start=18.0, depth=150.0, amount=0.7)
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
    jo.location = (0, -JAW_HINGE.y, JAW_HINGE.z)
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
    jo.location = (0, -JAW_HINGE.y, JAW_HINGE.z)
    jo.rotation_euler = (math.radians(-float(open_deg)), 0, 0)
    for o in (bo, jo):
        E.add_outline(o, 0.01)
    studio.shoot("croc_%s" % open_deg, target=(0, -0.5, 0.2), dist=3.4, yaw=325, pitch=20, lens=45)
