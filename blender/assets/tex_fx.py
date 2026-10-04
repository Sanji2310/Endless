"""
tex_fx — the effect sprites for every zone, the vehicles, pickups and power-ups (src/com/pongo/core/Fx.java).

Painted in the Sakura Line look: flat cel fills, a violet-tinted shade band on the side away from the light
(upper left), thin ink outlines on solid things (puffs, petals, leaves, droplets, debris), and soft unlined shapes
for light (glows, stars, sparks, streaks). Solid sprites are painted in their real colours; light sprites are
white so the particle colour tints them. Every sprite is listed in build/tex/_extra.txt so the AssetBuilder packs
it into the atlas by name.

  blender -b -P blender/run.py -- tex_fx build_all     -> build/tex/fx_*.png
  blender -b -P blender/run.py -- tex_fx preview       -> renders/design/tex_fx_sheet.png
"""
import os
import numpy as np
import erlib as E
import texgen as T

# the shared palette (see blender/assets/city.py and cave.py)
INK = T.rgb(0x3A2E52)          # outline ink, a little violet
SHADE = T.rgb(0xC6BEE6)        # violet cel shade on white things
LIGHT = (-0.55, 0.62)          # light from the upper left (u right, v up)
NAMES = []


# ------------------------------------------------------------------ painting helpers (u right, v up, both -1..1)

def grid(n):
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float64) + 0.5
    return (xs / n) * 2 - 1, 1 - (ys / n) * 2


def cov(sd, n, soft=1.0):
    """Anti-aliased coverage of a signed distance (positive inside, in uv units)."""
    return np.clip(0.5 + sd * n * 0.5 / soft, 0, 1)


def circle(u, v, cx, cy, r):
    return r - np.sqrt((u - cx) ** 2 + (v - cy) ** 2)


def ellipse(u, v, cx, cy, rx, ry, rot=0.0):
    c, s = np.cos(rot), np.sin(rot)
    x = ((u - cx) * c + (v - cy) * s) / rx
    y = (-(u - cx) * s + (v - cy) * c) / ry
    return (1 - np.sqrt(x * x + y * y)) * min(rx, ry)


def save(name, rgb, a):
    img = np.zeros(rgb.shape[:2] + (4,))
    img[..., :3] = np.clip(rgb, 0, 1)
    img[..., 3] = np.clip(a, 0, 1)
    T.write_png(name, img)
    NAMES.append(name)


def cel(n, sdf, base, shade=SHADE, ink=INK, ink_px=1.6, shift=0.16, hl=None, hl_col=(1, 1, 1), ink_a=0.9):
    """A solid cel shape: flat base colour, a shade crescent away from the light, a thin inside ink line.
    sdf(u, v) -> signed distance. shift: shade band thickness. hl: optional highlight sdf."""
    u, v = grid(n)
    sd = sdf(u, v)
    a = cov(sd, n)
    lit = cov(sdf(u - LIGHT[0] * shift, v - LIGHT[1] * shift), n, 1.5)
    col = np.zeros((n, n, 3)) + np.asarray(shade)
    col = col * (1 - lit[..., None]) + np.asarray(base) * lit[..., None]
    if hl is not None:
        h = cov(hl(u, v), n)
        col = col * (1 - h[..., None]) + np.asarray(hl_col) * h[..., None]
    if ink_px > 0:
        edge = np.clip(1 - np.abs(sd * n * 0.5 - ink_px * 0.5) / (ink_px * 0.5 + 0.5), 0, 1) * ink_a
        col = col * (1 - edge[..., None]) + np.asarray(ink) * edge[..., None]
    return col, a


def soft_sprite(n, a, core=None):
    """A light sprite: white, alpha = a, with an optional hotter core baked in as brighter alpha."""
    col = np.ones((n, n, 3))
    if core is not None:
        a = np.clip(a + core, 0, 1)
    return col, a


# ------------------------------------------------------------------ the sprites

