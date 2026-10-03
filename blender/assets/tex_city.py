"""Seamless painted textures for the Sakura Line city zone."""
import math
import numpy as np
import erlib as E
import texgen as T


def ballast(n=512, seed=3):
    """Track ballast: heaped angular stones painted back-to-front, each with a lit top-left
    facet, a darker lower-right facet and a contact shadow, over a dark gravel bed."""
    rng = np.random.default_rng(seed)
    img = T.colorize(T.noise(n, 30, seed), 0x4A4642, 0x6E6862)
    warm, cool = T.rgb(0xB3A797), T.rgb(0x9AA1AB)
    count = 2600
    order = np.argsort(rng.random(count))
    for i in order:
        cx, cy = rng.random() * n, rng.random() * n
        r = 5.0 + rng.random() * 6.0
        k = int(rng.integers(5, 8))
        ang = np.sort(rng.random(k) * 2 * math.pi)
        rad = r * (0.7 + 0.3 * rng.random(k))
        px = cx + np.cos(ang) * rad * (1.0 + 0.3 * rng.random())
        py = cy + np.sin(ang) * rad
        t = rng.random()
        base = (warm * t + cool * (1 - t)) * (0.75 + 0.3 * rng.random())
        x0, x1 = int(math.floor(px.min())) - 2, int(math.ceil(px.max())) + 3
        y0, y1 = int(math.floor(py.min())) - 2, int(math.ceil(py.max())) + 3
        ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float64) + 0.5
        inside = np.ones(xs.shape, bool)
        shadow = np.ones(xs.shape, bool)
        for j in range(k):
            ax, ay, bx, by = px[j], py[j], px[(j + 1) % k], py[(j + 1) % k]
            cr = (bx - ax) * (ys - ay) - (by - ay) * (xs - ax)
            cr2 = (bx - ax) * (ys - 1.6 - ay) - (by - ay) * (xs - 1.6 - ax)
            inside &= cr >= 0
            shadow &= cr2 >= 0
        # facet shading: split by a ridge line through the centre, lit from top-left (image y down)
        side = ((xs - cx) * 0.7 + (ys - cy) * 0.7) < (rng.random() - 0.5) * r * 0.6
        rim = np.zeros(xs.shape)
        col = np.where(side[..., None], base * 1.18, base * 0.82)
        yi = np.mod(ys.astype(int), n)
        xi = np.mod(xs.astype(int), n)
        sh = shadow & ~inside
        img[yi[sh], xi[sh]] *= 0.55
        img[yi[inside], xi[inside]] = col[inside]
    img = T.blur(img, 0.45)
    img *= (0.92 + 0.16 * T.noise(n, 4, seed + 2))[..., None]
    T.write_png("t_ballast", img)


def concrete(n=256, seed=11):
    """Light concrete: soft blotches, faint pores, weathering streaks."""
    lum = 0.86 + (T.noise(n, 3, seed, 3) - 0.5) * 0.22
    pores = T.noise(n, 90, seed + 1)
    lum -= np.clip(0.38 - pores, 0, 1) * 0.45
    streak = T.noise(n, 2, seed + 2, m=n)
    streak = T.blur(np.repeat(T.noise(n, 18, seed + 3)[:1, :], n, 0), 0.6) * 0 + T.noise(n, 1, seed + 4)
    lum -= np.clip(streak - 0.6, 0, 1) * 0.25
    lum = T.poster(lum, 10, 0.35)
    img = T.colorize(np.clip(lum, 0, 1), 0x000000, 0xFFFFFF) * T.rgb(0xFBF8F2)[None, None, :]
    T.write_png("t_concrete", img)


def asphalt(n=256, seed=21):
    lum = 0.88 + (T.noise(n, 4, seed, 2) - 0.5) * 0.18
    sp = T.noise(n, 110, seed + 1)
    lum += np.where(sp > 0.68, 0.18, 0) - np.where(sp < 0.3, 0.12, 0)
    img = np.repeat(np.clip(lum, 0, 1)[..., None], 3, -1)
    T.write_png("t_asphalt", img)


