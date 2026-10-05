"""
Side scenery shared by the vehicle zones (river, sky): the dense small detail that fills the frame either side of
the play lane. Same art style as the Sakura Line kit (flat toon, violet-tinted shadows, thin ink outlines, pastel),
but each zone passes its own palette, so the river stays green/blue and the sky valley stays sunny gold/teal.

Every helper adds geometry to an existing erlib.Mesher; materials are named by the caller's palette dict `P`:
  P["trunk"], P["leaf"], P["leaf2"], P["leaf3"], P["flower"], P["flower2"], P["wall"], P["timber"], P["roof"],
  P["stone"], P["stone2"], P["moss"], P["far"], P["far2"], P["snow"], P["water"], P["foam"], P["rope"], P["red"]
"""
import math, random
from mathutils import Vector, Matrix
import erlib as E

V = Vector


def round_tree(m, P, c, rnd, h=3.2, r=1.3):
    """Broadleaf tree: curved trunk, canopy of clustered blobs in two greens (cloud-like anime foliage)."""
    x, y, z = c
    lean = V((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), 1)).normalized()
    top = V(c) + lean * h * 0.62
    m.mat(P["trunk"])
    m.tube([tuple(V(c)), tuple(V(c).lerp(top, 0.5) + V((0.08, 0, 0))), tuple(top)], r=0.11 * h / 3.2, seg=7, taper=0.6)
    for k in range(rnd.randint(7, 10)):
        a = rnd.uniform(0, 2 * math.pi)
        rr = r * rnd.uniform(0.2, 0.75)
        p = top + V((math.cos(a) * rr, math.sin(a) * rr, rnd.uniform(0.0, r * 0.9)))
        hi = p.z - top.z > r * 0.45
        m.mat(P.get("leaf_hi", P["leaf"]) if hi else (P["leaf"] if k % 3 else P["leaf2"]))   # sunlit crown on top
        s = rnd.uniform(0.55, 0.85) * r
        m.ico(tuple(p), s, 2, s=(1, 1, 0.8))


def pine(m, P, c, rnd, h=4.0):
    """Japanese black pine: twisted trunk, branches reaching out to cloud pads; each pad is a cluster of soft lumps
    with a sunlit layer on top, so it reads as needles massed into clouds, not flat plates."""
    base = V(c)
    pts = [base]
    for k in range(1, 5):
        pts.append(base + V((math.sin(k * 1.3) * 0.25 * k / 4, math.cos(k * 0.9) * 0.15, h * k / 4)))
    m.mat(P["trunk"])
    m.tube([tuple(p) for p in pts], r=0.12 * h / 4, seg=8, taper=0.5)
    hi = P.get("leaf_hi", P["leaf"])
    for k in range(1, 5):
        a = rnd.uniform(0, 2 * math.pi) + k * 2.1
        reach = (1.3 - k * 0.22) * h / 4
        pad = pts[k] + V((math.cos(a) * reach * 0.6, math.sin(a) * reach * 0.6, 0.05))
        if k < 4:                                               # branch out to the pad
            m.mat(P["trunk"])
            m.tube([tuple(pts[k] + V((0, 0, -0.15))), tuple(pad)], r=0.05 * h / 4, seg=6, taper=0.6)
        w = (1.1 - k * 0.16) * h / 4
        for j in range(4):
            q = pad + V((rnd.uniform(-0.5, 0.5) * w, rnd.uniform(-0.5, 0.5) * w, rnd.uniform(-0.05, 0.05)))
            m.mat(P["leaf3"])
            m.ico(tuple(q), w * rnd.uniform(0.45, 0.6), 2, s=(1, 0.9, 0.42))
            m.mat(hi if j % 2 == 0 else P["leaf"])
            m.ico(tuple(q + V((0.05, 0.03, w * 0.16))), w * rnd.uniform(0.3, 0.4), 2, s=(1, 0.9, 0.35))