def puffs(n=128):
    """Cel dust/steam/cloud puffs: lumpy clusters of round lobes, white with a violet shade crescent and thin ink.
    Tinted by the particle colour: warm beige for landing dust, grey-brown for rock dust, white for steam and
    cloud puffs, cyan-white for river mist."""
    sets = {
        "fx_puff": [(0.0, -0.18, 0.5), (-0.42, -0.3, 0.36), (0.42, -0.28, 0.38), (-0.18, 0.22, 0.4), (0.24, 0.18, 0.36)],
        "fx_puff2": [(-0.1, -0.2, 0.55), (0.45, -0.1, 0.34), (-0.5, -0.38, 0.28), (0.12, 0.3, 0.38), (-0.38, 0.1, 0.3)],
        "fx_puff3": [(0.0, 0.0, 0.42), (-0.4, -0.2, 0.3), (0.38, -0.25, 0.32), (0.12, 0.4, 0.26), (-0.22, 0.38, 0.22)],
    }
    for name, lobes in sets.items():
        def sdf(u, v, lobes=lobes):
            return np.max([circle(u, v, cx, cy, r * 0.82) for cx, cy, r in lobes], axis=0)

        col, a = cel(n, sdf, (1, 1, 1), SHADE, INK, ink_px=1.8, shift=0.2, ink_a=0.55)
        save(name, col, a)


def petal(n=64):
    """Sakura petal: a rounded teardrop with the notch at the tip, pink with a deeper base and thin ink."""
    def sdf(u, v):
        # wide rounded top tapering to a point at the base, with the notch in the top edge
        t = np.clip((v + 0.85) / 1.6, 0, 1)
        w = 0.56 * np.sin(np.clip(t, 0, 1) * np.pi * 0.62) ** 0.8
        body = np.minimum(w - np.abs(u), np.minimum(v + 0.85, ellipse(u, v, 0, 0.18, 0.56, 0.62)))
        notch = circle(u, v, 0, 0.86, 0.2)
        return np.minimum(body, -notch)

    u, v = grid(n)
    col, a = cel(n, sdf, T.rgb(0xFFD3E2), T.rgb(0xE9A2C6), T.rgb(0x8A4A72), ink_px=1.2, shift=0.14, ink_a=0.7)
    base = np.clip((-v - 0.2) / 0.7, 0, 1)[..., None] * 0.5
    col = col * (1 - base) + T.rgb(0xF27FAE) * base
    save("fx_petal", col, a)


def leaves(n=64):
    """Bamboo leaf (slender, two-tone green with a midrib) and maple leaf (five lobes, sunset orange)."""
    u, v = grid(n)

    def bamboo(u, v):
        w = 0.2 * np.clip(1 - np.abs(v) ** 1.6, 0, 1) * (1 - 0.35 * (v > 0) * v)
        return np.minimum(w - np.abs(u + 0.06 * np.sin(v * 2.0)), 0.92 - np.abs(v))

    col, a = cel(n, bamboo, T.rgb(0x9FD67A), T.rgb(0x5E9E6A), T.rgb(0x2E4A3A), ink_px=1.1, shift=0.1, ink_a=0.7)
    rib = np.clip(1 - np.abs(u + 0.06 * np.sin(v * 2.0)) * n * 0.5 / 0.8, 0, 1) * (np.abs(v) < 0.8) * 0.5
    col = col * (1 - rib[..., None]) + T.rgb(0x4E8A52) * rib[..., None]
    save("fx_leaf_bamboo", col, a)

    def maple(u, v):
        ang = np.arctan2(u, v + 0.1)
        r = np.sqrt(u * u + (v + 0.1) ** 2)
        lobes = 0.62 + 0.26 * np.cos(ang * 5) ** 3 - 0.18 * (np.abs(ang) > 2.4)
        stem = np.minimum(0.04 - np.abs(u), np.minimum(-0.1 - v, v + 0.95))
        return np.maximum(lobes - r, stem)

    col, a = cel(n, maple, T.rgb(0xFF9A52), T.rgb(0xD8576A), T.rgb(0x6A2E3A), ink_px=1.1, shift=0.12, ink_a=0.7)
    save("fx_leaf_maple", col, a)