def kawara(n=256, rows=4, cols=4):
    """Japanese roof tiles (one tile = 1 x 1 m at uvscale 1): S-profile tiles in rows.
    v runs up the roof; each row overlaps the one below and casts a dark lip line."""
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float64)
    u = xs / n * cols
    v = (n - 1 - ys) / n * rows
    fu = u % 1.0
    fv = v % 1.0
    # S-profile across the tile: crest (convex) + trough
    # rounded tile columns: lit on the left flank, shadowed on the right, dark seam between
    ang = (fu - 0.5) * math.pi
    lit = 0.86 - 0.22 * np.sin(ang) + 0.06 * np.cos(ang)
    lit = T.poster(lit, 6, 0.6)
    lit *= 0.62 + 0.38 * T.smooth(np.minimum(fu, 1 - fu), 0.0, 0.07)
    # tile front lip at the bottom of each row: dark shadow then bright edge
    lip = T.smooth(fv, 0.0, 0.07)
    lum = lit * (0.55 + 0.45 * lip)
    lum += (1 - T.smooth(np.abs(fv - 0.085), 0.0, 0.03)) * 0.12
    # gently darken toward the top of each tile (under the next row)
    lum *= 1.0 - 0.12 * T.smooth(fv, 0.75, 1.0)
    # per-tile variation and soft weathering
    tid = (np.floor(u) * 7 + np.floor(v) * 13) % 5
    lum *= 0.94 + tid * 0.025
    lum *= 0.97 + (T.noise(n, 3, 31) - 0.5) * 0.12
    img = np.repeat(np.clip(lum, 0, 1)[..., None], 3, -1)
    T.write_png("t_kawara", img)


def siding(n=256, boards=8):
    """Horizontal lap siding (8 boards per metre at uvscale 1)."""
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float64)
    v = (n - 1 - ys) / n * boards
    fv = v % 1.0
    lum = 0.80 + 0.2 * fv                    # each board gets lighter toward its lower lap... (lit from above)
    lum = 0.97 - 0.18 * (1 - fv) ** 3
    lum *= 1 - 0.5 * (1 - T.smooth(fv, 0.0, 0.06))
    lum *= 0.96 + (T.noise(n, 4, 41) - 0.5) * 0.18
    grain = T.noise(n, 60, 42)
    lum *= 0.98 + (grain - 0.5) * 0.05
    img = np.repeat(np.clip(lum, 0, 1)[..., None], 3, -1)
    T.write_png("t_siding", img)


def plaster(n=256, seed=51):
    lum = 0.93 + (T.noise(n, 3, seed, 3) - 0.5) * 0.12
    lum -= np.clip(T.noise(n, 2, seed + 1) - 0.55, 0, 1) * 0.12      # soft rain stains
    lum += (T.noise(n, 70, seed + 2) - 0.5) * 0.04                    # trowel grain
    img = np.repeat(np.clip(lum, 0, 1)[..., None], 3, -1)
    T.write_png("t_plaster", img)


def blockwall(n=256, seed=61):
    """Concrete block wall: 0.4 x 0.2 m blocks, 2.5 x 5 per metre at uvscale 1."""
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float64)
    bw, bh = n / 2.5, n / 5.0
    # use 2 x 4 blocks per tile so the bond repeats (tile = 0.8 x 0.8 m at uvscale 0.8)
    bw, bh = n / 2.0, n / 4.0
    row = np.floor(ys / bh)
    xo = xs + (row % 2) * bw / 2
    fx = (xo % bw) / bw
    fy = (ys % bh) / bh
    mort = np.minimum(np.minimum(fx, 1 - fx) * bw, np.minimum(fy, 1 - fy) * bh)
    lum = 0.88 + (T.noise(n, 4, seed, 2) - 0.5) * 0.16
    bid = (np.floor(xo / bw) * 3 + row * 5) % 4
    lum *= 0.95 + bid * 0.025
    lum -= np.clip(0.36 - T.noise(n, 80, seed + 1), 0, 1) * 0.4
    lum *= 0.7 + 0.3 * T.smooth(mort, 1.0, 3.0)
    lum *= 1 + 0.06 * (1 - T.smooth(fy * bh, 2, 6))     # light top edge of each block
    # moss/rain darkening at the bottom of the tile
    img = np.repeat(np.clip(lum, 0, 1)[..., None], 3, -1)
    T.write_png("t_blockwall", img)