def shrub(m, P, c, rnd, r=0.5, flowers=None):
    """Rounded shrub of 3-4 blobs, optional flower dots (hydrangea, azalea)."""
    m.mat(P["leaf2"])
    for k in range(rnd.randint(3, 4)):
        p = V(c) + V((rnd.uniform(-r, r) * 0.6, rnd.uniform(-r, r) * 0.6, r * 0.5))
        m.ico(tuple(p), r * rnd.uniform(0.6, 0.85), 2, s=(1, 1, 0.8))
    if flowers:
        m.mat(flowers)
        for k in range(rnd.randint(4, 7)):
            a = rnd.uniform(0, 2 * math.pi)
            p = V(c) + V((math.cos(a) * r * 0.75, math.sin(a) * r * 0.75, r * rnd.uniform(0.6, 1.1)))
            m.ico(tuple(p), r * 0.22, 1)


def grass_tufts(m, P, c, rnd, n=8, spread=0.8, h=0.35):
    m.mat(P["leaf"])
    for i in range(n):
        p = V(c) + V((rnd.uniform(-spread, spread), rnd.uniform(-spread, spread), 0))
        for j in range(3):
            a = rnd.uniform(0, math.pi)
            d = V((math.cos(a), math.sin(a), 0)) * 0.05
            tip = p + V((rnd.uniform(-0.1, 0.1), rnd.uniform(-0.1, 0.1), h * rnd.uniform(0.6, 1.2)))
            m.poly([tuple(p - d), tuple(p + d), tuple(tip)])


def rock(m, P, c, rnd, r=0.4, moss=True):
    m.mat(P["stone"] if rnd.random() < 0.6 else P["stone2"])
    m.ico(tuple(c), r, 1, s=(1, rnd.uniform(0.8, 1.3), rnd.uniform(0.5, 0.8)))
    if moss:
        m.mat(P["moss"])
        m.ico(tuple(V(c) + V((0, 0, r * 0.45))), r * 0.7, 1, s=(1, 1, 0.25))


def bamboo_fence(m, P, a, b, h=0.9):
    """Takegaki fence: posts, three horizontal culms, rope ties."""
    a, b = V(a), V(b)
    n = max(2, int((b - a).length / 1.2) + 1)
    m.mat(P["timber"])
    for k in range(n):
        p = a.lerp(b, k / (n - 1))
        m.cyl(tuple(p + V((0, 0, h / 2 + 0.05))), r=0.05, h=h + 0.1, seg=6)
    m.mat(P["leaf2"] if "culm" not in P else P["culm"])
    for zz in (0.25, 0.55, 0.85):
        m.tube([tuple(a + V((0, 0, h * zz))), tuple(b + V((0, 0, h * zz)))], r=0.03, seg=6)
    m.mat(P["rope"])
    for k in range(n):
        p = a.lerp(b, k / (n - 1))
        for zz in (0.25, 0.55, 0.85):
            m.ico(tuple(p + V((0, 0, h * zz))), 0.045, 0)


