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


EYE_CHEER = dict(lid_top=((30, 112), (66, 204), (176, 214), (232, 150)), lid_bot=((232, 150), (210, 70), (92, 50), (30, 112)),
                 iris=(136, 122, 60, 80), crease=((58, 186), (96, 222), (170, 228), (214, 188)), hl=1.0)
# calm, determined gaze: flatter upper lid resting low on the iris, lifted lower lid, sharper outer corner
EYE_CALM = dict(lid_top=((28, 114), (70, 190), (178, 202), (238, 158)), lid_bot=((238, 158), (216, 92), (100, 66), (28, 114)),
                iris=(138, 126, 55, 74), crease=((56, 178), (96, 210), (172, 216), (222, 180)), hl=0.82)


def eye_g(name="d_eye_pongo_g", size=512, top=COL["iris_top"], mid=COL["iris_mid"], bot=COL["iris_bot"], shape=None):
    """Layered anime eye (outer corner at the right of the texture):
    almond white with lid shadow, tall gradient iris with ring, radial streaks and pupil,
    soft lower glow, two crisp highlights, thick upper lash line with outer wings,
    double-lid crease and a fine lower lash."""
    sh_ = shape or EYE_CHEER
    c = PT.Canvas(name, size, size)
    s = size / 256.0
    S = lambda pts: [(x * s, y * s) for (x, y) in pts]
    topc = FA._bez(*sh_["lid_top"], 28)
    botc = FA._bez(*sh_["lid_bot"], 28)
    ox, oy = sh_["lid_top"][3][0] - 232, sh_["lid_top"][3][1] - 150      # outer-corner shift for the lash wings
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
    icx, icy, irx, iry = sh_["iris"]
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
        def inside(q):
            return all((almond[(j + 1) % len(almond)][0] - almond[j][0]) * (q[1] - almond[j][1]) -
                       (almond[(j + 1) % len(almond)][1] - almond[j][1]) * (q[0] - almond[j][0]) >= 0
                       for j in range(len(almond)))
        for k in range(26):
            a = 2 * math.pi * k / 26 + 0.07 * math.sin(k * 3.1)
            r0, r1 = 0.36, 0.86
            p0 = (icx + math.cos(a) * irx * r0, icy + math.sin(a) * iry * r0)
            if not inside(p0):
                continue
            # trim the streak where it leaves the eye opening (no lines leaking onto the skin)
            rr = r0
            while rr < r1 and inside((icx + math.cos(a) * irx * (rr + 0.04), icy + math.sin(a) * iry * (rr + 0.04))):
                rr += 0.04
            if rr - r0 < 0.1:
                continue
            p1 = (icx + math.cos(a) * irx * rr, icy + math.sin(a) * iry * rr)
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
    h = sh_["hl"]
    c.ellipse((icx - 24) * s, (icy + 30) * s, 19 * s * h, 14 * s * h, 0xFFFFFF, rot=-25)
    c.ellipse((icx + 26) * s, (icy - 26) * s, 8 * s * h, 6 * s * h, 0xFFFFFF, rot=-25)
    c.circle((icx - 4) * s, (icy - 38) * s, 4 * s * h, 0xFFF6D8, 0.9)
    # upper lash line: thick tapered band following the top lid, heavier toward the outer corner
    lash = 0x23171F
    up = S(topc)
    c.stroke(up, 6 * s, 15 * s, lash)
    # outer wings and lash spikes
    W = lambda x, y: S([(min(255.0, x + ox), y + oy)])[0]
    c.curve(W(220, 156), W(236, 166), W(246, 180), W(254, 196), 12 * s, 1.5 * s, lash)
    c.curve(W(214, 160), W(228, 166), W(240, 168), W(252, 166), 8 * s, 1.2 * s, lash)
    c.curve(W(196, 178), W(206, 190), W(214, 198), W(222, 206), 5 * s, 1 * s, lash)
    # inner-corner hook
    c.curve(S([(32, 114)])[0], S([(26, 110)])[0], S([(22, 104)])[0], S([(20, 98)])[0], 4 * s, 1 * s, lash)
    # double-lid crease
    crease = S(FA._bez(*sh_["crease"], 20))
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
    elif kind == "calm":
        # small closed mouth: a short level line, heavier in the middle, soft lower-lip shade beneath
        c.ellipse(128, 50, 26, 9, 0xE98F93, 0.4)
        c.curve((84, 66), (100, 71), (114, 73), (128, 73), 5.0, 11.0, line)
        c.curve((128, 73), (142, 73), (156, 71), (172, 66), 11.0, 5.0, line)
        c.stroke([(112, 40), (144, 40)], 4.0, 4.0, 0xC86A72, 0.45)
    else:
        c.curve((80, 74), (104, 60), (152, 60), (176, 74), 5, 5, line)
    return c.save()


def blush_g(name="d_blush_g", w=256, h=128, alpha=0.5, hatch=3):
    c = PT.Canvas(name, w, h)
    c.radial(128, 64, 0, 120, 0xFF8FA0, 0xFF8FA0, alpha, 0.0, 64, 1.0, 0.45)
    for i in range(hatch):
        x = 96 + i * 26 + (13 if hatch == 2 else 0)
        c.stroke([(x, 52), (x + 10, 78)], 4, 2, 0xF06A82, 0.4)
    return c.save()


def build_face_art():
    E.reset()
    eye_g()
    eye_g("d_eye_pongo_g_calm", shape=EYE_CALM)
    mouth_g()
    mouth_g("d_mouth_pongo_g_closed", kind="closed")
    mouth_g("d_mouth_pongo_g_calm", kind="calm")
    blush_g()
    blush_g("d_blush_g_soft", alpha=0.3, hatch=2)


# ============================================================================ proportions / head

class Girl(CH.Body):
    """Petite build (~6.3 heads, 1.50 m): slender limbs, narrow shoulders, big expressive head."""

    def __init__(self):
        super().__init__(h=1.50, sho_x=0.142, hip_x=0.084, head_r=0.118, girth=0.88)
        k = self.k
        self.headc = V((0.0, 0.012 * k, self.HEADC + 0.004))


