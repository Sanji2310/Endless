"""
Sakura Line -> Crystal Cavern transition (docs/PONGO_DESIGN.md §4: "Sakura Line -> tunnel mouth -> Cavern").

Laid out in the shared track frame (Blender Z up, runner toward +Y, 12 m segments, lanes x = -2.4, 0, 2.4).
The transition is four segments long and starts where the last Sakura Line block ends:

  y -48 .. 0    approach    the line runs into a cutting: stone retaining walls, grassy slopes rising into a
                            wooded hill with sakura and sugi; the catenary ends on the portal
  y   0         portal      dressed-stone tunnel portal with ring stones, a name plaque (水晶洞), cornice and
                            wing walls, set into the hill
  y   0 .. 12   lined A     concrete-lined tunnel, still Sakura Line track, wall lamps, refuge niches
  y  12 .. 24   lined B     the track changes from concrete sleepers on ballast to mine ties on earth at
                            y = 18; crystals start to grow through the lining joints
  y  24         mouth       the lining ends in a heavy ring; the cavern vault (cave.py) opens out beyond it

The run is invulnerable from the portal to the mouth (Zones.java), the title card slides in at the portal and
the lighting crossfades from the time-of-day palette to the cave palette between y = -6 and y = 24.
"""
import math, random
import bpy
from mathutils import Vector, Matrix
import erlib as E
import studio
import city
import cave

V = Vector
SEG = 12.0
GROUND = city.GROUND
APPROACH = 48.0          # length of the cutting in front of the portal
LINED = 24.0             # length of the lined tunnel (portal -> mouth)
SPRING = 3.4             # springline of the lining arch
HALF_W = 5.6             # inner half width of the lining
CROWN = 7.6              # inner crown height
THICK = 0.7              # lining thickness
BOARD = 4.0              # Pongo boards the ore cart this far before the mouth (Zones.BOARD)
FACE_W = 11.25           # half width of the portal face
FACE_TOP = 11.0          # top of the portal cornice


def mats():
    M = E.mat
    sh = dict(shadow=cave.SHADOW)
    M("portal_stone", 0xC9BFAE, "t_portal_stone", soft=0.15, rim=0.2, outline=0.8)
    M("portal_ring", 0xB3A892, "t_portal_stone", soft=0.15, rim=0.25, outline=0.9)
    M("portal_dark", 0x3B3646, soft=0.15, rim=0.1, outline=0.6)
    M("plaque", 0x2E2A36, spec=0.3, rim=0.2, soft=0.1, outline=0.7)
    M("plaque_gold", 0xF2C35C, spec=0.95, rim=0.45, soft=0.04, flags=E.F_METAL, outline=0.0)
    M("hill_grass", 0xFFFFFF, "t_grass", soft=0.25, rim=0.1, outline=0)
    M("hill_dirt", 0xFFFFFF, "t_dirt", soft=0.2, rim=0.1, outline=0)
    M("sugi", 0x8FB27A, "t_leaves", soft=0.3, rim=0.25, outline=0.8, flags=E.F_FOLIAGE, sway=0.25, shadow=0x5E6A9A)
    M("sugi_bark", 0x6E4A3A, "t_wood", soft=0.15, rim=0.2, outline=0.8)
    M("lining", 0xB9B4AA, "t_concrete", soft=0.2, rim=0.15, outline=0, **sh)
    M("lining_joint", 0x6F6A62, soft=0.2, rim=0.0, outline=0, **sh)
    M("niche", 0x1C1828, soft=0.1, rim=0.0, outline=0, **sh)
    M("niche_frame", 0xEFEBE2, soft=0.12, rim=0.15, outline=0.4, **sh)
    M("tn_lamp_box", 0x5E6670, spec=0.4, rim=0.3, soft=0.1, flags=E.F_METAL, outline=0.6, **sh)
    M("tn_lamp", 0xFFE7B0, emis=1.4, rim=0.0, soft=0.05, outline=0.0, flags=E.F_NOCAST)
    M("sig_red", 0xFF4A3A, emis=1.2, rim=0.0, soft=0.05, outline=0.0, flags=E.F_NOCAST)
    M("sig_green", 0x3AFFA0, emis=0.25, rim=0.0, soft=0.05, outline=0.0, flags=E.F_NOCAST)


def darken(ob):
    """Swap an object's materials for '<name>_tn' twins with the cave shadow colour, so city pieces placed inside
    the tunnel read dark in their shadow band (the game uses one global shadow colour, so this is render-only)."""
    me = ob.data
    for i, bm in enumerate(me.materials):
        if bm is None or bm.name.endswith("_tn") or bm.name not in E._MATS:
            continue
        g = E._MATS[bm.name]
        tw = E.mat(bm.name + "_tn", g.color, g.tex, spec=g.spec, rim=g.rim, emis=g.emis, soft=g.soft,
                   outline=g.outline, skin=g.skin, sway=g.sway, flags=g.flags, shadow=cave.SHADOW)
        me.materials[i] = tw.bmat
    return ob