def house(m, P, c, rnd, rot=0.0, w=2.6, d=2.0, h=1.5):
    """Small minka, built properly: stone plinth into the slope, timber frame (sill, corner and mid posts, rails,
    eave beam) over cream plaster, shoji panels with lattice, a red noren over the door, a veranda with posts and
    a step stone, a two-tier tiled roof with tile courses, deep eaves, ridge and end tiles, an eave lantern, potted
    plants, a firewood stack and a rain barrel."""
    m.push(Matrix.Translation(c) @ Matrix.Rotation(rot, 4, 'Z'))
    z0 = 0.24
    m.mat(P["stone2"])
    m.box((0, 0, -0.3), (w + 0.3, d + 0.3, 1.08), smooth=False)     # plinth reaches into the slope (no gap downhill)
    m.mat(P["wall"])
    m.box((0, 0, z0 + h / 2), (w, d, h), smooth=False)
    m.mat(P["timber"])
    m.box((0, 0, z0 + 0.05), (w + 0.06, d + 0.06, 0.1), smooth=False)                 # sill
    m.box((0, 0, z0 + h - 0.05), (w + 0.08, d + 0.08, 0.12), smooth=False)            # eave beam
    for zz in (z0 + h * 0.62,):                                                        # mid rail
        m.box((0, 0, zz), (w + 0.04, d + 0.04, 0.06), smooth=False)
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.box((sx * w / 2, sy * d / 2, z0 + h / 2), (0.12, 0.12, h), smooth=False)  # corner posts
    for k in (-1, 1):
        m.box((k * w / 6, -d / 2 - 0.01, z0 + h / 2), (0.08, 0.05, h), smooth=False)
        m.box((k * w / 6, d / 2 + 0.01, z0 + h / 2), (0.08, 0.05, h), smooth=False)
        m.box((w / 2 + 0.01, k * d / 5, z0 + h / 2), (0.05, 0.08, h), smooth=False)
        m.box((-w / 2 - 0.01, k * d / 5, z0 + h / 2), (0.05, 0.08, h), smooth=False)
    glow = P.get("glow", P["flower"])
    m.mat(glow)                                                     # shoji: front pair and one per side
    for cx, cy, sx_, sy_ in ((w / 3, -d / 2 - 0.02, w * 0.26, 0.02), (-w / 3, -d / 2 - 0.02, w * 0.26, 0.02),
                             (w / 2 + 0.02, 0, 0.02, d * 0.3), (-w / 2 - 0.02, 0, 0.02, d * 0.3)):
        m.box((cx, cy, z0 + h * 0.36), (sx_, sy_, h * 0.48), smooth=False)
    m.mat(P["timber"])                                              # lattice over the shoji
    for cx, cy, along in ((w / 3, -d / 2 - 0.035, 'x'), (-w / 3, -d / 2 - 0.035, 'x'), (w / 2 + 0.035, 0, 'y'),
                          (-w / 2 - 0.035, 0, 'y')):
        span = w * 0.26 if along == 'x' else d * 0.3
        for k in range(1, 4):
            o = -span / 2 + span * k / 4
            m.box((cx + (o if along == 'x' else 0), cy + (o if along == 'y' else 0), z0 + h * 0.36),
                  (0.025 if along == 'x' else 0.02, 0.02 if along == 'x' else 0.025, h * 0.48), smooth=False)
        for k in range(1, 4):
            m.box((cx, cy, z0 + h * 0.12 + h * 0.48 * k / 4), (span if along == 'x' else 0.02, 0.02 if along == 'x' else span, 0.02),
                  smooth=False)
    m.box((0, -d / 2 - 0.02, z0 + h * 0.4), (w * 0.22, 0.03, h * 0.8), smooth=False)        # door
    m.mat(P["red"])
    for k in range(3):                                                                         # noren
        m.box((-w * 0.07 + k * w * 0.07, -d / 2 - 0.05, z0 + h * 0.68), (w * 0.065, 0.01, h * 0.24), smooth=False)
    m.mat(P["timber"])
    m.box((0, -d / 2 - 0.45, z0 + 0.08), (w + 0.1, 0.8, 0.07), smooth=False)                  # engawa veranda
    for sx in (-1, 1):
        m.box((sx * w / 2, -d / 2 - 0.82, z0 + h / 2), (0.08, 0.08, h), smooth=False)
        m.box((sx * w / 2, -d / 2 - 0.82, z0 - 0.15), (0.12, 0.12, 0.3), smooth=False)
    m.mat(P["stone"])
    m.box((0, -d / 2 - 1.05, z0 - 0.04), (0.6, 0.35, 0.12), smooth=False)                    # step stone
    # roof: lower eave skirt over the veranda, then the main hip roof with tile courses, ridge and end tiles
    ov = 0.5
    m.mat(P["timber"])
    m.box((0, 0, z0 + h + 0.03), (w + 2 * ov + 0.05, d + 2 * ov + 0.7, 0.06), smooth=False)   # fascia under the eaves
    m.mat(P["roof"])
    m.push(Matrix.Translation((0, -0.35, z0 + h + 0.06)) @ Matrix.Rotation(math.radians(45), 4, 'Z'))
    rw = (w * 0.5 + ov) * 1.414
    rd = (d * 0.5 + ov + 0.35) / (w * 0.5 + ov)
    m.pop()
    hr = h * 0.78
    for k, f in enumerate((0.0, 0.25, 0.5, 0.75)):                 # tile courses: stacked slices of the hip
        z_a = z0 + h + 0.06 + hr * f
        sc = 1 - f
        m.mat(P["roof"])
        m.push(Matrix.Translation((0, -0.35 * sc, z_a)) @ Matrix.Diagonal((1.0, rd, 1.0, 1.0)) @
               Matrix.Rotation(math.radians(45), 4, 'Z'))
        m.cyl((0, 0, hr * 0.125), r=rw * sc, h=hr * 0.25, seg=4, r2=rw * (sc - 0.25) + 0.02)
        m.pop()
        m.mat(P["timber"])                                          # shadow line at the foot of each course
        if k > 0:
            m.push(Matrix.Translation((0, -0.35 * sc, z_a)) @ Matrix.Diagonal((1.0, rd, 1.0, 1.0)) @
                   Matrix.Rotation(math.radians(45), 4, 'Z'))
            m.cyl((0, 0, 0.0), r=rw * sc + 0.015, h=0.025, seg=4)
            m.pop()
    m.mat(P["roof"])
    zr = z0 + h + 0.06 + hr
    m.box((0, -0.35 * 0.0, zr - 0.02), (w * 0.34, 0.16, 0.14), smooth=False)                 # ridge
    for sx in (-1, 1):
        m.box((sx * w * 0.17, 0, zr + 0.06), (0.1, 0.2, 0.2), smooth=False)                  # onigawara end tiles
    m.mat(P["timber"])                                              # eave lantern
    m.box((w * 0.42, -d / 2 - 0.85, z0 + h - 0.1), (0.02, 0.02, 0.2), smooth=False)
    m.mat(glow)
    m.sphere((w * 0.42, -d / 2 - 0.85, z0 + h - 0.32), 1.0, 10, 6, s=(0.1, 0.1, 0.13))
    m.mat(P.get("stone2"))                                          # pots with shrubs by the door
    for sx in (-1, 1):
        m.cyl((sx * (w * 0.2 + 0.25), -d / 2 - 0.62, z0 + 0.25), r=0.11, h=0.22, seg=10, r2=0.13)
        m.mat(P["leaf2"])
        m.ico((sx * (w * 0.2 + 0.25), -d / 2 - 0.62, z0 + 0.45), 0.17, 2, s=(1, 1, 0.9))
        m.mat(P.get("stone2"))
    m.mat(P["timber"])                                              # firewood stack on one side
    for k in range(3):
        for j in range(4 - k):
            m.cyl((w / 2 + 0.18, -d * 0.3 + j * 0.15 + k * 0.075, z0 + 0.08 + k * 0.13), r=0.065, h=0.5, seg=7, axis='X')
    m.mat(P["timber"])                                              # rain barrel at the back corner
    m.cyl((-w / 2 - 0.25, d / 2 - 0.2, z0 + 0.25), r=0.2, h=0.5, seg=12)
    m.mat(P.get("water", P["wall"]))
    m.cyl((-w / 2 - 0.25, d / 2 - 0.2, z0 + 0.49), r=0.17, h=0.02, seg=12)
    m.pop()


