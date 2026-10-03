"""
PONGO — heroine, built from scratch (polished anime / Genshin-like look).

Design: 16-year-old parkour runner from the Sakura Line. Navy hair fading to teal at the
tips, long low twin tails tied with orange bands (petite build and twin-tail silhouette in the
spirit of Hu Tao; outfit and colours are Pongo's own), long side locks, goggles pushed up on her head,
blue eyes, band-aid on her left cheek. Cropped white track jacket (blue sleeve stripes,
orange collar lining) over a black sports top, black shorts with an asymmetric orange wrap
panel, white knee socks with blue stripes, red high-top sneakers, fingerless gloves.

Techniques (from the tutorials studied):
  * head: lofted quad grid from designed profile curves, subdivided (JAEY head modelling);
    normals generated from object coordinates with a jaw bend (aVersionOfReality);
  * eyes/mouth: painted layered decals (iris gradient, streaks, double highlights, lash wings);
  * hair: tapered lens-section clumps along curves with clean loops, normals from a smooth
    hair-mass proxy, root-to-tip gradient UVs (aVersionOfReality flat hair method);
  * clothing: shells with real hem thickness and beveled rib bands (JAEY T-shirt);
  * shoes: separate overlapping sole / toe cap / upper / tongue, tori eyelets with dark holes,
    flat band laces (JAEY canvas shoes + laces);
  * secondary motion: spring bones for twin tails, side locks, wrap panel and charm.

Blender space: Z up, faces +Y, her right side is +X (her left cheek is at -X).
"""
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix, Euler
import erlib as E
import paint as PT
import studio
import characters as CH
import pongo4 as P4
import faces as FA

V = Vector

# GAME = True builds the in-game mesh: no subdivision on secondary parts (smooth custom normals carry the
# shape); design renders use subdivision everywhere for the showcase finish.
GAME = False


def SUB():
    return 0 if GAME else 1


COL = dict(
    skin=0xFFE6D6, skin_shade=0xF2B7A8, hair=0x22356E, hair_tip=0x37B4C8, hair_hi=0x8FD8F0,
    jacket=0xF7F8FC, jacket_blue=0x2F6BDA, orange=0xFF8A2A, top=0x24262E, shorts=0x343A5E,
    sock=0xFBFBFB, shoe=0xE8403A, sole=0xF7F4EC, glove=0x25272E, lens=0xFFA23A, frame=0xC9CED6,
    brow=0x2A3566, iris_top=0x0C2466, iris_mid=0x2F86E8, iris_bot=0xA8F0FF, pupil=0x081030)


# ============================================================================ face art

def _ccw(pts):
    a = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    return pts if a > 0 else pts[::-1]


def eye_g(name="d_eye_pongo_g", size=512, top=COL["iris_top"], mid=COL["iris_mid"], bot=COL["iris_bot"]):
    """Layered anime eye (outer corner at the right of the texture):
    almond white with lid shadow, tall gradient iris with ring, radial streaks and pupil,
    soft lower glow, two crisp highlights, thick upper lash line with outer wings,
    double-lid crease and a fine lower lash."""
    c = PT.Canvas(name, size, size)
    s = size / 256.0
    S = lambda pts: [(x * s, y * s) for (x, y) in pts]
    topc = FA._bez((30, 112), (66, 204), (176, 214), (232, 150), 28)
    botc = FA._bez((232, 150), (210, 70), (92, 50), (30, 112), 28)
    almond = _ccw(topc[:-1] + botc[:-1])
    A = S(almond)
    c.poly(A, 0xFFFFFF)
    # sclera shading: cool lid shadow at the top, a touch of warmth at the bottom
    band = FA._clip(S([(0, 140), (256, 162), (256, 256), (0, 256)]), A)
    if band:
        c.poly(band, 0xC9C8EA)
    band2 = FA._clip(S([(0, 168), (256, 186), (256, 256), (0, 256)]), A)
    if band2:
        c.poly(band2, 0xA9A6DA)
    icx, icy, irx, iry = 136, 122, 60, 80
    ringp = FA._clip(S(FA._ellipse(icx, icy, irx, iry, 72)), A)
    if ringp:
        c.poly(ringp, E.shade_hex(top, 0.7))
    ir = FA._clip(S(FA._ellipse(icx, icy, irx * 0.9, iry * 0.92, 72)), A)
    if ir:
        ys = [p[1] for p in ir]
        y0, y1 = min(ys), max(ys)
        cols = []
        for (x, y) in ir:
            t = (y - y0) / max(y1 - y0, 1e-6)
            col = E.mix_hex(bot, mid, min(1, t * 1.7)) if t < 0.55 else E.mix_hex(mid, top, min(1, (t - 0.55) / 0.4))
            cols.append((col, 1.0))
        c.gradient_poly(ir, cols)
        # radial streaks (iris fibres)
        for k in range(26):
            a = 2 * math.pi * k / 26 + 0.07 * math.sin(k * 3.1)
            r0, r1 = 0.36, 0.86
            p0 = (icx + math.cos(a) * irx * r0, icy + math.sin(a) * iry * r0)
            p1 = (icx + math.cos(a) * irx * r1, icy + math.sin(a) * iry * r1)
            seg = FA._clip(S([p0, (p0[0] + 0.6, p0[1] + 0.6), (p1[0] + 0.6, p1[1] + 0.6), p1]), A)
            c.stroke(S([p0, p1]), 2.2 * s, 0.6 * s, E.mix_hex(mid, 0xFFFFFF, 0.5) if k % 2 else E.shade_hex(top, 0.9),
                     0.35, cap=False)
        # mid ring around the pupil
        c.poly(FA._clip(S(FA._ellipse(icx, icy + 6, irx * 0.5, iry * 0.52, 48)), A) or S(FA._ellipse(icx, icy + 6, 1, 1)),
               E.mix_hex(top, mid, 0.4), 0.55)
    pu = FA._clip(S(FA._ellipse(icx, icy + 8, irx * 0.3, iry * 0.4, 48)), A)
    if pu:
        c.poly(pu, COL["pupil"])
    # soft glow at the bottom of the iris
    glow = FA._clip(S(FA._ellipse(icx + 4, icy - iry * 0.55, irx * 0.62, iry * 0.26, 48)), A)
    if glow:
        c.poly(glow, E.mix_hex(bot, 0xFFFFFF, 0.5), 0.6)
    # lid shadow over the top of the iris (darkens the upper third)
    lid = FA._clip(S([(0, 168), (256, 178), (256, 256), (0, 256)]), A)
    if lid:
        c.poly(lid, 0x2A1430, 0.38)
    # highlights: big soft-edged one up-left, small crisp one low-right, a tiny sparkle
    c.ellipse((icx - 24) * s, (icy + 34) * s, 19 * s, 14 * s, 0xFFFFFF, rot=-25)
    c.ellipse((icx + 28) * s, (icy - 28) * s, 8 * s, 6 * s, 0xFFFFFF, rot=-25)
    c.circle((icx - 4) * s, (icy - 40) * s, 4 * s, 0xFFF6D8, 0.9)
    # upper lash line: thick tapered band following the top lid, heavier toward the outer corner
    lash = 0x23171F
    up = S(topc)
    c.stroke(up, 6 * s, 15 * s, lash)
    # outer wings and lash spikes
    c.curve(S([(220, 156)])[0], S([(236, 166)])[0], S([(246, 180)])[0], S([(254, 196)])[0], 12 * s, 1.5 * s, lash)
    c.curve(S([(214, 160)])[0], S([(228, 166)])[0], S([(240, 168)])[0], S([(252, 166)])[0], 8 * s, 1.2 * s, lash)
    c.curve(S([(196, 178)])[0], S([(206, 190)])[0], S([(214, 198)])[0], S([(222, 206)])[0], 5 * s, 1 * s, lash)
    # inner-corner hook
    c.curve(S([(32, 114)])[0], S([(26, 110)])[0], S([(22, 104)])[0], S([(20, 98)])[0], 4 * s, 1 * s, lash)
    # double-lid crease
    crease = S(FA._bez((58, 186), (96, 222), (170, 228), (214, 188), 20))
    c.stroke(crease, 1.5 * s, 3.2 * s, 0x8A5C5C, 0.55)
    # fine lower lash (outer two thirds) with a couple of short spikes
    low = S(botc[:int(len(botc) * 0.6)])
    c.stroke(low, 3.5 * s, 1.0 * s, 0x5A3440, 0.85)
    for (x, y) in ((206, 100), (190, 90)):
        c.stroke(S([(x, y), (x + 6, y - 9)]), 2.5 * s, 0.6 * s, 0x5A3440, 0.8)
    return c.save()


def mouth_g(name="d_mouth_pongo_g", w=256, h=128, kind="open"):
    """Small anime mouth. open: little D-shaped smile with tongue; closed: soft curve with a lip hint."""
    c = PT.Canvas(name, w, h)
    line = 0x6A2830
    if kind == "open":
        top = FA._bez((70, 82), (100, 76), (156, 76), (186, 82), 20)
        bot = FA._bez((186, 82), (166, 30), (90, 30), (70, 82), 20)
        shape = _ccw(top[:-1] + bot[:-1])
        c.poly(shape, 0x9E3440)
        tg = FA._clip(FA._ellipse(128, 44, 34, 16, 40), shape)
        if tg:
            c.poly(tg, 0xF08A8E)
        c.poly(FA._clip([(70, 72), (186, 72), (186, 84), (70, 84)], shape) or [(0, 0), (1, 0), (1, 1)], 0xFFFFFF, 0.95)
        c.stroke(top, 5, 6, line)
        c.stroke(FA._bez((104, 30), (118, 24), (138, 24), (152, 30), 10), 3, 3, 0xE07A80, 0.6)
    else:
        c.curve((80, 74), (104, 60), (152, 60), (176, 74), 5, 5, line)
    return c.save()