# ----------------------------------------------------------------------------- profiles

def lining_profile(n_arch=24, offset=0.0, foot=GROUND - 0.05):
    """Horseshoe section from the left foot over the crown to the right foot as (x, z, nx, nz) with the inward
    normal; offset > 0 gives the outer face of the lining."""
    a, b = HALF_W + offset, CROWN - SPRING + offset
    pts = [(-a, foot), (-a, SPRING * 0.5), (-a, SPRING)]
    for i in range(1, n_arch):
        t = math.pi - math.pi * i / n_arch
        pts.append((a * math.cos(t), SPRING + b * math.sin(t)))
    pts += [(a, SPRING), (a, SPRING * 0.5), (a, foot)]
    out = []
    for i, (x, z) in enumerate(pts):
        p0, p1 = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        tx, tz = p1[0] - p0[0], p1[1] - p0[1]
        L = math.hypot(tx, tz) or 1.0
        out.append((x, z, tz / L, -tx / L))
    return out


# ----------------------------------------------------------------------------- terrain

def _hmax(y):
    """Hill crest height as the line approaches the portal (and above the tunnel)."""
    if y >= 1.0:
        return 13.0 + min(3.0, (y - 1.0) * 0.12)
    t = min(1.0, max(0.0, (y + APPROACH) / (APPROACH - 2.0)))
    return 1.4 + 11.6 * t * t * (3 - 2 * t)


def hill_height(x, y):
    ax = abs(x)
    n = 0.35 * math.sin(x * 0.31 + y * 0.17) + 0.25 * math.sin(x * 0.11 - y * 0.29 + 1.3) + 0.12 * math.sin(x * 0.9 + y * 0.7)
    if y >= 1.0:
        return _hmax(y) + n
    slope = GROUND + 1.3 + (ax - 6.25) * 0.85
    h = min(_hmax(y) + n, slope + n * min(1.0, (ax - 6.25) * 0.3))
    return max(GROUND + 1.3, h) if ax >= 6.25 else GROUND + 1.3


def hill(lod=0):
    """Heightfield around the cutting and over the tunnel. Cells over the track (|x| < 6.25, y < 1) are left out."""
    step = 1.25 if lod == 0 else 3.75
    xs = [-60 + i * step for i in range(int(120 / step) + 1)]
    xs = sorted(set([round(x, 3) for x in xs] + [-6.25, 6.25]))
    ys = [-APPROACH + i * step for i in range(int((APPROACH + 60) / step) + 1)]
    ys = sorted(set([round(y, 3) for y in ys] + [0.0, 1.0]))
    m = E.Mesher("tunnel_hill")
    bm = m.bm
    vid = {}
    for y in ys:
        for x in xs:
            vid[(x, y)] = bm.verts.new(m.M @ V((x, y, hill_height(x, y))))
    m.mat("hill_grass", uvscale=3.0)
    faces = []
    for j in range(len(ys) - 1):
        for i in range(len(xs) - 1):
            x0, x1, y0, y1 = xs[i], xs[i + 1], ys[j], ys[j + 1]
            if y1 <= 1.0 and min(abs(x0), abs(x1)) < 6.25 - 1e-6 and not (x0 >= 6.25 or x1 <= -6.25):
                continue
            f = bm.faces.new((vid[(x0, y0)], vid[(x1, y0)], vid[(x1, y1)], vid[(x0, y1)]))
            f.normal_update()
            faces.append(f)
    m._finish([v for f in faces for v in f.verts], None, 'box', True)
    return m.obj("tunnel_hill" + ("" if lod == 0 else "@1"), smooth_angle=60)


def sugi(m, c, h, rnd, lod=0):
    """Japanese cedar: straight trunk and stacked, drooping cone tiers."""
    x, y, z = c
    m.mat("sugi_bark", uvscale=0.6)
    m.cyl((x, y, z + h * 0.3), r=h * 0.035, r2=h * 0.02, h=h * 0.6, seg=8 if lod == 0 else 5)
    m.mat("sugi", uvscale=0.8)
    tiers = 4 if lod == 0 else 2
    for k in range(tiers):
        t = k / tiers
        r = h * (0.24 - 0.17 * t) * rnd.uniform(0.9, 1.1)
        zz = z + h * (0.32 + 0.6 * t)
        m.cyl((x, y, zz), r=r, r2=r * 0.12, h=h * 0.3, seg=9 if lod == 0 else 6)