HEAD_KEYS_G = [
    (-1.00, 0.09, 0.50, 0.05, 0.32, 2.2),
    (-0.975, 0.175, 0.555, 0.08, 0.30, 2.1),
    (-0.93, 0.27, 0.62, 0.13, 0.27, 2.0),
    (-0.86, 0.385, 0.69, 0.21, 0.22, 1.95),
    (-0.77, 0.515, 0.77, 0.33, 0.16, 1.95),
    (-0.65, 0.645, 0.84, 0.48, 0.10, 2.0),
    (-0.52, 0.745, 0.89, 0.66, 0.05, 2.1),
    (-0.36, 0.83, 0.925, 0.83, 0.01, 2.2),
    (-0.15, 0.88, 0.95, 0.97, -0.01, 2.2),
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
    M("g_eye", 0xFFFFFF, "d_eye_pongo_g_calm", flags=E.F_DECAL | E.F_NOCAST, outline=0, rim=0, spec=0, soft=0.02)
    M("g_mouth", 0xFFFFFF, "d_mouth_pongo_g_calm", flags=E.F_DECAL | E.F_NOCAST, outline=0, rim=0, soft=0.02)
    M("g_blush", 0xFFFFFF, "d_blush_g_soft", flags=E.F_DECAL | E.F_NOCAST, outline=0, rim=0)
    M("g_lash", 0x23171F, rim=0.0, soft=0.05, outline=0.0, flags=E.F_DOUBLE)
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
    # darker strand partings (structure lines) that fade toward the tips
    part = np.exp(-((np.abs(((xs / w) * 6 + 0.25) % 1.0 - 0.5)) / 0.035) ** 2)
    strands = strands - 0.12 * part * (1 - 0.5 * v)
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
    P4.face_normals_gfn(hd, B, bend=8.0, bend_top=-0.5, xs_mid=1.03, xs_low=0.9, width=0.88, flat_z=0.35)
    return hd


def face(B, hd):
    """Eyes, brows, mouth, blush, nose tip and the band-aid on her left cheek."""
    bvh = CH.bvh_of(hd)
    c = B.headc
    r = B.head_r
    m = E.Mesher("pongo_face")
    eye_w, eye_h, eye_x, eye_z = 0.092 * 0.93, 0.086 * 0.93, 0.0445, -0.034
    brow_z = eye_z + 0.086 * 0.56                     # brow height from the original eye size
    m.mat("g_eye")
    for side in (1, -1):
        CH.project_decal(m, bvh, side * eye_x, c.z + eye_z, eye_w, eye_h, 9, 9, off=0.0012, mirror=(side < 0))
    m.mat("g_mouth")
    CH.project_decal(m, bvh, 0.0, c.z - 0.088, 0.034, 0.017, 7, 4, off=0.0012)
    m.mat("g_blush")
    for side in (1, -1):
        CH.project_decal(m, bvh, side * 0.054, c.z - 0.06, 0.036, 0.018, 7, 5, off=0.0009)
    # brows: straight, set a little lower, heavier at the head with a slight inner furrow (calm, determined)
    m.mat("g_brow")
    for side in (1, -1):
        pts2 = []
        for i in range(11):
            t = i / 10
            x = side * (eye_x - eye_w * 0.36 + t * eye_w * 0.86)
            z = (c.z + brow_z + 0.0045 * math.sin(math.pi * min(1.0, t * 1.1)) + 0.002 * t
                 - 0.0022 * (1 - t) ** 3)
            pts2.append((x, z))
        path = CH.surface_path(bvh, pts2, 0.0015)
        m.sweep(path, [(-1, -0.3), (1, -0.3), (1, 0.3), (-1, 0.3)], closed=True, cap=True,
                scale=lambda t: (0.0036 * (1.0 - 0.72 * t ** 0.9) + 0.0005, 0.003), up=(0, 1, 0))
    # 3D lash flicks at the outer corners: silhouette depth in 3/4 views
    m.mat("g_lash")
    for side in (1, -1):
        u, v = EYE_CALM["lid_top"][3][0] / 256.0, EYE_CALM["lid_top"][3][1] / 256.0
        x0 = side * (eye_x - eye_w / 2 + u * eye_w)
        z0 = c.z + eye_z - eye_h / 2 + v * eye_h
        hit = bvh.ray_cast(V((x0, 1.0, z0)), V((0, -1, 0)))
        if hit[0] is None:
            continue
        base, nrm = hit[0] + hit[1] * 0.0012, hit[1]
        for (L, up, out, w) in ((0.0105, 0.55, 1.0, 0.0016), (0.0075, 0.15, 1.0, 0.0012), (0.006, 0.95, 0.55, 0.001)):
            d = (V((side * out, 0.0, up)) + nrm * 0.35).normalized()
            path = [base, base + d * L * 0.5 + nrm * 0.0012, base + d * L + V((0, 0, 0.0015))]
            m.sweep(path, [(-1, -0.25), (1, -0.25), (1, 0.25), (-1, 0.25)], closed=True, cap=True,
                    scale=lambda t, w=w: (w * max(0.08, 1 - t ** 1.2), w * 0.5), up=(0, 1, 0))
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
    bf = CH.project_decal(m, bvh, -0.043, c.z - 0.071, 0.022, 0.0085, 7, 3, off=0.0011,
                          curve_z=lambda u: (u - 0.5) * 0.006)
    m.mat("g_bandaid_pad")
    CH.project_decal(m, bvh, -0.043, c.z - 0.071, 0.0072, 0.0062, 3, 3, off=0.0016)
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
    for i, (a0, a1, zt, w) in enumerate(bangs):
        scalp_clump(m, B, a0, 0.8, a1, zt, w, thick=0.014, off0=0.008, off_mid=0.028, off1=0.016, curl=0.006,
                    taper=2.2, v1=0.62)
        # sub-strands peeling off the clump: separated, finer tips (piecey anime bangs)
        for (da, dz, wf, dof) in ((3.5, 0.05 + 0.03 * (i % 2), 0.36, 0.0025), (-3.0, -0.07 + 0.02 * (i % 3), 0.3, 0.004)):
            scalp_clump(m, B, a0 + da * 0.5, 0.79, a1 + da, zt + dz, w * wf, thick=0.0095, off0=0.009,
                        off_mid=0.029 + dof, off1=0.017 + dof, curl=0.008, taper=1.7, v1=0.66)
    # under layer to fill the gaps (shorter, thinner)
    for (a0, a1, zt, w) in ((-40, -44, 0.16, 0.04), (-20, -17, 0.12, 0.04), (0, 3, 0.1, 0.04),
                            (19, 22, 0.14, 0.04), (39, 44, 0.16, 0.04)):
        scalp_clump(m, B, a0, 0.76, a1, zt, w, thick=0.011, off0=0.006, off_mid=0.02, off1=0.01, taper=2.0, v1=0.55)
    # side bangs sweeping past the eyes to the cheek
    for side in (1, -1):
        scalp_clump(m, B, side * 68, 0.6, side * 80, -0.6, 0.04, thick=0.011, off0=0.004, off_mid=0.016, off1=0.013,
                    curl=0.007, taper=1.8, v1=0.7)
    # long side locks in front of the ears, falling to the chest (two clumps + a fine loose strand)
    for side in (1, -1):
        for (a, w, L, ph) in ((84, 0.036, 0.30, 0.0), (95, 0.026, 0.25, 0.8), (78, 0.013, 0.27, 1.9)):
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
        spec = [(0, 0.064, 1.0), (36, 0.05, 0.9), (72, 0.058, 0.94), (108, 0.046, 0.8), (144, 0.056, 0.86),
                (180, 0.06, 0.97), (216, 0.048, 0.84), (252, 0.054, 0.9), (288, 0.05, 0.78), (324, 0.056, 0.82)]
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
                  lambda t: 0.016 * max(0.25, 1 - 0.6 * t), v0=0.35, v1=1.0)
        # loose strands peeling off the lower half of the tail, tips curling
        for (ang, start, L, cur) in ((50, 0.35, 0.62, 0.012), (170, 0.45, 0.55, -0.01), (260, 0.3, 0.66, 0.014), (330, 0.5, 0.5, -0.012)):
            a = math.radians(ang)
            pts, nrms = [], []
            for i in range(16):
                t = start + (1.0 - start) * L / 0.62 * i / 15
                q = axis[min(int(t * (len(axis) - 1)), len(axis) - 1)]
                T_ = (axis[min(int(t * (len(axis) - 1)) + 1, len(axis) - 1)] - axis[max(int(t * (len(axis) - 1)) - 1, 0)]).normalized()
                X = V((1, 0, 0)) - T_ * T_.x
                X.normalize()
                Y = T_.cross(X).normalized()
                d = X * math.cos(a) + Y * math.sin(a)
                u = i / 15
                rad = 0.03 * math.sin(math.pi * min(1.0, 0.12 + t * 0.95)) + 0.008 + 0.012 * u
                pts.append(q + d * rad + V((0, cur * u * u, 0)))
                nrms.append(d)
            clump(m, pts, nrms, lambda t: 0.011 * max(0.05, 1 - t ** 1.6), lambda t: 0.0045 * max(0.3, 1 - 0.6 * t),
                  v0=0.45, v1=1.0)


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
    M("g_shorts_dark", 0x262B48, rim=0.2, soft=0.08, outline=0.0)
    M("g_sock_rib", 0xEDEFF4, rim=0.2, soft=0.1, outline=0.0)


TORSO_KEYS = [
    # z      w      f      b      cy        (slim build: narrow waist, slender hips and ribcage)
    (0.66, 0.108, 0.066, 0.078, 0.000),
    (0.71, 0.116, 0.070, 0.086, 0.000),
    (0.76, 0.112, 0.068, 0.083, 0.000),
    (0.81, 0.099, 0.062, 0.072, 0.002),
    (0.86, 0.084, 0.058, 0.063, 0.004),
    (0.91, 0.087, 0.060, 0.063, 0.006),
    (0.96, 0.096, 0.064, 0.066, 0.008),
    (1.01, 0.104, 0.070, 0.069, 0.010),
    (1.06, 0.109, 0.072, 0.071, 0.010),
    (1.11, 0.114, 0.069, 0.071, 0.008),
    (1.15, 0.117, 0.062, 0.068, 0.004),
    (1.18, 0.099, 0.051, 0.057, 0.000),
    (1.205, 0.056, 0.038, 0.042, -0.002),
    (1.22, 0.038, 0.033, 0.035, -0.003),
]


def bust(z):
    return 0.024 * math.exp(-((z - 1.045) / 0.045) ** 2)


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
            [(0.037, 0.035), (0.03, 0.029), (0.0275, 0.0275), (0.0265, 0.0265)], n=20)