def blush_g(name="d_blush_g", w=256, h=128):
    c = PT.Canvas(name, w, h)
    c.radial(128, 64, 0, 120, 0xFF8FA0, 0xFF8FA0, 0.5, 0.0, 64, 1.0, 0.45)
    for i in range(3):
        x = 96 + i * 26
        c.stroke([(x, 52), (x + 10, 78)], 4, 2, 0xF06A82, 0.4)
    return c.save()


def build_face_art():
    E.reset()
    eye_g()
    mouth_g()
    mouth_g("d_mouth_pongo_g_closed", kind="closed")
    blush_g()


# ============================================================================ proportions / head

class Girl(CH.Body):
    """Petite build (~6.3 heads, 1.50 m): slender limbs, narrow shoulders, big expressive head."""

    def __init__(self):
        super().__init__(h=1.50, sho_x=0.142, hip_x=0.084, head_r=0.118, girth=0.88)
        k = self.k
        self.headc = V((0.0, 0.012 * k, self.HEADC + 0.004))


HEAD_KEYS_G = [
    (-1.00, 0.10, 0.50, 0.05, 0.32, 2.4),
    (-0.975, 0.2, 0.555, 0.08, 0.30, 2.3),
    (-0.93, 0.305, 0.62, 0.13, 0.27, 2.15),
    (-0.86, 0.425, 0.69, 0.21, 0.22, 2.05),
    (-0.77, 0.56, 0.775, 0.33, 0.16, 2.0),
    (-0.65, 0.685, 0.85, 0.48, 0.10, 2.05),
    (-0.52, 0.775, 0.90, 0.66, 0.05, 2.1),
    (-0.36, 0.85, 0.93, 0.83, 0.01, 2.2),
    (-0.15, 0.89, 0.95, 0.97, -0.01, 2.2),
    (0.10, 0.90, 0.94, 1.03, -0.02, 2.1),
    (0.30, 0.875, 0.90, 1.04, -0.02, 2.0),
    (0.50, 0.81, 0.82, 0.98, -0.02, 2.0),
    (0.70, 0.68, 0.68, 0.83, -0.02, 2.0),
    (0.85, 0.52, 0.52, 0.64, -0.02, 2.0),
    (0.95, 0.33, 0.32, 0.39, -0.02, 2.0),
    (1.00, 0.0, 0.0, 0.0, -0.02, 2.0),
]


def mats():
    M = E.mat
    M("g_skin", COL["skin"], skin=1.0, rim=0.25, soft=0.08, shadow=0xE9A5A2)
    M("g_skin_detail", COL["skin"], skin=1.0, rim=0.0, soft=0.1, outline=0.0, shadow=0xE9A5A2)
    M("g_hair", 0xFFFFFF, "g_hair_grad", flags=E.F_HAIR, spec=0.05, rim=0.05, soft=0.05, shadow=0x7E86D8)
    M("g_hair_tie", COL["orange"], spec=0.3, rim=0.3, soft=0.08)
    M("g_brow", COL["brow"], rim=0.0, soft=0.05, outline=0.0)
    M("g_eye", 0xFFFFFF, "d_eye_pongo_g", flags=E.F_DECAL | E.F_NOCAST, outline=0, rim=0, spec=0, soft=0.02)
    M("g_mouth", 0xFFFFFF, "d_mouth_pongo_g", flags=E.F_DECAL | E.F_NOCAST, outline=0, rim=0, soft=0.02)
    M("g_blush", 0xFFFFFF, "d_blush_g", flags=E.F_DECAL | E.F_NOCAST, outline=0, rim=0)
    M("g_bandaid", 0xF6DDBE, outline=0.0, rim=0.1, soft=0.1)
    M("g_bandaid_pad", 0xEBCBA3, outline=0.0, rim=0.0, soft=0.1)


def hair_gradient(name="g_hair_grad", w=128, h=512):
    """v = 0 at the root, 1 at the tip: navy -> teal, faint strand lines, and a jagged 'angel ring'
    highlight band at v 0.16..0.26 (shows as a ring around the head on the scalp clumps)."""
    import numpy as np
    import texgen as T
    v = np.linspace(0, 1, h)[:, None]
    t = np.clip((v - 0.5) / 0.5, 0, 1) ** 1.4
    a, b = T.rgb(COL["hair"]), T.rgb(COL["hair_tip"])
    img = a[None, None, :] * (1 - t[..., None]) + b[None, None, :] * t[..., None]
    img = np.repeat(img, w, 1)
    xs = np.arange(w)[None, :].astype(float)
    strands = 0.05 * np.sin(xs / w * 2 * math.pi * 5 + 0.7) + 0.03 * np.sin(xs / w * 2 * math.pi * 13)
    img = img * (1 + strands[..., None])
    # angel ring: band with zig-zag edges, brightest in the middle of the clump (u ~ 0.5)
    zig = 0.012 * np.sin(xs / w * 2 * math.pi * 7) + 0.008 * np.sin(xs / w * 2 * math.pi * 17 + 1.0)
    lo, hi = 0.17 + zig, 0.245 - zig * 0.6
    band = ((v >= lo) & (v <= hi)).astype(float)
    centre = np.exp(-((xs / w - 0.5) / 0.3) ** 2)
    hl = T.rgb(COL["hair_hi"])
    k = (band * (0.55 + 0.45 * centre))[..., None]
    img = img * (1 - k * 0.75) + hl[None, None, :] * k * 0.75
    T.write_png(name, img[::-1])


def head(B):
    hd = P4.head4(B, "g_skin", "pongo_head", rings=36, seg=44, keys=HEAD_KEYS_G)
    P4.face_normals_gfn(hd, B, bend=8.0, bend_top=-0.5, xs_mid=1.04, xs_low=0.93, width=0.9, flat_z=0.35)
    return hd


def face(B, hd):
    """Eyes, brows, mouth, blush, nose tip and the band-aid on her left cheek."""
    bvh = CH.bvh_of(hd)
    c = B.headc
    r = B.head_r
    m = E.Mesher("pongo_face")
    eye_w, eye_h, eye_x, eye_z = 0.092, 0.086, 0.045, -0.034
    m.mat("g_eye")
    for side in (1, -1):
        CH.project_decal(m, bvh, side * eye_x, c.z + eye_z, eye_w, eye_h, 9, 9, off=0.0012, mirror=(side < 0))
    m.mat("g_mouth")
    CH.project_decal(m, bvh, 0.0, c.z - 0.088, 0.034, 0.017, 7, 4, off=0.0012)
    m.mat("g_blush")
    for side in (1, -1):
        CH.project_decal(m, bvh, side * 0.054, c.z - 0.06, 0.036, 0.018, 7, 5, off=0.0009)
    # brows: thin tapered strokes, gently arched, slightly raised (energetic)
    m.mat("g_brow")
    for side in (1, -1):
        pts2 = []
        for i in range(9):
            t = i / 8
            x = side * (eye_x - eye_w * 0.38 + t * eye_w * 0.86)
            z = c.z + eye_z + eye_h * 0.66 + 0.011 * math.sin(math.pi * (0.15 + 0.85 * t)) - 0.003 * t
            pts2.append((x, z))
        path = CH.surface_path(bvh, pts2, 0.0015)
        m.sweep(path, [(-1, -0.3), (1, -0.3), (1, 0.3), (-1, 0.3)], closed=True, cap=True,
                scale=lambda t: (0.0034 * (1.0 - 0.7 * t) + 0.0005, 0.003), up=(0, 1, 0))
    # nose: tiny soft tip, reads as a single small highlight/shadow
    m.mat("g_skin_detail")
    m.push(CH.surface_frame(bvh, 0.0, c.z - 0.06, -0.0006))
    m.sweep([(0, 0, 0.008), (0, 0.0022, 0.002), (0, 0.004, -0.002), (0, 0.0025, -0.004)],
            [(math.cos(2 * math.pi * k / 8), math.sin(2 * math.pi * k / 8) * 0.8) for k in range(8)],
            closed=True, cap=True, scale=lambda t: 0.0008 + 0.0026 * t ** 1.5, up=(0, 1, 0))
    m.pop()
    # band-aid on HER left cheek (-X), below the eye, slight tilt
    # band-aid: a strip projected onto the cheek (follows the surface), pad in the middle
    m.mat("g_bandaid")
    bf = CH.project_decal(m, bvh, -0.05, c.z - 0.077, 0.027, 0.0095, 7, 3, off=0.0011,
                          curve_z=lambda u: (u - 0.5) * 0.007)
    m.mat("g_bandaid_pad")
    CH.project_decal(m, bvh, -0.05, c.z - 0.077, 0.0085, 0.007, 3, 3, off=0.0016)
    return m.obj("pongo_face", smooth_angle=60)


# ============================================================================ design renders

def design_head():
    E.reset()
    hair_gradient()
    studio.stage(res=(1200, 1200))
    B = Girl()
    mats()
    hd = head(B)
    ear = P4.ears(B, "g_skin")
    fc = face(B, hd)
    for o in (hd, ear):
        E.add_outline(o, 0.0018)
    c = B.headc
    studio.shoot("g_head_front", target=(0, 0.05, c.z - 0.01), dist=0.9, yaw=180, pitch=2, lens=70)
    studio.shoot("g_head_34", target=(0, 0.05, c.z - 0.01), dist=0.9, yaw=215, pitch=4, lens=70)
    studio.shoot("g_head_side", target=(0, 0.0, c.z - 0.01), dist=0.9, yaw=270, pitch=2, lens=70)


# ============================================================================ hair

