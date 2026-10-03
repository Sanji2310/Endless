"""
Sakura Line — suburban Japanese railway zone kit.

Layout (Blender, Z up, the runner moves toward +Y; one segment = 12 m):
  lanes at x = -2.4, 0, +2.4 (gauge 1.067 m), sleeper tops at z = 0
  ballast bed to |x| = 4.4, slope to the U-ditch at |x| 5.2, fence at |x| 5.8
  road |x| 6.4 .. 10.0 (sunk to z = -0.35), building plots from |x| 11
"""
import math, random
import bpy
from mathutils import Vector, Matrix
import erlib as E
import studio

SEG = 12.0
LANES = (-2.4, 0.0, 2.4)
GAUGE = 1.067
GROUND = -0.35


def city_mats():
    M = E.mat
    M("ballast", 0xFFFFFF, "t_ballast", soft=0.2, rim=0.1, outline=0)
    M("sleeper", 0xCFC9BF, "t_concrete", soft=0.15, rim=0.15, outline=0.6)
    M("rail", 0x7D838F, spec=0.5, rim=0.35, soft=0.08, flags=E.F_METAL, outline=0.7)
    M("rail_top", 0xE4E8EF, spec=1.0, rim=0.5, soft=0.05, flags=E.F_METAL, outline=0)
    M("rail_clip", 0x3B3E46, spec=0.3, rim=0.1, outline=0)
    M("ditch", 0xC3BDB2, "t_concrete", soft=0.15, rim=0.15, outline=0.8)
    M("ditch_dark", 0x6F6A62, soft=0.2, rim=0.0, outline=0)
    M("fence_post", 0x3F7D52, spec=0.3, rim=0.3, outline=0.7)
    M("fence_mesh", 0x4E8E62, "t_fence", spec=0.2, rim=0.2, outline=0, flags=E.F_ALPHA | E.F_DOUBLE | E.F_NOCAST)
    M("asphalt", 0x6B7180, "t_asphalt", soft=0.18, rim=0.05, outline=0)
    M("road_line", 0xF6F3EA, soft=0.15, rim=0.0, outline=0)
    M("road_red", 0xC9453A, soft=0.15, rim=0.0, outline=0)
    M("curb", 0xD9D4CA, "t_concrete", soft=0.15, rim=0.15, outline=0.6)
    M("grass", 0xFFFFFF, "t_grass", soft=0.25, rim=0.15, outline=0)
    M("dirt", 0xFFFFFF, "t_dirt", soft=0.2, rim=0.1, outline=0)
    M("steel", 0x8E97A4, spec=0.45, rim=0.35, soft=0.1, flags=E.F_METAL, outline=0.8)
    M("steel_dark", 0x4D5562, spec=0.35, rim=0.25, soft=0.1, flags=E.F_METAL, outline=0.8)
    M("wire", 0x2B2D34, spec=0.2, rim=0.0, outline=0, flags=E.F_NOCAST)
    M("insulator", 0xF1ECE2, spec=0.7, rim=0.3, soft=0.1, outline=0.6)
    M("insulator_brown", 0x8E4E2C, spec=0.7, rim=0.3, soft=0.1, outline=0.6)
    M("pole_concrete", 0xC2BDB4, "t_concrete", soft=0.15, rim=0.25, outline=0.8)
    M("hazard_yellow", 0xF4C431, soft=0.12, rim=0.2, outline=0.6)
    M("hazard_black", 0x23242A, soft=0.12, rim=0.1, outline=0.6)
    M("transformer", 0x9AA3A8, spec=0.35, rim=0.3, soft=0.1, flags=E.F_METAL, outline=0.8)
    M("sign_blue", 0x2F6BDA, soft=0.12, rim=0.2, outline=0.6)
    M("sign_white", 0xF8F6F0, soft=0.12, rim=0.2, outline=0.6)


# ----------------------------------------------------------------------------- track

RAIL_PROF = [(-0.065, 0.0), (0.065, 0.0), (0.065, 0.012), (0.016, 0.03), (0.011, 0.105),
             (0.034, 0.118), (0.034, 0.152), (0.026, 0.16), (-0.026, 0.16), (-0.034, 0.152),
             (-0.034, 0.118), (-0.011, 0.105), (-0.016, 0.03), (-0.065, 0.012)]


def _rail(m, x, y0, y1, z0=0.0):
    """One rail along +Y. Profile is swept along a straight path; the polished top is its own strip."""
    m.mat("rail")
    path = [(x, y0, z0), (x, y1, z0)]
    m.sweep(path, [(-p[0], p[1]) for p in RAIL_PROF], closed=True, cap=True, up=(0, 0, 1))
    m.mat("rail_top")
    m.box((x, (y0 + y1) / 2, z0 + 0.1612), (0.05, y1 - y0, 0.003), smooth=False)


