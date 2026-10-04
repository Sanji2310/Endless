"""
Seamless material tiles for Pongo v6 (numpy): each writes a colour/luminance tile <name>.png and a height map
<name>_h.png (bump). Colour tiles are luminance detail around 0.8..1.0 multiplied by the material colour, except
the cookie which carries its own colours. Node structures follow docs/TUTORIAL_NOTES.md (weave from two wave
patterns + thread noise, chained bumps, sheen for fabric; Voronoi lumps + chips for the cookie surface).
"""
import math
import numpy as np
import texgen as T


def _grid(n):
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float64)
    return xs / n, ys / n


def twill(name, n=512, wales=36, steep=1, contrast=0.16, seed=1):
    """Twill weave: diagonal wales (steep=1: 45 deg cotton twill, 2: ~63 deg gabardine), yarn noise along the
    wales, slubs and a faint cross weave."""
    xs, ys = _grid(n)
    ph = xs * wales + ys * wales * steep
    ridge = 0.5 + 0.5 * np.cos(2 * np.pi * ph)
    ridge = ridge ** 0.7
    # yarn twist: fine periodic bumps along each wale
    twist = 0.5 + 0.5 * np.cos(2 * np.pi * (ys * wales * 3 - xs * wales * 0.0) + np.pi * ph)
    yarn = T.noise(n, 70, seed=seed)
    slub = T.noise(n, 6, seed=seed + 1)
    h = ridge * (0.8 + 0.2 * twist) * (0.85 + 0.3 * (yarn - 0.5)) + 0.25 * (slub - 0.5)
    h = (h - h.min()) / (h.max() - h.min())
    lum = 1.0 - contrast * (1 - ridge) - 0.05 * (slub - 0.5) - 0.04 * (yarn - 0.5)
    T.write_gray(name, np.clip(lum, 0, 1))
    T.write_gray(name + "_h", h)


def knit(name, n=512, cols=8, rows=11, seed=3):
    """Rib knit (2x2): columns of V-stitches, every third column a recessed purl rib."""
    xs, ys = _grid(n)
    u = xs * cols
    v = ys * rows
    fu, fv = u % 1.0, v % 1.0
    col = np.floor(u).astype(int)

    def leg(cx, ang):
        c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        dx, dy = fu - cx, fv - 0.5
        a = (dx * c + dy * s) / 0.17
        b = (-dx * s + dy * c) / 0.5
        r = np.sqrt(a * a + b * b)
        return np.clip(1 - r, 0, 1) ** 0.6
    st = np.maximum(leg(0.3, 62), leg(0.7, -62))
    purl = (col % 3 == 2)
    bump = 0.5 + 0.5 * np.cos(2 * np.pi * fv)
    h = np.where(purl, 0.25 * bump, st)
    fuzz = T.noise(n, 90, seed=seed)
    h = h * (0.85 + 0.3 * (fuzz - 0.5))
    h = T.blur(h, 0.8)
    lum = 0.72 + 0.28 * np.clip(h / max(h.max(), 1e-6), 0, 1) + 0.04 * (fuzz - 0.5)
    T.write_gray(name, np.clip(lum, 0, 1))
    T.write_gray(name + "_h", np.clip(h / max(h.max(), 1e-6), 0, 1))


def leather(name, n=512, cells=900, seed=5):
    """Leather grain: Voronoi pebble cells separated by fine grooves, soft creases, uneven tone."""
    rng = np.random.default_rng(seed)
    pts = rng.uniform(0, n, (cells, 2))
    f1, f2, _ = T.voronoi(n, pts)
    edge = f2 - f1
    groove = np.exp(-(edge / 1.6) ** 2)
    pebble = 1 - np.clip(f1 / (np.median(f1) * 2.2), 0, 1) ** 2
    crease = T.noise(n, 5, seed=seed + 1, octaves=3)
    wr = np.abs(np.sin(2 * np.pi * (T.noise(n, 3, seed=seed + 2) * 3)))
    h = 0.6 * pebble - 0.55 * groove + 0.25 * (crease - 0.5) - 0.12 * np.exp(-(wr / 0.08) ** 2)
    h = (h - h.min()) / (h.max() - h.min())
    lum = 0.9 + 0.08 * (h - 0.5) - 0.12 * (crease - 0.5) - 0.06 * groove
    T.write_gray(name, np.clip(lum, 0, 1))
    T.write_gray(name + "_h", h)


def hammered(name, n=512, dents=140, seed=7):
    """Hammered gold: overlapping shallow round dents with soft rims, a little fine brushing."""
    rng = np.random.default_rng(seed)
    pts = rng.uniform(0, n, (dents, 2))
    f1, f2, _ = T.voronoi(n, pts)
    rad = np.median(f2) * 0.9
    dent = -(1 - np.clip(f1 / rad, 0, 1) ** 2)
    rim = np.exp(-((f2 - f1) / 2.0) ** 2) * 0.25
    brush = T.noise(n, 120, seed=seed + 1) * 0.15
    h = dent + rim + brush
    h = (h - h.min()) / (h.max() - h.min())
    lum = 0.92 + 0.08 * h
    T.write_gray(name, lum)
    T.write_gray(name + "_h", h)


def cookie(name, n=512, chips=22, seed=9):
    """Baked cookie surface (own colours): browned dough with lumps, fine sugar crust, cracks and chocolate chips."""
    rng = np.random.default_rng(seed)
    lump = T.noise(n, 7, seed=seed, octaves=3, gain=0.55)
    fine = T.noise(n, 60, seed=seed + 1)
    pts = rng.uniform(0, n, (60, 2))
    f1, f2, _ = T.voronoi(n, pts)
    crack = np.exp(-((f2 - f1) / 1.8) ** 2) * (T.noise(n, 4, seed=seed + 2) > 0.52)
    h = 0.65 * lump + 0.15 * fine - 0.35 * crack
    brown = np.clip((lump - 0.35) * 1.8, 0, 1)
    dough = T.colorize(brown, 0xE0A962, 0xA8622A)
    dough = dough * (0.94 + 0.12 * (fine[..., None] - 0.5))
    dough = dough * (1 - 0.35 * crack[..., None])
    # chocolate chips: irregular dark blobs, glossy-ish and raised
    cpts = rng.uniform(0, n, (chips, 2))
    xs, ys = np.mgrid[0:n, 0:n].astype(np.float64)
    chipmask = np.zeros((n, n))
    for (px, py) in cpts:
        r = rng.uniform(9, 18)
        dx = np.abs(xs - px); dx = np.minimum(dx, n - dx)
        dy = np.abs(ys - py); dy = np.minimum(dy, n - dy)
        ang = np.arctan2(dy, dx)
        rr = np.sqrt(dx * dx + dy * dy) / (r * (1 + 0.25 * np.sin(ang * 3 + px) + 0.15 * np.sin(ang * 5 + py)))
        chipmask = np.maximum(chipmask, np.clip(1.4 - rr * 1.4, 0, 1))
    chip_col = T.colorize(fine, 0x3A2014, 0x5A3320)
    img = dough * (1 - chipmask[..., None]) + chip_col * chipmask[..., None]
    h = h * (1 - chipmask) + (0.9 + 0.1 * fine) * chipmask
    T.write_png(name, np.clip(img, 0, 1))
    T.write_gray(name + "_h", np.clip(h, 0, 1))


def gabardine(name, n=512):
    twill(name, n, wales=44, steep=2, contrast=0.1, seed=11)


def build_all():
    twill("t6_twill")
    gabardine("t6_gabardine")
    knit("t6_knit")
    leather("t6_leather")
    hammered("t6_hammer")
    cookie("t6_cookie")