def water_wheel(m, P, c, rot=0.0, r=1.1, axle=0.7):
    """Mill wheel turning in the water: two rims, spokes, paddles; the axle runs `axle` m along +X (rotated) into
    the mill wall, with a timber bearing post at the water's edge."""
    m.push(Matrix.Translation(c) @ Matrix.Rotation(rot, 4, 'Z'))
    m.mat(P["timber"])
    for sx in (-0.22, 0.22):
        m.torus((sx, 0, 0), R=r, r=0.05, seg=24, sides=5, axis='X')
    for k in range(12):
        a = 2 * math.pi * k / 12
        m.push(Matrix.Rotation(a, 4, 'X'))
        m.box((0, 0, r * 0.5), (0.05, 0.05, r), smooth=False)
        m.box((0, 0, r + 0.05), (0.5, 0.06, 0.25), smooth=False)
        m.pop()
    m.cyl((axle / 2 - 0.35, 0, 0), r=0.12, h=axle, seg=10, axis='X')
    m.box((0.45, 0, -0.6), (0.22, 0.22, 1.2), smooth=False)          # bearing post down into the river bed
    m.pop()


def dock(m, P, c, rot=0.0, L=2.4):
    """Landing stage: gapped deck planks on cross-beams and posts (posts run down into the river bed), mooring
    post with a rope tied off to a small punt lying in the water, a coil of rope, barrels and a lantern post."""
    m.push(Matrix.Translation(c) @ Matrix.Rotation(rot, 4, 'Z'))
    m.mat(P["timber"])
    for k in range(8):
        m.box((0, -L / 2 + (k + 0.5) * L / 8, 0.33), (1.2, L / 8 - 0.035, 0.05), smooth=False)
    for sy in (-L / 2 + 0.15, 0.0, L / 2 - 0.15):
        m.box((0, sy, 0.27), (1.3, 0.1, 0.08), smooth=False)
    for sx in (-0.55, 0.55):
        m.box((sx, 0, 0.27), (0.08, L, 0.08), smooth=False)
        for sy in (-L / 2 + 0.12, L / 2 - 0.12):
            m.cyl((sx, sy, -0.15), r=0.07, h=1.1, seg=8)
            m.mat(P["stone2"])
            m.cyl((sx, sy, 0.42), r=0.075, h=0.05, seg=8)
            m.mat(P["timber"])
    m.cyl((-0.55, 0.0, 0.5), r=0.06, h=0.4, seg=8)                         # mooring bollard
    m.mat(P["rope"])
    m.torus((0.3, L / 2 - 0.4, 0.38), R=0.13, r=0.03, seg=14, sides=5)
    m.torus((0.3, L / 2 - 0.4, 0.42), R=0.1, r=0.03, seg=14, sides=5)
    m.torus((-0.55, 0.0, 0.6), R=0.07, r=0.015, seg=10, sides=4)
    m.tube([(-0.6, 0.0, 0.58), (-0.85, 0.1, 0.25), (-1.0, 0.3, 0.2)], r=0.012, seg=4)
    m.mat(P["timber"])                                                     # barrels
    for k, (bx, by) in enumerate(((0.3, -L / 2 + 0.35), (0.05, -L / 2 + 0.3))):
        m.cyl((bx, by, 0.6), r=0.16, h=0.5, seg=12, r2=0.15)
        m.mat(P["stone2"])
        for zz in (0.42, 0.78):
            m.torus((bx, by, zz), R=0.163, r=0.012, seg=14, sides=4)
        m.mat(P["timber"])
    m.cyl((0.5, L / 2 - 0.1, 0.8), r=0.04, h=1.0, seg=6)                    # lantern post
    m.mat(P.get("glow", P["flower"]))
    m.box((0.5, L / 2 - 0.1, 1.35), (0.14, 0.14, 0.18), smooth=False)
    m.mat(P["roof"])
    m.cyl((0.5, L / 2 - 0.1, 1.48), r=0.15, h=0.08, seg=4, r2=0.02)
    # moored punt in the water beside the dock: a lofted flat-bottomed hull with raised ends and a seat
    m.push(Matrix.Translation((-1.05, 0.1, 0.0)))
    rings = []
    n = 12
    for k in range(n + 1):
        u = k / n
        y = -1.0 + 2.0 * u
        ww = 0.32 * math.sin(math.pi * min(1.0, 0.04 + u * 0.92)) ** 0.5
        rise = 0.12 * (abs(2 * u - 1) ** 3)
        rings.append([(-ww, y, 0.22 + rise), (-ww * 0.8, y, -0.04 + rise * 0.6), (ww * 0.8, y, -0.04 + rise * 0.6), (ww, y, 0.22 + rise)])
    m.mat(P["timber"])
    m.quad_strip(rings, closed=False, smooth=False)
    m.box((0, 0.2, 0.12), (0.5, 0.12, 0.04), smooth=False)
    m.mat(P["stone2"])
    m.box((0, -0.2, 0.0), (0.4, 0.9, 0.02), smooth=False)
    m.pop()
    m.pop()


