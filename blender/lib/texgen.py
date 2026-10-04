"""
texgen — numpy procedural painting for seamless anime textures.

All generators work on periodic grids (FFT noise, wrapped Voronoi) so every
tile repeats without seams. Most surface textures are painted as luminance
detail around 0.8-1.0 and get their hue from the material colour, so one tile
serves many buildings.
"""
import os, zlib, struct
import numpy as np
import erlib as E


def write_png(name, img):
    """img: HxWx3 or HxWx4 float array in 0..1 (sRGB), row 0 = top."""
    img = np.clip(img, 0.0, 1.0)
    h, w, c = img.shape
    data = (img * 255.0 + 0.5).astype(np.uint8)
    raw = b"".join(b"\x00" + data[y].tobytes() for y in range(h))
    ctype = 6 if c == 4 else 2

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, ctype, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path = os.path.join(E.OUT_TEX, name + ".png")
    with open(path, "wb") as f:
        f.write(png)
    print("tex", path, w, h)
    return path


def rgb(h):
    return np.array([((h >> 16) & 255) / 255.0, ((h >> 8) & 255) / 255.0, (h & 255) / 255.0])


def noise(n, freq, seed=0, octaves=1, gain=0.5, m=None):
    """Periodic band-limited noise in [0, 1]; freq = features per tile. m = height if non-square."""
    m = m or n
    rng = np.random.default_rng(seed)
    out = np.zeros((m, n))
    amp, tot = 1.0, 0.0
    fy = np.fft.fftfreq(m)[:, None] * m
    fx = np.fft.fftfreq(n)[None, :] * n
    r = np.sqrt(fx * fx + fy * fy)
    for o in range(octaves):
        f = freq * (2 ** o)
        spec = np.fft.fft2(rng.standard_normal((m, n)))
        filt = np.exp(-(r / max(f, 1e-3)) ** 2)
        layer = np.real(np.fft.ifft2(spec * filt))
        layer = (layer - layer.mean()) / (layer.std() + 1e-9)
        out += layer * amp
        tot += amp
        amp *= gain
    out /= tot
    return np.clip(0.5 + out * 0.18, 0, 1)


def voronoi(n, pts, m=None):
    """Wrapped Voronoi on an n x m tile. pts: (k,2) in pixels. Returns F1, F2, index."""
    m = m or n
    ys, xs = np.mgrid[0:m, 0:n].astype(np.float32)
    k = len(pts)
    best1 = np.full((m, n), 1e9, np.float32)
    best2 = np.full((m, n), 1e9, np.float32)
    idx = np.zeros((m, n), np.int32)
    for i, (px, py) in enumerate(pts):
        dx = np.abs(xs - px)
        dx = np.minimum(dx, n - dx)
        dy = np.abs(ys - py)
        dy = np.minimum(dy, m - dy)
        d = np.sqrt(dx * dx + dy * dy)
        closer = d < best1
        best2 = np.where(closer, best1, np.minimum(best2, d))
        idx = np.where(closer, i, idx)
        best1 = np.where(closer, d, best1)
    return best1, best2, idx


def smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def blur(img, sigma):
    """Periodic gaussian blur (FFT) of a 2D or 3D array."""
    if sigma <= 0:
        return img
    m, n = img.shape[:2]
    fy = np.fft.fftfreq(m)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    g = np.exp(-2 * (np.pi * sigma) ** 2 * (fx * fx + fy * fy))
    if img.ndim == 2:
        return np.real(np.fft.ifft2(np.fft.fft2(img) * g))
    return np.stack([np.real(np.fft.ifft2(np.fft.fft2(img[..., c]) * g)) for c in range(img.shape[2])], -1)


def shade_from_height(hgt, light=(-0.6, 0.7), strength=4.0):
    """Lambert-ish relief from a periodic height field (light from top-left)."""
    gx = (np.roll(hgt, -1, 1) - np.roll(hgt, 1, 1)) * 0.5
    gy = (np.roll(hgt, -1, 0) - np.roll(hgt, 1, 0)) * 0.5
    lx, ly = light
    return np.clip(-(gx * lx - gy * ly) * strength, -1, 1)


def colorize(lum, c0, c1):
    """Map a 0..1 field between two hex colours."""
    a, b = rgb(c0), rgb(c1)
    return a[None, None, :] * (1 - lum[..., None]) + b[None, None, :] * lum[..., None]