def wood(n=256, seed=71, planks=4):
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float64)
    pu = xs / n * planks
    pid = np.floor(pu)
    fu = pu % 1.0
    g = T.noise(n, 2, seed, 2)
    rings = np.sin((fu * 2.5 + g * 1.2 + np.sin(ys / n * 2 * math.pi + pid) * 0.12 + pid * 0.37) * 2 * math.pi * 2)
    lum = 0.86 + 0.08 * T.poster((rings + 1) / 2, 3, 0.8) + (pid % 3) * 0.03
    lum *= 0.65 + 0.35 * T.smooth(np.minimum(fu, 1 - fu) * n / planks, 0.5, 2.5)
    img = T.colorize(np.clip(lum, 0, 1), 0x000000, 0xFFFFFF) * T.rgb(0xFFF2E2)[None, None, :]
    T.write_png("t_wood", img)


def grass(n=256, seed=81):
    """Grass: painted green with blade strokes and soft clumps (full colour)."""
    rng = np.random.default_rng(seed)
    base = T.noise(n, 4, seed, 3)
    img = T.colorize(T.poster(base, 4, 0.6), 0x4E9A3A, 0x8BCB4E)
    layer = np.zeros((n, n))
    for i in range(1400):
        x, y = rng.random() * n, rng.random() * n
        L = 4 + rng.random() * 7
        a = math.pi / 2 + (rng.random() - 0.5) * 0.8
        for s in range(int(L)):
            px = int(x + math.cos(a) * s) % n
            py = int(y - math.sin(a) * s) % n
            layer[py, px] = max(layer[py, px], 1 - s / L * 0.4) * (1 if rng.random() > 0.5 else 0.7)
    layer = np.clip(T.blur(layer, 0.5) * 1.6, 0, 1)
    hi = T.rgb(0xB8E46A)
    img = img * (1 - 0.5 * layer[..., None]) + hi[None, None, :] * 0.5 * layer[..., None]
    T.write_png("t_grass", img)


def dirt(n=256, seed=91):
    lum = T.noise(n, 5, seed, 3)
    img = T.colorize(T.poster(lum, 5, 0.5), 0x9C7A56, 0xD2B48A)
    sp = T.noise(n, 100, seed + 1)
    img *= (1 - 0.18 * (sp < 0.33))[..., None]
    img = img + 0.12 * (sp > 0.7)[..., None]
    T.write_png("t_dirt", img)


def blossom(n=256, seed=101):
    """Sakura canopy surface: clusters of 5-petal flowers over a deeper pink base (full colour)."""
    rng = np.random.default_rng(seed)
    base = T.noise(n, 6, seed, 2)
    img = T.colorize(T.poster(base, 3, 0.7), 0xE98AAE, 0xF7B9CF)
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float64)
    acc = np.zeros((n, n))
    ctr = np.zeros((n, n))
    for i in range(120):
        cx, cy = rng.random() * n, rng.random() * n
        r = 7 + rng.random() * 6
        rot = rng.random() * 6.28
        dx = (xs - cx + n / 2) % n - n / 2
        dy = (ys - cy + n / 2) % n - n / 2
        d = np.sqrt(dx * dx + dy * dy)
        a = np.arctan2(dy, dx) + rot
        petal = r * (0.62 + 0.38 * np.abs(np.cos(a * 2.5)))
        notch = 1 - 0.18 * np.exp(-((np.cos(a * 5) - 1) ** 2) * 30)
        flower = d < petal * notch
        acc = np.maximum(acc, flower * (0.75 + 0.25 * (1 - d / (r + 1e-6))))
        ctr = np.maximum(ctr, d < r * 0.22)
    white = T.rgb(0xFFF1F6)
    img = img * (1 - acc[..., None]) + white[None, None, :] * acc[..., None] * (0.92 + 0.08 * base[..., None])
    img = img * (1 - ctr[..., None]) + T.rgb(0xE0577F)[None, None, :] * ctr[..., None]
    T.write_png("t_blossom", img)