def track(lod=0, seg=SEG):
    """Three-track ballast bed with PC sleepers, rails, fastenings and side ditches."""
    m = E.Mesher("track")
    # ballast: top plateau plus raised shoulders between and around the sleepers
    m.mat("ballast", uvscale=2.0)
    W, edge = 4.4, 5.05
    prof_x = [-edge, -W, W, edge]
    prof_z = [GROUND + 0.1, -0.06, -0.06, GROUND + 0.1]
    for i in range(3):
        x0, x1, z0, z1 = prof_x[i], prof_x[i + 1], prof_z[i], prof_z[i + 1]
        m.poly([(x0, 0, z0), (x1, 0, z1), (x1, seg, z1), (x0, seg, z0)], uv='box')
    # gentle mounds of stone between the sleeper rows (gives relief at grazing angles)
    # sleepers (PC concrete), 0.6 m pitch
    m.mat("sleeper", uvscale=1.0)
    n = int(round(seg / 0.6))
    for lx in LANES:
        for k in range(n):
            y = k * 0.6 + 0.3
            if lod == 0:
                # trapezoid section, slightly narrower at the centre
                m.push(Matrix.Translation((lx, y, -0.075)))
                m.extrude([(-1.0, -0.12), (1.0, -0.12), (1.0, 0.12), (-1.0, 0.12)], 0.15, bevel=(0.012, 1))
                m.pop()
            else:
                m.box((lx, y, -0.075), (2.0, 0.24, 0.15), smooth=False)
    # rails
    for lx in LANES:
        for s in (-1, 1):
            _rail(m, lx + s * GAUGE / 2, 0, seg)
    # fastenings (Pandrol-style clip plates) on LOD0
    if lod == 0:
        m.mat("rail_clip")
        for lx in LANES:
            for k in range(n):
                y = k * 0.6 + 0.3
                for s in (-1, 1):
                    rx = lx + s * GAUGE / 2
                    for side in (-1, 1):
                        m.box((rx + side * 0.085, y, 0.012), (0.06, 0.13, 0.024), smooth=False)
                        m.box((rx + side * 0.07, y, 0.03), (0.035, 0.05, 0.02), smooth=False)
    # U-ditches and cable troughs on both sides
    for s in (-1, 1):
        x = s * 5.25
        m.mat("ditch", uvscale=1.0)
        m.box((x - s * 0.22, seg / 2, GROUND + 0.05), (0.08, seg, 0.4), smooth=False)
        m.box((x + s * 0.22, seg / 2, GROUND + 0.05), (0.08, seg, 0.4), smooth=False)
        m.mat("ditch_dark")
        m.box((x, seg / 2, GROUND - 0.12), (0.38, seg, 0.04), smooth=False)
        # cable trough lids (concrete slabs with seams)
        m.mat("ditch", uvscale=1.0)
        for k in range(int(seg / 1.0)):
            m.box((s * 4.65, k * 1.0 + 0.5, -0.02), (0.36, 0.97, 0.08), bevel=(0.01, 1) if lod == 0 else None, smooth=False)
    return m.obj("track" if lod == 0 else "track@1", smooth_angle=30)


# ----------------------------------------------------------------------------- side street

