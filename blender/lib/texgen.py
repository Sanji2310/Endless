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