def leaves(n=256, seed=111):
    """Generic green tree canopy (for non-sakura trees and hedges)."""
    rng = np.random.default_rng(seed)
    pts = rng.random((180, 2)) * n
    f1, f2, idx = T.voronoi(n, pts)
    tone = rng.random(180)
    lum = 0.55 + 0.45 * tone[idx]
    lum *= 0.6 + 0.4 * T.smooth(f2 - f1, 0.5, 4)
    img = T.colorize(T.poster(np.clip(lum, 0, 1), 3, 0.7), 0x2F6E36, 0x7FC255)
    T.write_png("t_leaves", img)


def tactile(n=128):
    """Yellow tactile paving (dots), 0.3 m per tile."""
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float64)
    g = n / 5
    fx = (xs % g) / g - 0.5
    fy = (ys % g) / g - 0.5
    d = np.sqrt(fx * fx + fy * fy)
    dome = np.clip(1 - d / 0.32, 0, 1)
    sh = np.clip(-(fx - fy) * 2.2, -1, 1) * (d < 0.32)
    img = T.colorize(np.full((n, n), 1.0), 0xF2C230, 0xF6CB34)
    img *= (1 + 0.25 * sh)[..., None]
    img *= (0.95 + 0.05 * dome)[..., None]
    img *= (1 - 0.35 * ((np.minimum(np.minimum(xs, n - 1 - xs), np.minimum(ys, n - 1 - ys))) < 1.5))[..., None]
    T.write_png("t_tactile", img)


def build_all():
    ballast(); concrete(); asphalt(); kawara(); siding(); plaster(); blockwall()
    wood(); grass(); dirt(); blossom(); leaves(); tactile(); fence()


def preview():
    """Contact sheet of all city tiles (each repeated 2x2 to check seams)."""
    import os
    names = ["t_ballast", "t_concrete", "t_asphalt", "t_kawara", "t_siding", "t_plaster", "t_blockwall",
             "t_wood", "t_grass", "t_dirt", "t_blossom", "t_leaves", "t_tactile"]
    import bpy
    cell = 256
    cols = 5
    rows = (len(names) + cols - 1) // cols
    sheet = np.ones((rows * cell, cols * cell, 3))
    for i, nm in enumerate(names):
        img = bpy.data.images.load(os.path.join(E.OUT_TEX, nm + ".png"))
        w, h = img.size
        px = np.array(img.pixels[:]).reshape(h, w, 4)[::-1, :, :3]
        # 2x2 repeat then nearest downsample to the cell
        rep = np.tile(px, (2, 2, 1))
        sy = np.linspace(0, rep.shape[0] - 1, cell).astype(int)
        sx = np.linspace(0, rep.shape[1] - 1, cell).astype(int)
        r, c = divmod(i, cols)
        sheet[r * cell:(r + 1) * cell, c * cell:(c + 1) * cell] = rep[sy][:, sx]
    os.makedirs(os.path.join(E.OUT_RENDERS, "design"), exist_ok=True)
    T.write_png("_sheet_city", sheet)
    os.replace(os.path.join(E.OUT_TEX, "_sheet_city.png"), os.path.join(E.OUT_RENDERS, "design", "tex_city_sheet.png"))


def fence(n=256):
    """Green chain-link mesh with alpha (cutout); one tile = 0.5 m at uvscale 0.5."""
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float64)
    k = 6.0
    a = (xs + ys) / n * k
    b = (xs - ys) / n * k
    da = np.abs(a - np.round(a)) * n / k
    db = np.abs(b - np.round(b)) * n / k
    w = 2.6
    wire = np.maximum(1 - T.smooth(da, w * 0.5, w), 1 - T.smooth(db, w * 0.5, w))
    # wires over/under at crossings: lighter along one direction
    lit = np.where(da < db, 1.0, 0.82)
    col = T.colorize(np.full((n, n), 1.0), 0x000000, 0xFFFFFF) * (0.75 + 0.25 * lit)[..., None]
    img = np.concatenate([col, wire[..., None]], -1)
    T.write_png("t_fence", img)
