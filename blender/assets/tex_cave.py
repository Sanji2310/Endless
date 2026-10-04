"""Seamless painted textures for the Crystal Cavern zone (and the tunnel mouth that leads into it).

Like the city tiles, most of these are luminance detail around 0.7-1.0 that takes its hue from the
material colour, so one rock tile serves the walls, the boulders and the rock piles.
"""
import math
import numpy as np
import erlib as E
import texgen as T


def cave_rock(n=256, seed=201):
    """Clean painted rock in the Sakura Line manner: big flat value patches (two or three tones), a few wavy strata
    lines drawn like ink, and sparse cracks with a lit lip. No fine grain: shape and colour come from the mesh."""
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float64)
    patch = T.poster(T.noise(n, 2, seed, 2), 3, 1.0)                  # broad flat tones
    lum = 0.9 + (patch - 0.5) * 0.12
    warp = (T.noise(n, 2, seed + 1, 2) - 0.5) * 1.4
    v = (n - 1 - ys) / n * 3 + warp                                     # 3 strata per tile
    fv = v % 1.0
    line = 1 - T.smooth(np.abs(fv - 0.5), 0.0, 0.018)                   # thin strata line
    lip = (1 - T.smooth(np.abs(fv - 0.53), 0.0, 0.03)) * 0.06           # lit lip just above it
    lum = lum * (1 - 0.28 * line) + lip
    # sparse cracks: a few Voronoi edges only where a second noise allows, inked thin
    rng = np.random.default_rng(seed)
    f1, f2, idx = T.voronoi(n, rng.random((9, 2)) * n)
    crack = (1 - T.smooth(f2 - f1, 0.4, 1.6)) * (T.noise(n, 2, seed + 3) > 0.52)
    lum *= 1 - 0.3 * crack
    img = np.repeat(np.clip(lum, 0, 1)[..., None], 3, -1)
    T.write_png("t_cave_rock", img)


def cave_floor(n=256, seed=211):
    """Packed mine floor, clean like the Sakura Line ballast: a flat light ground with a few tidy pebbles, each a
    flat shape with a lit top and a crisp contact shadow."""
    rng = np.random.default_rng(seed)
    lum = 0.92 + (T.poster(T.noise(n, 2, seed, 2), 3, 1.0) - 0.5) * 0.06
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float64)
    for i in range(70):
        cx, cy = rng.random() * n, rng.random() * n
        rx, ry = 2.5 + rng.random() * 3.5, 2.0 + rng.random() * 2.6
        dx = (xs - cx + n / 2) % n - n / 2
        dy = (ys - cy + n / 2) % n - n / 2
        d = (dx / rx) ** 2 + (dy / ry) ** 2
        sh = ((dx - 1.0) / rx) ** 2 + ((dy - 1.2) / ry) ** 2
        lum = np.where((sh < 1.0) & (d >= 1.0), lum * 0.82, lum)
        top = ((dx + 0.6) / rx) ** 2 + ((dy + 0.7) / ry) ** 2 < 0.35
        lum = np.where(d < 1.0, np.where(top, 1.0, 0.86 + 0.06 * rng.random()), lum)
    img = np.repeat(np.clip(lum, 0, 1)[..., None], 3, -1)
    T.write_png("t_cave_floor", img)


def timber(n=256, seed=221):
    """Mine timber, clean in the shared toon style: two or three flat tones along the beam, a few wavy grain lines
    drawn thin like ink, and a knot or two as inked rings. No speckle: the outlines and shading carry the form.
    One tile = 1 m of beam at uvscale 1."""
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float64)
    lum = 0.93 + (T.poster(T.noise(n, 2, seed, 2), 3, 1.0) - 0.5) * 0.08          # broad flat tones
    # grain: 4 wavy lines across the tile height, running along u
    warp = (T.noise(n, 2, seed + 1, 2) - 0.5) * 0.9
    v = ys / n * 4 + warp
    fv = v % 1.0
    line = 1 - T.smooth(np.abs(fv - 0.5), 0.0, 0.03)
    gaps = T.noise(n, 3, seed + 2) > 0.38                                           # broken runs, not stripes
    lum *= 1 - 0.22 * line * gaps
    # knots: an inked ring with a darker heart
    rng = np.random.default_rng(seed)
    for k in range(2):
        cx, cy = rng.random() * n, rng.random() * n
        dx = (xs - cx + n / 2) % n - n / 2
        dy = (ys - cy + n / 2) % n - n / 2
        d = np.sqrt(dx * dx * 0.35 + dy * dy * 1.6)
        lum *= 1 - 0.25 * (1 - T.smooth(np.abs(d - 6.0), 0.0, 1.2))
        lum *= 1 - 0.12 * (1 - T.smooth(d, 2.0, 3.0))
    img = T.colorize(np.clip(lum, 0, 1), 0x000000, 0xFFFFFF) * T.rgb(0xFFF0E0)[None, None, :]
    T.write_png("t_timber", img)