def scalp(B, th_deg, z, off=0.0):
    """World point on the head surface (azimuth th: 0 front, +90 her right; z in units of r),
    pushed out along the surface normal by `off` (metres). Returns (point, normal)."""
    r, c = B.head_r, B.headc
    th = math.radians(th_deg)
    z = max(-1.0, min(0.995, z))
    p = P4.head_pt(z, th, HEAD_KEYS_G)
    e = 0.01
    pt = P4.head_pt(z, th + e, HEAD_KEYS_G) - P4.head_pt(z, th - e, HEAD_KEYS_G)
    pz = P4.head_pt(min(0.999, z + e), th, HEAD_KEYS_G) - P4.head_pt(max(-1.0, z - e), th, HEAD_KEYS_G)
    n = pt.cross(pz)
    if n.length < 1e-9 or n.dot(p - V((0, 0, 0))) < 0:
        n = -n if n.length > 1e-9 else V((math.sin(th), math.cos(th), 0))
    n.normalize()
    return c + p * r + n * off, n


LENS = [(1.0, 0.0), (0.8, 0.36), (0.45, 0.8), (0.0, 1.0), (-0.45, 0.8), (-0.8, 0.36),
        (-1.0, 0.0), (-0.8, -0.26), (-0.45, -0.55), (0.0, -0.66), (0.45, -0.55), (0.8, -0.26)]


def clump(m, pts, nrms, width, thick, v0=0.0, v1=1.0, tip=True, root_cap=True, vs=None):
    """Hair clump: lens-section strand along pts. width(t)/thick(t) in metres (t: 0 root .. 1 tip).
    nrms: per-point 'outward' direction (the flat of the lens faces it). UVs: u around, v root->tip."""
    bm = m.bm
    n = len(pts)
    rings = []
    for i, p in enumerate(pts):
        t = i / (n - 1)
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, n - 1)]
        T = (b - a).normalized()
        N = nrms[i] - T * nrms[i].dot(T)
        if N.length < 1e-6:
            N = V((0, 0, 1))
        N.normalize()
        X = T.cross(N).normalized()
        w, th = width(t), thick(t)
        ring = [bm.verts.new(m.M @ (p + X * (px * w) + N * (py * th))) for (px, py) in LENS]
        rings.append(ring)
    k = len(LENS)
    faces = []
    for i in range(n - 1):
        for j in range(k):
            jj = (j + 1) % k
            f = bm.faces.new((rings[i][j], rings[i + 1][j], rings[i + 1][jj], rings[i][jj]))   # outward winding
            faces.append((f, i, j))
    for (f, i, j) in faces:
        f.material_index = m.mi
        f.smooth = True
        for l in f.loops:
            vi = None
            for ii in (i, i + 1):
                if l.vert in rings[ii]:
                    vi = ii
                    jj = rings[ii].index(l.vert)
                    break
            uu = jj / k
            if jj == 0 and j == k - 1:
                uu = 1.0
            l[m.uv].uv = (0.1 + 0.8 * uu, vs[vi] if vs else v0 + (v1 - v0) * vi / (n - 1))
            l[m.col] = m.tint
    caps = []
    if root_cap:
        caps.append(bm.faces.new(rings[0]))
    if tip:
        caps.append(bm.faces.new(list(reversed(rings[-1]))))
    for f in caps:
        f.material_index = m.mi
        f.smooth = True
        for l in f.loops:
            l[m.uv].uv = (0.5, (vs[0] if vs else v0) if (f is caps[0] and root_cap) else (vs[-1] if vs else v1))
            l[m.col] = m.tint
    return rings


def ring_v(z):
    """Texture v for scalp hair from head height (units of r): the angel-ring band (v 0.17..0.245)
    lands at z 0.62..0.5 on every clump, the gradient reaches teal only below the jaw line."""
    return max(0.0, min(1.0, 0.17 + 0.625 * (0.62 - z)))


def _ease(t):
    return t * t * (3 - 2 * t)


def scalp_clump(m, B, th0, z0, th1, z1, w0, thick=0.011, off0=0.003, off_mid=0.012, off1=0.008, n=12,
                curl=0.0, taper=1.3, extra=None, v0=0.0, v1=1.0):
    """A clump that hugs the head from (th0, z0) to (th1, z1), lifting off the surface in the middle."""
    pts, nrms, zs = [], [], []
    for i in range(n):
        t = i / (n - 1)
        th = th0 + (th1 - th0) * _ease(t)
        z = z0 + (z1 - z0) * t
        off = off0 + (off_mid - off0) * math.sin(math.pi * min(1.0, t * 1.3)) * (1 - t) + (off1 - off0) * t * t
        p, nn = scalp(B, th, z, off)
        if curl:
            p = p - nn * curl * t ** 3            # tip curls in toward the face
        if extra:
            p = p + extra(t)
        pts.append(p)
        nrms.append(nn)
        zs.append(z)
    vs = [ring_v(z) for z in zs]
    clump(m, pts, nrms, lambda t: w0 * max(0.04, (1 - t ** taper)) * (0.92 + 0.08 * math.sin(math.pi * t)),
          lambda t: thick * max(0.15, 1 - 0.75 * t), vs=vs)


def hairline(th):
    """z (units of r) where the hair cap ends, by azimuth (deg)."""
    a = abs(((th + 180) % 360) - 180)
    if a < 60:
        return 0.48 - 0.25 * (a / 60) ** 2
    if a < 115:
        return 0.23 - 0.55 * ((a - 60) / 55)            # temples to just behind the ear front
    return -0.32 - 0.52 * ((a - 115) / 65) ** 1.4      # behind the ears down to the nape


def hair_cap(m, B, off=0.008, seg=48, rows=18):
    bm = m.bm
    grid = []
    for j in range(rows):
        s = j / (rows - 1)
        row = []
        for i in range(seg):
            th = -180 + 360 * i / seg
            z = 0.985 - s * (0.985 - hairline(th))
            p, nn = scalp(B, th, z, off + 0.002 * (1 - s))
            row.append(bm.verts.new(m.M @ p))
        grid.append(row)
    top_p, _ = scalp(B, 0, 0.999, off)
    top = bm.verts.new(m.M @ (B.headc + V((0, -0.02 * B.head_r, B.head_r + off))))
    faces = []
    for j in range(rows - 1):
        for i in range(seg):
            ii = (i + 1) % seg
            faces.append(bm.faces.new((grid[j][i], grid[j + 1][i], grid[j + 1][ii], grid[j][ii])))
    for i in range(seg):
        faces.append(bm.faces.new((top, grid[0][i], grid[0][(i + 1) % seg])))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    for f in faces:
        f.material_index = m.mi
        f.smooth = True
        for l in f.loops:
            l[m.uv].uv = (0.5, 0.08)
            l[m.col] = m.tint


def hair_front(m, B):
    """Bangs (two layers), side bangs and long side locks that frame the face."""
    # main bang layer: (th_root, th_tip, z_tip, width) - longer centre clump between the eyes
    bangs = [(-50, -58, -0.12, 0.05), (-30, -27, 0.06, 0.054), (-11, -5, -0.2, 0.05),
             (9, 13, 0.02, 0.052), (29, 33, -0.04, 0.054), (50, 58, -0.1, 0.05)]
    bangs += [(-19, -16, 0.02, 0.03), (20, 23, 0.06, 0.03)]
    for (a0, a1, zt, w) in bangs:
        scalp_clump(m, B, a0, 0.8, a1, zt, w, thick=0.014, off0=0.008, off_mid=0.028, off1=0.016, curl=0.006,
                    taper=2.2, v1=0.62)
    # under layer to fill the gaps (shorter, thinner)
    for (a0, a1, zt, w) in ((-40, -44, 0.16, 0.04), (-20, -17, 0.12, 0.04), (0, 3, 0.1, 0.04),
                            (19, 22, 0.14, 0.04), (39, 44, 0.16, 0.04)):
        scalp_clump(m, B, a0, 0.76, a1, zt, w, thick=0.011, off0=0.006, off_mid=0.02, off1=0.01, taper=2.0, v1=0.55)
    # side bangs sweeping past the eyes to the cheek
    for side in (1, -1):
        scalp_clump(m, B, side * 68, 0.6, side * 80, -0.6, 0.04, thick=0.011, off0=0.004, off_mid=0.016, off1=0.013,
                    curl=0.007, taper=1.8, v1=0.7)
    # long side locks in front of the ears, falling to the chest
    for side in (1, -1):
        for (a, w, L, ph) in ((84, 0.036, 0.30, 0.0), (95, 0.026, 0.25, 0.8)):
            pts, nrms = [], []
            for i in range(16):
                t = i / 15
                if t < 0.35:
                    z = 0.35 - (0.35 + 0.55) * (t / 0.35)
                    p, nn = scalp(B, side * (a + 6 * t), z, 0.008 + 0.02 * t)
                else:
                    u = (t - 0.35) / 0.65
                    base, nn = scalp(B, side * (a + 2.1), -0.55, 0.015)
                    p = base + V((side * (0.012 * u + 0.006 * math.sin(u * 3 + ph)), 0.022 * u - 0.008 * u * u, -L * u))
                    nn = V((side * 0.9, 0.35, 0)).normalized()
                pts.append(p)
                nrms.append(nn)
            clump(m, pts, nrms, lambda t, w=w: w * max(0.05, 1 - t ** 2.2) * (1 + 0.15 * math.sin(math.pi * t)),
                  lambda t: 0.011 * max(0.2, 1 - 0.7 * t))


def tie_point(B, side):
    p, nn = scalp(B, side * 122, -0.4, 0.03)
    return p, nn