def stars(n=128):
    """Light sprites: kira star (4 points + core), soft glow, shock ring, anime impact burst, spark streak,
    wind streak and the ribbon strip used by every trail."""
    u, v = grid(n)
    r = np.sqrt(u * u + v * v)
    ang = np.arctan2(v, u)
    # kira: four long thin points, two short diagonal ones, a hot core
    long_ = np.exp(-(r / (0.04 + 0.95 * np.abs(np.cos(2 * ang)) ** 40)) ** 2)
    short = np.exp(-(r / (0.03 + 0.45 * np.abs(np.cos(2 * ang + np.pi / 2)) ** 60)) ** 2) * 0.7
    save("fx_star", *soft_sprite(n, np.clip(long_ + short, 0, 1), np.exp(-(r / 0.13) ** 2)))
    # glow: round, soft, a brighter centre
    save("fx_glow", *soft_sprite(n, np.exp(-(r / 0.5) ** 2) * 0.85, np.exp(-(r / 0.16) ** 2) * 0.6))
    # ring: a crisp ring with a faint inner echo
    ring = np.exp(-((r - 0.82) / 0.05) ** 2) + 0.35 * np.exp(-((r - 0.62) / 0.03) ** 2)
    save("fx_ring", *soft_sprite(n, np.clip(ring, 0, 1)))
    # burst: thin radial lines of uneven length that taper outward, empty in the middle (anime impact lines and
    # the pickup starburst)
    k = 18
    a = np.zeros((n, n))
    for i in range(k):
        rnd = (np.sin(i * 12.9898) * 43758.5453) % 1.0
        th = (i + 0.3 * rnd) / k * 2 * np.pi
        r0, r1 = 0.36 + 0.14 * rnd, 0.78 + 0.2 * ((rnd * 7.31) % 1.0)
        d_ang = np.abs(np.angle(np.exp(1j * (ang - th))))
        t = np.clip((r - r0) / (r1 - r0), 0, 1)
        half = (0.075 + 0.03 * rnd) * (1 - t) ** 0.9
        line = np.clip((half - d_ang) * r * n * 0.5 + 0.5, 0, 1) * (r > r0) * (r < r1)
        a = np.maximum(a, line)
    save("fx_burst", *soft_sprite(n, a))
    # spark: a streak along u with a hot head on the right
    sp = np.exp(-(v / (0.07 * np.clip(1 - np.abs(u), 0, 1) + 0.01)) ** 2) * np.clip(1 - np.abs(u), 0, 1) ** 0.7
    save("fx_spark", *soft_sprite(n, sp, np.exp(-(((u - 0.55) / 0.2) ** 2 + (v / 0.08) ** 2))))
    # streak: a long thin wind line, tapered at both ends (sky wind, speed, gusts)
    st = np.exp(-(v / 0.05) ** 2) * np.clip(1 - u * u, 0, 1) ** 1.5
    save("fx_streak", *soft_sprite(n, st))
    # trail: a ribbon strip, u along the ribbon, v across: bright edge-to-edge with soft sides
    tr = np.clip(1 - np.abs(v), 0, 1) ** 0.8
    tr = tr * (0.75 + 0.25 * np.exp(-(v / 0.2) ** 2))
    save("fx_trail", *soft_sprite(n, tr))