def trees(lod=0, seed=21):
    """Cedar wood on the hill, kept off the cutting and the portal."""
    rnd = random.Random(seed)
    m = E.Mesher("tunnel_trees")
    n = 0
    while n < (60 if lod == 0 else 30):
        x = rnd.uniform(-55, 55)
        y = rnd.uniform(-APPROACH + 4, 55)
        if abs(x) < 9.5 + max(0.0, -y) * 0.1 or (abs(x) < FACE_W + 4 and -10 < y < 4):
            continue
        if y < 0 and hill_height(x, y) < 2.5:
            continue
        sugi(m, (x, y, hill_height(x, y) - 0.2), rnd.uniform(7, 12), rnd, lod)
        n += 1
    return m.obj("tunnel_trees" + ("" if lod == 0 else "@1"), smooth_angle=40)


def cutting(lod=0, seg=SEG, mirror=False):
    """One side of the cutting (right, x > 0; mirror=True for the left): gravel path, stone retaining wall."""
    m = E.Mesher("cutting")
    if mirror:
        m.push(Matrix.Diagonal((-1, 1, 1, 1)))
    m.mat("hill_dirt", uvscale=2.0)
    m.poly([(5.47, 0, GROUND + 0.1), (5.95, 0, GROUND + 0.12), (5.95, seg, GROUND + 0.12), (5.47, seg, GROUND + 0.1)])
    m.mat("portal_stone", uvscale=1.0)
    m.box((6.1, seg / 2, GROUND + 0.6), (0.3, seg, 1.5), smooth=False)
    m.mat("portal_ring", uvscale=1.0)
    m.box((6.08, seg / 2, GROUND + 1.38), (0.38, seg, 0.12), smooth=False)          # coping
    if mirror:
        m.pop()
    ob = m.obj(("cutting_l" if mirror else "cutting_r") + ("" if lod == 0 else "@1"), smooth_angle=30)
    if mirror:
        city._fix_winding(ob)
    return ob


# ----------------------------------------------------------------------------- portal

def _annulus(m, a, b, facing):
    """Faces between two matching point rings a -> b (same count, open), flipped to face `facing`."""
    import bmesh
    bm = m.bm
    va = [bm.verts.new(m.M @ V(p)) for p in a]
    vb = [bm.verts.new(m.M @ V(p)) for p in b]
    faces = []
    for j in range(len(va) - 1):
        f = bm.faces.new((va[j], va[j + 1], vb[j + 1], vb[j]))
        f.normal_update()
        faces.append(f)
    flip = [f for f in faces if f.normal.dot((m.M.to_3x3() @ V(facing))) < 0]
    if flip:
        bmesh.ops.reverse_faces(bm, faces=flip)
    return m._finish(va + vb, None, 'box', False)


def _ray_to_rect(pts, half_w, z0, z1, cz=SPRING):
    """Push each (x, z) out from (0, cz) along its ray until it meets the rectangle |x| = half_w, z0..z1."""
    out = []
    for (x, z) in pts:
        dx, dz = x, z - cz
        ts = []
        if abs(dx) > 1e-9:
            ts.append(half_w / abs(dx))
        if dz > 1e-9:
            ts.append((z1 - cz) / dz)
        if dz < -1e-9:
            ts.append((z0 - cz) / dz)
        t = min(ts)
        out.append((dx * t, cz + dz * t))
    return out


def _ray_to_poly(pts, poly, cz=SPRING):
    """Push each (x, z) out from (0, cz) along its ray to the first crossing with an open polyline `poly`."""
    out = []
    for (x, z) in pts:
        dx, dz = x, z - cz
        best = None
        for i in range(len(poly) - 1):
            (ax, az), (bx, bz) = poly[i], poly[i + 1]
            ex, ez = bx - ax, bz - az
            den = dx * ez - dz * ex
            if abs(den) < 1e-12:
                continue
            t = (ax * ez - (az - cz) * ex) / den
            u = (ax * dz - (az - cz) * dx) / den
            if t > 0 and -1e-6 <= u <= 1 + 1e-6 and (best is None or t < best):
                best = t
        t = best if best is not None else 1.0
        out.append((dx * t, cz + dz * t))
    return out