def pagoda(m, P, c, tiers=3, s=1.0):
    """Small pagoda: stepped stone base, each storey with red corner posts, cream walls, a timber bracket band and
    a broad roof whose corners turn up with little bells, and a ringed sorin spire on top."""
    x, y, z = c
    m.push(Matrix.Translation((x, y, z)) @ Matrix.Diagonal((s, s, s, 1.0)))
    m.mat(P["stone2"])
    m.box((0, 0, 0.12), (2.6, 2.6, 0.24), smooth=False)
    m.box((0, 0, 0.32), (2.2, 2.2, 0.16), smooth=False)
    m.box((0, -1.4, 0.08), (0.8, 0.3, 0.16), smooth=False)
    zz = 0.4
    for k in range(tiers):
        w = 1.5 - k * 0.28
        hh = 0.8 - k * 0.08
        m.mat(P["wall"])
        m.box((0, 0, zz + hh / 2), (w, w, hh), smooth=False)
        m.mat(P["red"])
        for sx in (-1, 1):
            for sy in (-1, 1):
                m.box((sx * w / 2, sy * w / 2, zz + hh / 2), (0.1, 0.1, hh), smooth=False)
        m.box((0, -w / 2 - 0.01, zz + hh * 0.42), (w * 0.3, 0.03, hh * 0.84), smooth=False)   # door
        m.mat(P["timber"])
        m.box((0, 0, zz + hh - 0.04), (w + 0.12, w + 0.12, 0.1), smooth=False)               # bracket band
        for j in range(5):
            o = -w / 2 + w * j / 4
            for sd in (-1, 1):
                m.box((o, sd * (w / 2 + 0.1), zz + hh + 0.03), (0.06, 0.1, 0.06), smooth=False)
                m.box((sd * (w / 2 + 0.1), o, zz + hh + 0.03), (0.1, 0.06, 0.06), smooth=False)
        m.mat(P["roof"])
        rw = (w * 0.5 + 0.55) * 1.414
        zr = zz + hh + 0.06
        m.push(Matrix.Translation((0, 0, zr)) @ Matrix.Rotation(math.radians(45), 4, 'Z'))
        m.cyl((0, 0, 0.04), r=rw, h=0.08, seg=4, r2=rw - 0.05)
        m.cyl((0, 0, 0.2), r=rw - 0.05, h=0.24, seg=4, r2=w * 0.5)
        m.pop()
        hw = w * 0.5 + 0.55
        for sx in (-1, 1):                                          # upturned corners with bells
            for sy in (-1, 1):
                p = V((sx * hw * 0.98, sy * hw * 0.98, zr + 0.06))
                m.tube([tuple(p - V((sx, sy, 0)) * 0.25), tuple(p + V((0, 0, 0.12)) + V((sx, sy, 0)) * 0.05)], r=0.05, seg=5,
                       taper=0.4)
                m.mat(P.get("glow", P["flower"]))
                m.sphere(tuple(p + V((0, 0, -0.08))), 0.04, 8, 5)
                m.mat(P["roof"])
        zz = zr + 0.34
    m.mat(P["timber"])
    m.cyl((0, 0, zz + 0.6), r=0.04, h=1.2, seg=8)
    m.mat(P.get("glow", P["flower"]))
    for j in range(5):
        m.torus((0, 0, zz + 0.25 + j * 0.15), R=0.09 - j * 0.008, r=0.018, seg=12, sides=4)
    m.sphere((0, 0, zz + 1.25), 0.07, 10, 6)
    m.pop()