def water(n=128):
    """Cel water: droplet (spray), splash crown seen from the side, foam patch and ripple rings seen from above."""
    u, v = grid(n)
    pale, deep, foam = T.rgb(0xDDF4FF), T.rgb(0x8CC8E8), T.rgb(0xFFFFFF)
    ink = T.rgb(0x2E4A6A)

    def drop(u, v):
        t = np.clip((0.85 - v) / 1.6, 0, 1)
        w = 0.5 * np.sqrt(t) * np.clip(1.15 - t, 0, 1) ** 0.5
        return np.minimum(w - np.abs(u), np.minimum(v + 0.72, 0.85 - v)) * 0.9

    col, a = cel(n, drop, pale, deep, ink, ink_px=2.0, shift=0.18,
                 hl=lambda u, v: ellipse(u, v, -0.12, -0.15, 0.08, 0.16, 0.3), ink_a=0.7)
    save("fx_droplet", col, a)

    def crown(u, v):
        # a low cup of water opening upward into five tapered spikes, each ending in a round droplet
        sd = np.minimum(ellipse(u, v, 0, -0.62, 0.62, 0.22), 9)
        cup = np.minimum(0.32 + 0.35 * np.clip(v + 0.6, 0, 1) - np.abs(u), np.minimum(v + 0.62, 0.05 - v))
        sd = np.maximum(sd, cup)
        for i, (x, top) in enumerate([(-0.62, 0.25), (-0.3, 0.58), (0.0, 0.72), (0.3, 0.55), (0.6, 0.22)]):
            t = np.clip((v + 0.1) / (top + 0.1), 0, 1)
            spike = np.minimum(0.15 * (1 - t) + 0.03 - np.abs(u - x - 0.1 * x * t), np.minimum(v + 0.2, top - v))
            sd = np.maximum(sd, spike)
            sd = np.maximum(sd, circle(u, v, x * 1.1, top + 0.06, 0.085))
        return sd

    col, a = cel(n, crown, foam, pale, ink, ink_px=1.8, shift=0.08, ink_a=0.6)
    band = np.clip((-0.5 - v) / 0.25, 0, 1)[..., None] * 0.6
    col = col * (1 - band) + deep * band
    save("fx_crown", col, a)

    # foam: a lumpy flat patch for wakes, white with a pale blue edge (alpha blended, seen from above)
    lump = T.noise(n, 5, 31)
    fd = 0.62 + (lump - 0.5) * 0.9 - np.sqrt(u * u + v * v)
    fa = cov(fd, n, 2.0)
    fc = np.ones((n, n, 3))
    edge = np.clip(1 - fd * 6, 0, 1)[..., None]
    fc = fc * (1 - edge) + pale * edge
    holes = cov(T.noise(n, 9, 32) - 0.62, n, 2.0) * (fd > 0.1)
    save("fx_foam", fc, fa * (1 - holes * 0.8))

    # ripple: two crisp rings with a faint fill between (seen from above)
    r = np.sqrt(u * u + v * v)
    rp = np.exp(-((r - 0.85) / 0.04) ** 2) + 0.6 * np.exp(-((r - 0.6) / 0.03) ** 2)
    save("fx_ripple", *soft_sprite(n, np.clip(rp, 0, 1)))


def flame(n=128):
    """Hayate Rocket wind-swirl flame: an orange teardrop with a yellow inner flame, white core and a curl at the
    tail (points down the sprite's -v axis, so the code aligns v with the thrust)."""
    u, v = grid(n)
    t = np.clip((0.9 - v) / 1.8, 0, 1)                 # 0 at the nozzle (top), 1 at the tail
    curl = 0.16 * np.sin(t * 7.0) * t
    def body(u, v, s):
        tt = np.clip((0.9 - v) / 1.8, 0, 1)
        w = s * 0.55 * np.sin(np.clip(tt, 0, 1) * np.pi) ** 0.7 * (1 - 0.5 * tt)
        return w - np.abs(u - 0.16 * np.sin(tt * 7.0) * tt)
    outer, mid, core = cov(body(u, v, 1.0), n), cov(body(u, v, 0.62), n), cov(body(u, v, 0.3), n)
    col = np.zeros((n, n, 3)) + T.rgb(0xFF6A3A)
    col = col * (1 - mid[..., None]) + T.rgb(0xFFC24A) * mid[..., None]
    col = col * (1 - core[..., None]) + T.rgb(0xFFF6D8) * core[..., None]
    save("fx_flame", col, outer)