def hair_back(m, B):
    """Back of the head: two hugging layers from crown to nape (no gaps), crown fill and the ahoge."""
    for a in range(100, 261, 16):
        a2 = a + (a - 180) * 0.12
        scalp_clump(m, B, a, 0.9, a2, -0.98, 0.06, thick=0.013, off0=0.009, off_mid=0.022, off1=0.018, taper=2.5,
                    v1=0.6)
    for a in range(108, 253, 16):
        scalp_clump(m, B, a, 0.6, a + (a - 180) * 0.2, -1.1, 0.045, thick=0.011, off0=0.01, off_mid=0.02, off1=0.022,
                    taper=1.8, v1=0.7)
    for a in (-150, -110, -70, -35, 0, 35, 70, 110, 150, 180):
        scalp_clump(m, B, a, 0.99, a, 0.66 if abs(a) < 90 else 0.45, 0.065, thick=0.012, off0=0.01, off_mid=0.02,
                    off1=0.016, taper=3.0, v1=0.35)
    base, nn = scalp(B, 12, 0.95, 0.004)
    path = [V(p) for p in E.bezier(base, base + V((0, 0.006, 0.045)), base + V((0, 0.05, 0.07)), base + V((0, 0.07, 0.035)), 14)]
    clump(m, path, [V((1, 0, 0))] * len(path), lambda t: 0.01 * (1 - t) ** 0.8 + 0.0008, lambda t: 0.0035 * (1 - 0.6 * t),
          v0=0.0, v1=0.6)


def tail_axis(B, side, length=0.62, n=7):
    """Centre line of a twin tail (also the dyn bone chain)."""
    tp, tn = tie_point(B, side)
    pts = []
    for i in range(n):
        t = i / (n - 1)
        out = side * (0.035 * math.sin(min(1.0, t * 2.5) * math.pi * 0.5) + 0.02 * t)
        pts.append(tp + V((out, -0.03 * math.sin(t * math.pi) - 0.01 * t, -length * t ** 1.05)))
    return pts


def twin_tails(m, B, length=0.62):
    for side in (1, -1):
        axis = tail_axis(B, side, length, 24)
        # 5 clumps around the axis with different phase/length -> full, tapered bundle
        spec = [(0, 0.064, 1.0), (60, 0.058, 0.94), (120, 0.056, 0.86), (180, 0.06, 0.97), (240, 0.054, 0.9), (300, 0.056, 0.82)]
        for (ang, w, Lf) in spec:
            a = math.radians(ang)
            pts, nrms = [], []
            cnt = int(24 * Lf)
            for i in range(cnt):
                t = i / (cnt - 1)
                q = axis[min(i, len(axis) - 1)]
                T = (axis[min(i + 1, len(axis) - 1)] - axis[max(i - 1, 0)]).normalized()
                X = V((1, 0, 0)) - T * T.x
                X.normalize()
                Y = T.cross(X).normalized()
                rad = 0.03 * math.sin(math.pi * min(1.0, 0.12 + t * 0.95)) + 0.006
                d = X * math.cos(a) + Y * math.sin(a)
                wob = 0.006 * math.sin(t * 6 + ang)
                pts.append(q + d * (rad + wob))
                nrms.append(d)
            clump(m, pts, nrms, lambda t, w=w: w * (0.55 + 0.45 * math.sin(math.pi * min(1.0, 0.25 + t * 0.9))) * max(0.03, 1 - t ** 3),
                  lambda t: 0.018 * max(0.25, 1 - 0.6 * t), v0=0.35, v1=1.0)


def hair_ties(m, B):
    m.mat("g_hair_tie")
    for side in (1, -1):
        tp, tn = tie_point(B, side)
        axis = tail_axis(B, side, 0.62, 7)
        d = (axis[1] - axis[0]).normalized()
        R = d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        m.push(Matrix.Translation(tp + d * 0.012) @ R)
        m.torus((0, 0, 0), R=0.024, r=0.009, seg=24, sides=10)
        m.pop()
        # small blue bead charm on a short string
        E.mat("g_bead", COL["jacket_blue"], spec=0.8, rim=0.4, soft=0.05, outline=0.5)
        m.mat("g_bead")
        m.sphere(tuple(tp + d * 0.012 + V((side * 0.022, -0.006, -0.03))), 0.008, 12, 8)
        m.mat("g_hair_tie")


def build_hair(B):
    m = E.Mesher("pongo_hair").mat("g_hair")
    hair_cap(m, B)
    hair_front(m, B)
    hair_back(m, B)
    ob = m.obj("pongo_hair", smooth_angle=180)
    if SUB():
        sub = ob.modifiers.new("subsurf", 'SUBSURF')
        sub.levels = SUB()
        E.apply_modifiers(ob)
    # hair-mass normals: the scalp hair shades as one clean volume (partial transfer keeps clump edges)
    proxy = E.proxy_ellipsoid("pongo_hair_proxy", B.headc + V((0, -0.008, 0.012)),
                              (B.head_r * 1.16, B.head_r * 1.2, B.head_r * 1.18))
    E.transfer_normals(ob, proxy, 0.8)
    E.apply_modifiers(ob)
    tm = E.Mesher("pongo_tails").mat("g_hair")
    twin_tails(tm, B)
    tails = tm.obj("pongo_tails", smooth_angle=180, subsurf=SUB())
    E.apply_modifiers(tails)
    tie = E.Mesher("pongo_ties")
    hair_ties(tie, B)
    ties = tie.obj("pongo_ties", smooth_angle=60)
    return ob, tails, ties


def design_hair():
    E.reset()
    hair_gradient()
    studio.stage(res=(1200, 1200))
    B = Girl()
    mats()
    hd = head(B)
    ear = P4.ears(B, "g_skin")
    fc = face(B, hd)
    hair, tails, ties = build_hair(B)
    for o in (hd, ear, hair, tails, ties):
        E.add_outline(o, 0.0018)
    c = B.headc
    studio.shoot("g_hair_front", target=(0, 0.05, c.z - 0.03), dist=1.1, yaw=180, pitch=3, lens=60)
    studio.shoot("g_hair_34", target=(0, 0.05, c.z - 0.03), dist=1.1, yaw=215, pitch=6, lens=60)
    studio.shoot("g_hair_back", target=(0, 0.0, c.z - 0.2), dist=1.8, yaw=20, pitch=8, lens=50)
    studio.shoot("g_hair_side", target=(0, 0.0, c.z - 0.2), dist=1.8, yaw=270, pitch=4, lens=50)


# ============================================================================ body

def body_mats():
    M = E.mat
    M("g_top", COL["top"], rim=0.35, soft=0.08, spec=0.15)
    M("g_top_trim", COL["jacket_blue"], rim=0.3, soft=0.08)
    M("g_jacket", COL["jacket"], rim=0.3, soft=0.1, shadow=0xB8B4E0)
    M("g_jacket_blue", COL["jacket_blue"], rim=0.3, soft=0.1)
    M("g_jacket_lining", COL["orange"], rim=0.2, soft=0.1)
    M("g_zip", 0xC9CED6, spec=0.8, rim=0.4, soft=0.05, flags=E.F_METAL, outline=0.5)
    M("g_shorts", COL["shorts"], rim=0.35, soft=0.08)
    M("g_belt", COL["orange"], rim=0.3, soft=0.08)
    M("g_buckle", 0xD8DCE3, spec=0.9, rim=0.4, soft=0.05, flags=E.F_METAL, outline=0.6)
    M("g_wrap", COL["orange"], rim=0.3, soft=0.1, flags=E.F_DOUBLE)
    M("g_wrap_trim", 0xFFF4E6, rim=0.3, soft=0.1, flags=E.F_DOUBLE)
    M("g_sock", COL["sock"], rim=0.25, soft=0.1)
    M("g_sock_stripe", COL["jacket_blue"], rim=0.25, soft=0.1)
    M("g_glove", COL["glove"], spec=0.25, rim=0.35, soft=0.06)
    M("g_glove_strap", COL["orange"], rim=0.3, soft=0.08)
    M("g_choker", COL["top"], rim=0.3, soft=0.08)
    M("g_charm", COL["orange"], spec=0.6, rim=0.3, soft=0.05)


TORSO_KEYS = [
    # z      w      f      b      cy
    (0.66, 0.122, 0.074, 0.088, 0.000),
    (0.71, 0.131, 0.078, 0.096, 0.000),
    (0.76, 0.128, 0.076, 0.094, 0.000),
    (0.81, 0.115, 0.070, 0.082, 0.002),
    (0.86, 0.098, 0.066, 0.072, 0.004),
    (0.91, 0.100, 0.068, 0.072, 0.006),
    (0.96, 0.108, 0.072, 0.074, 0.008),
    (1.01, 0.114, 0.078, 0.076, 0.010),
    (1.06, 0.118, 0.080, 0.078, 0.010),
    (1.11, 0.122, 0.076, 0.078, 0.008),
    (1.15, 0.124, 0.068, 0.074, 0.004),
    (1.18, 0.104, 0.056, 0.062, 0.000),
    (1.205, 0.06, 0.042, 0.046, -0.002),
    (1.22, 0.042, 0.036, 0.038, -0.003),
]


def bust(z):
    return 0.028 * math.exp(-((z - 1.045) / 0.045) ** 2)