def side(lod=0, seg=SEG, mirror=False):
    """One side of the line: fence, grass verge, curb, asphalt lane with markings and a gutter.
    Built for the right side (x > 0); mirror=True builds the left side."""
    sx = -1 if mirror else 1
    m = E.Mesher("side")
    if mirror:
        m.push(Matrix.Diagonal((-1, 1, 1, 1)))
    # grass verge between ditch and fence, then a strip to the road
    m.mat("grass", uvscale=2.0)
    m.poly([(5.47, 0, GROUND + 0.1), (6.3, 0, GROUND + 0.02), (6.3, seg, GROUND + 0.02), (5.47, seg, GROUND + 0.1)])
    # fence: concrete footing, posts every 2 m, mesh panel, top rail
    m.mat("curb", uvscale=1.0)
    m.box((5.8, seg / 2, GROUND + 0.12), (0.18, seg, 0.24), smooth=False)
    m.mat("fence_post")
    for k in range(int(seg / 2)):
        y = k * 2.0
        m.cyl((5.8, y, GROUND + 0.24 + 0.85), r=0.035, h=1.7, seg=10 if lod == 0 else 6)
    m.cyl((5.8, seg / 2, GROUND + 1.94), r=0.025, h=seg, seg=8 if lod == 0 else 5, axis='Y')
    m.cyl((5.8, seg / 2, GROUND + 0.3), r=0.018, h=seg, seg=6, axis='Y')
    m.mat("fence_mesh", uvscale=0.5)
    m.poly([(5.8, 0, GROUND + 0.28), (5.8, seg, GROUND + 0.28), (5.8, seg, GROUND + 1.94), (5.8, 0, GROUND + 1.94)])
    # curb + gutter + asphalt
    m.mat("curb", uvscale=1.0)
    m.box((6.38, seg / 2, GROUND + 0.04), (0.16, seg, 0.16), bevel=(0.02, 1) if lod == 0 else None, smooth=False)
    m.mat("ditch_dark")
    m.box((6.6, seg / 2, GROUND - 0.035), (0.28, seg, 0.01), smooth=False)
    m.mat("asphalt", uvscale=3.0)
    m.poly([(6.46, 0, GROUND - 0.03), (11.0, 0, GROUND - 0.03), (11.0, seg, GROUND - 0.03), (6.46, seg, GROUND - 0.03)])
    m.mat("road_line")
    m.box((6.85, seg / 2, GROUND - 0.025), (0.12, seg, 0.01), smooth=False)
    # dashed centre-less lane: the white edge line on the far side plus a green pedestrian strip
    m.mat("road_line")
    m.box((10.6, seg / 2, GROUND - 0.025), (0.12, seg, 0.01), smooth=False)
    E.mat("ped_green", 0x4FA36A, soft=0.15, rim=0.0, outline=0)
    m.mat("ped_green")
    m.box((10.82, seg / 2, GROUND - 0.026), (0.32, seg, 0.01), smooth=False)
    if mirror:
        m.pop()
    ob = m.obj(("side_l" if mirror else "side_r") + ("" if lod == 0 else "@1"), smooth_angle=30)
    if mirror:
        _fix_winding(ob)
    return ob