def swirl(n=128):
    """A spiral of three tapered arms: the Maneki Magnet's pull swirl and the sky gust's eddy (light sprite)."""
    u, v = grid(n)
    r = np.sqrt(u * u + v * v)
    ang = np.arctan2(v, u)
    arms = 3
    ph = (ang * arms / (2 * np.pi) + r * 1.6) % 1.0
    d = np.abs(ph - 0.5) * 2                            # 0 on an arm
    width = 0.22 * np.clip(r / 0.9, 0, 1)
    a = np.clip(1 - (1 - d) / np.maximum(width, 1e-3), 0, 1)
    a = (1 - a) * np.clip((0.92 - r) / 0.12, 0, 1) * np.clip(r / 0.15, 0, 1)
    save("fx_swirl", *soft_sprite(n, a))


def windring(n=128):
    """Tobi Boots wind ring (seen from above, laid flat under her feet): a broken white swoosh ring with violet
    shade on its inner edge and a thin ink line."""
    u, v = grid(n)
    r = np.sqrt(u * u + v * v)
    ang = np.arctan2(v, u)
    w = 0.09 * (0.5 + 0.5 * np.cos(ang * 3 + 0.5)) ** 0.6 + 0.02
    sd = w - np.abs(r - 0.78)
    a = cov(sd, n)
    inner = np.clip((0.78 - r) / max(1e-3, 0.08), 0, 1)[..., None]
    col = np.ones((n, n, 3)) * (1 - inner) + SHADE * inner
    edge = np.clip(1 - np.abs(sd * n * 0.5 - 0.8) / 1.3, 0, 1)[..., None] * 0.45
    col = col * (1 - edge) + INK * edge
    save("fx_windring", col, a)


def bits(n=64):
    """Small solid bits: rock chip (crash debris, rockfall), crow feather, confetti (Gacha pop), crystal shard."""
    u, v = grid(n)

    def chip(u, v):
        pts = [(-0.6, -0.4), (-0.1, -0.7), (0.62, -0.3), (0.5, 0.42), (-0.05, 0.66), (-0.66, 0.2)]
        sd = np.full(u.shape, 1e9)
        inside = np.zeros(u.shape, bool)
        for i in range(len(pts)):
            ax, ay = pts[i]
            bx, by = pts[(i + 1) % len(pts)]
            dx, dy = bx - ax, by - ay
            t = np.clip(((u - ax) * dx + (v - ay) * dy) / (dx * dx + dy * dy), 0, 1)
            sd = np.minimum(sd, np.sqrt((u - ax - t * dx) ** 2 + (v - ay - t * dy) ** 2))
            inside ^= ((ay > v) != (by > v)) & (u < dx * (v - ay) / (dy if dy else 1e-9) + ax)
        return np.where(inside, sd, -sd)

    col, a = cel(n, chip, T.rgb(0xCBBBA8), T.rgb(0x7C6E8E), INK, ink_px=1.4, shift=0.3, ink_a=0.8)
    save("fx_chip", col, a)

    def feather(u, v):
        w = 0.24 * np.clip(1 - ((v - 0.05) / 0.9) ** 2, 0, 1) ** 0.6
        vane = w - np.abs(u - 0.08 * v * v)
        quill = np.minimum(0.035 - np.abs(u - 0.08 * v * v), np.minimum(v + 0.98, 0.9 - v))
        return np.maximum(vane, quill)

    col, a = cel(n, feather, T.rgb(0x3C3550), T.rgb(0x1E1A2C), T.rgb(0x0E0C16), ink_px=1.0, shift=0.12,
                 hl=lambda u, v: ellipse(u, v, -0.06, 0.2, 0.05, 0.35, 0.05), hl_col=T.rgb(0x7A6CA8), ink_a=0.6)
    save("fx_feather", col, a)

    def confetti(u, v):
        x = u * 0.94 + v * 0.34
        y = -u * 0.34 + v * 0.94
        return np.minimum(0.34 - np.abs(x), 0.62 - np.abs(y + 0.1 * np.sin(x * 4)))

    col, a = cel(n, confetti, (1, 1, 1), T.rgb(0xD8D2EE), INK, ink_px=1.0, shift=0.12, ink_a=0.4)
    save("fx_confetti", col, a)

    def shard(u, v):
        return np.minimum(np.minimum(0.32 - np.abs(u) - 0.3 * np.abs(v), 0.9 - np.abs(v)), 0.5)

    col, a = cel(n, shard, T.rgb(0xE6FBFF), T.rgb(0x8FB6F2), T.rgb(0x2E3A6A), ink_px=1.2, shift=0.14,
                 hl=lambda u, v: np.minimum(0.06 - np.abs(u + 0.06), 0.5 - np.abs(v - 0.1)), ink_a=0.7)
    save("fx_shard", col, a)