def _arch_stones(m, prof, y, depth, mat="portal_ring", key_mat="portal_stone", width=0.75):
    """Ring stones (voussoirs) along the arch part of a lining profile, standing proud of the face at y."""
    arch = [(x, z, nx, nz) for (x, z, nx, nz) in prof if z >= SPRING - 1e-6]
    n = len(arch)
    for i in range(n - 1):
        x0, z0, nx0, nz0 = arch[i]
        x1, z1, nx1, nz1 = arch[i + 1]
        nx, nz = (nx0 + nx1) / 2, (nz0 + nz1) / 2
        L = math.hypot(nx, nz) or 1
        nx, nz = nx / L, nz / L
        key = i == (n - 1) // 2
        w = width * (1.35 if key else (1.0 if i % 2 == 0 else 0.82))
        inner = [(x0, z0), (x1, z1)]
        outer = [(x1 - nx * w, z1 - nz * w), (x0 - nx * w, z0 - nz * w)]
        pts2 = inner + outer
        m.mat(key_mat if key else mat, uvscale=1.0)
        m.push(Matrix.Translation((0, y, 0)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
        m.extrude(pts2, depth + (0.08 if key else 0.0), c=(0, 0, 0), bevel=None)
        m.pop()


def portal(lod=0):
    """Tunnel portal at y = 0 facing the runner: face wall with the arch opening, ring stones, pilasters, cornice,
    name plaque, wing walls, and catenary anchors."""
    m = E.Mesher("tunnel_portal")
    prof = lining_profile(28 if lod == 0 else 14)
    face_bottom, face_top = GROUND - 0.6, FACE_TOP - 0.4
    hole = [(x, z) for (x, z, nx, nz) in prof]
    rect = _ray_to_rect(hole, FACE_W, face_bottom, face_top)
    m.mat("portal_stone", uvscale=1.0)
    _annulus(m, [(x, 0.0, z) for x, z in hole], [(x, 0.0, z) for x, z in rect], V((0, -1, 0)))
    # thickness: top and sides of the face block (the back is buried in the hill)
    m.box((0, 0.6, face_top + 0.0), (FACE_W * 2, 1.2, 0.02), smooth=False)
    for side in (-1, 1):
        m.box((side * FACE_W, 0.6, (face_bottom + face_top) / 2), (0.02, 1.2, face_top - face_bottom), smooth=False)
    _arch_stones(m, prof, -0.05, 0.3)
    # quoins down the arch jambs
    for s in (-1, 1):
        for k in range(5):
            z0 = GROUND + k * (SPRING - GROUND) / 5
            h = (SPRING - GROUND) / 5 - 0.03
            w = 0.7 if k % 2 == 0 else 0.45
            m.mat("portal_ring", uvscale=1.0)
            m.box((s * (HALF_W + w / 2), -0.05, z0 + h / 2), (w, 0.3, h), smooth=False)
    # pilasters and cornice
    for s in (-1, 1):
        m.mat("portal_ring", uvscale=1.0)
        m.box((s * (FACE_W - 0.45), -0.12, (GROUND + FACE_TOP - 0.4) / 2), (0.9, 0.45, FACE_TOP - 0.4 - GROUND), smooth=False)
    m.mat("portal_ring", uvscale=1.0)
    m.box((0, 0.2, FACE_TOP - 0.25), (FACE_W * 2 + 0.6, 1.6, 0.3), bevel=(0.03, 1) if lod == 0 else None, smooth=False)
    m.box((0, 0.3, FACE_TOP + 0.05), (FACE_W * 2 + 0.2, 1.3, 0.3), smooth=False)
    m.mat("portal_stone", uvscale=1.0)
    m.box((0, 0.3, FACE_TOP + 0.5), (FACE_W * 2, 1.1, 0.6), smooth=False)            # parapet
    # name plaque: 水晶洞 (Crystal Cave), with the tunnel's year in small type
    pz = CROWN + 1.55
    m.mat("portal_ring")
    m.box((0, -0.12, pz), (3.4, 0.25, 1.15), bevel=(0.03, 1) if lod == 0 else None, smooth=False)
    m.mat("plaque")
    m.box((0, -0.2, pz), (3.0, 0.15, 0.85), smooth=False)
    m.mat("plaque_gold")
    m.push(Matrix.Translation((0, -0.28, pz + 0.04)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
    m.text("水晶洞", size=0.62, depth=0.03, font=E.FONT_JP, c=(0, 0, 0), spacing=1.25)
    m.pop()
    # wing walls: battered stone walls stepping down the slope toward the runner
    for s in (-1, 1):
        x0, y0 = s * (FACE_W - 0.2), 0.0
        x1, y1 = s * (FACE_W + 3.2), -6.5
        L = math.hypot(x1 - x0, y1 - y0)
        ang = math.atan2(y1 - y0, x1 - x0)
        top0, top1 = FACE_TOP - 1.2, max(hill_height(x1, y1) + 0.6, GROUND + 2.0)
        m.mat("portal_stone", uvscale=1.0)
        m.push(Matrix.Translation((x0, y0, 0)) @ Matrix.Rotation(ang, 4, 'Z') @ Matrix.Rotation(math.radians(90), 4, 'X'))
        m.extrude([(0, GROUND - 0.5), (L, GROUND - 0.5), (L, top1), (0, top0)], 0.8, c=(0, 0, 0))
        m.pop()
        m.mat("portal_ring", uvscale=1.0)
        a, b = V((x0, y0, top0 + 0.1)), V((x1, y1, top1 + 0.1))
        m.sweep([tuple(a), tuple(b)], [(-0.5, -0.12), (0.5, -0.12), (0.5, 0.12), (-0.5, 0.12)], closed=True, cap=True)
    # catenary anchors (the wires end here) and a drip channel over the arch
    bz = 6.4
    bx = HALF_W * math.sqrt(max(0.0, 1 - ((bz - SPRING) / (CROWN - SPRING)) ** 2)) + 0.3
    m.mat("steel_dark" if "steel_dark" in E._MATS else "portal_dark")
    m.box((0, -0.25, bz), (bx * 2, 0.16, 0.22), smooth=False)                       # head beam across the arch
    for side in (-1, 1):
        m.box((side * bx, -0.12, bz), (0.3, 0.3, 0.3), smooth=False)                  # wall plates
    for lx in city.LANES:
        m.box((lx + 0.1, -0.25, bz - 0.45), (0.06, 0.06, 0.7), smooth=False)        # droppers to the wire ends
        m.mat("insulator_brown" if "insulator_brown" in E._MATS else "portal_dark")
        m.cyl((lx + 0.1, -0.25, bz - 0.85), r=0.05, h=0.12, seg=10)
        m.mat("steel_dark" if "steel_dark" in E._MATS else "portal_dark")
    ob = m.obj("tunnel_portal" + ("" if lod == 0 else "@1"), smooth_angle=30)
    if lod == 0:
        E.finish_hard(ob, width=0.015, segments=1, angle=35)
    return ob


def block_signal(m, c):
    """Small tunnel-entrance block signal on a mast (red over green), face toward -Y."""
    x, y, z = c
    m.mat("steel")
    m.cyl((x, y, z + 1.6), r=0.06, h=3.2, seg=10)
    m.mat("hazard_black")
    m.rbox((x, y, z + 3.1), (0.42, 0.18, 0.8), r=0.05)
    for k, mt in enumerate(("sig_red", "sig_green")):
        m.mat("hazard_black")
        m.cyl((x, y - 0.12, z + 3.3 - k * 0.38), r=0.15, r2=0.13, h=0.12, seg=14, axis='Y', caps=False)
        m.mat(mt)
        m.cyl((x, y - 0.1, z + 3.3 - k * 0.38), r=0.12, h=0.02, seg=14, axis='Y')


# ----------------------------------------------------------------------------- lined tunnel

def _lining_surface(m, prof, y0, y1, ring=1.5, inward=True, joints=True):
    """Lining between y0 and y1 in 'ring' long pours, each a slightly different concrete tone, with dark joints."""
    n = int(round((y1 - y0) / ring))
    for k in range(n):
        a, b = y0 + k * ring, y0 + (k + 1) * ring
        m.mat("lining", uvscale=2.0, tint=(1, 1, 1, 1) if k % 2 == 0 else (0.94, 0.93, 0.9, 1))
        rings = [[(x, a, z) for (x, z, nx, nz) in prof], [(x, b, z) for (x, z, nx, nz) in prof]]
        cave._grid(m, rings, inward=inward)
        if joints and inward:
            m.mat("lining_joint")
            j = [[(x + nx * 0.005, a - 0.03, z + nz * 0.005) for (x, z, nx, nz) in prof],
                 [(x + nx * 0.005, a + 0.03, z + nz * 0.005) for (x, z, nx, nz) in prof]]
            cave._grid(m, j, inward=True)


def wall_lamp(m, x, y, z, side):
    """Bulkhead lamp on the tunnel wall; side = -1 left wall, +1 right wall."""
    m.mat("tn_lamp_box")
    m.rbox((x - side * 0.08, y, z), (0.16, 0.5, 0.22), r=0.03)
    m.mat("tn_lamp")
    m.box((x - side * 0.165, y, z), (0.01, 0.4, 0.14), smooth=False)


def niche(m, y, side):
    """Refuge niche (待避所) suggested by a dark recess panel with a white frame and a green sign."""
    x = side * (HALF_W - 0.01)
    m.mat("niche")
    pts = [(x, y - 0.6, GROUND + 0.1), (x, y + 0.6, GROUND + 0.1), (x, y + 0.6, 2.2), (x, y - 0.6, 2.2)]
    m.poly(pts if side > 0 else pts[::-1])
    m.mat("niche_frame")
    for (yy, zz, sy, sz) in ((y - 0.66, 1.15, 0.12, 2.2), (y + 0.66, 1.15, 0.12, 2.2), (y, 2.26, 1.44, 0.12)):
        m.box((x - side * 0.01, yy, zz), (0.03, sy, sz), smooth=False)
    m.mat("sig_green")
    m.box((x - side * 0.02, y, 2.6), (0.02, 0.5, 0.18), smooth=False)


def tunnel_lined(lod=0, part=0):
    """One 12 m lined segment (part 0: y 0..12, part 1: y 12..24, built at its own origin)."""
    m = E.Mesher("tunnel_lined")
    prof = lining_profile(24 if lod == 0 else 10)
    _lining_surface(m, prof, 0.0, SEG, joints=lod == 0)
    # invert slab under the track bed, wall to wall (closes the joint between the ditches and the lining foot)
    m.mat("lining_joint")
    m.poly([(-HALF_W, 0, GROUND - 0.2), (HALF_W, 0, GROUND - 0.2), (HALF_W, SEG, GROUND - 0.2), (-HALF_W, SEG, GROUND - 0.2)])
    m.mat("lining", uvscale=1.0)
    for side in (-1, 1):                      # side walkways over the cable troughs
        m.box((side * (HALF_W - 0.12), SEG / 2, GROUND + 0.12), (0.24, SEG, 0.5), smooth=False)
    # lamps (staggered) and refuge niches
    for k, (y, side) in enumerate(((3.0, -1), (9.0, 1))):
        wall_lamp(m, side * HALF_W, y, 2.6, side)
    if lod == 0:
        niche(m, 6.0, -1 if part == 0 else 1)
    if part == 1 and lod == 0:
        # crystals pushing through the last joints before the mouth
        rnd = random.Random(77)
        for (y, z, side) in ((8.5, 1.2, 1), (10.4, 4.6, -1), (11.2, 0.6, -1), (10.9, 2.4, 1)):
            x = side * HALF_W
            cave.crystal_cluster(m, (x + side * 0.15, y, z), (-side, 0, 0.3), size=rnd.uniform(0.45, 0.8), rnd=rnd,
                                 mats=("c_crystal", "c_crystal_violet"), n=5)
    return m.obj("tunnel_lined_%d" % part + ("" if lod == 0 else "@1"), smooth_angle=50)


def tunnel_mouth(lod=0):
    """The end of the lining at y = 0 (placed at y = 24): a heavy ring of stones facing into the cavern, the lining's
    end face, and a rock wall closing the gap between the lining and the cavern vault."""
    m = E.Mesher("tunnel_mouth")
    inner = lining_profile(24 if lod == 0 else 10)
    outer = lining_profile(24 if lod == 0 else 10, offset=THICK)
    # end face of the lining (annulus between inner and outer), facing +Y into the cave
    m.mat("lining", uvscale=1.0)
    _annulus(m, [(x, 0.0, z) for (x, z, _, _) in inner], [(x, 0.0, z) for (x, z, _, _) in outer], V((0, 1, 0)))
    # rock wall from the lining's outer face out to the cavern vault (the vault's shared seam profile at y = 0)
    vprof, arc = cave.vault_profile(60)
    seam = [cave.shell_point(x, z, nx, nz, arc[i], 0.0, 1) for i, (x, z, nx, nz) in enumerate(vprof)]
    seam = [(p.x * 1.02, p.z * 1.01 + 0.02) for p in seam]
    rock = _ray_to_poly([(x, z) for (x, z, _, _) in outer], seam)
    m.mat("c_rock", uvscale=2.5)
    _annulus(m, [(x, 0.02, z) for (x, z, _, _) in outer], [(x, 0.02, z) for (x, z) in rock], V((0, 1, 0)))
    # stone ring on the cavern side
    _arch_stones(m, [(x, z, nx, nz) for (x, z, nx, nz) in inner], 0.25, 0.5, width=0.9)
    # a pair of lanterns on brackets either side of the mouth, and fallen stones at the foot
    for s in (-1, 1):
        m.mat("c_iron_dark")
        m.box((s * (HALF_W + 0.5), 0.35, 4.2), (0.9, 0.08, 0.08), smooth=False)
        cave.lantern(m, (s * (HALF_W + 0.85), 0.4, 4.2), lod)
    rnd = random.Random(5)
    for k in range(6 if lod == 0 else 2):
        s = rnd.choice((-1, 1))
        cave._rock(m, (s * rnd.uniform(4.6, 5.4), rnd.uniform(0.4, 2.0), cave.FLOOR + 0.1), rnd.uniform(0.15, 0.35), rnd,
                   mat="portal_ring")
    return m.obj("tunnel_mouth" + ("" if lod == 0 else "@1"), smooth_angle=40)


def track_change(lod=0):
    """Segment where the Sakura Line track becomes mine track (y 0..6 city, 6..12 cave) with joint bars."""
    a = city.track(lod, seg=6.0)
    b = cave.cave_track(lod, seg=6.0)
    b.location.y = 6.0
    m = E.Mesher("track_joint")
    m.mat("c_iron_dark")
    for lx in city.LANES:
        for s in (-1, 1):
            m.box((lx + s * city.GAUGE / 2, 6.0, 0.07), (0.09, 0.5, 0.07), smooth=False)
    m.mat("c_floor", uvscale=3.0)
    for s in (-1, 1):                                     # earth spill over the ditch where the floor changes
        pts = [(s * 4.6, 6.0, cave.FLOOR), (s * 5.6, 6.0, GROUND + 0.05), (s * 5.6, 7.5, cave.FLOOR + 0.02), (s * 4.6, 7.5, cave.FLOOR)]
        m.poly(pts if s > 0 else pts[::-1])
    c = m.obj("track_joint")
    bpy.context.view_layer.update()
    ob = E.join([a, b, c], "track_change" + ("" if lod == 0 else "@1"))
    return ob


# ----------------------------------------------------------------------------- title cards

def title_cards():
    """Zone title cards (build/tex/ui_zone_*.png) shown when a zone begins; listed in _extra.txt for the builder."""
    import os
    import paint as PT

    def card(name, kanji, latin, zone, c0, c1, edge, accent, motif):
        c = PT.Canvas(name, 640, 200)
        # slanted banner with a gradient and an accent edge
        c.gradient_poly([(40, 30), (620, 30), (600, 170), (20, 170)], [(c0, 1.0), (c0, 1.0), (c1, 1.0), (c1, 1.0)])
        c.poly([(40, 30), (620, 30), (617, 40), (37, 40)], edge)
        c.poly([(23, 160), (603, 160), (600, 170), (20, 170)], edge)
        motif(c)
        c.text(kanji, 290, 112, 78, 0xFFFFFF, font=E.FONT_JP, outline=4, outline_color=accent, spacing=1.05)
        c.text(latin, 290, 54, 24, edge, spacing=1.3)
        c.poly([(500, 150), (600, 150), (594, 186), (494, 186)], accent)
        c.text(zone, 547, 168, 20, 0xFFFFFF)
        return c.save()

    def crystals(c):
        for (x, y, h, w, col) in ((70, 40, 120, 22, 0x7FF0FF), (100, 40, 85, 18, 0xB59CFF), (48, 40, 70, 16, 0xFF9AD6),
                                  (530, 40, 80, 18, 0x7FF0FF), (560, 40, 55, 14, 0xB59CFF)):
            c.poly([(x - w, y), (x + w, y), (x + w * 0.9, y + h * 0.7), (x, y + h), (x - w * 0.9, y + h * 0.7)], col)
            c.poly([(x, y), (x + w, y), (x + w * 0.9, y + h * 0.7), (x, y + h)], 0xFFFFFF, alpha=0.35)

    def petals(c):
        rnd = random.Random(3)
        for k in range(14):
            x, y = rnd.uniform(40, 600), rnd.uniform(36, 168)
            c.ellipse(x, y, 9, 5, 0xFFE3EC, rot=rnd.uniform(0, 3.14), alpha=0.9)

    card("ui_zone_cavern", "水晶洞窟", "CRYSTAL CAVERN", "ZONE 2", 0x1E1640, 0x3B2A78, 0x7FF0FF, 0x6A3FD0, crystals)
    card("ui_zone_sakura", "桜線", "SAKURA LINE", "ZONE 1", 0xE98AAE, 0xF7B9CF, 0xFFFFFF, 0xD94F7A, petals)
    path = os.path.join(E.OUT_TEX, "_extra.txt")
    have = open(path).read().split() if os.path.exists(path) else []
    with open(path, "a") as f:
        for n in ("ui_zone_cavern", "ui_zone_sakura"):
            if n not in have:
                f.write(n + "\n")


# ----------------------------------------------------------------------------- scene

def transition_scene(cave_segments=3, outlines=True, approach_segments=4, sakura_trees=True):
    """Builds the approach, portal, lined tunnel, mouth and the first cave segments into the current scene."""
    import buildings as BL
    city.city_mats()
    cave.mats()
    mats()
    obs = []
    # approach: Sakura Line track and catenary in the cutting
    for i in range(approach_segments):
        y0 = -APPROACH + i * SEG
        for fn in (city.track, cutting, lambda: cutting(mirror=True), city.wires):
            ob = fn(); ob.location.y = y0; obs.append(ob)
    for k in range(2):
        ob = city.gantry(); ob.location.y = -44 + k * 22; obs.append(ob)
    sg = E.Mesher("tunnel_signal"); block_signal(sg, (-4.7, -4.0, GROUND + 0.1)); obs.append(sg.obj())
    obs += [hill(), trees(), portal()]
    if sakura_trees:
        for k, (x, y) in enumerate(((-15.5, -16.0), (17.0, -22.0), (-21.0, -4.0), (13.5, -34.0))):
            parts = BL.sakura("sakura_t%d" % k, seed=k + 11, height=7.0)
            for t in parts:
                if t.name.endswith("_shadow"):
                    E.delete(t)
                    continue
                t.location = (x, y, hill_height(x, y) - 0.15)
    # lined tunnel
    a = city.track(); a.location.y = 0.0; darken(a); obs.append(a)
    b = track_change(); b.location.y = SEG; darken(b); obs.append(b)
    for part in (0, 1):
        ob = tunnel_lined(part=part); ob.location.y = part * SEG; obs.append(ob)
    mo = tunnel_mouth(); mo.location.y = LINED; obs.append(mo)
    # Pongo's ore cart waits on the centre track where she boards it (Zones.BOARD m before the mouth)
    import vehicles as VH
    VH.mats()
    cart = VH.ore_cart(); cart.location = (0, LINED - BOARD, 0); obs.append(cart)
    # the cavern beyond
    obs += cave.cave_run(cave_segments, y0=LINED, seeds=(1, 2, 3), outlines=False)
    # render-only: a curtain in the cave's distance violet where the built cave ends, so the sky does not show through
    E.mat("cave_far", 0x3E3570, emis=1.0, rim=0.0, soft=0.0, outline=0, flags=E.F_NOCAST)
    end = E.Mesher("cave_end").mat("cave_far")
    ye = LINED + cave_segments * SEG
    end.poly([(-9, ye, -1), (9, ye, -1), (9, ye, 10), (-9, ye, 10)][::-1])
    end.obj()
    if outlines:
        for ob in obs:
            nm = ob.name
            if any(k in nm for k in ("portal", "signal", "gantry", "mouth", "cave_frame", "cave_deco", "cave_pipe", "trees",
                                     "cave_props", "ore_cart")):
                E.add_outline(ob, 0.02)
    return obs


def transition_lights(cave_segments=3):
    lights = cave.cave_lights(cave_segments, y0=LINED + 1.0)
    for (y, side) in ((3.0, -1), (9.0, 1), (15.0, -1), (21.0, 1)):
        ld = bpy.data.lights.new("tn_lamp", 'POINT')
        ld.energy = 60
        ld.color = E.hexrgb(0xFFE2B0)
        ob = bpy.data.objects.new("tn_lamp", ld)
        E.link(ob)
        ob.location = (side * (HALF_W - 0.5), y, 2.5)
        lights.append(ob)
    return lights


def design_transition(only=""):
    """The tunnel mouth from the cutting (daylight), and the view from inside the lining into the cavern."""
    E.reset()
    studio.stage(res=(1280, 720), floor=False)
    transition_scene()
    transition_lights()
    shots = {
        "transition_portal": dict(target=(0, 2, 4.6), dist=19, yaw=14, pitch=8, lens=30),
        "transition_approach": dict(target=(0, -4, 1.8), dist=9, yaw=0, pitch=6, lens=24),
        "transition_inside": dict(target=(0, 26, 1.6), dist=16, yaw=0, pitch=4, lens=24),
        "transition_mouth": dict(target=(0, 24, 3.0), dist=13, yaw=180 + 15, pitch=6, lens=24),
    }
    sun = studio._SUN[0]
    for name, kw in shots.items():
        if only and only not in name:
            continue
        # underground shots: no sun at all (EEVEE's cascades can leak it through the hill)
        sun.data.energy = 0.0 if name in ("transition_inside", "transition_mouth") else 4.0
        studio.shoot(name, light=name not in ("transition_inside", "transition_mouth"), **kw)


def export_transition():
    """build/models/*.erm for the transition pieces (LOD0 + LOD1) and the zone title cards. The game places them
    from the portal (src/com/endlessrush/core/ZoneWorld.java), turned round for the way out of the cavern."""
    for lod in (0, 1):
        sfx = "" if lod == 0 else "@1"
        E.reset(); city.city_mats(); cave.mats(); mats()
        E.export_erm(hill(lod), "tunnel_hill" + sfx)
        E.export_erm(trees(lod), "tunnel_trees" + sfx)
        E.export_erm(portal(lod), "tunnel_portal" + sfx)
        E.export_erm(cutting(lod), "cutting_r" + sfx)
        E.export_erm(cutting(lod, mirror=True), "cutting_l" + sfx)
        E.export_erm(tunnel_lined(lod, 0), "tunnel_lined_0" + sfx)
        E.export_erm(tunnel_lined(lod, 1), "tunnel_lined_1" + sfx)
        E.export_erm(tunnel_mouth(lod), "tunnel_mouth" + sfx)
        E.export_erm(track_change(lod), "track_change" + sfx)
        E.export_erm(city.track(lod), "city_track" + sfx)        # the Sakura Line track in the first lined part
    E.reset(); city.city_mats(); mats()
    sg = E.Mesher("tunnel_signal"); block_signal(sg, (0, 0, 0))
    E.export_erm(sg.obj(), "tunnel_signal")
    title_cards()