def _fix_winding(ob):
    """A mirror transform flips triangle winding; flip normals back."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


# ----------------------------------------------------------------------------- catenary

def _hbeam(m, a, b, w=0.2, d=0.2, t=0.018):
    """H-section steel member from a to b (flanges facing +-local x)."""
    a, b = Vector(a), Vector(b)
    prof = [(-w / 2, -d / 2), (-w / 2 + t, -d / 2), (-w / 2 + t, -t / 2), (w / 2 - t, -t / 2), (w / 2 - t, -d / 2),
            (w / 2, -d / 2), (w / 2, d / 2), (w / 2 - t, d / 2), (w / 2 - t, t / 2), (-w / 2 + t, t / 2),
            (-w / 2 + t, d / 2), (-w / 2, d / 2)]
    m.sweep([tuple(a), tuple(b)], prof, closed=True, cap=True, smooth=False)


def _insulator(m, c, axis='Z', n=4, r=0.07, pitch=0.06, mat="insulator"):
    """Stack of porcelain discs."""
    m.mat(mat)
    for i in range(n):
        o = (i - (n - 1) / 2) * pitch
        cc = (c[0] + (o if axis == 'X' else 0), c[1] + (o if axis == 'Y' else 0), c[2] + (o if axis == 'Z' else 0))
        m.cyl(cc, r=r, h=0.025, r2=r * 0.55, seg=12, axis=axis)


def gantry(lod=0):
    """Portal catenary gantry spanning all three tracks, with cantilevers and contact-wire registration."""
    m = E.Mesher("gantry")
    H = 6.6
    for s in (-1, 1):
        x = s * 4.95
        m.mat("pole_concrete", uvscale=1.0)
        # tapered concrete mast with a base plinth
        m.cyl((x, 0, GROUND + 0.2), r=0.32, h=0.4, seg=16 if lod == 0 else 8, r2=0.3)
        m.cyl((x, 0, GROUND + 0.4 + (H - GROUND - 0.4) / 2), r=0.2, r2=0.15, h=H - GROUND - 0.4, seg=16 if lod == 0 else 8)
        m.mat("hazard_yellow")
        m.cyl((x, 0, GROUND + 1.3), r=0.205, h=0.5, seg=16 if lod == 0 else 8)
        m.mat("hazard_black")
        for k in range(3 if lod == 0 else 0):
            m.cyl((x, 0, GROUND + 1.12 + k * 0.17), r=0.207, h=0.06, seg=16)
        # number plate
        m.mat("sign_white")
        m.box((x - s * 0.21, 0, 2.4), (0.02, 0.22, 0.3), smooth=False)
    m.mat("steel")
    # top beam: two H-beams with lattice diagonals
    _hbeam(m, (-5.2, 0, H), (5.2, 0, H), 0.22, 0.24)
    _hbeam(m, (-5.2, 0, H - 0.7), (5.2, 0, H - 0.7), 0.16, 0.18)
    if lod == 0:
        n = 14
        for i in range(n):
            x0 = -4.8 + 9.6 * i / n
            x1 = -4.8 + 9.6 * (i + 1) / n
            za, zb = (H - 0.62, H - 0.08) if i % 2 == 0 else (H - 0.08, H - 0.62)
            m.box(((x0 + x1) / 2, 0, (za + zb) / 2), (0.05, 0.05, 0.05))  # node
            m.tube([(x0, 0, za), (x1, 0, zb)], r=0.025, seg=6)
    # brackets onto the masts
    for s in (-1, 1):
        m.box((s * 4.95, 0, H - 0.35), (0.5, 0.36, 0.9), bevel=(0.02, 1) if lod == 0 else None)
    # droppers + registration arms per lane
    for lx in LANES:
        m.mat("steel_dark")
        m.tube([(lx - 0.3, 0, H - 0.8), (lx - 0.3, 0, 5.55)], r=0.03, seg=6)
        m.tube([(lx - 0.3, 0, 5.55), (lx + 0.1, 0, 5.3)], r=0.022, seg=6)
        _insulator(m, (lx - 0.3, 0, H - 0.98), 'Z', 3 if lod == 0 else 1, 0.06, 0.07, "insulator_brown")
    return m.obj("gantry" if lod == 0 else "gantry@1", smooth_angle=35)


def wires(lod=0, seg=SEG):
    """Overhead contact wire + messenger with hangers, per lane, for one segment."""
    m = E.Mesher("wires")
    m.mat("wire")
    for lx in LANES:
        m.box((lx + 0.1, seg / 2, 5.3), (0.022, seg, 0.022), smooth=False)
        if lod == 0:
            m.box((lx + 0.1, seg / 2, 6.0), (0.026, seg, 0.026), smooth=False)
            for k in range(int(seg / 3)):
                y = k * 3 + 1.5
                m.box((lx + 0.1, y, 5.65), (0.008, 0.008, 0.7), smooth=False)
    return m.obj("wires" if lod == 0 else "wires@1", smooth_angle=0)


# ----------------------------------------------------------------------------- utility pole

def utility_pole(lod=0, span=24.0):
    """Japanese concrete utility pole (denchū) with crossarms, transformer, insulators and
    sagging cables to the next pole `span` metres ahead."""
    m = E.Mesher("upole")
    x = 9.4
    H = 10.5
    seg = 16 if lod == 0 else 8
    m.mat("pole_concrete", uvscale=1.0)
    m.cyl((x, 0, GROUND + H / 2), r=0.19, r2=0.13, h=H, seg=seg)
    m.cyl((x, 0, GROUND + H + 0.05), r=0.135, h=0.1, seg=seg)
    # yellow/black anti-collision cover on the lower part
    m.mat("hazard_yellow")
    m.cyl((x, 0, GROUND + 1.0), r=0.2, r2=0.192, h=1.8, seg=seg)
    if lod == 0:
        m.mat("hazard_black")
        for k in range(6):
            z = GROUND + 0.25 + k * 0.3
            m.push(Matrix.Translation((x, 0, z)) @ Matrix.Rotation(math.radians(18), 4, 'X'))
            m.cyl((0, 0, 0), r=0.203, h=0.11, seg=seg)
            m.pop()
    # step bolts
    if lod == 0:
        m.mat("steel_dark")
        for k in range(10):
            z = GROUND + 2.2 + k * 0.45
            pr = 0.19 - 0.06 * (z - GROUND) / H
            if k % 2:
                m.cyl((x - pr - 0.06, 0, z), r=0.012, h=0.2, seg=5, axis='X')
            else:
                m.cyl((x, pr + 0.06, z), r=0.012, h=0.2, seg=5, axis='Y')
    # crossarms
    arms = [(H - 0.5, 1.6), (H - 1.4, 1.3), (H - 2.6, 0.9)]
    m.mat("steel")
    for (z, half) in arms:
        m.box((x, 0, GROUND + z), (half * 2, 0.09, 0.09), bevel=(0.008, 1) if lod == 0 else None)
        # insulators on top of the arm
        for k in range(3):
            ix = x - half + 0.15 + k * (2 * half - 0.3) / 2
            if lod == 0:
                _insulator(m, (ix, 0, GROUND + z + 0.12), 'Z', 3, 0.05, 0.05)
            else:
                m.mat("insulator")
                m.cyl((ix, 0, GROUND + z + 0.12), r=0.04, h=0.15, seg=6)
        m.mat("steel")
        # diagonal braces
        m.tube([(x - half * 0.6, 0, GROUND + z - 0.05), (x, 0, GROUND + z - 0.6)], r=0.018, seg=5)
        m.tube([(x + half * 0.6, 0, GROUND + z - 0.05), (x, 0, GROUND + z - 0.6)], r=0.018, seg=5)
    # pole-top transformer (grey can + bushings)
    m.mat("transformer")
    m.cyl((x - 0.42, 0, GROUND + H - 3.5), r=0.27, h=0.85, seg=seg)
    m.cyl((x - 0.42, 0, GROUND + H - 3.05), r=0.29, h=0.05, seg=seg)
    if lod == 0:
        for k in range(3):
            _insulator(m, (x - 0.55 + k * 0.13, 0, GROUND + H - 2.95), 'Z', 2, 0.03, 0.05)
    m.mat("steel_dark")
    m.box((x - 0.18, 0, GROUND + H - 3.5), (0.12, 0.3, 0.5))
    # street-light arm toward the road with a lamp
    m.mat("steel")
    m.tube([(x, 0, GROUND + 5.0), (x - 0.6, 0, GROUND + 5.3), (x - 1.1, 0, GROUND + 5.3)], r=0.03, seg=6)
    E.mat("lamp", 0xFFF2C8, emis=0.25, soft=0.1, rim=0.2, outline=0.5, flags=E.F_NIGHT)
    m.mat("transformer")
    m.box((x - 1.25, 0, GROUND + 5.28), (0.42, 0.18, 0.08), bevel=(0.02, 1) if lod == 0 else None)
    m.mat("lamp")
    m.box((x - 1.25, 0, GROUND + 5.235), (0.36, 0.14, 0.02), smooth=False)
    # blue address plate
    m.mat("sign_blue")
    m.box((x - 0.2, 0, GROUND + 2.6), (0.02, 0.18, 0.55), smooth=False)
    m.mat("sign_white")
    m.box((x - 0.211, 0, GROUND + 2.6), (0.004, 0.15, 0.48), smooth=False)
    # cables to the next pole (sagging), plus a thick bundled telecom cable lower down
    m.mat("wire")
    for (z, half) in arms:
        for k in range(3):
            ix = x - half + 0.15 + k * (2 * half - 0.3) / 2
            pts = E.catenary((ix, 0, GROUND + z + 0.2), (ix, span, GROUND + z + 0.2), sag=0.45, n=12 if lod == 0 else 6)
            m.tube(pts, r=0.012, seg=4, cap=False)
    pts = E.catenary((x - 0.25, 0, GROUND + 5.9), (x - 0.25, span, GROUND + 5.9), sag=0.7, n=12 if lod == 0 else 6)
    m.tube(pts, r=0.035, seg=6 if lod == 0 else 4, cap=False)
    pts = E.catenary((x + 0.25, 0, GROUND + 5.6), (x + 0.25, span, GROUND + 5.6), sag=0.6, n=12 if lod == 0 else 6)
    m.tube(pts, r=0.022, seg=5 if lod == 0 else 4, cap=False)
    return m.obj("upole" if lod == 0 else "upole@1", smooth_angle=35)


# ----------------------------------------------------------------------------- design renders

def _scene_base(res=(1280, 720)):
    E.reset()
    studio.stage(res=res, floor=False)
    city_mats()


def design_track():
    _scene_base()
    for i in range(4):
        y0 = i * SEG
        for fn in (track, side, lambda: side(mirror=True), wires):
            ob = fn()
            ob.location.y += y0
    for i in range(2):
        ob = gantry()
        ob.location.y = i * 24 + 6
    for i in range(2):
        ob = utility_pole()
        ob.location.y = i * 24 + 2
        ob2 = utility_pole()
        ob2.scale.x = -1
        ob2.location.y = i * 24 + 14
    studio.shoot("city_track", target=(0, 14, 1.0), dist=13, yaw=180 + 8, pitch=16, lens=28)
    studio.shoot("city_track_close", target=(1.6, 6, 0.0), dist=4.5, yaw=180 + 35, pitch=32, lens=35)
    studio.shoot("city_pole", target=(9.4, 2, 6.5), dist=8, yaw=-60, pitch=10, lens=35)