def torso_ring(z, n, grow=0.0, keys=TORSO_KEYS):
    w, f, b, cy = P4.catmull(keys, z)
    pts = []
    for i in range(n):
        th = 2 * math.pi * i / n
        s, c = math.sin(th), math.cos(th)
        p = 2.4 if c > 0 else 2.2
        x = (w + grow) * math.copysign(abs(s) ** (2.0 / p), s)
        y = ((f if c > 0 else b) + grow) * math.copysign(abs(c) ** (2.0 / p), c) + cy
        a = abs(th if th <= math.pi else th - 2 * math.pi)
        y += bust(z) * math.exp(-((a - 0.52) / 0.33) ** 2) * (1 if c > 0 else 0)
        x += math.copysign(bust(z) * 0.25 * math.exp(-((a - 0.7) / 0.35) ** 2), s)
        # shoulder blades and spine groove (back)
        if c < 0:
            y -= 0.006 * math.exp(-((z - 1.1) / 0.06) ** 2) * math.exp(-((a - 2.6) / 0.3) ** 2)
            y += 0.003 * math.exp(-(a - math.pi) ** 2 / 0.02)
        pts.append((x, y, z))
    return pts


def loft(m, rings, cap0=False, cap1=False, vgrid=None):
    """Quad loft through rings (closed). vgrid: optional per-ring v for UVs."""
    faces = m.quad_strip(rings, closed=True, cap0=cap0, cap1=cap1, uv='box', smooth=True)
    return faces


def sports_top(m, B, n=36):
    """Fitted black sports top from the hips to the neck (high round neck), thin blue piping."""
    zs = [0.80 + (1.215 - 0.80) * i / 20 for i in range(21)]
    rings = [torso_ring(z, n, 0.004) for z in zs]
    m.mat("g_top")
    fs = loft(m, rings, cap0=False, cap1=False)
    # piping band at the neckline and hem
    ti = m.mats.index("g_top_trim") if "g_top_trim" in m.mats else (m.mats.append("g_top_trim") or len(m.mats) - 1)
    for f in fs:
        z = f.calc_center_median().z
        if z > 1.198 or z < 0.812:
            f.material_index = ti
    return fs


def neck_g(m, B):
    m.mat("g_skin")
    CH.limb(m, [V((0, -0.004, 1.17)), V((0, -0.002, 1.215)), V((0, 0.0, 1.26)), V((0, 0.006, 1.3))],
            [(0.042, 0.04), (0.034, 0.033), (0.031, 0.031), (0.03, 0.03)], n=20)