def choker(m, B):
    m.mat("g_choker")
    m.torus((0, -0.001, 1.235), R=0.0298, r=0.0038, seg=36, sides=8)
    m.mat("g_charm")
    # small orange star charm hanging at the front
    m.push(Matrix.Translation((0, 0.0322, 1.222)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
    m.extrude(E.star_pts(5, 0.009, 0.0042), 0.003, bevel=(0.0008, 1))
    m.pop()
    m.mat("g_zip")
    m.torus((0, 0.0318, 1.2315), R=0.0025, r=0.0008, seg=10, sides=4, axis='Y')


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
        rad = [0.035, 0.031, 0.027, 0.0245, 0.026, 0.0235, 0.0202, 0.0186]
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
        rad = [(0.061, 0.058), (0.056, 0.054), (0.047, 0.046), (0.038, 0.038), (0.035, 0.036), (0.036, 0.038),
               (0.037, 0.041), (0.031, 0.033), (0.025, 0.025), (0.0225, 0.0235)]
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
        prof = [(0.0, 0.0268), (0.2, 0.0272), (0.45, 0.0335), (0.7, 0.0405), (0.85, 0.041), (1.0, 0.041)]
        def rad(t):
            for i in range(len(prof) - 1):
                if prof[i][0] <= t <= prof[i + 1][0]:
                    u = (t - prof[i][0]) / (prof[i + 1][0] - prof[i][0])
                    return prof[i][1] + (prof[i + 1][1] - prof[i][1]) * u
            return prof[-1][1]
        pts = [a.lerp(top, t) for t in cuts]
        m.mat("g_sock")
        fs = CH.limb(m, pts, [(rad(t), rad(t) * 1.06) for t in cuts], n=22, cap=False)
        si = m.mats.index("g_sock_stripe") if "g_sock_stripe" in m.mats else (m.mats.append("g_sock_stripe") or len(m.mats) - 1)
        for f in fs:
            z = f.calc_center_median().z
            for (z0, z1) in stripes:
                if z0 < z < z1:
                    f.material_index = si
        m.mat("g_sock")
        m.torus(tuple(top), R=0.0418, r=0.0038, seg=28, sides=8)


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
        fs = CH.limb(m, [top, top.lerp(bot, 0.5), bot - d * 0.01, bot], [(0.069, 0.066), (0.066, 0.063), (0.063, 0.061), (0.064, 0.062)],
                     n=24, cap=False)
        # hem cuff
        m.torus(tuple(bot), R=0.063, r=0.0045, seg=28, sides=8, axis='Z')
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


def torso_pt(z, th, grow=0.0, keys=TORSO_KEYS):
    """Single point of torso_ring (th: 0 = front, +pi/2 = her right side)."""
    w, f, b, cy = P4.catmull(keys, z)
    s_, c_ = math.sin(th), math.cos(th)
    p = 2.4 if c_ > 0 else 2.2
    x = (w + grow) * math.copysign(abs(s_) ** (2.0 / p), s_)
    y = ((f if c_ > 0 else b) + grow) * math.copysign(abs(c_) ** (2.0 / p), c_) + cy
    a = abs(th if th <= math.pi else th - 2 * math.pi)
    y += bust(z) * math.exp(-((a - 0.52) / 0.33) ** 2) * (1 if c_ > 0 else 0)
    x += math.copysign(bust(z) * 0.25 * math.exp(-((a - 0.7) / 0.35) ** 2), s_)
    if c_ < 0:
        y -= 0.006 * math.exp(-((z - 1.1) / 0.06) ** 2) * math.exp(-((a - 2.6) / 0.3) ** 2)
        y += 0.003 * math.exp(-(a - math.pi) ** 2 / 0.02)
    return V((x, y, z))


def torso_nrm(z, th, grow=0.0):
    e = 0.004
    t = torso_pt(z, th + e, grow) - torso_pt(z, th - e, grow)
    n = V((0, 0, 1)).cross(t) * -1.0
    n = V((t.y, -t.x, 0.0))
    return n.normalized() if n.length > 1e-9 else V((math.sin(th), math.cos(th), 0))


def dash_line(m, pts, nrms, spacing=0.004, length=0.0024, width=0.0007, lift=0.0005):
    """Running stitch: short raised flat dashes along a surface polyline (JAEY stitch strips)."""
    cum = [0.0]
    for i in range(1, len(pts)):
        cum.append(cum[-1] + (pts[i] - pts[i - 1]).length)

    def at(sv):
        j = 0
        while j < len(pts) - 2 and cum[j + 1] < sv:
            j += 1
        t = max(0.0, min(1.0, (sv - cum[j]) / max(cum[j + 1] - cum[j], 1e-12)))
        return pts[j].lerp(pts[j + 1], t), nrms[j].lerp(nrms[j + 1], t).normalized()
    prof = [(-width / 2, -0.00018), (width / 2, -0.00018), (width / 2, 0.00018), (-width / 2, 0.00018)]
    sv = spacing * 0.5
    while sv + length < cum[-1]:
        a, na = at(sv)
        b, nb = at(sv + length)
        n = (na + nb).normalized()
        m.sweep([a + n * lift, (a + b) / 2 + n * (lift + 0.00015), b + n * lift], prof, closed=True, cap=True, up=tuple(n))
        sv += spacing


def _jacket_grow(z):
    return 0.014 + 0.004 * (1.205 - z) / 0.22


def _jacket_open(z):
    return math.radians(22) + math.radians(14) * (1.205 - z) / 0.22 - math.radians(10) * max(0, (z - 1.15) / 0.055)


def cloth_details(B, shorts_obj=None):
    """Fine garment details for the showcase: jacket zip teeth, hem and cuff stitching, a sleeve emblem; shorts hem,
    side-seam and back-pocket stitching, belt holes and buckle prong; wrap-panel hem stitching; sock ribs."""
    E.mat("g_stitch_blue", 0x8E9CC4, rim=0.1, soft=0.1, outline=0.0)
    E.mat("g_stitch_gold", 0xE7B85A, rim=0.2, soft=0.08, outline=0.0)
    E.mat("g_stitch_dark", 0x1E2034, rim=0.1, soft=0.1, outline=0.0)
    E.mat("g_hole", 0x1C1C22, rim=0.0, soft=0.1, outline=0.0)
    m = E.Mesher("pongo_cloth_detail")
    # --- jacket hem stitching (outer shell = ring + grow + 4 mm solidify)
    m.mat("g_stitch_blue")
    for z in (0.993, 1.0):
        oh = _jacket_open(z)
        ths = [oh + 0.02 + (2 * math.pi - 2 * oh - 0.04) * i / 160 for i in range(161)]
        pts = [torso_pt(z, th, _jacket_grow(z) + 0.0043) for th in ths]
        nrm = [torso_nrm(z, th, _jacket_grow(z) + 0.0043) for th in ths]
        if z == 0.993:
            dash_line(m, pts, nrm)
    # --- zip teeth along both tape edges (the jacket is worn open)
    m.mat("g_zip")
    for side in (1, -1):
        for k in range(76):
            z = 0.992 + (1.196 - 0.992) * k / 75
            oh = _jacket_open(z)
            th = (side * oh) % (2 * math.pi)
            g_ = 0.0175 + 0.004 * (1.205 - z) / 0.22
            p = torso_pt(z, th, g_)
            tan = (torso_pt(z, th + 0.01, g_) - torso_pt(z, th - 0.01, g_)).normalized()
            toward = tan * (-1.0 if side > 0 else 1.0)
            n = torso_nrm(z, th, g_)
            off = 0.0026 + (0.0006 if k % 2 else 0.0)
            c = p + toward * off + n * 0.0004
            R = Matrix((toward, n.cross(toward).normalized(), n)).transposed().to_4x4()
            m.push(Matrix.Translation(c) @ R)
            m.box((0, 0, 0), (0.0022, 0.0014, 0.0016), smooth=False)
            m.pop()
    # --- sleeve cuff stitching and her left-sleeve emblem
    for side in (1, -1):
        sh, el = B.mirror(B.shoulder, side), B.mirror(B.elbow, side)
        d = (el - sh).normalized()
        end = el - d * 0.01
        for (off, r) in ((0.016, 0.0398), (0.021, 0.0399)):
            c = end - d * off
            ring = CH.ring(c, d, V((1, 0, 0)), r + 0.0008, r + 0.0008, 72)
            pts = [V(q) for q in ring] + [V(ring[0])]
            nrm = [(V(q) - c).normalized() for q in ring] + [(V(ring[0]) - c).normalized()]
            m.mat("g_stitch_blue")
            dash_line(m, pts, nrm, spacing=0.0036)
            break
    sh, el = B.mirror(B.shoulder, -1), B.mirror(B.elbow, -1)
    d = (el - sh).normalized()
    c = sh.lerp(el, 0.4)
    out = V((-1, 0.1, 0.25))
    out = (out - d * out.dot(d)).normalized()
    R = Matrix((d.cross(out).normalized(), d, out)).transposed().to_4x4()
    m.push(Matrix.Translation(c + out * 0.0458) @ R)
    m.mat("g_belt")
    m.cyl((0, 0, 0.0006), r=0.0115, h=0.0012, seg=32)
    m.mat("g_jacket")
    m.torus((0, 0, 0.0012), R=0.0103, r=0.0009, seg=32, sides=6)
    m.extrude(E.star_pts(5, 0.0072, 0.0032), 0.0008, c=(0, 0, 0.0016))
    m.pop()
    # --- shorts: hem and outer side-seam stitching
    m.mat("g_stitch_dark")
    for side in (1, -1):
        h, k = B.mirror(B.hipj, side), B.mirror(B.knee, side)
        top = h + V((side * 0.012, 0, 0.02))
        bot = h.lerp(k, 0.3)
        d = (bot - top).normalized()
        c = bot - d * 0.009
        ring = CH.ring(c, d, V((1, 0, 0)), 0.0642 + 0.0008, 0.0622 + 0.0008, 72)
        pts = [V(q) for q in ring] + [V(ring[0])]
        nrm = [(V(q) - c).normalized() for q in ring] + [(V(ring[0]) - c).normalized()]
        dash_line(m, pts, nrm)
        sx = V((1, 0, 0)) - d * d.x
        sx.normalize()
        sp = [top.lerp(bot, t) + sx * side * (0.0665 - 0.0025 * t) for t in [i / 20 for i in range(19)]]
        dash_line(m, sp, [sx * side] * len(sp))
        hz = [0.855 - 0.12 * i / 20 for i in range(21)]
        th = math.pi / 2 * side
        dash_line(m, [torso_pt(z, th % (2 * math.pi), 0.0088) for z in hz],
                  [torso_nrm(z, th % (2 * math.pi), 0.0088) for z in hz])
    # --- back pocket on her right (stitched outline + flap line) and belt holes / buckle prong
    if shorts_obj is not None:
        bvh = CH.bvh_of(shorts_obj)
        outline = []
        for i in range(41):
            t = i / 40
            a = 2 * math.pi * t
            x = 0.048 + 0.024 * math.copysign(abs(math.cos(a)) ** 0.5, math.cos(a))
            z = 0.765 + 0.022 * math.copysign(abs(math.sin(a)) ** 0.5, math.sin(a))
            hit = bvh.ray_cast(V((x, -0.4, z)), V((0, 1, 0)))
            if hit[0] is not None:
                outline.append((hit[0], hit[1]))
        if len(outline) > 10:
            dash_line(m, [p for p, n in outline], [n for p, n in outline], spacing=0.0035)
        flap = []
        for i in range(12):
            x = 0.026 + 0.044 * i / 11
            hit = bvh.ray_cast(V((x, -0.4, 0.778)), V((0, 1, 0)))
            if hit[0] is not None:
                flap.append((hit[0], hit[1]))
        if len(flap) > 4:
            m.mat("g_shorts_dark")
            m.sweep([p + n * 0.0004 for p, n in flap], [(-0.0006, -0.0003), (0.0006, -0.0003), (0.0006, 0.0003), (-0.0006, 0.0003)],
                    closed=True, cap=True, up=(0, -1, 0))
    m.mat("g_hole")
    for th in (-0.24, -0.31, -0.38):
        p = torso_pt(0.8725, th % (2 * math.pi), 0.0145)
        n = torso_nrm(0.8725, th % (2 * math.pi), 0.0145)
        m.push(Matrix.Translation(p) @ n.to_track_quat('Z', 'Y').to_matrix().to_4x4())
        m.cyl((0, 0, 0), r=0.0013, h=0.0008, seg=10)
        m.pop()
    w_, f_, b_, cy_ = P4.catmull(TORSO_KEYS, 0.872)
    m.mat("g_buckle")
    m.box((0.0, cy_ + f_ + 0.0205, 0.8725), (0.0016, 0.0016, 0.016), smooth=False)
    # --- wrap panel hem stitching (cream trim)
    m.mat("g_stitch_blue")
    n_ = 14
    pts, nrm = [], []
    v = 0.93
    z = 0.86 - 0.26 * v
    for i in range(n_ * 3 + 1):
        u = i / (n_ * 3)
        th = math.radians(-135 + 90 * u)
        w, f, b, cy = P4.catmull(TORSO_KEYS, max(0.70, z))
        grow = 0.02 + 0.03 * v
        x = (w + grow) * math.sin(th)
        y = ((f if math.cos(th) > 0 else b) + grow) * math.cos(th) + cy
        zz = z - 0.05 * v * (1 - u)
        q = V((x * (1 + 0.12 * v), y * (1 + 0.1 * v), zz))
        nn = V((q.x, q.y - cy, 0.0)).normalized()
        pts.append(q + nn * 0.0032)
        nrm.append(nn)
    dash_line(m, pts, nrm, spacing=0.0045)
    # --- sock top ribs
    m.mat("g_sock_rib")
    for side in (1, -1):
        k, a = B.mirror(B.knee, side), B.mirror(B.ankle, side)
        top = k.lerp(a, 0.12)
        d = (top - a).normalized()
        for i in range(28):
            th = 2 * math.pi * i / 28
            ring0 = CH.ring(top - d * 0.03, d, V((1, 0, 0)), 0.0412, 0.0412 * 1.06, 28)
            ring1 = CH.ring(top - d * 0.004, d, V((1, 0, 0)), 0.0412, 0.0412 * 1.06, 28)
            p0, p1 = V(ring0[i]), V(ring1[i])
            nn = (p0 - (top - d * 0.03)).normalized()
            m.sweep([p0 + nn * 0.0003, p1 + nn * 0.0003], [(-0.0008, -0.0004), (0.0008, -0.0004), (0.0008, 0.0004), (-0.0008, 0.0004)],
                    closed=True, cap=True, up=tuple(nn))
    ob = m.obj("pongo_cloth_detail", smooth_angle=40)
    _recalc(ob)
    return ob


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
        r0 = 0.0445 + 0.006 * j
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
        rad = [(0.049, 0.052), (0.047, 0.049), (0.043, 0.044), (0.04, 0.04), (0.039, 0.039)]
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
        sm.torus((0, 0, 0), R=0.04, r=0.0082, seg=28, sides=10)
        sm.mat("g_jacket_blue")
        sm.torus((0, 0, 0.004), R=0.0435, r=0.0032, seg=28, sides=6)
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
    """Fingerless gloves in gilded snack gear: a cookie plate on the back of the hand (scalloped gold rim,
    chocolate-chip studs), gold knuckle rivets, gold cuff rings and a mini soda-can cartridge clipped over the
    wrist; slim skin fingers in a relaxed curl."""
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
        m.rbox((0.0, 0.0, -0.04), (0.022, 0.056, 0.054), 0.010, 3)
        m.cyl((0, 0, -0.006), 0.022, 0.024, 20, r2=0.025)
        # gold cuff rings framing the wrist band
        m.mat("g_gold")
        m.torus((0, 0, -0.0165), R=0.0222, r=0.0022, seg=28, sides=8)
        m.torus((0, 0, 0.0055), R=0.0252, r=0.0022, seg=28, sides=8)
        # cookie plate on the back of the hand
        m.push(Matrix.Translation((0.0118, 0.0, -0.035)) @ Matrix.Rotation(math.radians(90), 4, 'Y'))
        cookie_disc(m, 0.0135, chips=5, seed=7 if side > 0 else 11, dome=0.0026)
        m.pop()
        # knuckle rivets
        m.mat("g_gold")
        for k in range(4):
            m.sphere((0.0112, -0.0195 + k * 0.013, -0.0625), 1.0, 10, 6, s=(0.0018, 0.0024, 0.0024))
        # soda-can cartridge on the back of the wrist (top toward the fingers), gold clip band
        m.push(Matrix.Translation((0.0305, 0.0, -0.002)) @ Matrix.Rotation(math.radians(180), 4, 'X'))
        soda_can(m, 0.0068, 0.024)
        m.mat("g_gold")
        m.torus((0, 0, 0.0), R=0.0072, r=0.0012, seg=20, sides=6)
        m.pop()
        m.rbox((0.0262, 0.0, -0.002), (0.004, 0.006, 0.01), 0.0015, 1)
        m.mat("g_skin")
        for k in range(4):
            yy = -0.0198 + k * 0.0133
            L = 1.0 - 0.13 * abs(k - 1.2)
            a = V((0.0, yy, -0.064))
            b = V((-0.011, yy, -0.088 * L))
            cpt = V((-0.026, yy, -0.094 * L))
            path = [a, a.lerp(b, 0.5), b, b.lerp(cpt, 0.5), cpt]
            m.sweep(path, [(math.cos(2 * math.pi * i / 10), math.sin(2 * math.pi * i / 10)) for i in range(10)], closed=True,
                    cap=True, scale=lambda t: 0.0066 * (1 - 0.18 * t))
        path = [V((-0.009, 0.0235, -0.021)), V((-0.02, 0.0325, -0.042)), V((-0.029, 0.027, -0.059))]
        m.sweep(path, [(math.cos(2 * math.pi * i / 10), math.sin(2 * math.pi * i / 10)) for i in range(10)], closed=True,
                cap=True, scale=lambda t: 0.0076 * (1 - 0.2 * t))
        m.pop()
    ob = m.obj("pongo_hands", smooth_angle=50, subsurf=SUB())
    E.apply_modifiers(ob)
    _recalc(ob)
    return ob


# ============================================================================ sneakers (JAEY canvas-shoe method)

def gear_mats():
    """Gilded snack gear: gold, cookie dough with chocolate chips, soda glass with fizz bubbles, soda cans."""
    M = E.mat
    M("g_gold", 0xF2C35C, spec=0.95, rim=0.45, soft=0.04, flags=E.F_METAL, outline=0.6, shadow=0xB07A3A)
    M("g_gold_dark", 0xC48A34, spec=0.7, rim=0.3, soft=0.05, flags=E.F_METAL, outline=0.0)
    M("g_cookie", 0xDCA35E, spec=0.08, rim=0.25, soft=0.1, outline=0.5, shadow=0xA8704A)
    M("g_choco", 0x4A2A1C, spec=0.6, rim=0.2, soft=0.05, outline=0.0)
    M("g_soda", 0x5ED7EA, spec=1.0, rim=0.55, soft=0.04, emis=0.12, flags=E.F_GLASS, outline=0.5, shadow=0x3C8FC8)
    M("g_bubble", 0xEFFDFF, spec=0.6, rim=0.3, soft=0.05, emis=0.35, outline=0.0, flags=E.F_NOCAST)
    M("g_can", 0x2FAFCB, spec=0.7, rim=0.4, soft=0.05, flags=E.F_METAL, outline=0.5)
    M("g_can_stripe", COL["orange"], spec=0.5, rim=0.35, soft=0.05, outline=0.0)
    M("g_alu", 0xD9DEE6, spec=0.9, rim=0.4, soft=0.05, flags=E.F_METAL, outline=0.5)


def crimp_ring(m, R, r, crimps=21, depth=0.06, z=0.0, seg=84):
    """Bottle-cap style crimped ring (local XY plane, centred on Z)."""
    path = []
    for i in range(seg + 2):
        a = 2 * math.pi * i / seg
        rr = R * (1 + depth * math.cos(crimps * a))
        path.append(V((rr * math.cos(a), rr * math.sin(a), z)))
    m.sweep(path, [(math.cos(2 * math.pi * k / 8), math.sin(2 * math.pi * k / 8)) for k in range(8)], closed=True,
            cap=False, scale=lambda t: r)


def cookie_disc(m, r, chips=5, seed=1, rim=True, dome=0.0028):
    """Gilded cookie (local +Z out): scalloped gold rim, domed dough face, chocolate-chip studs."""
    if rim:
        m.mat("g_gold")
        crimp_ring(m, r * 1.02, r * 0.11, crimps=12, depth=0.05, z=dome * 0.35)
        m.cyl((0, 0, dome * 0.15), r=r * 1.02, h=dome * 0.3, seg=36)
    m.mat("g_cookie")
    m.sphere((0, 0, 0.0), 1.0, 28, 10, s=(r * 0.94, r * 0.94, dome))
    m.mat("g_choco")
    rnd = random.Random(seed)
    for k in range(chips):
        a = 2 * math.pi * k / chips + rnd.uniform(-0.35, 0.35)
        rr = r * (0.25 + 0.4 * rnd.random()) if k else 0.0
        cr = r * rnd.uniform(0.13, 0.18)
        m.sphere((math.cos(a) * rr, math.sin(a) * rr, dome * 0.85), 1.0, 8, 5, s=(cr, cr * 0.85, cr * 0.55))


def soda_can(m, r, h, tab=True):
    """Mini soda can along local +Z (top at +Z): teal body, orange band, aluminium rims, gold pull tab."""
    m.mat("g_can")
    m.cyl((0, 0, 0), r=r, h=h * 0.86, seg=24)
    m.mat("g_can_stripe")
    m.cyl((0, 0, -h * 0.05), r=r * 1.015, h=h * 0.22, seg=24, caps=False)
    m.mat("g_alu")
    m.cyl((0, 0, h * 0.465), r=r * 0.86, h=h * 0.07, seg=24, r2=r * 0.8)
    m.torus((0, 0, h * 0.5), R=r * 0.8, r=r * 0.09, seg=24, sides=6)
    m.cyl((0, 0, -h * 0.465), r=r * 0.86, h=h * 0.07, seg=24)
    if tab:
        m.mat("g_gold")
        m.rbox((0, r * 0.25, h * 0.52), (r * 0.5, r * 0.85, r * 0.08), r * 0.12, 1)


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
    O = Matrix.Translation((a.x, a.y + 0.004, 0.0)) @ Matrix.Diagonal((side * 0.86, 0.9, 0.9, 1))
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
    # outsole (dark rubber) + translucent-looking soda midsole with fizz bubbles + gold foxing stripe
    m.mat("g_tread")
    m.extrude(outline, 0.006, bevel=(0.002, 1), c=(0, 0, 0.003))
    m.mat("g_soda")
    m.extrude(outline, 0.0175, bevel=(0.003, 2), c=(0, 0, 0.0145))
    m.mat("g_bubble")
    rnd = random.Random(21 + (side > 0))
    for k in range(len(outline)):
        if rnd.random() < 0.45:
            continue
        x, y = outline[k]
        x2, y2 = outline[(k + 1) % len(outline)]
        nx_, ny_ = (y2 - y), -(x2 - x)
        ln = math.hypot(nx_, ny_) or 1.0
        f = rnd.random()
        bx, by = x + (x2 - x) * f, y + (y2 - y) * f
        br = rnd.uniform(0.0007, 0.0019) * (1.0 if rnd.random() < 0.8 else 1.5)
        m.sphere((bx + nx_ / ln * 0.0024, by + ny_ / ln * 0.0024, rnd.uniform(0.0085, 0.0215)), 1.0, 8, 5, s=(br, br, br))
    m.mat("g_gold")
    m.push(Matrix.Translation((0, 0, 0.0238)) @ Matrix.Diagonal((1.012, 1.008, 1, 1)))
    m.extrude(outline, 0.0028)
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
    m.mat("g_gold")
    m.rbox((0.0, 0.029, 0.152), (0.016, 0.006, 0.012), 0.002, 1)
    # eyelets and laces along the opening (front of the shaft down the instep)
    lace_pts = []
    for i, (y, z) in enumerate([(0.064, 0.0705), (0.047, 0.078), (0.036, 0.09), (0.031, 0.108), (0.03, 0.128)]):
        t = i / 4
        for sd in (1, -1):
            p = V((sd * (0.021 + 0.004 * t), y, z + 0.002))
            m.mat("g_gold")
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
        # gold aglet on the lace end
        m.mat("g_gold")
        tipd = V((sd * 0.004, 0.002, -0.012)).normalized()
        m.push(Matrix.Translation(top + V((sd * 0.01, 0.012, -0.024)) + tipd * 0.002) @ tipd.to_track_quat('Z', 'Y').to_matrix().to_4x4())
        m.cyl((0, 0, 0), r=0.0016, h=0.006, seg=10)
        m.pop()
        m.mat("g_lace")
    m.rbox(tuple(top), (0.006, 0.004, 0.005), 0.0015, 1)
    # ankle cookie patch (outer side) and a gold soda-can pull tab at the heel
    m.push(Matrix.Translation((0.0505, -0.017, 0.098)) @ Matrix.Rotation(math.radians(90), 4, 'Y'))
    cookie_disc(m, 0.0145, chips=5, seed=31, dome=0.003)
    m.pop()
    m.mat("g_gold")
    hp = V((0, -0.071, 0.146))
    m.push(Matrix.Translation(hp) @ Matrix.Rotation(math.radians(90), 4, 'X') @ Matrix.Rotation(math.radians(-12), 4, 'X'))
    loop = [V((x, y, 0.0)) for (x, y) in E.rounded_rect(0.014, 0.026, 0.006, 4)]
    m.sweep(loop + loop[:2], [(math.cos(2 * math.pi * k / 6), math.sin(2 * math.pi * k / 6)) for k in range(6)],
            closed=True, cap=False, scale=lambda t: 0.0016)
    m.rbox((0.0, -0.007, 0.0), (0.011, 0.01, 0.0026), 0.002, 1)
    m.pop()
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
    """Gilded soda goggles pushed up over the bangs: leather strap with cookie rivets, gold cups with crimped
    bottle-cap rims, fizzy soda-blue lenses with bubbles, and a gold soda-can pull tab as the bridge."""
    c, r = B.headc, B.head_r
    m = E.Mesher("pongo_goggles")
    E.mat("g_gstrap", 0x3B2A24, rim=0.3, soft=0.08, outline=0.7)
    m.mat("g_gstrap")
    path = []
    for i in range(49):
        th = -180 + 360 * i / 48
        p, nn = scalp(B, th, 0.46 + 0.26 * math.cos(math.radians(th)) ** 2 * (1 if abs(th) < 90 else 0.2), 0.036)
        path.append(p)
    m.sweep(path, [(-0.0035, -0.008), (0.0035, -0.008), (0.0035, 0.008), (-0.0035, 0.008)], closed=True, cap=False, up=(0, 0, 1))
    # cookie rivets on the strap at the temples
    for side in (1, -1):
        th = side * 68
        p, nn = scalp(B, th, 0.46 + 0.26 * math.cos(math.radians(th)) ** 2, 0.04)
        m.push(Matrix.Translation(p) @ nn.to_track_quat('Z', 'Y').to_matrix().to_4x4())
        cookie_disc(m, 0.0068, chips=3, seed=3 + side, dome=0.0018)
        m.pop()
    for side in (1, -1):
        p, nn = scalp(B, side * 22, 0.72, 0.046)
        R = nn.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        m.push(Matrix.Translation(p) @ R)
        m.mat("g_gold")
        m.lathe([(0.0, -0.009), (0.024, -0.009), (0.027, -0.003), (0.027, 0.006), (0.023, 0.009), (0.019, 0.007)], seg=32)
        crimp_ring(m, 0.0255, 0.0024, crimps=21, depth=0.055, z=0.0075)
        m.mat("g_soda")
        m.sphere((0, 0, 0.0045), 1.0, 24, 10, s=(0.0195, 0.0195, 0.0072))
        m.mat("g_bubble")
        rnd = random.Random(5 + side)
        for k in range(8):
            a = rnd.uniform(0, 2 * math.pi)
            rr = 0.0165 * math.sqrt(rnd.random())
            br = rnd.uniform(0.0008, 0.0019)
            zz = 0.0045 + 0.0072 * math.sqrt(max(0.0, 1 - (rr / 0.0195) ** 2)) - br * 0.3
            m.sphere((math.cos(a) * rr, math.sin(a) * rr, zz), 1.0, 8, 5, s=(br, br, br))
        m.pop()
    # bridge: a gold pull tab (rounded loop + rivet plate)
    p, nn = scalp(B, 0, 0.75, 0.052)
    m.push(Matrix.Translation(p) @ nn.to_track_quat('Z', 'Y').to_matrix().to_4x4())
    m.mat("g_gold")
    loop = [V((x, y, 0.0)) for (x, y) in E.rounded_rect(0.03, 0.013, 0.006, 4)]
    loop = loop + loop[:2]
    m.sweep(loop, [(math.cos(2 * math.pi * k / 6), math.sin(2 * math.pi * k / 6)) for k in range(6)], closed=True, cap=False,
            scale=lambda t: 0.0017)
    m.rbox((0.0085, 0.0, 0.0), (0.011, 0.011, 0.0028), 0.002, 1)
    m.mat("g_gold_dark")
    m.cyl((0.0085, 0.0, 0.0018), r=0.0022, h=0.0012, seg=12)
    m.pop()
    return m.obj("pongo_goggles", smooth_angle=45, subsurf=SUB())


def design_body():
    E.reset()
    hair_gradient()
    studio.stage(res=(1000, 1400))
    B = Girl()
    mats()
    body_mats()
    gear_mats()
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
    objs.append(cloth_details(B, shorts))
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
    gear_mats()
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
    detail_o = None if GAME else cloth_details(B, shorts_o)
    handL, handR = CH.split_by_side(hands_o)
    tails_pts = {sd: tail_axis(B, sd, 0.62, 5) for sd in (1, -1)}
    arm = CH.human_rig(B, "pongo", dyn_chains=[("tailL", "head", tails_pts[-1]), ("tailR", "head", tails_pts[1]),
                                               ("wrap", "root", wrap_chain(B))])
    objs = [hd, ear, fc, hair, ties, gog, tails, neck_o, arms_o, legs_o, top_o, shorts_o, socks_o, wrap_o, jk, sleeves,
            zip_o, handL, handR, shoeL, shoeR] + ([detail_o] if detail_o else [])
    for o in objs:
        E.apply_modifiers(o, skip=('SOLIDIFY',))
    CH.bind([(neck_o, CH.NECK_BONES), (top_o, CH.TORSO_BONES), (jk, CH.TORSO_BONES), (zip_o, CH.TORSO_BONES),
             (sleeves, CH.ARM_BONES), (arms_o, CH.ARM_BONES), (shorts_o, CH.HIP_BONES), (legs_o, CH.LEG_BONES),
             (socks_o, CH.LEG_BONES)] +
            ([(detail_o, sorted(set(CH.TORSO_BONES + CH.ARM_BONES + CH.HIP_BONES + CH.LEG_BONES)))] if detail_o else []),
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
    girl_clips(arm)
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
    clips = girl_clips(arm)
    body = E.join(objs, "pongo")
    E.export_erm(body, "pongo", arm=arm, clips=clips)
    dec = body.modifiers.new("dec", 'DECIMATE')
    dec.ratio = 0.4
    E.export_erm(body, "pongo@1", arm=arm, clips=clips)


# ============================================================================ her own animation

def _replace_action(arm, name):
    old = bpy.data.actions.get(name)
    if old:
        bpy.data.actions.remove(old)
    E.new_action(arm, name)


RUN_LEG = {0: (52, -12, 8), 5: (10, -28, -6), 10: (-38, -22, 28), 14: (4, -130, 40), 17: (62, -95, 5), 20: (52, -12, 8)}


def _run_leg(f):
    keys = sorted(RUN_LEG)
    f = f % 20
    for i in range(len(keys) - 1):
        a, b = keys[i], keys[i + 1]
        if a <= f <= b:
            t = (f - a) / (b - a)
            t = t * t * (3 - 2 * t)
            return tuple(RUN_LEG[a][j] + (RUN_LEG[b][j] - RUN_LEG[a][j]) * t for j in range(3))
    return RUN_LEG[0]


def run_pose(f, Z):
    """Pongo's run pose at frame f (20-frame loop): forward lean, high knees, compact arm pump, hip roll."""
    th, sh, ft = _run_leg(f)
    th2, sh2, ft2 = _run_leg(f + 10)
    ph = 2 * math.pi * f / 20
    sw = math.sin(ph)
    bob = 0.034 * math.cos(2 * ph) - 0.016
    p = CH._merge(Z, {
        "root": (0, 3 * math.cos(2 * ph), -9 * sw), "spine": (-14, 0, 7 * sw), "chest": (-4, 0, 10 * sw),
        "neck": (6, 0, -8 * sw), "head": (8, 0, -9 * sw),
        "thigh.R": (th, 0, 0), "shin.R": (sh, 0, 0), "foot.R": (ft, 0, 0),
        "thigh.L": (th2, 0, 0), "shin.L": (sh2, 0, 0), "foot.L": (ft2, 0, 0),
        "clav.R": (0, 0, 5 * sw), "clav.L": (0, 0, 5 * sw),
        "upper_arm.R": (-44 * sw + 4, 16, 6), "forearm.R": (100 + 18 * sw, 0, 14), "hand.R": (0, 0, -12),
        "upper_arm.L": (44 * sw + 4, -16, -6), "forearm.L": (100 - 18 * sw, 0, -14), "hand.L": (0, 0, 12)})
    return p, (0, 0, bob)


def _key_all(arm, keys, Z):
    for (f, pose, root) in keys:
        CH.pose_key(arm, f, CH._merge(Z, pose), root)


# Action key poses (degrees about armature axes; thigh/arm +X swings forward, shin -X bends the knee,
# spine/root +X lean back, head +X looks up; right arm +Y lowers it, left arm -Y lowers it).
JUMP_KEYS = [
    # load: stance leg bends, arms counter-swing
    (1, {"spine": (-16, 0, 0), "chest": (-4, 0, 0), "neck": (8, 0, 0), "head": (10, 0, 0),
         "thigh.R": (30, 0, 0), "shin.R": (-55, 0, 0), "thigh.L": (-8, 0, 0), "shin.L": (-42, 0, 0), "foot.L": (-6, 0, 0),
         "upper_arm.R": (-35, 18, 4), "forearm.R": (75, 0, 10), "upper_arm.L": (30, -16, -4), "forearm.L": (85, 0, -10)},
     (0, 0, -0.045)),
    # push: knee drive, the stance leg extends, the right arm swings up
    (3, {"spine": (-8, 0, 0), "neck": (6, 0, 0), "head": (6, 0, 0),
         "thigh.R": (80, 0, 0), "shin.R": (-95, 0, 0), "foot.R": (12, 0, 0),
         "thigh.L": (-24, 0, 0), "shin.L": (-10, 0, 0), "foot.L": (28, 0, 0),
         "upper_arm.R": (105, -10, 0), "forearm.R": (35, 0, 0), "upper_arm.L": (-40, -10, 0), "forearm.L": (45, 0, 0)},
     (0, 0, 0.03)),
    # rise: the trailing leg tucks up, arms open
    (6, {"spine": (-2, 0, 0), "head": (2, 0, 0),
         "thigh.R": (88, 0, 0), "shin.R": (-118, 0, 0), "foot.R": (18, 0, 0),
         "thigh.L": (38, 0, 0), "shin.L": (-98, 0, 0), "foot.L": (20, 0, 0),
         "upper_arm.R": (70, -45, 0), "forearm.R": (30, 0, 0), "upper_arm.L": (40, 45, 0), "forearm.L": (30, 0, 0)},
     (0, 0, 0.11)),
    # apex tuck: compact, arms out for balance, eyes forward
    (9, {"spine": (3, 0, 0), "chest": (-2, 0, 0), "head": (-2, 0, 0),
         "thigh.R": (78, 0, 4), "shin.R": (-125, 0, 0), "foot.R": (16, 0, 0),
         "thigh.L": (62, 0, -4), "shin.L": (-120, 0, 0), "foot.L": (16, 0, 0),
         "upper_arm.R": (38, -62, 0), "forearm.R": (26, 0, 0), "upper_arm.L": (28, 62, 0), "forearm.L": (26, 0, 0)},
     (0, 0, 0.16)),
    (12, {"spine": (4, 0, 0), "chest": (-2, 0, 0), "head": (-3, 0, 0),
          "thigh.R": (74, 0, 4), "shin.R": (-122, 0, 0), "foot.R": (14, 0, 0),
          "thigh.L": (64, 0, -4), "shin.L": (-118, 0, 0), "foot.L": (14, 0, 0),
          "upper_arm.R": (34, -66, 0), "forearm.R": (24, 0, 0), "upper_arm.L": (26, 66, 0), "forearm.L": (24, 0, 0)},
     (0, 0, 0.17)),
]


def _fall_pose(s):
    return {"spine": (4, 0, 0), "head": (-6, 0, 0),
            "thigh.R": (32 + 6 * s, 0, 3), "shin.R": (-42 - 6 * s, 0, 0), "foot.R": (8, 0, 0),
            "thigh.L": (14 - 6 * s, 0, -3), "shin.L": (-56 + 6 * s, 0, 0), "foot.L": (8, 0, 0),
            "upper_arm.R": (44 + 6 * s, -74, 0), "forearm.R": (22, 0, 0),
            "upper_arm.L": (34 - 6 * s, 74, 0), "forearm.L": (22, 0, 0)}


LAND_KEYS = [
    # contact: legs reach for the ground, arms still up
    (1, {"spine": (2, 0, 0), "head": (-4, 0, 0),
         "thigh.R": (28, 0, 2), "shin.R": (-16, 0, 0), "foot.R": (-8, 0, 0),
         "thigh.L": (6, 0, -2), "shin.L": (-24, 0, 0), "foot.L": (-4, 0, 0),
         "upper_arm.R": (40, -60, 0), "forearm.R": (24, 0, 0), "upper_arm.L": (30, 60, 0), "forearm.L": (24, 0, 0)},
     (0, 0, 0.0)),
    # impact squash: deep knees, torso folds forward, arms drop
    (3, {"spine": (-26, 0, 0), "chest": (-6, 0, 0), "neck": (14, 0, 0), "head": (12, 0, 0),
         "thigh.R": (64, 0, 4), "shin.R": (-108, 0, 0), "foot.R": (-18, 0, 0),
         "thigh.L": (40, 0, -4), "shin.L": (-84, 0, 0), "foot.L": (-10, 0, 0),
         "upper_arm.R": (28, 6, 0), "forearm.R": (62, 0, 8), "upper_arm.L": (14, -6, 0), "forearm.L": (62, 0, -8)},
     (0, 0, -0.12)),
    # recover: rising into the run lean
    (6, {"spine": (-17, 0, 0), "chest": (-4, 0, 0), "neck": (8, 0, 0), "head": (8, 0, 0),
         "thigh.R": (46, 0, 0), "shin.R": (-58, 0, 0), "foot.R": (0, 0, 0),
         "thigh.L": (8, 0, 0), "shin.L": (-40, 0, 0), "foot.L": (6, 0, 0),
         "upper_arm.R": (-10, 14, 4), "forearm.R": (95, 0, 12), "upper_arm.L": (20, -14, -4), "forearm.L": (95, 0, -12)},
     (0, 0, -0.045)),
]

SLIDE_KEYS = [
    # entry from the run: hips start to drop, lead leg swings through
    (1, {"root": (8, 0, 4), "spine": (-10, 0, 0), "neck": (4, 0, 0), "head": (4, 0, 0),
         "thigh.R": (48, 0, 0), "shin.R": (-38, 0, 0), "thigh.L": (-6, 0, 0), "shin.L": (-72, 0, 0),
         "upper_arm.R": (40, -10, 0), "forearm.R": (60, 0, 0), "upper_arm.L": (-30, -6, 0), "forearm.L": (50, 0, 0)},
     (0, 0, -0.08)),
    # dropping: lean back, trailing knee folds under
    (3, {"root": (16, 0, 9), "spine": (-6, 0, 0), "neck": (-4, 0, 0), "head": (-4, 0, 0),
         "thigh.R": (58, 0, 0), "shin.R": (-14, 0, 0), "foot.R": (-14, 0, 0),
         "thigh.L": (34, 12, -4), "shin.L": (-120, 0, 0), "foot.L": (10, 0, 0),
         "upper_arm.R": (62, -36, 0), "forearm.R": (40, 0, 0), "upper_arm.L": (-42, 28, 0), "forearm.L": (16, 0, 0)},
     (0, 0.02, -0.4)),
    # slide: low on the lead leg, torso back, head level, trailing hand skims the ground behind
    (5, {"root": (20, 0, 12), "spine": (-10, 0, -4), "chest": (-6, 0, -4), "neck": (-8, 0, 2), "head": (-6, 0, 4),
         "thigh.R": (62, 0, 2), "shin.R": (-4, 0, 0), "foot.R": (-24, 0, 0),
         "thigh.L": (46, 20, -6), "shin.L": (-138, 0, 0), "foot.L": (12, 0, 0),
         "upper_arm.R": (74, -48, 0), "forearm.R": (26, 0, 0), "hand.R": (0, 0, -10),
         "upper_arm.L": (-56, 38, 0), "forearm.L": (10, 0, 0), "hand.L": (20, 0, 0)},
     (0, 0.03, -0.5)),
    (9, {"root": (21, 0, 12), "spine": (-11, 0, -4), "chest": (-6, 0, -4), "neck": (-8, 0, 2), "head": (-7, 0, 5),
         "thigh.R": (61, 0, 2), "shin.R": (-5, 0, 0), "foot.R": (-26, 0, 0),
         "thigh.L": (47, 20, -6), "shin.L": (-139, 0, 0), "foot.L": (12, 0, 0),
         "upper_arm.R": (78, -52, 0), "forearm.R": (24, 0, 0), "hand.R": (0, 0, -12),
         "upper_arm.L": (-58, 40, 0), "forearm.L": (8, 0, 0), "hand.L": (22, 0, 0)},
     (0, 0.03, -0.51)),
    (13, {"root": (20, 0, 11), "spine": (-12, 0, -4), "chest": (-6, 0, -4), "neck": (-8, 0, 2), "head": (-6, 0, 4),
          "thigh.R": (62, 0, 2), "shin.R": (-6, 0, 0), "foot.R": (-22, 0, 0),
          "thigh.L": (46, 19, -6), "shin.L": (-136, 0, 0), "foot.L": (12, 0, 0),
          "upper_arm.R": (72, -50, 0), "forearm.R": (28, 0, 0), "hand.R": (0, 0, -10),
          "upper_arm.L": (-54, 36, 0), "forearm.L": (12, 0, 0), "hand.L": (18, 0, 0)},
     (0, 0.03, -0.49)),
    # push up: trailing leg drives, torso comes forward
    (16, {"root": (8, 0, 5), "spine": (-18, 0, 0), "chest": (-4, 0, 0), "neck": (8, 0, 0), "head": (8, 0, 0),
          "thigh.R": (40, 0, 0), "shin.R": (-34, 0, 0), "foot.R": (-6, 0, 0),
          "thigh.L": (22, 0, -2), "shin.L": (-100, 0, 0), "foot.L": (14, 0, 0),
          "upper_arm.R": (24, 6, 0), "forearm.R": (80, 0, 10), "upper_arm.L": (-14, -8, 0), "forearm.L": (80, 0, -10)},
     (0, 0.01, -0.26)),
]


def _ground_samples(arm):
    """Points on the soles, kneecaps and fingertips (rest space) with the bone that carries them."""
    out = []
    for sfx, sd in (("L", -1), ("R", 1)):
        foot = arm.data.bones["foot." + sfx]
        a = foot.head_local
        for (dx, dy, dz) in ((0.0, -0.075, -a.z + 0.002), (0.0, 0.17, -a.z + 0.004), (sd * 0.04, 0.1, -a.z + 0.003),
                             (-sd * 0.035, 0.1, -a.z + 0.003), (0.0, -0.03, 0.06)):
            out.append(("foot." + sfx, a + V((dx, dy, dz))))
        shin = arm.data.bones["shin." + sfx]
        out.append(("shin." + sfx, shin.head_local + V((0, 0.038, 0.0))))
        out.append(("shin." + sfx, shin.head_local + V((0, 0.0, -0.035))))
        hand = arm.data.bones["hand." + sfx]
        out.append(("hand." + sfx, hand.tail_local))
    return out


def ground_clearance(arm, samples):
    lo = 1e9
    for bn, p in samples:
        pb = arm.pose.bones[bn]
        M = pb.matrix @ arm.data.bones[bn].matrix_local.inverted()
        lo = min(lo, (M @ p).z)
    return lo


def clamp_ground(arm, action, floor=0.008):
    """Raise the root key of every keyed frame whose soles/knees/hands would dip below the floor."""
    act = bpy.data.actions[action]
    arm.animation_data.action = act
    frames = sorted({int(round(k.co.x)) for fc in act.fcurves for k in fc.keyframe_points})
    samples = _ground_samples(arm)
    rr = CH.rest_rot(arm, "root")
    pb = arm.pose.bones["root"]
    sc = bpy.context.scene
    fixed = 0
    for f in frames:
        sc.frame_set(f)
        lo = ground_clearance(arm, samples)
        if lo < floor:
            world = rr @ pb.location
            world.z += floor - lo
            pb.location = rr.inverted() @ world
            pb.keyframe_insert("location", frame=f)
            fixed += 1
    return fixed


def girl_clips(arm):
    """Shared gameplay clips, with Pongo's own run, idle, jump/fall/land and slide on top."""
    clips = CH.make_clips(arm)
    Z = CH.all_bones_zero(arm)
    # ---- run: 20 frames, forward lean, high knees, compact arm pump, hip roll, light bounce
    _replace_action(arm, "run")
    for f in range(0, 21):
        p, root = run_pose(f, Z)
        CH.pose_key(arm, f + 1, p, root)
    # ---- jump (takeoff -> apex), fall loop, land (impact -> run), slide (drop -> slide -> push up)
    _replace_action(arm, "jump")
    _key_all(arm, JUMP_KEYS, Z)
    _replace_action(arm, "fall")
    for f, s_ in ((1, 0.0), (9, 1.0), (17, 0.0)):
        CH.pose_key(arm, f, CH._merge(Z, _fall_pose(s_)), (0, 0, 0.0))
    _replace_action(arm, "land")
    _key_all(arm, LAND_KEYS, Z)
    p, root = run_pose(0, Z)
    CH.pose_key(arm, 9, p, root)
    clips.append(("land", False))
    _replace_action(arm, "slide")
    _key_all(arm, SLIDE_KEYS, Z)
    p, root = run_pose(10, Z)
    CH.pose_key(arm, 20, p, root)
    clips.append(("slide", False))
    # ---- idle: weight on her left leg, head tilt, left hand drifting behind, gentle breathing sway
    _replace_action(arm, "idle")
    for f, br in ((1, 0.0), (19, 1.0), (37, 0.0), (55, -0.6), (73, 0.0)):
        p = CH._merge(Z, {
            "root": (0, 4, -6), "spine": (-2 - 1.5 * br, -5, 4), "chest": (1.5 * br, 2, -5), "neck": (2, 4, 4),
            "head": (-4 - br, 6, 8 + 2 * br),
            "clav.R": (0, 0, 2 * br), "clav.L": (0, 0, -1.5 * br),
            "upper_arm.R": (-3, 13 + 2 * br, 0), "forearm.R": (18, 0, 0), "hand.R": (0, 0, -8),
            "upper_arm.L": (14, -11 - 2 * br, 0), "forearm.L": (30, 0, 0), "hand.L": (0, 0, 10),
            "thigh.L": (2, 0, 2), "shin.L": (-2, 0, 0),
            "thigh.R": (8, 0, -9), "shin.R": (-16, 0, 0), "foot.R": (6, 0, 6)})
        CH.pose_key(arm, f, p, (0.012 + 0.004 * br, 0, -0.01 + 0.004 * br))
    # nothing may sink into the floor (soles, kneecaps, fingertips)
    for act in ("slide", "land", "run", "idle"):
        n = clamp_ground(arm, act)
        if n:
            print("  ground clamp: %s raised %d keys" % (act, n))
    arm.animation_data.action = bpy.data.actions["idle"]
    return clips


# ============================================================================ action design renders

def _set_frame_pose(arm, action, frame):
    arm.animation_data.action = bpy.data.actions[action]
    bpy.context.scene.frame_set(frame)


def design_action_keys():
    """Key-pose check sheet: each action key from the side and three-quarter views."""
    E.reset()
    studio.stage(res=(500, 620))
    B, arm, objs = build_pongo_g()
    for o in objs:
        if o.type == 'MESH' and "face" not in o.name:
            E.add_outline(o, 0.0022)
    girl_clips(arm)
    shots = [("jump", 1), ("jump", 3), ("jump", 6), ("jump", 9), ("fall", 1), ("land", 3), ("land", 6),
             ("slide", 3), ("slide", 5), ("slide", 16)]
    for (act, f) in shots:
        _set_frame_pose(arm, act, f)
        studio.shoot("k_%s_%02d_side" % (act, f), target=(0, 0, 0.6), dist=2.6, yaw=270, pitch=4, lens=50)
        studio.shoot("k_%s_%02d_34" % (act, f), target=(0, 0, 0.6), dist=2.6, yaw=215, pitch=8, lens=50)