def mountains(m, P, c, rnd, n=6, w=80.0, h=(10, 22), depth=6.0):
    """Row of soft pastel peaks along x, centred on c; front row P['far'], back row P['far2'] with snow tips."""
    x0, y0, z0 = c
    for row, (mat, dy, sc) in enumerate(((P["far2"], depth, 1.25), (P["far"], 0.0, 1.0))):
        for k in range(n):
            x = x0 - w / 2 + (k + rnd.uniform(0.2, 0.8)) * w / n
            hh = rnd.uniform(*h) * sc
            r = hh * rnd.uniform(0.8, 1.1)
            m.mat(mat)
            m.cyl((x, y0 + dy, z0 + hh / 2), r=r, h=hh, seg=9, r2=r * 0.12)
            if row == 0 and "snow" in P:
                m.mat(P["snow"])
                m.cyl((x, y0 + dy, z0 + hh * 0.86), r=r * 0.26, h=hh * 0.28, seg=9, r2=r * 0.1)


def waterfall(m, P, top, drop=8.0, w=1.2, out=(0.0, -1.0, 0.0)):
    """Falls pouring off a lip: a curved sheet that leaves the edge and bends down (out = direction away from
    the cliff), lighter streaks down its face, and a foam/mist cloud where it lands."""
    t, o = V(top), V(out).normalized()
    side = o.cross(V((0, 0, 1))).normalized()
    n = 12
    path = []
    for k in range(n + 1):
        u = k / n
        path.append(t + o * (0.9 * math.sqrt(u) * min(1.0, drop / 6.0)) + V((0, 0, -drop * u)))
    rings = [[tuple(p - side * (w / 2) * (1 + 0.5 * k / n)), tuple(p + side * (w / 2) * (1 + 0.5 * k / n))]
             for k, p in enumerate(path)]
    m.mat(P["water"])
    m.quad_strip(rings, closed=False, smooth=True)
    m.mat(P["foam"])
    for j in (-0.3, 0.05, 0.32):                       # streaks just in front of the sheet
        pts = [p + side * (w * j) + o * 0.03 for p in path[1:]]
        m.tube([tuple(p) for p in pts], r=0.04 * w, seg=4)
    m.ico(tuple(t + o * 0.05 + V((0, 0, 0.02))), w * 0.3, 1, s=(1.6, 0.6, 0.4))     # lip foam
    end = path[-1]
    for k in range(6):
        a = 2 * math.pi * k / 6
        m.ico(tuple(end + side * math.cos(a) * w * 0.7 + o * (0.4 + math.sin(a) * 0.5) + V((0, 0, 0.2))),
              0.45 * w + 0.1 * (k % 3), 1, s=(1, 1, 0.6))


