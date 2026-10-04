"""
PONGO zone vehicles (toon style), each with grip points so Pongo's clips line up with them:

  ore_cart   Crystal Cavern mine cart: plank-and-iron body, flanged wheels for the 1.067 m rails, lantern,
             brake lever, glowing crystal cargo. Origin: rail plane centre under the cart, faces +Y.
             GRIP_CART: hands on the front rim; FLOOR_CART: cart floor height (her feet).
  boat       Bamboo River canoe: bundled bamboo culms curving up at bow and stern, rope lashings, woven seat,
             stern lantern pole. Origin: waterline centre, faces +Y. SEAT_BOAT: kneeling point.
  paddle     Single-blade bamboo paddle; origin at the upper (right) hand grip, shaft along -Z.
  glider     Sky Glide paraglider: arched 13-cell canopy (Pongo's palette, gold leading edge), lines to two risers,
             brake toggles and a seat harness. Origin: harness seat, faces +Y. TOGGLES: hand positions.
"""
import math, random
import bpy
from mathutils import Vector, Matrix
import erlib as E

V = Vector

# Pongo is drawn PONGO_SCALE x her 1.55 m model (1.86 m) so she fills the cart, canoe and harness. The parts sized to
# her body (harness seat, toggles, risers, paddle) scale with her; the hulls and the canopy do not.
PONGO_SCALE = 1.2
CART_RIM = 1.12        # rim height: her hips when standing, and still under the 1.25 m crouch beams
GRIP_CART = (V((0.24, 0.62, CART_RIM)), V((-0.24, 0.62, CART_RIM)))
FLOOR_CART = 0.45
SEAT_BOAT = V((0.0, -0.15, 0.12))
TOGGLES = (V((0.3, 0.1, 0.66)) * PONGO_SCALE, V((-0.3, 0.1, 0.66)) * PONGO_SCALE)   # shoulder height when seated
RISERS = (V((0.2, 0.02, 1.0)) * PONGO_SCALE, V((-0.2, 0.02, 1.0)) * PONGO_SCALE)
CARABINERS = (V((0.2, 0.0, 0.42)) * PONGO_SCALE, V((-0.2, 0.0, 0.42)) * PONGO_SCALE)
GAUGE = 1.067


def mats():
    M = E.mat
    M("v_iron", 0x4B4F58, spec=0.6, rim=0.35, soft=0.06, flags=E.F_METAL)
    M("v_iron_dark", 0x2C2F36, spec=0.5, rim=0.3, soft=0.06, flags=E.F_METAL)
    M("v_rivet", 0xA9AFB8, spec=0.9, rim=0.4, soft=0.05, flags=E.F_METAL, outline=0.0)
    M("v_wood", 0x9A6A44, spec=0.1, rim=0.25, soft=0.1, shadow=0x6E4A6A)
    M("v_wood_dark", 0x6E4A30, spec=0.1, rim=0.2, soft=0.1)
    M("v_lamp_glass", 0xFFD27A, emis=1.0, rim=0.2, soft=0.05, outline=0.3)
    M("v_crystal", 0x7FF0FF, emis=0.8, spec=1.0, rim=0.5, soft=0.04, flags=E.F_GLASS, outline=0.5)
    M("v_crystal_pink", 0xFF9AD6, emis=0.7, spec=1.0, rim=0.5, soft=0.04, flags=E.F_GLASS, outline=0.5)
    M("v_ore", 0x3A3440, rim=0.2, soft=0.1)
    M("v_red", 0xE8473C, rim=0.3, soft=0.08)
    M("v_bamboo", 0x9CC45A, spec=0.25, rim=0.3, soft=0.08, shadow=0x5E8A6A)
    M("v_bamboo_node", 0x7DA346, spec=0.2, rim=0.25, soft=0.08)
    M("v_bamboo_dry", 0xD8C27A, spec=0.2, rim=0.3, soft=0.08)
    M("v_rope", 0xC9A86A, rim=0.2, soft=0.12)
    M("v_mat", 0xE2CC8E, rim=0.2, soft=0.12)
    M("v_paper", 0xFFF1D6, emis=0.45, rim=0.2, soft=0.1)
    M("v_paper_red", 0xE8473C, emis=0.3, rim=0.2, soft=0.1)
    M("v_canopy_navy", 0x22356E, rim=0.35, soft=0.1, flags=E.F_DOUBLE)
    M("v_canopy_teal", 0x37B4C8, rim=0.35, soft=0.1, flags=E.F_DOUBLE)
    M("v_canopy_white", 0xF7F8FC, rim=0.3, soft=0.1, flags=E.F_DOUBLE)
    M("v_canopy_orange", 0xFF8A2A, rim=0.3, soft=0.1, flags=E.F_DOUBLE)
    M("v_canopy_dark", 0x161C34, rim=0.1, soft=0.1, flags=E.F_DOUBLE, outline=0.0)
    M("v_line", 0x2A2E3E, rim=0.1, soft=0.1, outline=0.0)
    M("v_strap", 0x2E2A36, rim=0.3, soft=0.08)
    M("v_gold", 0xF2C35C, spec=0.95, rim=0.45, soft=0.04, flags=E.F_METAL)


