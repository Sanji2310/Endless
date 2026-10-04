"""Painted (non-repeating) tiles for the city: windows, shop fronts, signs, vending machines."""
import math, random
import erlib as E
import paint as PT


def _glass(c, x, y, w, h, top=0x6C9CC8, bot=0xBFE0F2, dark=False):
    if dark:
        top, bot = 0x334A66, 0x6F8EAE
    c.gradient_poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], [(bot, 1), (bot, 1), (top, 1), (top, 1)])


def _streaks(c, x, y, w, h, alpha=0.55):
    """Diagonal anime glass highlights."""
    for (u, t, a) in ((0.18, 0.16, alpha), (0.42, 0.06, alpha * 0.8), (0.7, 0.1, alpha * 0.6)):
        x0 = x + u * w
        c.poly([(x0, y + h), (x0 + t * w, y + h), (x0 + t * w - 0.45 * h, y), (x0 - 0.45 * h, y)][:4], 0xFFFFFF, a)


def window(name, kind="curtain", w=128, h=160, seed=0, curtain=0xF2A6B8):
    """Sliding sash window, two panes. kind: curtain | blinds | frosted | dark | shoji."""
    rnd = random.Random(seed)
    c = PT.Canvas(name, w, h)
    c.rect(0, 0, w, h, 0xE8E6E0)
    if kind == "frosted":
        c.gradient_poly([(0, 0), (w, 0), (w, h), (0, h)], [(0xDDE8EC, 1), (0xDDE8EC, 1), (0xF4F8F8, 1), (0xF4F8F8, 1)])
        for i in range(0, w, 8):
            c.rect(i, 0, 3, h, 0xFFFFFF, 0.35)
    elif kind == "shoji":
        c.rect(0, 0, w, h, 0xF6EFD8)
        for i in range(1, 4):
            c.rect(i * w / 4 - 1.5, 0, 3, h, 0xB08A5C)
        for j in range(1, 6):
            c.rect(0, j * h / 6 - 1.5, w, 3, 0xB08A5C)
    else:
        _glass(c, 0, 0, w, h, dark=(kind == "dark"))
        if kind == "curtain":
            # sheer lace then side curtains with folds
            c.rect(0, 0, w, h, 0xF8F4EE, 0.45)
            for side in (0, 1):
                x0 = 0 if side == 0 else w * 0.7
                cw = w * 0.3
                pts = [(x0, 0), (x0 + cw, 0), (x0 + cw - (8 if side == 0 else -8), h * 0.5), (x0 + cw, h), (x0, h)]
                c.poly([(x0, 0), (x0 + cw, 0), (x0 + cw, h), (x0, h)], curtain)
                for k in range(3):
                    fx = x0 + cw * (0.2 + 0.3 * k)
                    c.stroke([(fx, 2), (fx + 2, h * 0.5), (fx, h - 2)], 3, 3, E.shade_hex(curtain, 0.8), 0.8)
            c.rect(0, h - 10, w, 10, E.shade_hex(curtain, 0.85))
        elif kind == "blinds":
            for j in range(0, h, 9):
                c.rect(0, j, w, 6, 0xEDE3CC)
                c.rect(0, j, w, 2, 0xC9BC9E)
            c.rect(w * 0.3, 0, 2, h, 0xB8AB8E)
        elif kind == "dark":
            # room interior silhouettes: shelf, lamp shade
            c.rect(w * 0.08, 0, w * 0.3, h * 0.55, 0x2A3550)
            c.rect(w * 0.1, h * 0.2, w * 0.26, 3, 0x51607E)
            c.rect(w * 0.1, h * 0.38, w * 0.26, 3, 0x51607E)
            c.poly([(w * 0.62, h * 0.62), (w * 0.82, h * 0.62), (w * 0.78, h * 0.75), (w * 0.66, h * 0.75)], 0x5E6E8E)
        _streaks(c, 0, 0, w, h, 0.4 if kind != "dark" else 0.25)
    # sash frames: outer, meeting rail in the middle
    fr = 0xC8CCD2
    c.rect(0, 0, w, 6, fr); c.rect(0, h - 6, w, 6, fr)
    c.rect(0, 0, 6, h, fr); c.rect(w - 6, 0, 6, h, fr)
    c.rect(w / 2 - 4, 0, 8, h, fr)
    c.rect(w / 2 - 1, 0, 2, h, 0x8E949C)
    # latch
    c.rect(w / 2 - 6, h * 0.48, 12, 6, 0x6E747C)
    return c.save()