def rnd_off(k, w):
    return (k - 2) * w * 0.3


# ----------------------------------------------------------------------------- ground cover (Genshin-style lushness)

def grass_carpet(m, P, x0, x1, y0, y1, zfn, rnd, density=2.5, h=0.38, flowers=0.06):
    """Covers a rectangle with grass clumps (dark base blades, light-tipped tall ones) and scattered wildflowers so no
    bare ground shows. zfn(x, y) -> ground height. Jittered grid, so it is even without gaps."""
    mats_ = (P.get("grass_a", P["leaf"]), P.get("grass_b", P["leaf2"]), P.get("grass_tip", P["leaf"]))
    step = 1.0 / math.sqrt(density)
    y = y0
    while y < y1:
        x = x0
        while x < x1:
            px, py = x + rnd.uniform(0, step), y + rnd.uniform(0, step)
            c = V((px, py, zfn(px, py) - 0.02))
            if c.z < -5.0:                          # zfn says: no ground here
                x += step
                continue
            for j in range(rnd.randint(4, 6)):
                a = rnd.uniform(0, math.pi)
                d = V((math.cos(a), math.sin(a), 0)) * rnd.uniform(0.035, 0.05)
                hh = h * rnd.uniform(0.55, 1.25)
                lean = V((rnd.uniform(-0.12, 0.12), rnd.uniform(-0.12, 0.12), 0))
                base = c + V((rnd.uniform(-0.12, 0.12), rnd.uniform(-0.12, 0.12), 0))
                m.mat(mats_[2] if hh > h * 1.05 else mats_[j % 2])
                m.poly([tuple(base - d), tuple(base + d), tuple(base + lean + V((0, 0, hh)))])
            if rnd.random() < flowers:
                flower(m, P, c, rnd)
            x += step
        y += step


def flower(m, P, c, rnd):
    """A small wildflower: stem and a five-petal head (white, yellow, blue or pink)."""
    col = rnd.choice([P.get("fl_white", P["flower"]), P.get("fl_yellow", P["flower"]), P["flower"],
                      P.get("fl_pink", P["flower2"])])
    hh = rnd.uniform(0.25, 0.45)
    top = V(c) + V((rnd.uniform(-0.05, 0.05), rnd.uniform(-0.05, 0.05), hh))
    m.mat(P.get("grass_a", P["leaf"]))
    m.poly([tuple(V(c) + V((-0.01, 0, 0))), tuple(V(c) + V((0.01, 0, 0))), tuple(top)])
    m.mat(col)
    for k in range(5):
        a = 2 * math.pi * k / 5
        m.sphere(tuple(top + V((math.cos(a) * 0.035, math.sin(a) * 0.035, 0))), 1.0, 6, 4, s=(0.035, 0.035, 0.012))
    m.mat(P.get("fl_yellow", P["flower"]))
    m.sphere(tuple(top + V((0, 0, 0.008))), 0.018, 6, 4)