def portal_stone(n=256, seed=231, courses=4, per=2.5):
    """Dressed-stone masonry (ashlar) for the tunnel portal: running bond, 4 courses per metre at uvscale 1,
    chamfered block edges, darker mortar, rock-face texture on each block, rain streaks."""
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float64)
    v = (n - 1 - ys) / n * courses
    row = np.floor(v)
    u = xs / n * per + 0.5 * (row % 2)
    fu, fv = u % 1.0, v % 1.0
    bid = np.floor(u) * 7 + row * 13
    edge = np.minimum(np.minimum(fu, 1 - fu) * per * 2.0, np.minimum(fv, 1 - fv))
    joint = 1 - T.smooth(edge, 0.02, 0.05)
    lum = 0.88 + ((bid % 5) - 2) * 0.03
    # chamfer: lit top/left, shaded bottom/right
    lum += 0.08 * (1 - T.smooth(1 - fv, 0.04, 0.1)) - 0.12 * (1 - T.smooth(fv, 0.04, 0.1))
    lum += 0.05 * (1 - T.smooth(fu, 0.03, 0.08)) - 0.08 * (1 - T.smooth(1 - fu, 0.03, 0.08))
    lum *= 0.95 + 0.1 * T.shade_from_height(T.noise(n, 18, seed, 2), strength=10) * 0.5
    lum = lum * (1 - joint) + 0.45 * joint
    streak = T.noise(n, 1, seed + 1)
    lum *= 1 - 0.12 * np.clip(T.noise(n, 12, seed + 2) * 2 - 1.1, 0, 1) * (streak > 0.5)
    lum = T.poster(np.clip(lum, 0, 1), 8, 0.4)
    img = np.repeat(lum[..., None], 3, -1)
    T.write_png("t_portal_stone", img)


def fx_sprites(n=64):
    """Particle sprites for the cave effects (RGBA, white-ish so the particle colour tints them):
    fx_drip (falling water drop), fx_splash (drip ring on a puddle), fx_mote (dust mote in the lamp beam),
    fx_sparkle (crystal glint), fx_rockdust (puff when rubble falls). Listed in _extra.txt for the builder."""
    import os
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float64) + 0.5
    c = n / 2
    dx, dy = (xs - c) / c, (ys - c) / c
    r = np.sqrt(dx * dx + dy * dy)

    def save(name, a, col=(1, 1, 1), hl=None):
        img = np.zeros((n, n, 4))
        img[..., :3] = np.array(col)[None, None, :]
        if hl is not None:
            img[..., :3] = img[..., :3] * (1 - hl[..., None]) + hl[..., None]
        img[..., 3] = np.clip(a, 0, 1)
        T.write_png(name, img)

    # drip: teardrop, pointed at the top, with a bright glint
    t = np.clip((dy + 0.9) / 1.6, 0, 1)
    width = 0.42 * np.sqrt(np.clip(t, 0, 1)) * np.clip((1.0 - (dy - 0.25) / 0.45), 0, 1) ** 0.5
    drop = 1 - T.smooth(np.abs(dx) - width, -0.05, 0.03)
    drop *= (dy > -0.85) & (dy < 0.72)
    glint = np.exp(-(((dx + 0.12) / 0.07) ** 2 + ((dy - 0.25) / 0.12) ** 2))
    save("fx_drip", drop, (0.75, 0.88, 1.0), np.clip(glint * 1.5, 0, 1))
    # splash ring
    ring = np.exp(-((r - 0.62) / 0.08) ** 2) * (0.6 + 0.4 * np.cos(np.arctan2(dy, dx) * 6) ** 2)
    save("fx_splash", ring, (0.8, 0.92, 1.0))
    # mote: soft round dot
    save("fx_mote", np.exp(-(r / 0.45) ** 2), (1.0, 0.95, 0.85))
    # sparkle: four-point star with a hot core
    ang = np.arctan2(dy, dx)
    star = np.exp(-(r / (0.08 + 0.85 * np.abs(np.cos(2 * ang)) ** 18)) ** 2)
    save("fx_sparkle", np.clip(star + np.exp(-(r / 0.15) ** 2), 0, 1), (0.85, 1.0, 1.0))
    # rock dust: lumpy cloud
    lump = T.noise(n, 3, 5)
    save("fx_rockdust", np.clip((1 - T.smooth(r, 0.45, 0.95)) * (0.6 + 0.8 * (lump - 0.5) + 0.4), 0, 1) * 0.85, (0.82, 0.78, 0.74))
    path = os.path.join(E.OUT_TEX, "_extra.txt")
    have = open(path).read().split() if os.path.exists(path) else []
    with open(path, "a") as f:
        for nm in ("fx_drip", "fx_splash", "fx_mote", "fx_sparkle", "fx_rockdust"):
            if nm not in have:
                f.write(nm + "\n")


def build_all():
    cave_rock(); cave_floor(); timber(); portal_stone(); fx_sprites()


def preview():
    """Contact sheet of the cave tiles (each repeated 2x2 to check seams) -> renders/design/tex_cave_sheet.png."""
    import os
    import bpy
    names = ["t_cave_rock", "t_cave_floor", "t_timber", "t_portal_stone", "fx_drip", "fx_splash", "fx_mote", "fx_sparkle",
             "fx_rockdust"]
    cell = 256
    sheet = np.ones((cell, len(names) * cell, 3))
    for i, nm in enumerate(names):
        img = bpy.data.images.load(os.path.join(E.OUT_TEX, nm + ".png"))
        w, h = img.size
        px4 = np.array(img.pixels[:]).reshape(h, w, 4)[::-1]
        if nm.startswith("fx_"):      # sprites over a dark backdrop, not tiled
            px = px4[..., :3] * px4[..., 3:] + np.array([0.12, 0.1, 0.2]) * (1 - px4[..., 3:])
            rep = px
        else:
            rep = np.tile(px4[..., :3], (2, 2, 1))
        sy = np.linspace(0, rep.shape[0] - 1, cell).astype(int)
        sx = np.linspace(0, rep.shape[1] - 1, cell).astype(int)
        sheet[:, i * cell:(i + 1) * cell] = rep[sy][:, sx]
    os.makedirs(os.path.join(E.OUT_RENDERS, "design"), exist_ok=True)
    T.write_png("_sheet_cave", sheet)
    os.replace(os.path.join(E.OUT_TEX, "_sheet_cave.png"), os.path.join(E.OUT_RENDERS, "design", "tex_cave_sheet.png"))


def main():
    build_all()
    preview()