# ----------------------------------------------------------------------------- ore cart

def _wheel(m, c):
    """Flanged cart wheel in the YZ plane (axis X): hub, spokes, rim, flange on the inner side."""
    x, y, z = c
    side = 1 if x > 0 else -1
    m.push(Matrix.Translation(c) @ Matrix.Rotation(math.radians(90), 4, 'Y'))
    m.mat("v_iron_dark")
    m.cyl((0, 0, 0), r=0.17, h=0.06, seg=28)
    m.cyl((0, 0, -side * 0.035), r=0.2, h=0.016, seg=28)
    m.mat("v_iron")
    m.cyl((0, 0, side * 0.02), r=0.13, h=0.03, seg=24)
    m.mat("v_rivet")
    m.cyl((0, 0, side * 0.04), r=0.045, h=0.03, seg=12)
    m.pop()


def ore_cart(name="ore_cart", seed=4):
    mats()
    rnd = random.Random(seed)
    m = E.Mesher(name)
    zc = 0.161 + 0.17
    # running gear: wheels, axles, chassis beams, axle boxes
    for y in (-0.42, 0.42):
        for sx in (-1, 1):
            _wheel(m, (sx * GAUGE / 2, y, zc))
        m.mat("v_iron_dark")
        m.cyl((0, y, zc), r=0.03, h=GAUGE + 0.12, seg=12, axis='X')
    for sx in (-1, 1):
        m.mat("v_iron_dark")
        m.box((sx * 0.4, 0, zc + 0.04), (0.08, 1.4, 0.1), smooth=False)
        for y in (-0.42, 0.42):
            m.box((sx * 0.46, y, zc), (0.06, 0.16, 0.14), smooth=False)
    # tapered body (open top): plank walls with gaps, iron corner angles and a tube rim
    z0, z1 = 0.44, CART_RIM
    bw0, bl0, bw1, bl1 = 0.46, 0.56, 0.54, 0.66          # half width / half length at bottom and top
    m.mat("v_wood_dark")
    m.box((0, 0, z0 - 0.02), (bw0 * 2, bl0 * 2, 0.04), smooth=False)
    planks = 5
    for k in range(planks):
        t0, t1 = k / planks, (k + 1) / planks - 0.035
        za, zb = z0 + (z1 - z0) * t0, z0 + (z1 - z0) * t1
        wa, wb = bw0 + (bw1 - bw0) * t0, bw0 + (bw1 - bw0) * t1
        la, lb = bl0 + (bl1 - bl0) * t0, bl0 + (bl1 - bl0) * t1
        m.mat("v_wood" if k % 2 == 0 else "v_wood_dark")
        for sx in (-1, 1):              # long sides
            m.poly([(sx * wa, -la, za), (sx * wa, la, za), (sx * wb, lb, zb), (sx * wb, -lb, zb)][::(1 if sx > 0 else -1)])
            m.poly([(sx * (wa - 0.04), la - 0.03, za), (sx * (wa - 0.04), -la + 0.03, za), (sx * (wb - 0.04), -lb + 0.03, zb),
                    (sx * (wb - 0.04), lb - 0.03, zb)][::(1 if sx > 0 else -1)])
        for sy in (-1, 1):              # front/back
            m.poly([(wa, sy * la, za), (-wa, sy * la, za), (-wb, sy * lb, zb), (wb, sy * lb, zb)][::(1 if sy > 0 else -1)])
            m.poly([(-wa + 0.03, sy * (la - 0.04), za), (wa - 0.03, sy * (la - 0.04), za), (wb - 0.03, sy * (lb - 0.04), zb),
                    (-wb + 0.03, sy * (lb - 0.04), zb)][::(1 if sy > 0 else -1)])
    # iron corner angles + rivets
    for sx in (-1, 1):
        for sy in (-1, 1):
            p0, p1 = V((sx * bw0, sy * bl0, z0 - 0.02)), V((sx * bw1, sy * bl1, z1))
            m.mat("v_iron")
            m.sweep([p0, p1], [(-0.035, -0.035), (0.035, -0.035), (0.035, 0.035), (-0.035, 0.035)], closed=True, cap=True)
            m.mat("v_rivet")
            for k in range(5):
                q = p0.lerp(p1, (k + 0.5) / 5)
                for d in (V((sx * 0.012, -sy * 0.05, 0)), V((-sx * 0.05, sy * 0.012, 0))):
                    m.sphere(tuple(q + d), 0.012, 8, 5)
    # horizontal iron bands
    for zb in (z0 + 0.12, z1 - 0.12):
        t = (zb - z0) / (z1 - z0)
        w, l = bw0 + (bw1 - bw0) * t + 0.012, bl0 + (bl1 - bl0) * t + 0.012
        m.mat("v_iron")
        m.sweep([V((w, -l, zb)), V((w, l, zb)), V((-w, l, zb)), V((-w, -l, zb)), V((w, -l, zb)), V((w, l, zb))],
                [(-0.01, -0.03), (0.01, -0.03), (0.01, 0.03), (-0.01, 0.03)], closed=True, cap=False)
    m.mat("v_iron_dark")
    rim = [V((bw1, -bl1, z1)), V((bw1, bl1, z1)), V((-bw1, bl1, z1)), V((-bw1, -bl1, z1)), V((bw1, -bl1, z1)), V((bw1, bl1, z1))]
    m.sweep(rim, [(math.cos(2 * math.pi * k / 8) * 0.03, math.sin(2 * math.pi * k / 8) * 0.03) for k in range(8)],
            closed=True, cap=False)
    # front lantern on a bracket, number plate
    m.mat("v_iron_dark")
    m.box((0.0, bl1 + 0.03, z1 - 0.25), (0.04, 0.06, 0.3), smooth=False)
    m.box((0.0, bl1 + 0.08, z1 - 0.12), (0.18, 0.12, 0.03), smooth=False)
    m.box((0.0, bl1 + 0.08, z1 + 0.12), (0.2, 0.14, 0.03), smooth=False)
    m.mat("v_lamp_glass")
    m.cyl((0.0, bl1 + 0.08, z1), r=0.065, h=0.2, seg=16)
    m.mat("v_iron_dark")
    for a in (45, 135, 225, 315):
        m.box((math.cos(math.radians(a)) * 0.07, bl1 + 0.08 + math.sin(math.radians(a)) * 0.07, z1), (0.012, 0.012, 0.22),
              smooth=False)
    m.mat("v_red")
    m.box((0.28, bl0 + 0.05, z0 + 0.25), (0.22, 0.012, 0.14), smooth=False)
    m.mat("v_canopy_white")
    m.push(Matrix.Translation((0.28, bl0 + 0.06, z0 + 0.25)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
    m.text("06", size=0.1, depth=0.006, c=(0, 0, 0))
    m.pop()
    # brake lever on her right side
    m.mat("v_iron_dark")
    m.push(Matrix.Translation((bw0 + 0.09, -0.3, z0 + 0.1)) @ Matrix.Rotation(math.radians(-20), 4, 'X'))
    m.cyl((0, 0, 0.25), r=0.018, h=0.5, seg=10)
    m.mat("v_red")
    m.cyl((0, 0, 0.53), r=0.03, h=0.1, seg=12)
    m.pop()
    # cargo in the back: ore lumps and glowing crystals
    for k in range(9):
        m.mat("v_ore")
        m.ico((rnd.uniform(-0.35, 0.35), rnd.uniform(-0.5, -0.25), z0 + rnd.uniform(0.04, 0.12)), rnd.uniform(0.07, 0.12), 1)
    for k, (x, y, h, mt) in enumerate(((0.28, -0.44, 0.3, "v_crystal"), (0.2, -0.5, 0.22, "v_crystal"),
                                       (-0.3, -0.45, 0.26, "v_crystal_pink"), (-0.22, -0.5, 0.18, "v_crystal"))):
        m.mat(mt)
        m.push(Matrix.Translation((x, y, z0 + 0.08)) @ Matrix.Rotation(math.radians(rnd.uniform(-20, 20)), 4, 'X') @
               Matrix.Rotation(math.radians(rnd.uniform(-20, 20)), 4, 'Y'))
        m.cyl((0, 0, h / 2), r=0.05, h=h, seg=6, r2=0.0)
        m.pop()
    ob = m.obj(name, smooth_angle=35)
    return ob


# ----------------------------------------------------------------------------- bamboo canoe + paddle

def _hull(y, L=1.75):
    """Half width, depth and sheer (end rise) of the canoe hull at y."""
    u = max(0.0, min(1.0, abs(y) / L))
    w = 0.44 * (1 - u ** 2.2) ** 0.55 + 0.02
    d = 0.26 * (1 - u ** 3) ** 0.5 + 0.03
    rise = 0.32 * u ** 3.5
    return w, d, rise


def _culm(m, path, r=0.045, node_every=0.32):
    """Bamboo culm along path: tube with node rings."""
    m.mat("v_bamboo")
    m.sweep(path, [(math.cos(2 * math.pi * k / 10), math.sin(2 * math.pi * k / 10)) for k in range(10)], closed=True,
            cap=True, scale=lambda t: r)
    m.mat("v_bamboo_node")
    acc, last = 0.0, path[0]
    for i in range(1, len(path)):
        seg = (path[i] - path[i - 1]).length
        acc += seg
        if acc >= node_every:
            acc = 0.0
            d = (path[min(i + 1, len(path) - 1)] - path[i - 1]).normalized()
            m.push(Matrix.Translation(path[i]) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4())
            m.torus((0, 0, 0), R=r, r=r * 0.2, seg=14, sides=6)
            m.pop()


def boat(name="bamboo_boat", L=1.75):
    mats()
    m = E.Mesher(name)
    n = 11
    for i in range(n):
        a = math.radians(-78 + 156 * i / (n - 1))           # around the hull section
        path = []
        for k in range(29):
            y = -L + 2 * L * k / 28
            w, d, rise = _hull(y, L)
            path.append(V((w * math.sin(a), y, 0.16 - d * math.cos(a) * 0.95 + rise)))
        _culm(m, path, r=0.045 if i not in (0, n - 1) else 0.05)
    # gunwale culms (thicker, run along the top edge)
    for sx in (-1, 1):
        path = []
        for k in range(29):
            y = -L * 0.97 + 2 * L * 0.97 * k / 28
            w, d, rise = _hull(y, L)
            path.append(V((sx * (w + 0.02), y, 0.2 + rise)))
        _culm(m, path, r=0.055)
    # rope lashings around the hull
    m.mat("v_rope")
    for y in (-1.25, -0.65, 0.0, 0.65, 1.25):
        w, d, rise = _hull(y, L)
        loop = []
        for k in range(25):
            a = math.radians(-100 + 200 * k / 24)
            loop.append(V(((w + 0.05) * math.sin(a), y, 0.18 - (d + 0.03) * math.cos(a) * 0.95 + rise)))
        m.sweep(loop, [(math.cos(2 * math.pi * k / 6), math.sin(2 * math.pi * k / 6)) for k in range(6)], closed=True,
                cap=True, scale=lambda t: 0.012)
    # floor slats, woven seat mat and a front thwart
    m.mat("v_bamboo_dry")
    for x in (-0.18, -0.06, 0.06, 0.18):
        m.cyl((x, 0, 0.05), r=0.025, h=2.4, seg=8, axis='Y')
    m.mat("v_mat")
    m.rbox((0, -0.12, 0.085), (0.5, 0.6, 0.03), 0.01, 1)
    m.mat("v_bamboo_dry")
    w, d, rise = _hull(0.85, L)
    m.cyl((0, 0.85, 0.19), r=0.03, h=2 * w + 0.06, seg=8, axis='X')
    # curled bow tip and a lantern pole at the stern
    m.mat("v_bamboo")
    tip = [V((0, L * 0.98, 0.5)), V((0, L * 1.05, 0.62)), V((0, L * 1.0, 0.72)), V((0, L * 0.92, 0.7))]
    m.sweep(tip, [(math.cos(2 * math.pi * k / 8), math.sin(2 * math.pi * k / 8)) for k in range(8)], closed=True, cap=True,
            scale=lambda t: 0.04 * (1 - 0.5 * t))
    pole = [V((0.0, -L * 0.85, 0.3)), V((0.0, -L * 0.95, 1.0)), V((0.0, -L * 0.92, 1.25)), V((0.0, -L * 0.8, 1.32))]
    m.sweep(pole, [(math.cos(2 * math.pi * k / 8), math.sin(2 * math.pi * k / 8)) for k in range(8)], closed=True, cap=True,
            scale=lambda t: 0.022 * (1 - 0.4 * t))
    m.mat("v_rope")
    m.cyl((0.0, -L * 0.8, 1.2), r=0.004, h=0.22, seg=6)
    m.mat("v_paper_red")
    m.sphere((0.0, -L * 0.8, 1.04), 1.0, 14, 10, s=(0.09, 0.09, 0.12))
    m.mat("v_iron_dark")
    m.cyl((0.0, -L * 0.8, 1.15), r=0.05, h=0.02, seg=12)
    m.cyl((0.0, -L * 0.8, 0.93), r=0.05, h=0.02, seg=12)
    ob = m.obj(name, smooth_angle=50)
    return ob


def paddle(name="paddle"):
    """Bamboo paddle: T grip at the origin (upper hand), shaft down -Z, leaf blade, rope wrap at the lower grip."""
    mats()
    m = E.Mesher(name)
    m.mat("v_bamboo_dry")
    m.cyl((0, 0, -0.62), r=0.018, h=1.24, seg=10)
    m.cyl((0, 0, 0.0), r=0.02, h=0.12, seg=10, axis='X')
    m.mat("v_bamboo_node")
    for z in (-0.3, -0.62, -0.94):
        m.torus((0, 0, z), R=0.019, r=0.004, seg=12, sides=5)
    m.mat("v_rope")
    m.cyl((0, 0, -0.5), r=0.022, h=0.14, seg=10)
    m.mat("v_wood")
    blade = [(0.0, -1.24), (0.08, -1.3), (0.095, -1.5), (0.06, -1.7), (0.0, -1.76), (-0.06, -1.7), (-0.095, -1.5), (-0.08, -1.3)]
    m.push(Matrix.Rotation(math.radians(90), 4, 'X'))
    m.extrude([(x, z) for (x, z) in blade], 0.018, bevel=(0.004, 1), c=(0, 0, 0))
    m.pop()
    m.mat("v_gold")
    m.cyl((0, 0, -1.2), r=0.024, h=0.05, seg=12)
    ob = m.obj(name, smooth_angle=40)
    return ob


# ----------------------------------------------------------------------------- paraglider

CANOPY_COLS = ("v_canopy_navy", "v_canopy_teal", "v_canopy_white", "v_canopy_orange", "v_canopy_white", "v_canopy_teal",
               "v_canopy_navy", "v_canopy_teal", "v_canopy_white", "v_canopy_orange", "v_canopy_white", "v_canopy_teal",
               "v_canopy_navy")


def _canopy_pt(u, v, span=3.6, chord=1.1, R=2.3, h=2.55, thick=0.13):
    """u: -1..1 across the span, v: 0 leading edge .. 1 trailing edge, top surface. Returns point, centre-line."""
    ang = u * math.radians(62)
    c = chord * (1 - 0.35 * u * u)
    y = 0.42 * c - v * c
    t = thick * (1 - 0.3 * u * u) * math.sin(math.pi * min(1.0, (v + 0.05) / 1.05)) * (1 - 0.2 * v)
    x = R * math.sin(ang)
    z = h + R * (math.cos(ang) - 1) * 0.55
    return V((x, y, z)), t, ang


def glider(name="glider"):
    mats()
    m = E.Mesher(name)
    cells = len(CANOPY_COLS)
    nv = 10
    risers = RISERS
    for ci in range(cells):
        u0 = -1 + 2 * ci / cells
        u1 = -1 + 2 * (ci + 1) / cells
        m.mat(CANOPY_COLS[ci])
        top, bot = [], []
        for ui in range(3):
            u = u0 + (u1 - u0) * ui / 2
            rt, rb = [], []
            for vi in range(nv + 1):
                v = vi / nv
                p, t, ang = _canopy_pt(u, v)
                nrm = V((math.sin(ang), 0, math.cos(ang)))
                billow = 0.025 * math.sin(math.pi * ui / 2)
                rt.append(tuple(p + nrm * (t * 0.5 + billow)))
                rb.append(tuple(p - nrm * t * 0.5))
            top.append(rt)
            bot.append(rb)
        m.quad_strip(top, closed=False)
        m.quad_strip(bot[::-1], closed=False)
        # cell walls (ribs) and the dark intake openings at the leading edge
        m.mat("v_canopy_dark")
        m.quad_strip([[top[0][0], top[-1][0]], [bot[0][0], bot[-1][0]]], closed=False)
        m.mat(CANOPY_COLS[ci])
        m.quad_strip([[top[0][-1], top[-1][-1]], [bot[0][-1], bot[-1][-1]]][::-1], closed=False)
    # gold leading-edge piping
    m.mat("v_gold")
    le = [_canopy_pt(-1 + 2 * k / 40, 0.0)[0] + V((0, 0.012, 0.03)) for k in range(41)]
    m.sweep(le, [(math.cos(2 * math.pi * k / 6), math.sin(2 * math.pi * k / 6)) for k in range(6)], closed=True, cap=True,
            scale=lambda t: 0.012)
    # lines: from three rows under every second cell boundary to the risers of the same side
    m.mat("v_line")
    for ci in range(0, cells + 1, 2):
        u = -1 + 2 * ci / cells
        side = 0 if u >= 0 else 1
        for v in (0.1, 0.45, 0.8):
            p, t, ang = _canopy_pt(u, v)
            p = p - V((math.sin(ang), 0, math.cos(ang))) * t * 0.5
            m.sweep([p, risers[side]], [(math.cos(2 * math.pi * k / 4), math.sin(2 * math.pi * k / 4)) for k in range(4)],
                    closed=True, cap=False, scale=lambda tt: 0.003)
    # risers, brake toggles, seat harness
    for sd, rp in zip((1, -1), risers):
        m.mat("v_strap")
        m.sweep([rp, CARABINERS[0 if sd > 0 else 1]], [(-0.012, -0.004), (0.012, -0.004), (0.012, 0.004), (-0.012, 0.004)],
                closed=True, cap=True)
        m.mat("v_line")
        tg = TOGGLES[0 if sd > 0 else 1]
        # brake line: trailing edge of the outer canopy -> through a pulley on the rear riser -> toggle
        te, tt_, ta = _canopy_pt(sd * 0.72, 1.0)
        te = te - V((math.sin(ta), 0, math.cos(ta))) * tt_ * 0.5
        pul = rp + V((0, -0.03, -0.02))
        m.sweep([te, pul, tg], [(math.cos(2 * math.pi * k / 4), math.sin(2 * math.pi * k / 4)) for k in range(4)],
                closed=True, cap=False, scale=lambda tt: 0.004)
        m.mat("v_gold")
        m.torus(tuple(pul), R=0.014, r=0.004, seg=10, sides=5, axis='X')
        m.mat("v_canopy_orange")
        m.rbox(tuple(tg + V((0, 0, -0.04))), (0.03, 0.03, 0.09), 0.01, 1)
        m.mat("v_gold")
        m.torus(tuple(CARABINERS[0 if sd > 0 else 1]), R=0.03, r=0.007, seg=14, sides=6, axis='Y')
    m.mat("v_strap")
    k = PONGO_SCALE
    m.rbox((0.0, -0.05 * k, 0.0), (0.36 * k, 0.32 * k, 0.05), 0.02, 2)
    for sd in (1, -1):
        m.sweep([V((sd * 0.17 * k, -0.18 * k, 0.0)), V((sd * 0.2 * k, -0.12 * k, 0.22 * k)), CARABINERS[0 if sd > 0 else 1]],
                [(-0.018, -0.004), (0.018, -0.004), (0.018, 0.004), (-0.018, 0.004)], closed=True, cap=True)
    ob = m.obj(name, smooth_angle=40)
    return ob


def design_vehicles():
    import studio
    E.reset()
    studio.stage(res=(1400, 900))
    c = ore_cart()
    c.location = (-2.4, 0, 0)
    b = boat()
    b.location = (0.6, 0.0, 0.0)
    p = paddle()
    p.location = (1.6, -0.6, 1.4)
    g = glider()
    g.location = (3.6, 1.0, 0.0)
    for o in (c, b, p, g):
        E.add_outline(o, 0.012)
    studio.shoot("vehicles", target=(0.8, 0.3, 0.9), dist=9.5, yaw=205, pitch=14, lens=40)
