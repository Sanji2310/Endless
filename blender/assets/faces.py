"""Painted anime face textures: eyes, mouths and brows for every character."""
import math
import erlib as E
import paint as PT


def _bez(p0, p1, p2, p3, n=24):
    out = []
    for i in range(n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def _clip(subject, clipper):
    """Sutherland–Hodgman polygon clip (clipper must be convex, CCW)."""
    def inside(p, a, b):
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= 0
    def inter(p, q, a, b):
        x1, y1, x2, y2 = p[0], p[1], q[0], q[1]
        x3, y3, x4, y4 = a[0], a[1], b[0], b[1]
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(den) < 1e-12:
            return q
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
    out = subject
    for i in range(len(clipper)):
        a, b = clipper[i], clipper[(i + 1) % len(clipper)]
        inp, out = out, []
        if not inp:
            break
        s = inp[-1]
        for e in inp:
            if inside(e, a, b):
                if not inside(s, a, b):
                    out.append(inter(s, e, a, b))
                out.append(e)
            elif inside(s, a, b):
                out.append(inter(s, e, a, b))
            s = e
    return out


def _ellipse(cx, cy, rx, ry, n=64):
    return [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]


def eye(name, iris_top, iris_mid, iris_bot, lash=0x1C1830, sclera=0xFFFFFF, shade=0xD9DDF2, size=256,
        shape="round", pupil=0x14101E, sparkle=True):
    """Right eye (viewer's left) of an anime face; the left eye mirrors the UVs."""
    c = PT.Canvas(name, size, size)
    s = size / 256.0
    def S(pts):
        return [(x * s, y * s) for (x, y) in pts]
    if shape == "sharp":      # cool / narrow (Kaito)
        top = _bez((38, 118), (80, 186), (170, 196), (226, 152))
        bot = _bez((226, 152), (190, 92), (95, 80), (38, 118))
    elif shape == "big":      # big sparkly (Hana, Yuki)
        top = _bez((34, 120), (62, 214), (190, 222), (228, 150))
        bot = _bez((228, 150), (205, 60), (70, 50), (34, 120))
    elif shape == "stern":    # inspector
        top = _bez((40, 130), (90, 170), (170, 176), (224, 150))
        bot = _bez((224, 150), (190, 100), (90, 96), (40, 130))
    else:                     # Pongo: bright, determined
        top = _bez((36, 118), (70, 200), (180, 210), (228, 152))
        bot = _bez((228, 152), (198, 72), (84, 62), (36, 118))
    almond = top[:-1] + bot[:-1]
    # make CCW for the clipper
    area = sum(almond[i][0] * almond[(i + 1) % len(almond)][1] - almond[(i + 1) % len(almond)][0] * almond[i][1] for i in range(len(almond)))
    if area < 0:
        almond = almond[::-1]
    c.poly(S(almond), sclera)
    # lid shadow on the sclera
    shadow_band = _clip(S([(0, 150), (256, 175), (256, 256), (0, 256)]), S(almond))
    if shadow_band:
        c.poly(shadow_band, shade)
    # iris with vertical gradient, clipped to the eye
    icx, icy = 134, 126 if shape != "sharp" else 130
    irx, iry = (52, 66) if shape != "sharp" else (44, 56)
    if shape == "big":
        irx, iry = 58, 74
    ir = _clip(S(_ellipse(icx, icy, irx, iry)), S(almond))
    if ir:
        ys = [p[1] for p in ir]
        y0, y1 = min(ys), max(ys)
        cols = []
        for (x, y) in ir:
            t = (y - y0) / max(y1 - y0, 1e-6)
            col = E.mix_hex(iris_bot, iris_mid, min(1, t * 1.6)) if t < 0.6 else E.mix_hex(iris_mid, iris_top, (t - 0.6) / 0.4)
            cols.append((col, 1.0))
        c.gradient_poly(ir, cols)
        # darker rim and inner ring
        ring = _clip(S(_ellipse(icx, icy + 4, irx * 0.62, iry * 0.62)), S(almond))
        if ring:
            c.poly(ring, E.mix_hex(iris_mid, pupil, 0.35), 0.35)
    pu = _clip(S(_ellipse(icx, icy + 4, irx * 0.36, iry * 0.46)), S(almond))
    if pu:
        c.poly(pu, pupil)
    # lower iris glow
    glow = _clip(S(_ellipse(icx, icy - iry * 0.55, irx * 0.6, iry * 0.28)), S(almond))
    if glow:
        c.poly(glow, E.mix_hex(iris_bot, 0xFFFFFF, 0.45), 0.55)
    if sparkle:
        c.circle(icx * s - 20 * s, (icy + 28) * s, 17 * s, 0xFFFFFF)
        c.circle(icx * s + 24 * s, (icy - 30) * s, 8 * s, 0xFFFFFF)
        c.circle(icx * s + 6 * s, (icy + 40) * s, 5 * s, 0xFFFFFF, 0.9)
    # upper lash: thick tapered stroke with a flick at the outer corner
    lash_pts = S(top)
    c.stroke(lash_pts, 9 * s, 16 * s, lash)
    c.curve(S([(222, 154)])[0], S([(236, 162)])[0], S([(244, 172)])[0], S([(250, 186)])[0], 12 * s, 2 * s, lash)
    c.curve(S([(214, 150)])[0], S([(230, 150)])[0], S([(240, 146)])[0], S([(248, 140)])[0], 7 * s, 1.5 * s, lash)
    # lower lash on the outer half
    lower = S(bot[:int(len(bot) * 0.45)])
    c.stroke(lower, 5 * s, 1.5 * s, lash, 0.9)
    return c.save()


def mouth(name, kind="grin", w=128, h=64, line=0x3B1E24, inner=0x8C2F3A, tongue=0xE06A6F):
    c = PT.Canvas(name, w, h)
    if kind == "grin":
        # open happy grin
        top = _bez((14, 44), (40, 34), (88, 34), (114, 44), 20)
        bot = _bez((114, 44), (96, 6), (32, 6), (14, 44), 20)
        shape = top[:-1] + bot[:-1]
        c.poly(shape, inner)
        ccw = shape if sum(shape[i][0] * shape[(i + 1) % len(shape)][1] - shape[(i + 1) % len(shape)][0] * shape[i][1] for i in range(len(shape))) > 0 else shape[::-1]
        tg = _clip(_ellipse(64, 14, 26, 11), ccw)
        if tg:
            c.poly(tg, tongue)
        c.poly([(24, 40), (104, 40), (100, 46), (28, 46)], 0xFFFFFF)
        c.stroke(top, 5, 5, line)
        c.stroke(bot, 3, 3, line, 0.8)
    elif kind == "smile":
        c.curve((18, 40), (40, 18), (88, 18), (110, 40), 6, 6, line)
    elif kind == "cat":
        c.curve((18, 40), (30, 22), (52, 22), (64, 36), 5, 5, line)
        c.curve((64, 36), (76, 22), (98, 22), (110, 40), 5, 5, line)
    elif kind == "flat":
        c.curve((34, 32), (54, 30), (74, 30), (94, 32), 5, 5, line)
    elif kind == "shout":
        shape = _ellipse(64, 30, 30, 22)
        c.poly(shape, inner)
        c.ellipse(64, 18, 18, 8, tongue)
        c.stroke(shape + [shape[0]], 4, 4, line)
    return c.save()


def blush(name="d_blush", w=128, h=64):
    c = PT.Canvas(name, w, h)
    c.radial(64, 32, 0, 60, 0xFF7A8A, 0xFF7A8A, 0.55, 0.0, 48, 1.0, 0.5)
    for i in range(3):
        x = 44 + i * 16
        c.stroke([(x, 22), (x + 8, 42)], 4, 3, 0xE8536A, 0.9)
    return c.save()


def build_all():
    E.reset()
    # Pongo: warm amber eyes
    eye("d_eye_pongo", 0x7A3A10, 0xE0892A, 0xFFD27A)
    # Hana: rose pink sparkle
    eye("d_eye_hana", 0x7A1F4A, 0xE0508C, 0xFFB6D4, shape="big")
    # Kaito: steel blue narrow
    eye("d_eye_kaito", 0x10284A, 0x2F6FB8, 0x8EC5F0, shape="sharp")
    # Yuki: icy teal big
    eye("d_eye_yuki", 0x0B4A5A, 0x27A7B8, 0xA9F2F2, shape="big")
    # Daigo: small stern dark eyes
    eye("d_eye_daigo", 0x2A1A10, 0x5A3A22, 0x9A6A44, shape="stern", sparkle=False)
    # Kuro (dog): glossy black-brown
    eye("d_eye_kuro", 0x120A06, 0x3A2212, 0x7A4A28, shape="round")
    mouth("d_mouth_grin", "grin")
    mouth("d_mouth_smile", "smile")
    mouth("d_mouth_cat", "cat")
    mouth("d_mouth_flat", "flat")
    mouth("d_mouth_shout", "shout")
    blush()


def pongo_logo(name="d_pongo_logo", size=256):
    """Chest emblem: orange disc, white P with speed streaks, navy ring."""
    c = PT.Canvas(name, size, size)
    s = size / 256.0
    c.circle(128 * s, 128 * s, 120 * s, 0x1E2B55)
    c.circle(128 * s, 128 * s, 104 * s, 0xFF7A1F)
    c.radial(128 * s, 150 * s, 0, 90 * s, 0xFFB25C, 0xFF7A1F, 0.9, 0.0, 48)
    for i, (y, L) in enumerate(((150, 70), (124, 90), (98, 60))):
        c.stroke([(40 * s, y * s), ((40 + L) * s, (y + 4) * s)], 7 * s, 1.5 * s, 0xFFFFFF, 0.9)
    c.text("P", 150 * s, 126 * s, 150 * s, 0xFFFFFF, font=E.FONT_LATIN, outline=0.035, outline_color=0x1E2B55)
    return c.save()


def pongo_back(name="d_pongo_back", w=512, h=256):
    """Back print: PONGO in bold italics over a sunburst star, with a katakana tag."""
    c = PT.Canvas(name, w, h)
    cx, cy = w / 2, h / 2 + 10
    for i in range(12):
        a = math.radians(i * 30 + 15)
        c.poly([(cx, cy), (cx + 170 * math.cos(a - 0.09), cy + 170 * math.sin(a - 0.09)),
                (cx + 170 * math.cos(a + 0.09), cy + 170 * math.sin(a + 0.09))], 0xFFC24A, 0.35)
    c.poly([(cx + 80 * math.cos(math.radians(90 + 72 * k)) * (1 if k % 1 == 0 else 1), cy + 80 * math.sin(math.radians(90 + 72 * k)))
            for k in range(5)], 0xFF7A1F, 0.0)
    star = []
    for k in range(10):
        r = 92 if k % 2 == 0 else 40
        a = math.radians(90 + 36 * k)
        star.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    c.poly(star, 0xFF7A1F)
    c.text("PONGO", cx, cy - 4, 118, 0xFFFFFF, font=E.FONT_LATIN, outline=0.06, outline_color=0x1E2B55, spacing=0.95)
    c.text("ポンゴ", cx, cy - 92, 40, 0x2F6BDA, font=E.FONT_JP)
    return c.save()


def build_clothing_art():
    E.reset()
    pongo_logo()
    pongo_back()
