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
    for k in range(rnd.randint(5, 8)):
        a = rnd.uniform(0, 2 * math.pi)
        rr = r * rnd.uniform(0.2, 0.7)
        p = top + V((math.cos(a) * rr, math.sin(a) * rr, rnd.uniform(0.0, r * 0.8)))
        m.mat(P["leaf"] if k % 3 else P["leaf2"])
        s = rnd.uniform(0.55, 0.85) * r
        m.ico(tuple(p), s, 1, s=(1, 1, 0.8))


def pine(m, P, c, rnd, h=4.0):
    """Japanese black pine: twisted trunk with flat cloud-pad tiers."""
    base = V(c)
    pts = [base]
    for k in range(1, 5):
        pts.append(base + V((math.sin(k * 1.3) * 0.25 * k / 4, math.cos(k * 0.9) * 0.15, h * k / 4)))
    m.mat(P["trunk"])
    m.tube([tuple(p) for p in pts], r=0.12 * h / 4, seg=7, taper=0.5)
    m.mat(P["leaf3"])
    for k in range(1, 5):
        p = pts[k] + V((rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4), 0.1))
        w = (1.5 - k * 0.22) * h / 4
        m.ico(tuple(p), w, 1, s=(1, 0.8, 0.32))


def shrub(m, P, c, rnd, r=0.5, flowers=None):
    """Rounded shrub of 3-4 blobs, optional flower dots (hydrangea, azalea)."""
    m.mat(P["leaf2"])
    for k in range(rnd.randint(3, 4)):
        p = V(c) + V((rnd.uniform(-r, r) * 0.6, rnd.uniform(-r, r) * 0.6, r * 0.5))
        m.ico(tuple(p), r * rnd.uniform(0.6, 0.85), 1, s=(1, 1, 0.8))
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
    """Small minka: cream plaster walls with timber frame, deep hip roof, veranda, a glowing paper window."""
    m.push(Matrix.Translation(c) @ Matrix.Rotation(rot, 4, 'Z'))
    m.mat(P["stone2"])
    m.box((0, 0, 0.12), (w + 0.3, d + 0.3, 0.24), smooth=False)
    m.mat(P["wall"])
    m.box((0, 0, 0.24 + h / 2), (w, d, h), smooth=False)
    m.mat(P["timber"])
    for sx in (-1, 0, 1):
        m.box((sx * w / 2, -d / 2 - 0.01, 0.24 + h / 2), (0.1, 0.06, h), smooth=False)
    m.box((0, -d / 2 - 0.01, 0.24 + h - 0.06), (w, 0.07, 0.1), smooth=False)
    m.box((0, -d / 2 - 0.45, 0.32), (w, 0.8, 0.08), smooth=False)          # engawa veranda
    m.mat(P["flower"] if "glow" not in P else P["glow"])
    m.box((w * 0.25, -d / 2 - 0.02, 0.24 + h * 0.5), (w * 0.3, 0.03, h * 0.45), smooth=False)
    m.mat(P["roof"])
    m.push(Matrix.Translation((0, 0, 0.24 + h)) @ Matrix.Rotation(math.radians(45), 4, 'Z'))
    m.cyl((0, 0, h * 0.36), r=(w * 0.5 + 0.3) * 1.414, h=h * 0.72, seg=4, r2=0.2)
    m.pop()
    m.box((0, 0, 0.24 + h * 1.66), (w * 0.3, 0.14, 0.1), smooth=False)        # ridge
    m.pop()


def water_wheel(m, P, c, rot=0.0, r=1.1):
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
    m.cyl((0, 0, 0), r=0.12, h=0.7, seg=10, axis='X')
    m.pop()


def dock(m, P, c, rot=0.0, L=2.4):
    """Little landing stage on posts with a coil of rope and a moored punt."""
    m.push(Matrix.Translation(c) @ Matrix.Rotation(rot, 4, 'Z'))
    m.mat(P["timber"])
    for k in range(6):
        m.box((0, -L / 2 + (k + 0.5) * L / 6, 0.32), (1.2, L / 6 - 0.04, 0.06), smooth=False)
    for sx in (-0.5, 0.5):
        for sy in (-L / 2 + 0.1, L / 2 - 0.1):
            m.cyl((sx, sy, 0.1), r=0.06, h=0.7, seg=6)
    m.mat(P["rope"])
    m.torus((0.3, L / 2 - 0.4, 0.38), R=0.14, r=0.035, seg=12, sides=5)
    m.mat(P["timber"])
    m.push(Matrix.Translation((-1.05, 0, 0.05)))
    m.box((0, 0, 0.0), (0.7, 2.2, 0.16), smooth=False)
    m.box((0.33, 0, 0.12), (0.06, 2.2, 0.2), smooth=False)
    m.box((-0.33, 0, 0.12), (0.06, 2.2, 0.2), smooth=False)
    m.pop()
    m.pop()


def pagoda(m, P, c, tiers=3, s=1.0):
    x, y, z = c
    m.mat(P["stone2"])
    m.box((x, y, z + 0.2 * s), (2.4 * s, 2.4 * s, 0.4 * s), smooth=False)
    zz = z + 0.4 * s
    for k in range(tiers):
        w = (1.6 - k * 0.3) * s
        m.mat(P["red"])
        m.box((x, y, zz + 0.45 * s), (w, w, 0.9 * s), smooth=False)
        m.mat(P["roof"])
        m.push(Matrix.Translation((x, y, zz + 0.95 * s)) @ Matrix.Rotation(math.radians(45), 4, 'Z'))
        m.cyl((0, 0, 0.15 * s), r=(w * 0.5 + 0.55 * s) * 1.414, h=0.3 * s, seg=4, r2=w * 0.5)
        m.pop()
        zz += 1.2 * s
    m.mat(P["timber"])
    m.cyl((x, y, zz + 0.5 * s), r=0.05 * s, h=1.2 * s, seg=6)


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


def waterfall(m, P, top, drop=8.0, w=1.2):
    """Thin ribbon falls with a foam pool (flat, reads as animated by the water shader's scroll)."""
    t = V(top)
    m.mat(P["water"])
    m.poly([tuple(t + V((-w / 2, 0, 0))), tuple(t + V((w / 2, 0, 0))), tuple(t + V((w * 0.7, -0.4, -drop))),
            tuple(t + V((-w * 0.7, -0.4, -drop)))])
    m.mat(P["foam"])
    for k in range(5):
        m.ico(tuple(t + V((rnd_off(k, w), -0.5, -drop + 0.1))), 0.35 + 0.08 * k, 1, s=(1, 1, 0.5))


def rnd_off(k, w):
    return (k - 2) * w * 0.3