def wisp(n=128):
    """A cloud wisp streaming past in Sky Glide: a long, flat cel cloud (no ink) with a violet underside, fading out
    at both ends."""
    u, v = grid(n)
    lobes = [(-0.62, -0.05, 0.2), (-0.32, 0.04, 0.27), (0.0, 0.1, 0.32), (0.3, 0.03, 0.26), (0.6, -0.04, 0.2)]

    def sdf(u, v):
        s = np.max([circle(u, v, cx, cy, r) for cx, cy, r in lobes], axis=0)
        return np.minimum(s, v + 0.16)

    col, a = cel(n, sdf, (1, 1, 1), SHADE, INK, ink_px=0, shift=0.16)
    save("fx_wisp", col, a * np.clip((1 - np.abs(u)) * 2.2, 0, 1) * 0.95)


def build_all():
    del NAMES[:]
    puffs(); petal(); leaves(); stars(); water(); flame(); swirl(); windring(); bits(); wisp()
    path = os.path.join(E.OUT_TEX, "_extra.txt")
    have = open(path).read().split() if os.path.exists(path) else []
    with open(path, "a") as f:
        for nm in NAMES:
            if nm not in have:
                f.write(nm + "\n")


def preview():
    """Contact sheet of every fx sprite over a light and a dark backdrop -> renders/design/tex_fx_sheet.png."""
    import zlib
    names = sorted(nm for nm in os.listdir(E.OUT_TEX) if nm.startswith("fx_") and nm.endswith(".png"))
    cell, cols = 160, 8
    rows = (len(names) + cols - 1) // cols
    sheet = np.ones((rows * cell * 2, cols * cell, 3))
    for i, nm in enumerate(names):
        px = _read_png(os.path.join(E.OUT_TEX, nm))
        h, w = px.shape[:2]
        sy = np.linspace(0, h - 1, cell - 16).astype(int)
        sx = np.linspace(0, w - 1, cell - 16).astype(int)
        p = px[sy][:, sx]
        for k, bg in enumerate((np.array([0.93, 0.95, 1.0]), np.array([0.14, 0.12, 0.24]))):
            out = p[..., :3] * p[..., 3:] + bg * (1 - p[..., 3:])
            r0 = (i // cols) * cell * 2 + k * cell + 8
            c0 = (i % cols) * cell + 8
            sheet[r0 - 8:r0 + cell - 8, c0 - 8:c0 + cell - 8] = bg
            sheet[r0:r0 + cell - 16, c0:c0 + cell - 16] = out
    os.makedirs(os.path.join(E.OUT_RENDERS, "design"), exist_ok=True)
    T.write_png("_sheet_fx", sheet)
    os.replace(os.path.join(E.OUT_TEX, "_sheet_fx.png"), os.path.join(E.OUT_RENDERS, "design", "tex_fx_sheet.png"))
    print("sheet:", ", ".join(n[:-4] for n in names))


def _read_png(path):
    """Reads an 8-bit RGBA/RGB PNG written by texgen.write_png (filter 0 rows) without needing bpy images."""
    import zlib, struct
    data = open(path, "rb").read()
    pos, w, h, ct, idat = 8, 0, 0, 6, b""
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w, h, _, ct = struct.unpack(">IIBB", body[:10])
        elif typ == b"IDAT":
            idat += body
        pos += 12 + ln
    c = 4 if ct == 6 else 3
    raw = np.frombuffer(zlib.decompress(idat), np.uint8).reshape(h, 1 + w * c)[:, 1:].reshape(h, w, c) / 255.0
    if c == 3:
        raw = np.concatenate([raw, np.ones((h, w, 1))], -1)
    return raw


def main():
    build_all()
    preview()