def shopfront(name="w_shop", w=512, h=256):
    """Konbini glass front: shelves stocked with colourful goods, magazine rack, posters."""
    rnd = random.Random(7)
    c = PT.Canvas(name, w, h)
    c.gradient_poly([(0, 0), (w, 0), (w, h), (0, h)], [(0xF4F7F2, 1), (0xF4F7F2, 1), (0xFFFFFF, 1), (0xFFFFFF, 1)])
    # ceiling lights
    for i in range(6):
        c.rect(20 + i * 82, h - 18, 60, 6, 0xFFFFFF)
    # back shelves (3 rows of goods)
    for row in range(3):
        y = 40 + row * 46
        c.rect(0, y - 6, w, 6, 0xB9C0C8)
        x = 4
        while x < w - 10:
            bw = rnd.choice((8, 10, 12, 16))
            bh = rnd.choice((18, 22, 28, 34))
            col = rnd.choice((0xE8473C, 0xF5B82E, 0x3E8FE0, 0x52B66A, 0xF07AA6, 0xFFFFFF, 0x7A5CCB, 0xF28B2C))
            c.rect(x, y, bw, bh, col)
            c.rect(x, y + bh * 0.5, bw, bh * 0.18, 0xFFFFFF, 0.6)
            x += bw + 2
    # magazine rack under the window
    c.rect(0, 0, w, 34, 0x8E959E)
    x = 4
    while x < w - 20:
        col = rnd.choice((0xF04E6A, 0x2E7AD8, 0xF6C134, 0x62C07A, 0xFFFFFF))
        c.rect(x, 4, 22, 28, col)
        c.rect(x + 3, 20, 16, 6, 0x222222, 0.4)
        x += 26
    # posters on the glass
    c.rect(w * 0.06, h * 0.55, 60, 80, 0xFF6B3D)
    c.text("SALE", w * 0.06 + 30, h * 0.55 + 52, 20, 0xFFFFFF)
    c.text("おにぎり", w * 0.06 + 30, h * 0.55 + 24, 14, 0xFFFFFF, font=E.FONT_JP)
    c.rect(w * 0.82, h * 0.55, 60, 80, 0x2E7AD8)
    c.text("NEW", w * 0.82 + 30, h * 0.55 + 52, 20, 0xFFFFFF)
    c.text("ラムネ", w * 0.82 + 30, h * 0.55 + 24, 14, 0xFFFFFF, font=E.FONT_JP)
    _streaks(c, 0, 0, w, h, 0.3)
    # mullions
    for i in range(5):
        c.rect(i * w / 4 - 4, 0, 8, h, 0xC8CCD2)
    return c.save()


def konbini_sign(name="s_konbini", w=512, h=128):
    """Original chain: HOSHI MART (ほしマート) — white panel with a star and three stripes."""
    c = PT.Canvas(name, w, h)
    c.rect(0, 0, w, h, 0xFFFFFF)
    c.rect(0, 0, w, 18, 0x2BA35A)
    c.rect(0, 18, w, 12, 0xF5A623)
    c.rect(0, 30, w, 8, 0xE8473C)
    st = E.star_pts(5, 34, 15)
    c.poly([(70 + x, 82 + y) for (x, y) in st], 0xF5A623)
    c.text("HOSHI MART", 290, 92, 40, 0x1E5FB4, spacing=1.05)
    c.text("ほしマート 24h", 290, 52, 22, 0x2BA35A, font=E.FONT_JP)
    return c.save()


def vending(name="s_vending", w=128, h=256, seed=3, body=0xE8473C):
    """Drink vending machine front: lit display of cans and bottles, price buttons, logo, slot."""
    rnd = random.Random(seed)
    c = PT.Canvas(name, w, h)
    c.rect(0, 0, w, h, body)
    # display window
    c.rect(8, 96, w - 16, 150, 0xF6F8FA)
    for row in range(4):
        y = 104 + row * 36
        for k in range(6):
            x = 12 + k * 18
            col = rnd.choice((0xE8473C, 0x2E7AD8, 0xF6C134, 0x47B36B, 0xFFFFFF, 0x7A4A2A, 0xF07AA6, 0x1A1A1A))
            if rnd.random() < 0.5:
                c.rect(x, y, 13, 22, col)             # can
                c.rect(x, y + 9, 13, 5, 0xFFFFFF, 0.7)
            else:
                c.rect(x + 2, y, 9, 18, col)          # bottle
                c.rect(x + 4, y + 18, 5, 5, 0xF0F0F0)
            c.rect(x + 3, y - 6, 8, 4, 0x50E070)      # price button (lit)
    c.rect(8, 96, w - 16, 150, 0xFFFFFF, 0.12)
    _streaks(c, 8, 96, w - 16, 150, 0.35)
    # lower panel: coin slot, bill slot, logo, pickup flap
    c.rect(10, 70, 50, 18, 0x1E1E22)
    c.text("COLD", 35, 79, 10, 0x6EC0FF)
    c.rect(w - 30, 64, 16, 22, 0xB8BDC4)
    c.rect(w - 26, 72, 8, 3, 0x222222)
    c.rect(14, 10, w - 28, 34, 0x1E1E22)
    c.rect(18, 14, w - 36, 26, 0x3A3A42)
    c.text("PONGO", w / 2, 56, 14, 0xFFFFFF)
    return c.save()


def blob_shadow(name="s_blob", size=128):
    c = PT.Canvas(name, size, size)
    c.radial(size / 2, size / 2, 0, size * 0.48, 0xFFFFFF, 0xFFFFFF, 0.55, 0.0, 64)
    return c.save()


def build_all():
    E.reset()
    window("w_win_a", "curtain", seed=1, curtain=0xF2A6B8)
    window("w_win_b", "blinds", seed=2)
    window("w_win_c", "frosted", w=96, h=96, seed=3)
    window("w_win_d", "dark", seed=4)
    window("w_win_e", "curtain", seed=5, curtain=0x8FC6E8)
    window("w_win_f", "shoji", seed=6)
    shopfront()
    konbini_sign()
    vending("s_vending", body=0xE8473C, seed=3)
    vending("s_vending_b", body=0x2E7AD8, seed=8)
    blob_shadow()