def fern(m, P, c, rnd, r=0.6):
    """Arching fronds from one crown."""
    m.mat(P["leaf2"])
    for k in range(7):
        a = 2 * math.pi * k / 7 + rnd.uniform(-0.2, 0.2)
        d = V((math.cos(a), math.sin(a), 0))
        base = V(c)
        mid = base + d * r * 0.5 + V((0, 0, r * 0.45))
        tip = base + d * r + V((0, 0, r * 0.15))
        sd = d.cross(V((0, 0, 1))) * r * 0.12
        m.poly([tuple(base), tuple(mid + sd), tuple(tip), tuple(mid - sd)])


def canopy_mass(m, P, x0, x1, y0, y1, zfn, rnd, n=20, r=(1.6, 2.6)):
    """Far forest: tight cluster of canopy blobs (no trunks) that fills the hillside; lighter crowns on top."""
    for k in range(n):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        rr = rnd.uniform(*r)
        z = zfn(x, y) + rr * 0.55
        m.mat(P["leaf2"] if k % 2 else P["leaf3"])
        m.ico((x, y, z), rr, 2, s=(1, 1, 0.85))
        m.mat(P.get("leaf_hi", P["leaf"]))
        m.ico((x + rnd.uniform(-0.3, 0.3), y + rnd.uniform(-0.3, 0.3), z + rr * 0.45), rr * 0.6, 2, s=(1, 1, 0.7))


def windmill(m, P, c, rnd, rot=0.0, h=3.4):
    """Tall timber windmill (a nod to the wind theme): tapered tower, cap, four cloth sails."""
    m.push(Matrix.Translation(c) @ Matrix.Rotation(rot, 4, 'Z'))
    m.mat(P["wall"])
    m.cyl((0, 0, h / 2), r=0.8, h=h, seg=8, r2=0.55)
    m.mat(P["timber"])
    for z in (0.2, h * 0.5, h - 0.15):
        m.cyl((0, 0, z), r=0.82 - 0.27 * z / h, h=0.12, seg=8)
    m.box((0, -0.81 + 0.27 * 0.3, 0.6), (0.4, 0.06, 0.8), smooth=False)
    m.mat(P.get("stone2", P["timber"]))                # stone footing, and a gallery round the middle
    m.cyl((0, 0, 0.1), r=0.9, h=0.2, seg=10)
    m.mat(P["timber"])
    m.cyl((0, 0, h * 0.55), r=0.95, h=0.06, seg=12)
    for k in range(12):
        a = 2 * math.pi * k / 12
        m.cyl((math.cos(a) * 0.92, math.sin(a) * 0.92, h * 0.55 + 0.2), r=0.02, h=0.4, seg=4)
    m.torus((0, 0, h * 0.55 + 0.4), R=0.92, r=0.02, seg=24, sides=4)
    m.mat(P.get("glow", P["flower"]))
    m.box((0, -(0.8 - 0.25 * 0.72) - 0.01, h * 0.72), (0.22, 0.03, 0.3), smooth=False)       # window
    m.mat(P["roof"])
    m.cyl((0, 0, h + 0.4), r=0.75, h=0.8, seg=8, r2=0.05)
    m.mat(P["timber"])
    m.cyl((0, -0.75, h - 0.1), r=0.08, h=0.5, seg=8, axis='Y')
    a0 = rnd.uniform(0, 90)
    for k in range(4):
        m.push(Matrix.Translation((0, -1.0, h - 0.1)) @ Matrix.Rotation(math.radians(a0 + 90 * k), 4, 'Y'))
        m.mat(P["timber"])                          # whip, lattice frame, then the cloth over it
        m.box((0, 0, 1.3), (0.08, 0.08, 2.6), smooth=False)
        for zz in range(6):
            m.box((0.22, 0.0, 0.65 + zz * 0.36), (0.44, 0.04, 0.03), smooth=False)
        m.box((0.44, 0.0, 1.55), (0.03, 0.04, 1.85), smooth=False)
        m.mat(P.get("sail", P["wall"]))
        m.box((0.22, 0.03, 1.55), (0.38, 0.015, 1.8), smooth=False)
        m.pop()
    m.pop()