def poster(x, levels, mix=0.6):
    """Partial posterisation for the painted look."""
    q = np.round(x * levels) / levels
    return x * (1 - mix) + q * mix


# ----------------------------------------------------------------------------- vector painting (decals)

def _grid(w, h):
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    return xs + 0.5, ys + 0.5


def _seg_dist(xs, ys, ax, ay, bx, by):
    """Distance from every pixel to segment a-b, and the segment parameter t."""
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = np.clip(((xs - ax) * dx + (ys - ay) * dy) / max(L2, 1e-12), 0.0, 1.0)
    px, py = ax + t * dx - xs, ay + t * dy - ys
    return np.sqrt(px * px + py * py), t


def poly_cov(w, h, pts, soft=1.0):
    """Anti-aliased coverage (0..1) of a closed polygon (pixel coords, y down). soft: edge width in px."""
    xs, ys = _grid(w, h)
    inside = np.zeros((h, w), bool)
    dist = np.full((h, w), 1e9, np.float32)
    n = len(pts)
    for i in range(n):
        ax, ay = pts[i]
        bx, by = pts[(i + 1) % n]
        if (ay > ys[:, :1]).any() or True:
            cond = ((ay > ys) != (by > ys)) & (xs < (bx - ax) * (ys - ay) / ((by - ay) if by != ay else 1e-12) + ax)
            inside ^= cond
        d, _ = _seg_dist(xs, ys, ax, ay, bx, by)
        dist = np.minimum(dist, d)
    sd = np.where(inside, dist, -dist)
    return np.clip(0.5 + sd / max(soft, 1e-6), 0.0, 1.0)


def stroke_cov(w, h, pts, widths, soft=1.0):
    """Coverage of a polyline with per-point half-widths (px), round joins."""
    xs, ys = _grid(w, h)
    best = np.full((h, w), -1e9, np.float32)
    for i in range(len(pts) - 1):
        (ax, ay), (bx, by) = pts[i], pts[i + 1]
        d, t = _seg_dist(xs, ys, ax, ay, bx, by)
        hw = widths[i] + (widths[i + 1] - widths[i]) * t
        best = np.maximum(best, hw - d)
    return np.clip(0.5 + best / max(soft, 1e-6), 0.0, 1.0)


def ellipse_cov(w, h, cx, cy, rx, ry, rot=0.0, soft=1.0):
    xs, ys = _grid(w, h)
    c, s = np.cos(np.radians(rot)), np.sin(np.radians(rot))
    u = ((xs - cx) * c + (ys - cy) * s) / rx
    v = (-(xs - cx) * s + (ys - cy) * c) / ry
    r = np.sqrt(u * u + v * v)
    return np.clip(0.5 + (1.0 - r) * min(rx, ry) / max(soft, 1e-6), 0.0, 1.0)


def over(img, alpha, color, a):
    """Alpha-over a flat colour (hex or rgb array, or HxWx3 image) with coverage a into img/alpha (in place)."""
    col = rgb(color) if isinstance(color, int) else np.asarray(color)
    if col.ndim == 1:
        col = col[None, None, :]
    a3 = a[..., None]
    img[:] = img * (1 - a3) + col * a3
    alpha[:] = alpha + a * (1 - alpha)


def bezier2d(p0, p1, p2, p3, n=48):
    out = []
    for i in range(n):
        t = i / (n - 1)
        mt = 1 - t
        out.append((mt ** 3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t ** 3 * p3[0],
                    mt ** 3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t ** 3 * p3[1]))
    return out


def normal_from_height(hgt, strength=2.0):
    """Tangent-space (OpenGL, +Y up) normal map from a periodic height field (row 0 = top)."""
    gx = (np.roll(hgt, -1, 1) - np.roll(hgt, 1, 1)) * 0.5
    gy = (np.roll(hgt, 1, 0) - np.roll(hgt, -1, 0)) * 0.5      # +v is up (rows go down)
    nx, ny = -gx * strength, -gy * strength
    nz = np.ones_like(nx)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([nx / ln * 0.5 + 0.5, ny / ln * 0.5 + 0.5, nz / ln * 0.5 + 0.5], -1)


def write_gray(name, g):
    g = np.clip(g, 0, 1)
    return write_png(name, np.repeat(g[..., None], 3, 2))