def choker(m, B):
    m.mat("g_choker")
    m.torus((0, -0.001, 1.235), R=0.0335, r=0.0042, seg=36, sides=8)
    m.mat("g_charm")
    # small orange star charm hanging at the front
    m.push(Matrix.Translation((0, 0.036, 1.222)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
    m.extrude(E.star_pts(5, 0.009, 0.0042), 0.003, bevel=(0.0008, 1))
    m.pop()
    m.mat("g_zip")
    m.torus((0, 0.0355, 1.2315), R=0.0025, r=0.0008, seg=10, sides=4, axis='Y')


def arms_g(m, B):
    """Upper arm (under the sleeve) and forearm skin, slim and tapered."""
    for side in (1, -1):
        sh = B.mirror(B.shoulder, side)
        el = B.mirror(B.elbow, side)
        w = B.mirror(B.wrist, side)
        d = (w - el).normalized()
        m.mat("g_skin")
        pts = [sh + V((-side * 0.015, 0, 0)), sh.lerp(el, 0.35), sh.lerp(el, 0.7), el, el.lerp(w, 0.25), el.lerp(w, 0.55),
               el.lerp(w, 0.85), w + d * 0.006]
        rad = [0.042, 0.038, 0.033, 0.03, 0.031, 0.028, 0.024, 0.022]
        CH.limb(m, pts, [(r, r * 0.92) for r in rad], n=18)


def legs_g(m, B):
    """Thighs to ankles: soft thigh, knee, calf and slim ankle."""
    for side in (1, -1):
        h = B.mirror(B.hipj, side)
        k = B.mirror(B.knee, side)
        a = B.mirror(B.ankle, side)
        m.mat("g_skin")
        pts = [h + V((side * 0.008, 0, 0.04)), h.lerp(k, 0.25), h.lerp(k, 0.55), h.lerp(k, 0.85), k, k.lerp(a, 0.15),
               k.lerp(a, 0.35), k.lerp(a, 0.6), k.lerp(a, 0.85), a + V((0, 0, 0.012))]
        rad = [(0.072, 0.068), (0.066, 0.064), (0.056, 0.054), (0.045, 0.044), (0.042, 0.043), (0.042, 0.044),
               (0.043, 0.047), (0.036, 0.038), (0.029, 0.029), (0.026, 0.027)]
        CH.limb(m, pts, rad, n=20)


def socks_g(m, B):
    """White knee socks with two blue stripes (exact ring edges) and a ribbed rolled top."""
    for side in (1, -1):
        k = B.mirror(B.knee, side)
        a = B.mirror(B.ankle, side)
        top = k.lerp(a, 0.12)
        L = (top - a).length
        d = (top - a).normalized()
        stripes = [(top.z - 0.03, top.z - 0.02), (top.z - 0.05, top.z - 0.04)]
        cuts = sorted(set([0.0, 0.2, 0.45, 0.62, 0.75, 0.85] + [((z - a.z) / (top.z - a.z)) for st in stripes for z in st] + [1.0]))
        prof = [(0.0, 0.031), (0.2, 0.0315), (0.45, 0.039), (0.7, 0.0465), (0.85, 0.047), (1.0, 0.047)]
        def rad(t):
            for i in range(len(prof) - 1):
                if prof[i][0] <= t <= prof[i + 1][0]:
                    u = (t - prof[i][0]) / (prof[i + 1][0] - prof[i][0])
                    return prof[i][1] + (prof[i + 1][1] - prof[i][1]) * u
            return prof[-1][1]
        pts = [a.lerp(top, t) for t in cuts]
        m.mat("g_sock")
        fs = CH.limb(m, pts, [(rad(t), rad(t) * 1.04) for t in cuts], n=22, cap=False)
        si = m.mats.index("g_sock_stripe") if "g_sock_stripe" in m.mats else (m.mats.append("g_sock_stripe") or len(m.mats) - 1)
        for f in fs:
            z = f.calc_center_median().z
            for (z0, z1) in stripes:
                if z0 < z < z1:
                    f.material_index = si
        m.mat("g_sock")
        m.torus(tuple(top), R=0.0475, r=0.0042, seg=28, sides=8)


def shorts_g(m, B, n=40):
    """Low-rise shorts: hip shell + two leg tubes merged visually by overlap; belt with buckle."""
    zs = [0.70 + (0.875 - 0.70) * i / 8 for i in range(9)]
    rings = [torso_ring(z, n, 0.008) for z in zs]
    m.mat("g_shorts")
    loft(m, rings, cap0=False, cap1=False)
    for side in (1, -1):
        h = B.mirror(B.hipj, side)
        k = B.mirror(B.knee, side)
        top = h + V((side * 0.012, 0, 0.02))
        bot = h.lerp(k, 0.3)
        d = (bot - top).normalized()
        fs = CH.limb(m, [top, top.lerp(bot, 0.5), bot - d * 0.01, bot], [(0.08, 0.076), (0.077, 0.074), (0.074, 0.072), (0.075, 0.073)],
                     n=24, cap=False)
        # hem cuff
        m.torus(tuple(bot), R=0.074, r=0.005, seg=28, sides=8, axis='Z')
    # belt: orange band + metal buckle + belt loops
    m.mat("g_belt")
    m.quad_strip([torso_ring(0.86, n, 0.014), torso_ring(0.885, n, 0.014)], closed=True)
    m.quad_strip([torso_ring(0.885, n, 0.014), torso_ring(0.885, n, 0.008)], closed=True)
    m.quad_strip([torso_ring(0.86, n, 0.008), torso_ring(0.86, n, 0.014)], closed=True)
    w, f, b, cy = P4.catmull(TORSO_KEYS, 0.872)
    m.mat("g_buckle")
    m.push(Matrix.Translation((0.0, cy + f + 0.016, 0.8725)))
    m.extrude(E.rounded_rect(0.036, 0.026, 0.005, 3), 0.004, holes=[E.rounded_rect(0.024, 0.014, 0.003, 3)[::-1]],
              bevel=(0.0008, 1), c=(0, 0, 0)) if False else None
    m.rbox((0, 0, 0), (0.036, 0.006, 0.026), 0.003, 2)
    m.mat("g_belt")
    m.box((0, 0.0032, 0), (0.024, 0.002, 0.014), smooth=False)
    m.pop()


def wrap_panel(B, n=14):
    """Asymmetric wrap panel on her left hip (-X): orange cloth with a cream hem, hanging to mid-thigh.
    Built as a curved sheet around the hip; weighted to a dyn chain for motion."""
    m = E.Mesher("pongo_wrap")
    rows = []
    for j in range(8):
        v = j / 7
        z = 0.86 - 0.26 * v
        ring = []
        for i in range(n):
            u = i / (n - 1)
            th = math.radians(-135 + 90 * u)         # from back-left round to front-left (her left = -X)
            w, f, b, cy = P4.catmull(TORSO_KEYS, max(0.70, z))
            grow = 0.02 + 0.03 * v
            x = (w + grow) * math.sin(th)
            y = ((f if math.cos(th) > 0 else b) + grow) * math.cos(th) + cy
            # flare at the hem, diagonal hem line (longer at the back)
            zz = z - 0.05 * v * (1 - u)
            ring.append((x * (1 + 0.12 * v), y * (1 + 0.1 * v), zz))
        rows.append(ring)
    m.mat("g_wrap")
    fs = m.quad_strip(rows, closed=False)
    ti = m.mats.index("g_wrap_trim") if "g_wrap_trim" in m.mats else (m.mats.append("g_wrap_trim") or len(m.mats) - 1)
    bottom = min(f.calc_center_median().z for f in fs)
    for f in fs:
        vs = [l.vert for l in f.loops]
    # hem trim: last row of faces
    for f in fs:
        if all(any((V(p) - lv.co).length < 1e-5 for p in rows[-1]) or any((V(p) - lv.co).length < 1e-5 for p in rows[-2]) for lv in f.verts):
            f.material_index = ti
    ob = m.obj("pongo_wrap", smooth_angle=180)
    so = ob.modifiers.new("solid", 'SOLIDIFY')
    so.thickness = 0.003
    so.offset = 1.0
    if SUB():
        sub = ob.modifiers.new("sub", 'SUBSURF')
        sub.levels = 1
    E.apply_modifiers(ob)
    return ob


def jacket(B, n=40):
    """Cropped open track jacket: body shell (open at the front), stand collar with orange lining,
    sleeves to the elbow with blue side stripes and rolled cuffs. Real thickness (solidify)."""
    m = E.Mesher("pongo_jacket")
    m.mat("g_jacket")
    open_half = math.radians(22)
    zs = [0.985 + (1.205 - 0.985) * i / 14 for i in range(15)]
    rows = []
    for z in zs:
        full = torso_ring(z, 240, 0.014 + 0.004 * (1.205 - z) / 0.22)
        # keep the arc from +open to 2pi-open (front opening widens toward the hem)
        oh = open_half + math.radians(14) * (1.205 - z) / 0.22 - math.radians(10) * max(0, (z - 1.15) / 0.055)
        ring = []
        for i in range(n + 1):
            th = oh + (2 * math.pi - 2 * oh) * i / n
            k = th / (2 * math.pi) * 240
            k0 = int(k) % 240
            k1 = (k0 + 1) % 240
            fr = k - int(k)
            p = V(full[k0]).lerp(V(full[k1]), fr)
            ring.append(tuple(p))
        rows.append(ring)
    m.quad_strip(rows, closed=False)
    # stand collar (open at the front), leaning out slightly
    crow = []
    for j in range(4):
        z = 1.2 + 0.02 * j
        r0 = 0.05 + 0.006 * j
        ring = []
        for i in range(n + 1):
            th = math.radians(28) + (2 * math.pi - math.radians(56)) * i / n
            ring.append((r0 * math.sin(th), r0 * math.cos(th) * 0.92 - 0.002, z))
        crow.append(ring)
    m.mat("g_jacket")
    m.quad_strip(crow, closed=False)
    body = m.obj("pongo_jacket", smooth_angle=180)
    so = body.modifiers.new("solid", 'SOLIDIFY')
    so.thickness = 0.004
    so.offset = 1.0
    so.material_offset = 1
    so.use_rim = True
    so.material_offset_rim = 2
    body.data.materials.append(E._MATS["g_jacket_lining"].bmat)
    body.data.materials.append(E._MATS["g_jacket_blue"].bmat)
    if SUB():
        sub = body.modifiers.new("sub", 'SUBSURF')
        sub.levels = 1
    E.apply_modifiers(body)
    # sleeves (separate shells), stripe faces by angle, rolled cuff
    sm = E.Mesher("pongo_sleeves")
    for side in (1, -1):
        sh = B.mirror(B.shoulder, side)
        el = B.mirror(B.elbow, side)
        d = (el - sh).normalized()
        start = sh + V((-side * 0.03, 0, 0.012))
        end = el - d * 0.01
        pts = [start, sh.lerp(el, 0.15), sh.lerp(el, 0.45), sh.lerp(el, 0.75), end]
        rad = [(0.056, 0.06), (0.054, 0.056), (0.05, 0.051), (0.047, 0.047), (0.046, 0.046)]
        sm.mat("g_jacket")
        fs = CH.limb(sm, pts, rad, n=24, cap=False)
        bi = sm.mats.index("g_jacket_blue") if "g_jacket_blue" in sm.mats else (sm.mats.append("g_jacket_blue") or len(sm.mats) - 1)
        for f in fs:
            cen = f.calc_center_median()
            # outer side of the arm: two stripes
            rel = cen - sh
            out = V((side, 0, 0.25)).normalized()
            radial = rel - d * rel.dot(d)
            if radial.length > 1e-6:
                cosang = radial.normalized().dot((out - d * out.dot(d)).normalized())
                if 0.86 < cosang < 0.93 or cosang > 0.975:
                    f.material_index = bi
        # rolled cuff at the elbow
        sm.mat("g_jacket")
        R = d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        sm.push(Matrix.Translation(end) @ R)
        sm.torus((0, 0, 0), R=0.047, r=0.009, seg=28, sides=10)
        sm.mat("g_jacket_blue")
        sm.torus((0, 0, 0.004), R=0.0505, r=0.0035, seg=28, sides=6)
        sm.pop()
    sleeves = sm.obj("pongo_sleeves", smooth_angle=180, subsurf=SUB())
    E.apply_modifiers(sleeves)
    # zipper tapes along both opening edges + a pull on her right side (detail)
    zm = E.Mesher("pongo_zip")
    zm.mat("g_zip")
    for side in (1, -1):
        path = []
        for i in range(16):
            z = 0.99 + (1.198 - 0.99) * i / 15
            oh = open_half + math.radians(14) * (1.205 - z) / 0.22 - math.radians(10) * max(0, (z - 1.15) / 0.055)
            ring = torso_ring(z, 1440, 0.0175 + 0.004 * (1.205 - z) / 0.22)
            k = int((((side * oh) % (2 * math.pi)) / (2 * math.pi)) * 1440) % 1440
            path.append(V(ring[k]))
        zm.sweep(path, [(-0.0022, -0.0012), (0.0022, -0.0012), (0.0022, 0.0012), (-0.0022, 0.0012)], closed=True, cap=True,
                 up=(0, 1, 0))
        if side > 0:
            p0 = path[2]
            zm.rbox(tuple(p0 + V((0.0, 0.004, -0.012))), (0.007, 0.0028, 0.018), 0.0018, 1)
    zip_o = zm.obj("pongo_zip", smooth_angle=40)
    return body, sleeves, zip_o


def hands_g(B):
    """Fingerless gloves: padded palm, knuckle band and orange strap; slim skin fingers in a relaxed curl."""
    m = E.Mesher("pongo_hands")
    for side in (1, -1):
        w = B.mirror(B.wrist, side)
        e = B.mirror(B.handend, side)
        d = (e - w).normalized()
        zl = -d
        xl = V((side, 0, 0))
        xl = (xl - zl * xl.dot(zl)).normalized()
        yl = zl.cross(xl).normalized()
        R = Matrix((xl, yl, zl)).transposed().to_4x4()
        m.push(Matrix.Translation(w) @ R)
        m.mat("g_glove")
        m.rbox((0.0, 0.0, -0.042), (0.024, 0.062, 0.058), 0.011, 3)
        m.cyl((0, 0, -0.006), 0.026, 0.024, 20, r2=0.029)
        m.mat("g_glove_strap")
        m.rbox((0.0, 0.0, -0.02), (0.027, 0.064, 0.012), 0.004, 2)
        m.mat("g_skin")
        for k in range(4):
            yy = -0.022 + k * 0.0148
            L = 1.0 - 0.13 * abs(k - 1.2)
            a = V((0.0, yy, -0.068))
            b = V((-0.012, yy, -0.092 * L))
            cpt = V((-0.028, yy, -0.098 * L))
            path = [a, a.lerp(b, 0.5), b, b.lerp(cpt, 0.5), cpt]
            m.sweep(path, [(math.cos(2 * math.pi * i / 10), math.sin(2 * math.pi * i / 10)) for i in range(10)], closed=True,
                    cap=True, scale=lambda t: 0.0074 * (1 - 0.18 * t))
        path = [V((-0.01, 0.026, -0.022)), V((-0.022, 0.036, -0.044)), V((-0.031, 0.03, -0.062))]
        m.sweep(path, [(math.cos(2 * math.pi * i / 10), math.sin(2 * math.pi * i / 10)) for i in range(10)], closed=True,
                cap=True, scale=lambda t: 0.0085 * (1 - 0.2 * t))
        m.pop()
    ob = m.obj("pongo_hands", smooth_angle=50, subsurf=SUB())
    E.apply_modifiers(ob)
    return ob


# ============================================================================ sneakers (JAEY canvas-shoe method)

def shoe_mats():
    M = E.mat
    M("g_shoe", COL["shoe"], spec=0.12, rim=0.3, soft=0.08)
    M("g_shoe_dark", 0xB82E2C, spec=0.1, rim=0.3, soft=0.08)
    M("g_sole", COL["sole"], rim=0.2, soft=0.08)
    M("g_sole_line", 0x2F6BDA, rim=0.1, soft=0.08, outline=0.0)
    M("g_tread", 0x5A5E68, rim=0.0, soft=0.1, outline=0.0)
    M("g_lace", 0xFBFBF8, rim=0.2, soft=0.1, outline=0.5)
    M("g_eyelet", 0xD8DCE3, spec=0.8, rim=0.4, soft=0.05, flags=E.F_METAL, outline=0.4)
    M("g_hole", 0x1C1C22, rim=0.0, soft=0.1, outline=0.0)
    M("g_patch", 0xFFFFFF, rim=0.2, soft=0.08, outline=0.4)
    M("g_patch_star", COL["jacket_blue"], rim=0.2, soft=0.08, outline=0.0)
    M("g_tab", COL["orange"], rim=0.3, soft=0.08, outline=0.4)


SHOE = [
    # y (from the ankle), half width, top height, x shift
    (-0.072, 0.024, 0.060, 0.000),
    (-0.064, 0.033, 0.072, 0.000),
    (-0.045, 0.037, 0.078, 0.000),
    (-0.015, 0.038, 0.082, 0.001),
    (0.020, 0.040, 0.080, 0.002),
    (0.055, 0.043, 0.071, 0.004),
    (0.090, 0.045, 0.060, 0.006),
    (0.120, 0.044, 0.052, 0.007),
    (0.145, 0.039, 0.046, 0.008),
    (0.160, 0.030, 0.040, 0.008),
    (0.168, 0.018, 0.034, 0.008),
]


def _shoe_ring(y, n, grow=0.0, zb=0.014):
    hw, ht, sx = [P4.catmull([(k[0], k[1], k[2], k[3]) for k in SHOE], y)][0][:3]
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        c, s_ = math.cos(a), math.sin(a)
        p = 2.6
        x = (hw + grow) * math.copysign(abs(c) ** (2 / p), c) + sx
        zc = (zb + ht) / 2
        hz = (ht - zb) / 2 + grow
        z = zc + hz * math.copysign(abs(s_) ** (2 / p), s_)
        pts.append((x, y, z))
    return pts


def sneaker(B, side):
    """Red canvas high-top: rubber sole with blue foxing line and tread, white toe cap, red upper,
    padded high collar, tongue, metal eyelets with dark holes, flat criss-cross laces, ankle star patch,
    orange heel pull-tab. Separate overlapping pieces like a real shoe build."""
    a = B.mirror(B.ankle, side)
    m = E.Mesher("pongo_shoe_" + ("R" if side > 0 else "L"))
    O = Matrix.Translation((a.x, a.y + 0.004, 0.0)) @ Matrix.Diagonal((side * 0.93, 0.93, 0.93, 1))
    m.push(O)
    n = 28
    ys = [SHOE[0][0] + (SHOE[-1][0] - SHOE[0][0]) * i / 16 for i in range(17)]
    # upper (closed loft; ends capped and rounded by subdivision)
    m.mat("g_shoe")
    rings = [_shoe_ring(y, n) for y in ys]
    m.quad_strip(rings, closed=True, cap0=True, cap1=True)
    # ankle shaft: open at the front (the tongue shows between the eyelet rows), real thickness
    gap = math.radians(30)
    cuff = []
    for j in range(7):
        z = 0.05 + 0.088 * j / 6
        ry, rx = 0.053 - 0.003 * j / 6, 0.048 - 0.003 * j / 6
        ring = []
        for i in range(n + 1):
            a_ = math.pi / 2 + gap + (2 * math.pi - 2 * gap) * i / n
            ring.append((rx * math.cos(a_), -0.017 + ry * math.sin(a_) - 0.003 * j / 6, z))
        cuff.append(ring)
    # thickness by an inner copy
    inner = [[(x * 0.93, -0.017 + (y + 0.017) * 0.93, z) for (x, y, z) in ring] for ring in cuff]
    m.quad_strip(cuff, closed=False)
    m.quad_strip(inner[::-1], closed=False)
    m.quad_strip([cuff[-1], inner[-1]], closed=False)
    m.quad_strip([[cuff[j][0] for j in range(7)], [inner[j][0] for j in range(7)]], closed=False)
    m.quad_strip([[inner[j][-1] for j in range(7)], [cuff[j][-1] for j in range(7)]], closed=False)
    # padded collar (open arc)
    m.push(Matrix.Translation((0, -0.02, 0.138)) @ Matrix.Diagonal((1.0, 1.1, 1, 1)) @ Matrix.Rotation(math.pi / 2 + gap + math.radians(4), 4, 'Z'))
    m.torus((0, 0, 0), R=0.0465, r=0.0068, seg=24, sides=10, arc=360 - 2 * math.degrees(gap) - 8)
    m.pop()
    # toe cap (white rubber shell over the front)
    m.mat("g_sole")
    tys = [0.108 + (0.17 - 0.108) * i / 6 for i in range(7)]
    m.quad_strip([_shoe_ring(min(y, 0.168), n, 0.0022, 0.012) for y in tys], closed=True, cap1=True)
    # sole: outline extruded, with the foxing line and tread underneath
    outline = []
    for y in ys:
        hw, ht, sx = P4.catmull([(k[0], k[1], k[2], k[3]) for k in SHOE], y)[:3]
        outline.append((hw + 0.004 + sx, y))
    outline += [(-p[0] + 2 * P4.catmull([(k[0], k[3]) for k in SHOE], p[1])[0], p[1]) for p in reversed(outline)]
    outline = [(x, y) for (x, y) in outline]
    tip_y = SHOE[-1][0] + 0.004
    m.mat("g_sole")
    m.extrude(outline, 0.024, bevel=(0.004, 2), c=(0, 0, 0.012))
    m.mat("g_sole_line")
    m.extrude([(x * 1.0, y) for (x, y) in outline], 0.003, c=(0, 0, 0.016)) if False else None
    m.push(Matrix.Translation((0, 0, 0.0165)) @ Matrix.Diagonal((1.012, 1.008, 1, 1)))
    m.extrude(outline, 0.0035)
    m.pop()
    m.mat("g_tread")
    for i in range(9):
        y = -0.06 + i * 0.026
        hw = P4.catmull([(k[0], k[1]) for k in SHOE], min(y, 0.16))[0]
        m.box((0.004, y, 0.0005), (2 * hw * 0.8, 0.008, 0.002), smooth=False)
    # tongue (separate slab rising from the instep above the collar) with an orange tab
    m.mat("g_shoe")
    tpath = [V((0.002, 0.075, 0.064)), V((0.002, 0.046, 0.083)), V((0.001, 0.031, 0.11)), V((0.0, 0.027, 0.152))]
    m.sweep(tpath, [(-0.024, -0.003), (0.024, -0.003), (0.024, 0.003), (-0.024, 0.003)], closed=True, cap=True, up=(0, 1, 0.3))
    m.mat("g_tab")
    m.rbox((0.0, 0.029, 0.152), (0.016, 0.006, 0.012), 0.002, 1)
    # eyelets and laces along the opening (front of the shaft down the instep)
    lace_pts = []
    for i, (y, z) in enumerate([(0.064, 0.0705), (0.047, 0.078), (0.036, 0.09), (0.031, 0.108), (0.03, 0.128)]):
        t = i / 4
        for sd in (1, -1):
            p = V((sd * (0.021 + 0.004 * t), y, z + 0.002))
            m.mat("g_eyelet")
            m.push(Matrix.Translation(p) @ Matrix.Rotation(math.radians(-sd * 28), 4, 'Y') @ Matrix.Rotation(math.radians(-50 * t), 4, 'X'))
            m.torus((0, 0, 0), R=0.0042, r=0.0013, seg=12, sides=6)
            m.mat("g_hole")
            m.cyl((0, 0, -0.0004), r=0.0032, h=0.001, seg=10)
            m.pop()
        lace_pts.append((y, z))
    m.mat("g_lace")
    for i in range(4):
        (y0, z0), (y1, z1) = lace_pts[i], lace_pts[i + 1]
        for sd in (1, -1):
            pa = V((sd * (0.021 + 0.004 * i / 4), y0 + 0.002, z0 + 0.004))
            pb = V((-sd * (0.021 + 0.004 * (i + 1) / 4), y1 + 0.002, z1 + 0.004))
            mid = (pa + pb) / 2 + V((0, 0.002, 0.004))
            m.sweep([pa, mid, pb], [(-0.0028, -0.0007), (0.0028, -0.0007), (0.0028, 0.0007), (-0.0028, 0.0007)],
                    closed=True, cap=True, up=(0, 0.3, 1))
    # bow at the top with two loops and short ends
    y, z = lace_pts[-1]
    top = V((0.0, y + 0.004, z + 0.01))
    for sd in (1, -1):
        loop = [top, top + V((sd * 0.012, 0.006, 0.008)), top + V((sd * 0.022, 0.003, 0.004)), top + V((sd * 0.012, 0.0, -0.002)), top]
        m.sweep(loop, [(-0.0026, -0.0007), (0.0026, -0.0007), (0.0026, 0.0007), (-0.0026, 0.0007)], closed=True, cap=True,
                up=(0, 1, 0))
        m.sweep([top, top + V((sd * 0.006, 0.01, -0.012)), top + V((sd * 0.01, 0.012, -0.024))],
                [(-0.0024, -0.0007), (0.0024, -0.0007), (0.0024, 0.0007), (-0.0024, 0.0007)], closed=True, cap=True,
                up=(0, 1, 0))
    m.rbox(tuple(top), (0.006, 0.004, 0.005), 0.0015, 1)
    # ankle star patch (outer side) and heel pull tab
    m.mat("g_patch")
    m.push(Matrix.Translation((0.049, -0.017, 0.098)) @ Matrix.Rotation(math.radians(90), 4, 'Y'))
    m.cyl((0, 0, 0), 0.016, 0.003, 24)
    m.mat("g_patch_star")
    m.extrude(E.star_pts(5, 0.012, 0.005), 0.002, c=(0, 0, 0.0018))
    m.pop()
    m.mat("g_tab")
    m.sweep([V((0, -0.068, 0.128)), V((0, -0.078, 0.14)), V((0, -0.074, 0.156)), V((0, -0.064, 0.15))],
            [(-0.007, -0.0012), (0.007, -0.0012), (0.007, 0.0012), (-0.007, 0.0012)], closed=True, cap=True, up=(1, 0, 0))
    m.pop()
    ob = m.obj(m.name, smooth_angle=45, subsurf=SUB())
    if side < 0:
        pass
    E.apply_modifiers(ob)
    if side > 0:
        pass
    # the mirror (left shoe) flips winding on some primitives: make every island face outward
    _recalc(ob)
    return ob


def _recalc(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def _flip(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def goggles_g(B):
    """Goggles pushed up over the bangs: strap around the hair volume, two orange lenses in metal rims."""
    c, r = B.headc, B.head_r
    m = E.Mesher("pongo_goggles")
    E.mat("g_gstrap", 0x2E2A36, rim=0.3, soft=0.08, outline=0.7)
    E.mat("g_gframe", COL["frame"], flags=E.F_METAL, spec=0.9, rim=0.4, soft=0.05, outline=0.7)
    E.mat("g_lens", COL["lens"], flags=E.F_GLASS, spec=1.0, rim=0.5, soft=0.05, outline=0.5)
    m.mat("g_gstrap")
    path = []
    for i in range(49):
        th = -180 + 360 * i / 48
        p, nn = scalp(B, th, 0.46 + 0.26 * math.cos(math.radians(th)) ** 2 * (1 if abs(th) < 90 else 0.2), 0.036)
        path.append(p)
    m.sweep(path, [(-0.0035, -0.008), (0.0035, -0.008), (0.0035, 0.008), (-0.0035, 0.008)], closed=True, cap=False, up=(0, 0, 1))
    for side in (1, -1):
        p, nn = scalp(B, side * 22, 0.72, 0.046)
        R = nn.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        m.push(Matrix.Translation(p) @ R)
        m.mat("g_gframe")
        m.lathe([(0.0, -0.009), (0.024, -0.009), (0.027, -0.003), (0.027, 0.008), (0.022, 0.011), (0.018, 0.007)], seg=28)
        m.mat("g_lens")
        m.sphere((0, 0, 0.004), 1.0, 22, 10, s=(0.019, 0.019, 0.007))
        m.pop()
    p, nn = scalp(B, 0, 0.75, 0.052)
    m.mat("g_gframe")
    m.push(Matrix.Translation(p) @ nn.to_track_quat('Z', 'Y').to_matrix().to_4x4())
    m.rbox((0, 0, 0), (0.026, 0.01, 0.009), 0.003, 1)
    m.pop()
    return m.obj("pongo_goggles", smooth_angle=45, subsurf=SUB())


def design_body():
    E.reset()
    hair_gradient()
    studio.stage(res=(1000, 1400))
    B = Girl()
    mats()
    body_mats()
    objs = []
    hd = head(B)
    objs += [hd, P4.ears(B, "g_skin"), face(B, hd)]
    hair, tails, ties = build_hair(B)
    objs += [hair, tails, ties]
    sk = E.Mesher("pongo_skin")
    neck_g(sk, B)
    arms_g(sk, B)
    legs_g(sk, B)
    skin = sk.obj("pongo_skin", smooth_angle=180, subsurf=1)
    E.apply_modifiers(skin)
    objs.append(skin)
    tp = E.Mesher("pongo_top")
    sports_top(tp, B)
    choker(tp, B)
    top = tp.obj("pongo_top", smooth_angle=180, subsurf=1)
    E.apply_modifiers(top)
    objs.append(top)
    sh = E.Mesher("pongo_shorts")
    shorts_g(sh, B)
    shorts = sh.obj("pongo_shorts", smooth_angle=180, subsurf=1)
    E.apply_modifiers(shorts)
    objs.append(shorts)
    objs.append(wrap_panel(B))
    sc = E.Mesher("pongo_socks")
    socks_g(sc, B)
    socks = sc.obj("pongo_socks", smooth_angle=180, subsurf=1)
    E.apply_modifiers(socks)
    objs.append(socks)
    objs += list(jacket(B))
    objs.append(hands_g(B))
    shoe_mats()
    objs += [sneaker(B, 1), sneaker(B, -1), goggles_g(B)]
    for o in objs:
        if "face" not in o.name:
            E.add_outline(o, 0.0022)
    studio.shoot("g_body_front", target=(0, 0, 0.8), dist=3.4, yaw=200, pitch=4, lens=50)
    studio.shoot("g_body_back", target=(0, 0, 0.8), dist=3.4, yaw=20, pitch=6, lens=50)
    studio.shoot("g_body_side", target=(0, 0, 0.8), dist=3.4, yaw=270, pitch=4, lens=50)
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = 1200, 900
    studio.shoot("g_shoes", target=(0, 0.03, 0.08), dist=0.75, yaw=225, pitch=20, lens=60)
    studio.shoot("g_face", target=(0, 0.05, B.headc.z - 0.02), dist=0.85, yaw=200, pitch=4, lens=70)



# ============================================================================ assembly, rig, export

def _skin_part(name, build):
    m = E.Mesher(name)
    build(m)
    ob = m.obj(name, smooth_angle=180, subsurf=SUB())
    E.apply_modifiers(ob)
    return ob


def wrap_chain(B):
    """Dyn chain down the middle of the wrap panel (her left hip)."""
    th = math.radians(-90)
    pts = []
    for j in range(4):
        v = j / 3
        z = 0.86 - 0.24 * v
        w, f, b, cy = P4.catmull(TORSO_KEYS, max(0.70, z))
        pts.append(V(((w + 0.02 + 0.03 * v) * math.sin(th) * (1 + 0.12 * v), cy, z - 0.02 * v)))
    return pts


def build_pongo_g(lod=0):
    """Full heroine: returns (B, armature, [objects])."""
    hair_gradient()
    B = Girl()
    mats()
    body_mats()
    shoe_mats()
    hd = head(B)
    ear = P4.ears(B, "g_skin", subsurf=SUB())
    fc = face(B, hd)
    hair, tails, ties = build_hair(B)
    gog = goggles_g(B)
    neck_o = _skin_part("pongo_neck", lambda m: neck_g(m, B))
    arms_o = _skin_part("pongo_arms", lambda m: arms_g(m, B))
    legs_o = _skin_part("pongo_legs", lambda m: legs_g(m, B))
    top_o = _skin_part("pongo_top", lambda m: (sports_top(m, B), choker(m, B)))
    shorts_o = _skin_part("pongo_shorts", lambda m: shorts_g(m, B))
    socks_o = _skin_part("pongo_socks", lambda m: socks_g(m, B))
    wrap_o = wrap_panel(B)
    jk, sleeves, zip_o = jacket(B)
    hands_o = hands_g(B)
    shoeR, shoeL = sneaker(B, 1), sneaker(B, -1)
    handL, handR = CH.split_by_side(hands_o)
    tails_pts = {sd: tail_axis(B, sd, 0.62, 5) for sd in (1, -1)}
    arm = CH.human_rig(B, "pongo", dyn_chains=[("tailL", "head", tails_pts[-1]), ("tailR", "head", tails_pts[1]),
                                               ("wrap", "root", wrap_chain(B))])
    objs = [hd, ear, fc, hair, ties, gog, tails, neck_o, arms_o, legs_o, top_o, shorts_o, socks_o, wrap_o, jk, sleeves,
            zip_o, handL, handR, shoeL, shoeR]
    for o in objs:
        E.apply_modifiers(o, skip=('SOLIDIFY',))
    CH.bind([(neck_o, CH.NECK_BONES), (top_o, CH.TORSO_BONES), (jk, CH.TORSO_BONES), (zip_o, CH.TORSO_BONES),
             (sleeves, CH.ARM_BONES), (arms_o, CH.ARM_BONES), (shorts_o, CH.HIP_BONES), (legs_o, CH.LEG_BONES),
             (socks_o, CH.LEG_BONES)],
            [(hd, "head"), (ear, "head"), (fc, "head"), (hair, "head"), (ties, "head"), (gog, "head"),
             (handL, "hand.L"), (handR, "hand.R"), (shoeL, "foot.L"), (shoeR, "foot.R")], arm)
    # tails: head at the tie, then the spring chain
    for sd, pre in ((-1, "tailL"), (1, "tailR")):
        pass
    for o, chains in ((tails, (("tailL", tails_pts[-1]), ("tailR", tails_pts[1]))), (wrap_o, (("wrap", wrap_chain(B)),))):
        for vg in list(o.vertex_groups):
            o.vertex_groups.remove(vg)
        if len(chains) == 2:
            tl, tr = CH.split_by_side(o)
            for part, (pre, pts) in ((tl, chains[0]), (tr, chains[1])):
                CH.weight_chain(part, arm, pre, pts)
                am = part.modifiers.new("Armature", 'ARMATURE')
                am.object = arm
                part.parent = arm
            objs.remove(tails)
            objs += [tl, tr]
        else:
            CH.weight_chain(o, arm, chains[0][0], chains[0][1])
            am = o.modifiers.new("Armature", 'ARMATURE')
            am.object = arm
            o.parent = arm
    return B, arm, objs


def design_pongo_g_sheet():
    E.reset()
    studio.stage(res=(1000, 1400))
    B, arm, objs = build_pongo_g()
    for o in objs:
        if o.type == 'MESH' and "face" not in o.name:
            E.add_outline(o, 0.0022)
    CH.make_clips(arm)
    sc = bpy.context.scene
    arm.animation_data.action = bpy.data.actions["idle"]
    sc.frame_set(10)
    studio.shoot("g_sheet_front", target=(0, 0, 0.78), dist=3.0, yaw=200, pitch=4, lens=50)
    arm.animation_data.action = bpy.data.actions["run"]
    sc.frame_set(4)
    studio.shoot("g_sheet_run", target=(0, 0, 0.8), dist=3.0, yaw=245, pitch=6, lens=50)
    sc.frame_set(14)
    studio.shoot("g_sheet_run_back", target=(0, 0, 0.82), dist=3.0, yaw=25, pitch=12, lens=50)


def export_pongo_g():
    global GAME
    GAME = True
    E.reset()
    B, arm, objs = build_pongo_g()
    clips = CH.make_clips(arm)
    body = E.join(objs, "pongo")
    E.export_erm(body, "pongo", arm=arm, clips=clips)
    dec = body.modifiers.new("dec", 'DECIMATE')
    dec.ratio = 0.4
    E.export_erm(body, "pongo@1", arm=arm, clips=clips)
