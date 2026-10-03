"""
Sakura Line buildings and street props.

Every building is modelled with its street front facing -Y (toward a camera at -Y),
centred on x = 0 with its front wall at y = 0 and the ground at z = 0; the depth
runs toward +Y. The scene builder rotates them to face the track.
"""
import math, random
import bpy
from mathutils import Vector, Matrix
import erlib as E

FLOOR_H = 2.8

WALLS = {
    "cream": (0xF3E6CC, "t_siding", 1.0),
    "mint": (0xCFE6D6, "t_siding", 1.0),
    "sky": (0xCFDDEB, "t_siding", 1.0),
    "white": (0xF5F2EA, "t_plaster", 2.0),
    "beige": (0xE6D3B8, "t_plaster", 2.0),
    "brown": (0x9C7458, "t_siding", 1.0),
    "pink": (0xF2D5D2, "t_plaster", 2.0),
}
ROOFS = {
    "ibushi": 0x6D7C92,   # silver-grey smoked tiles
    "navy": 0x3E5478,
    "brick": 0xB25A3C,
    "green": 0x4E7E6A,
    "choco": 0x6A4E44,
}


def mats():
    M = E.mat
    for k, (col, tex, sc) in WALLS.items():
        M("wall_" + k, col, tex, soft=0.15, rim=0.2, outline=1.0)
    for k, col in ROOFS.items():
        M("roof_" + k, col, "t_kawara", spec=0.25, rim=0.3, soft=0.1, outline=1.0)
        M("ridge_" + k, E.shade_hex(col, 0.85), spec=0.3, rim=0.3, soft=0.1, outline=1.0)
    M("foundation", 0xB9B4AA, "t_concrete", soft=0.15, rim=0.1, outline=0.8)
    M("trim", 0xF4F3EF, soft=0.12, rim=0.2, outline=0.8)
    M("trim_dark", 0x5A5048, soft=0.12, rim=0.2, outline=0.8)
    M("sash", 0xC9CED6, spec=0.4, rim=0.3, soft=0.1, flags=E.F_METAL, outline=0.6)
    M("gutter", 0xE9E6DF, spec=0.2, rim=0.2, outline=0.6)
    M("gutter_brown", 0x6A4E3E, spec=0.2, rim=0.2, outline=0.6)
    M("door_wood", 0x8A5A3A, "t_wood", spec=0.15, rim=0.2, outline=0.8)
    M("door_steel", 0x5E6E7E, spec=0.4, rim=0.3, outline=0.8)
    M("rail_white", 0xF2F2EE, spec=0.3, rim=0.3, outline=0.6)
    M("rail_metal", 0x9AA1AA, spec=0.5, rim=0.3, flags=E.F_METAL, outline=0.6)
    M("block", 0xC8C2B6, "t_blockwall", soft=0.15, rim=0.15, outline=0.8)
    M("ac_unit", 0xEEEDE8, spec=0.2, rim=0.2, outline=0.7)
    M("ac_grill", 0x55595F, soft=0.1, rim=0.0, outline=0)
    M("pot", 0xB4643C, soft=0.12, rim=0.2, outline=0.6)
    M("bush", 0xFFFFFF, "t_leaves", soft=0.3, rim=0.25, outline=1.0, flags=E.F_FOLIAGE)
    M("laundry_w", 0xF8F8F4, soft=0.25, rim=0.2, outline=0.6, flags=E.F_DOUBLE | E.F_FOLIAGE, sway=0.6)
    M("laundry_b", 0x7FB2E6, soft=0.25, rim=0.2, outline=0.6, flags=E.F_DOUBLE | E.F_FOLIAGE, sway=0.6)
    M("laundry_p", 0xF2A6B8, soft=0.25, rim=0.2, outline=0.6, flags=E.F_DOUBLE | E.F_FOLIAGE, sway=0.6)
    M("laundry_y", 0xF6D35A, soft=0.25, rim=0.2, outline=0.6, flags=E.F_DOUBLE | E.F_FOLIAGE, sway=0.6)
    M("futon", 0xF6E7EE, "t_plaster", soft=0.3, rim=0.2, outline=0.8)
    M("yard", 0xFFFFFF, "t_dirt", soft=0.2, rim=0.1, outline=0)
    M("mailbox", 0xD8473C, spec=0.4, rim=0.3, outline=0.6)
    M("nameplate", 0xE9DDC4, soft=0.1, rim=0.1, outline=0.4)
    M("glass_door", 0x9EC4DE, spec=0.8, rim=0.4, soft=0.05, flags=E.F_GLASS, outline=0.6)
    for w in ("a", "b", "c", "d", "e", "f"):
        night = E.F_NIGHT if w in ("a", "b", "e", "f") else 0
        M("win_" + w, 0xFFFFFF, "w_win_" + w, spec=0.6, rim=0.1, soft=0.05, emis=0.35 if night else 0.0,
          flags=night, outline=0, shadow=0xC4C8DC)
    M("shopfront", 0xFFFFFF, "w_shop", spec=0.5, emis=0.25, soft=0.05, outline=0, shadow=0xE0E2EA)
    M("konbini_sign", 0xFFFFFF, "s_konbini", emis=0.3, soft=0.05, rim=0.1, outline=0.6, shadow=0xE8E8EE)
    M("vend_face", 0xFFFFFF, "s_vending", emis=0.3, spec=0.4, soft=0.05, outline=0, shadow=0xE0E0E8)
    M("vend_face_b", 0xFFFFFF, "s_vending_b", emis=0.3, spec=0.4, soft=0.05, outline=0, shadow=0xE0E0E8)
    M("vend_red", 0xE8473C, spec=0.4, rim=0.3, outline=0.8)
    M("vend_blue", 0x2E7AD8, spec=0.4, rim=0.3, outline=0.8)
    M("awning_g", 0x2BA35A, soft=0.15, rim=0.2, outline=0.8)
    M("bike_frame", 0x3AA3C9, spec=0.5, rim=0.3, outline=0.6)
    M("tyre", 0x26272C, soft=0.1, rim=0.1, outline=0.5)


# ----------------------------------------------------------------------------- parts

def window(m, x, z, w, h, kind="a", wall_y=0.0, sill=True, shutter_box=False, lod=0):
    """Window on a wall facing -Y (wall surface at y = wall_y): painted glass panel, aluminium frame, sill."""
    y = wall_y
    m.mat("win_" + kind)
    f = m.poly([(x - w / 2, y - 0.012, z - h / 2), (x + w / 2, y - 0.012, z - h / 2),
                (x + w / 2, y - 0.012, z + h / 2), (x - w / 2, y - 0.012, z + h / 2)], uv=None)
    m.uv_rect(f, 0, 0, 1, 1, axis=((1, 0, 0), (0, 0, 1)))
    m.mat("sash")
    t, d = 0.05, 0.06
    m.box((x, y - d / 2, z + h / 2 + t / 2), (w + 2 * t, d, t), smooth=False)
    m.box((x, y - d / 2, z - h / 2 - t / 2), (w + 2 * t, d, t), smooth=False)
    m.box((x - w / 2 - t / 2, y - d / 2, z), (t, d, h), smooth=False)
    m.box((x + w / 2 + t / 2, y - d / 2, z), (t, d, h), smooth=False)
    if sill:
        m.mat("trim")
        m.box((x, y - 0.07, z - h / 2 - t - 0.025), (w + 0.24, 0.14, 0.05), bevel=(0.01, 1) if lod == 0 else None)
    if shutter_box:
        m.mat("sash")
        m.box((x, y - 0.13, z + h / 2 + t + 0.12), (w + 0.2, 0.26, 0.24), bevel=(0.02, 1) if lod == 0 else None)
        m.box((x - w / 2 - 0.08, y - 0.09, z), (0.06, 0.18, h), smooth=False)
        m.box((x + w / 2 + 0.08, y - 0.09, z), (0.06, 0.18, h), smooth=False)


def ac_unit(m, c, lod=0):
    """Outdoor air-conditioner unit on a small stand, facing -Y."""
    x, y, z = c
    m.mat("ac_unit")
    m.rbox((x, y, z + 0.3), (0.78, 0.28, 0.56), r=0.03, seg=2 if lod == 0 else 1)
    m.mat("ac_grill")
    m.cyl((x - 0.1, y - 0.141, z + 0.3), r=0.2, h=0.01, seg=20 if lod == 0 else 10, axis='Y')
    if lod == 0:
        m.mat("ac_unit")
        for k in range(4):
            m.box((x - 0.1, y - 0.15, z + 0.14 + k * 0.1), (0.42, 0.012, 0.012), smooth=False)
        m.mat("rail_metal")
        for sx in (-0.3, 0.3):
            m.box((x + sx, y, z + 0.01), (0.06, 0.3, 0.02), smooth=False)
        m.mat("gutter")
        m.tube([(x + 0.4, y + 0.05, z + 0.4), (x + 0.5, y + 0.05, z + 0.4), (x + 0.5, y + 0.12, z + 1.4)], r=0.025, seg=6)


def gutters(m, w, d, eave_z, lod=0, mat="gutter"):
    """Half-round gutters along the front/back eaves and downpipes at the front corners."""
    m.mat(mat)
    for yy in (-0.62, d + 0.62):
        m.cyl((0, yy, eave_z - 0.06), r=0.06, h=w + 1.2, seg=8 if lod == 0 else 5, axis='X')
    for sx in (-1, 1):
        x = sx * (w / 2 + 0.12)
        m.tube([(x + sx * 0.4, -0.6, eave_z - 0.1), (x, -0.15, eave_z - 0.4), (x, -0.15, 0.25)], r=0.04, seg=6 if lod == 0 else 4)
        if lod == 0:
            for zz in (eave_z - 1.6, 1.2):
                m.box((x, -0.06, zz), (0.1, 0.12, 0.04), smooth=False)


def hip_roof(m, w, d, z0, pitch=0.5, over=0.6, roof="ibushi", lod=0, gable=False):
    """Hipped (yosemune) or gable (kirizuma) kawara roof with thick eaves and a ridge cap."""
    W, D = w / 2 + over, d / 2 + over
    cy = d / 2
    rise = D * pitch
    ridge_half = max(W - D, 0.4) if not gable else W
    m.mat("roof_" + roof, uvscale=1.0)
    th = 0.14
    # roof planes (front and back trapezoids; hips at the ends) — each with eave thickness
    zr = z0 + rise
    fl = [(-W, cy - D, z0), (W, cy - D, z0), (ridge_half, cy, zr), (-ridge_half, cy, zr)]
    bk = [(W, cy + D, z0), (-W, cy + D, z0), (-ridge_half, cy, zr), (ridge_half, cy, zr)]
    for quad in (fl, bk):
        f = m.poly(quad, uv=None)
        _roof_uv(m, f, quad)
    if not gable:
        for sx in (-1, 1):
            tri = [(sx * W, cy - D, z0), (sx * ridge_half, cy, zr), (sx * W, cy + D, z0)]
            if sx < 0:
                tri = tri[::-1]
            f = m.poly(tri, uv=None)
            _roof_uv(m, f, tri, side=True)
    else:
        # gable walls get the wall material later; verge boards here
        m.mat("trim_dark")
        for sx in (-1, 1):
            for (a, b) in (((sx * W, cy - D, z0), (sx * W, cy, zr)), ((sx * W, cy, zr), (sx * W, cy + D, z0))):
                m.sweep([a, b], [(-0.05, -0.12), (0.05, -0.12), (0.05, 0.06), (-0.05, 0.06)], up=(1, 0, 0), smooth=False)
    # eave fascia boards (thickness of the roof)
    m.mat("trim_dark")
    m.box((0, cy - D - 0.02, z0 - th / 2), (2 * W + 0.04, 0.05, th), smooth=False)
    m.box((0, cy + D + 0.02, z0 - th / 2), (2 * W + 0.04, 0.05, th), smooth=False)
    if not gable:
        m.box((-W - 0.02, cy, z0 - th / 2), (0.05, 2 * D + 0.04, th), smooth=False)
        m.box((W + 0.02, cy, z0 - th / 2), (0.05, 2 * D + 0.04, th), smooth=False)
    # soffit under the eaves
    m.mat("trim")
    m.poly([(-W, cy - D, z0 - th), (-W, cy + D, z0 - th), (W, cy + D, z0 - th), (W, cy - D, z0 - th)])
    # ridge cap (rounded) and hip caps, plus onigawara end tiles
    m.mat("ridge_" + roof)
    m.cyl((0, cy, zr + 0.06), r=0.13, h=2 * ridge_half + 0.2, seg=10 if lod == 0 else 6, axis='X')
    m.box((0, cy, zr + 0.0), (2 * ridge_half + 0.2, 0.3, 0.12), smooth=False)
    if not gable:
        for sx in (-1, 1):
            for sy in (-1, 1):
                m.tube([(sx * ridge_half, cy, zr + 0.06), (sx * W, cy + sy * D, z0 + 0.06)], r=0.09, seg=8 if lod == 0 else 5)
    if lod == 0:
        for sx in (-1, 1):
            m.box((sx * (ridge_half + 0.1), cy, zr + 0.12), (0.12, 0.42, 0.36), bevel=(0.04, 2))
    # front row of round eave-end tiles (nokigawara)
    if lod == 0:
        m.mat("ridge_" + roof)
        n = int(2 * W / 0.3)
        for i in range(n):
            x = -W + (i + 0.5) * 2 * W / n
            m.cyl((x, cy - D - 0.04, z0 + 0.02), r=0.075, h=0.06, seg=8, axis='Y')
    return zr


def _roof_uv(m, faces, quad, side=False):
    """UV so kawara rows run along the eave and v climbs up the slope (1 m per tile)."""
    p0, p1 = Vector(quad[0]), Vector(quad[1])
    along = (p1 - p0).normalized()
    up = Vector(quad[-1]) - p0
    up = (up - along * up.dot(along)).normalized()
    for f in faces:
        for l in f.loops:
            q = l.vert.co
            l[m.uv].uv = ((q - p0).dot(along), (q - p0).dot(up))


def railing(m, x0, x1, y, z, h=1.0, lod=0, mat="rail_metal", bars=True):
    m.mat(mat)
    m.box(((x0 + x1) / 2, y, z + h), ((x1 - x0), 0.06, 0.05), bevel=(0.01, 1) if lod == 0 else None)
    m.box(((x0 + x1) / 2, y, z + 0.08), ((x1 - x0), 0.04, 0.04), smooth=False)
    if bars:
        step = 0.11 if lod == 0 else 0.33
        n = max(1, int((x1 - x0) / step))
        for i in range(n + 1):
            x = x0 + (x1 - x0) * i / n
            m.box((x, y, z + 0.08 + (h - 0.08) / 2), (0.022, 0.022, h - 0.08), smooth=False)


def laundry(m, x0, x1, y, z, rnd, lod=0):
    """Laundry pole with hanging shirts, towels and a futon over the railing."""
    m.mat("rail_metal")
    m.cyl(((x0 + x1) / 2, y, z), r=0.018, h=x1 - x0, seg=6, axis='X')
    for sx in (x0, x1):
        m.box((sx, y, z - 0.25), (0.03, 0.03, 0.5), smooth=False)
    x = x0 + 0.25
    palette = ["laundry_w", "laundry_b", "laundry_p", "laundry_y", "laundry_w", "laundry_b"]
    rnd.shuffle(palette)
    i = 0
    while x < x1 - 0.3:
        kind = rnd.choice(("shirt", "towel", "towel", "pants"))
        col = palette[i % len(palette)]
        i += 1
        m.mat(col)
        if kind == "shirt":
            pts = [(-0.25, 0), (0.25, 0), (0.32, -0.12), (0.2, -0.18), (0.18, -0.6), (-0.18, -0.6), (-0.2, -0.18), (-0.32, -0.12)]
            ww = 0.6
        elif kind == "pants":
            pts = [(-0.2, 0), (0.2, 0), (0.2, -0.75), (0.04, -0.75), (0.0, -0.25), (-0.04, -0.75), (-0.2, -0.75)]
            ww = 0.45
        else:
            pts = [(-0.18, 0), (0.18, 0), (0.18, -0.55), (-0.18, -0.55)]
            ww = 0.4
        m.poly([(x + ww / 2 + px, y, z + pz) for (px, pz) in pts], smooth=False)
        if lod == 0:
            m.mat("rail_metal")
            m.box((x + ww / 2, y, z + 0.03), (0.02, 0.02, 0.06), smooth=False)
        x += ww + 0.08 + rnd.random() * 0.1


def block_wall(m, x0, x1, y, h=1.2, lod=0, cap=True):
    m.mat("block", uvscale=0.8)
    m.box(((x0 + x1) / 2, y, h / 2), (x1 - x0, 0.15, h), smooth=False)
    if cap:
        m.mat("foundation")
        m.box(((x0 + x1) / 2, y, h + 0.03), (x1 - x0 + 0.04, 0.19, 0.06), smooth=False)


def plant_pot(m, c, r=0.18, lod=0):
    x, y, z = c
    m.mat("pot")
    m.cyl((x, y, z + r * 0.7), r=r, r2=r * 0.75, h=r * 1.4, seg=12 if lod == 0 else 6)
    m.mat("bush", uvscale=0.6)
    m.ico((x, y, z + r * 1.4 + r * 0.6), r=r * 1.3, sub=1 if lod else 2, s=(1, 1, 0.85))


def bush(m, c, r=0.6, lod=0, rnd=None):
    rnd = rnd or random.Random(1)
    m.mat("bush", uvscale=0.8)
    x, y, z = c
    for k in range(3 if lod == 0 else 1):
        ox, oy = (rnd.random() - 0.5) * r, (rnd.random() - 0.5) * r * 0.5
        m.ico((x + ox, y + oy, z + r * 0.7), r=r * (0.7 + rnd.random() * 0.3), sub=2 if lod == 0 else 1, s=(1.2, 1, 0.85))


def mailbox_post(m, c, lod=0):
    x, y, z = c
    m.mat("rail_metal")
    m.cyl((x, y, z + 0.5), r=0.025, h=1.0, seg=8)
    m.mat("mailbox")
    m.rbox((x, y, z + 1.12), (0.34, 0.22, 0.28), r=0.03, seg=2 if lod == 0 else 1)
    m.mat("ac_grill")
    m.box((x, y - 0.111, z + 1.17), (0.22, 0.004, 0.03), smooth=False)


# ----------------------------------------------------------------------------- houses

def house(name="house_a", w=7.0, d=7.5, floors=2, wall="cream", roof="ibushi", style=0, seed=1, lod=0):
    """Detached two-storey house (ikkodate) with a kawara roof.
    style 0: hipped roof, balcony with laundry. style 1: gable roof, bay window, shoji room.
    style 2: modern box with a shed roof, horizontal windows."""
    rnd = random.Random(seed)
    mats()
    m = E.Mesher(name)
    H = floors * FLOOR_H
    wm = "wall_" + wall
    # foundation
    m.mat("foundation", uvscale=1.0)
    m.box((0, d / 2, 0.22), (w + 0.08, d + 0.08, 0.44), smooth=False)
    if lod == 0:
        m.mat("ac_grill")
        for sx in (-w / 3, w / 3):
            m.box((sx, -0.045, 0.24), (0.36, 0.01, 0.12), smooth=False)   # under-floor vents
    # walls with a floor band
    m.mat(wm, uvscale=WALLS[wall][2])
    m.box((0, d / 2, 0.44 + H / 2), (w, d, H), smooth=False)
    m.mat("trim")
    for f in range(1, floors):
        m.box((0, d / 2, 0.44 + f * FLOOR_H), (w + 0.06, d + 0.06, 0.12), smooth=False)
    base = 0.44
    # ground floor: entrance door with canopy, windows
    door_x = -w / 2 + 1.1 if style != 1 else w / 2 - 1.2
    m.mat("door_wood" if style != 2 else "door_steel", uvscale=1.0)
    m.box((door_x, -0.03, base + 1.05), (0.95, 0.08, 2.1), bevel=(0.01, 1) if lod == 0 else None)
    m.mat("sash")
    m.box((door_x + 0.32, -0.08, base + 1.05), (0.04, 0.05, 0.4), smooth=False)          # handle
    m.mat("glass_door")
    m.box((door_x - 0.15, -0.075, base + 1.4), (0.18, 0.01, 0.9), smooth=False)          # side light
    m.mat("trim_dark" if style != 2 else "sash")
    m.box((door_x, -0.45, base + 2.45), (1.6, 0.9, 0.07), bevel=(0.01, 1) if lod == 0 else None)   # canopy
    # entrance step
    m.mat("foundation")
    m.box((door_x, -0.45, 0.1), (1.4, 0.9, 0.2), smooth=False)
    m.box((door_x, -0.3, 0.3), (1.2, 0.6, 0.2), smooth=False)
    # nameplate + intercom + lamp
    m.mat("nameplate")
    m.box((door_x + 0.75, -0.015, base + 1.5), (0.22, 0.03, 0.12), smooth=False)
    E.mat("porch_lamp", 0xFFE6A8, emis=0.4, soft=0.1, outline=0.5, flags=E.F_NIGHT)
    m.mat("porch_lamp")
    m.cyl((door_x - 0.75, -0.08, base + 2.0), r=0.08, h=0.22, seg=10, axis='Z')
    # ground floor windows
    gx = [x for x in (door_x + 2.1, door_x + 4.0, door_x - 2.1) if -w / 2 + 0.8 < x < w / 2 - 0.8]
    kinds = ["a", "b", "d", "e"]
    for i, x in enumerate(gx[:2]):
        if style == 1 and i == 0:
            # bay window (demado)
            m.mat(wm, uvscale=WALLS[wall][2])
            m.box((x, -0.25, base + 1.35), (1.9, 0.5, 1.5), smooth=False)
            m.mat("trim")
            m.box((x, -0.27, base + 2.15), (2.0, 0.6, 0.1), smooth=False)
            m.box((x, -0.27, base + 0.55), (2.0, 0.6, 0.1), smooth=False)
            window(m, x, base + 1.35, 1.5, 1.1, "f", wall_y=-0.5, sill=False, lod=lod)
        else:
            window(m, x, base + 1.4, 1.6 if style != 2 else 2.2, 1.2 if style != 2 else 0.7, rnd.choice(kinds),
                   shutter_box=(style == 0), lod=lod)
    # small frosted bathroom window on the side wall area of the front
    window(m, -w / 2 + 0.45 if style == 1 else w / 2 - 0.45, base + 1.9, 0.45, 0.45, "c", sill=False, lod=lod)
    # upper floors
    for f in range(1, floors):
        z = base + f * FLOOR_H + 1.35
        if style == 0 and f == floors - 1:
            # balcony across most of the front with laundry
            bw = w * 0.62
            bx = w / 2 - bw / 2 - 0.3
            m.mat("trim")
            m.box((bx, -0.55, base + f * FLOOR_H + 0.06), (bw, 1.1, 0.14), smooth=False)
            railing(m, bx - bw / 2, bx + bw / 2, -1.08, base + f * FLOOR_H + 0.12, 1.0, lod)
            for sx in (-1, 1):
                m.mat("rail_metal")
                m.box((bx + sx * bw / 2, -0.55, base + f * FLOOR_H + 0.62), (0.05, 1.1, 1.0), smooth=False)
            window(m, bx, z - 0.15, 2.4, 1.9, rnd.choice(("a", "e")), sill=False, lod=lod)
            laundry(m, bx - bw / 2 + 0.2, bx + bw / 2 - 0.2, -0.75, base + f * FLOOR_H + 2.15, rnd, lod)
            # futon over the railing
            m.mat("futon", uvscale=1.0)
            fx = bx - bw / 4
            m.box((fx, -1.08, base + f * FLOOR_H + 0.95), (1.3, 0.14, 0.12), bevel=(0.05, 2) if lod == 0 else None)
            m.box((fx, -1.15, base + f * FLOOR_H + 0.62), (1.3, 0.06, 0.72), bevel=(0.025, 1) if lod == 0 else None)
            m.box((fx, -1.0, base + f * FLOOR_H + 0.62), (1.3, 0.06, 0.72), bevel=(0.025, 1) if lod == 0 else None)
            ac_unit(m, (bx + bw / 2 - 0.6, -0.6, base + f * FLOOR_H + 0.13), lod)
            window(m, -w / 2 + 0.9, z, 0.9, 1.1, rnd.choice(kinds), lod=lod)
        else:
            for x in (-w / 4, w / 4):
                window(m, x, z, 1.5 if style != 2 else 2.4, 1.15 if style != 2 else 0.6, rnd.choice(kinds),
                       shutter_box=(style == 1), lod=lod)
            if style != 2:
                ac_unit(m, (w / 4 + 1.15, -0.2, base + f * FLOOR_H + 0.6), lod)
                m.mat("rail_metal")
                m.box((w / 4 + 1.15, -0.18, base + f * FLOOR_H + 0.58), (0.86, 0.36, 0.04), smooth=False)
    # roof
    top = base + H
    if style == 2:
        # shed roof with metal edge and a parapet line
        m.mat("sash")
        m.push(Matrix.Translation((0, d / 2, top + 0.25)) @ Matrix.Rotation(math.radians(-6), 4, 'X'))
        m.box((0, 0, 0), (w + 0.5, d + 0.5, 0.18), bevel=(0.02, 1) if lod == 0 else None)
        m.pop()
        gutters(m, w, d, top + 0.05, lod, "gutter")
    else:
        gable = style == 1
        zr = hip_roof(m, w, d, top + 0.12, 0.48, 0.6, roof, lod, gable)
        if gable:
            m.mat(wm, uvscale=WALLS[wall][2])
            for sx in (-1, 1):
                tri = [(sx * w / 2, 0, top), (sx * w / 2, d, top), (sx * w / 2, d / 2, top + (d / 2) * 0.48 + 0.12)]
                if sx < 0:
                    tri = tri[::-1]
                m.poly(tri)
        gutters(m, w, d, top + 0.12, lod, "gutter" if wall not in ("brown",) else "gutter_brown")
    # front yard: block wall with gap for the path, mailbox, plants
    fy = -2.4
    block_wall(m, -w / 2 - 0.3, door_x - 0.8, fy, 1.15, lod)
    block_wall(m, door_x + 0.8, w / 2 + 0.3, fy, 1.15, lod)
    for sx in (-1, 1):
        m.mat("block", uvscale=0.8)
        m.box((sx * (w / 2 + 0.375), (fy + d) / 2, 0.575), (0.15, d - fy, 1.15), smooth=False)
    # gate posts
    m.mat("foundation")
    for sx in (-1, 1):
        m.box((door_x + sx * 0.8, fy, 0.7), (0.32, 0.32, 1.4), bevel=(0.02, 1) if lod == 0 else None)
    if lod == 0:
        mailbox_post(m, (door_x + 1.25, fy - 0.3, 0), lod)
    m.mat("yard", uvscale=2.0)
    m.poly([(-w / 2 - 0.3, fy, 0.02), (w / 2 + 0.3, fy, 0.02), (w / 2 + 0.3, 0, 0.02), (-w / 2 - 0.3, 0, 0.02)])
    m.mat("foundation")
    m.box((door_x, fy / 2, 0.035), (1.2, -fy, 0.05), smooth=False)          # front path
    # garden
    if lod == 0:
        bush(m, (door_x + 2.2, fy + 0.6, 0), 0.55, lod, rnd)
        plant_pot(m, (door_x - 0.7, -0.75, 0.2), 0.16, lod)
        plant_pot(m, (door_x + 0.7, -0.75, 0.2), 0.13, lod)
    return m.obj(name + ("" if lod == 0 else "@1"), smooth_angle=35)


def design_houses():
    import studio
    E.reset()
    studio.stage(res=(1600, 900), floor=True, floor_col=0xB8B2A8)
    specs = [("house_a", 7.0, 7.5, "cream", "ibushi", 0, 1),
             ("house_b", 7.6, 7.0, "white", "brick", 1, 2),
             ("house_c", 6.6, 7.0, "sky", "navy", 2, 3)]
    x = -8.6
    for (nm, w, d, wall, roof, style, seed) in specs:
        ob = house(nm, w, d, 2, wall, roof, style, seed)
        ob.location.x = x
        x += w + 2.0
    studio.shoot("houses", target=(0.0, 2.0, 3.2), dist=27, yaw=8, pitch=10, lens=40)
    studio.shoot("house_a_close", target=(-8.6, -0.5, 3.4), dist=10, yaw=-25, pitch=8, lens=35)


# ----------------------------------------------------------------------------- apartment

def apartment(name="apartment", units=4, floors=3, wall="white", seed=7, lod=0):
    """Small apartment block (apāto): balcony side to the street, laundry, AC units,
    external stairs on the left, parapet roof with a water tank and the building name."""
    rnd = random.Random(seed)
    mats()
    E.mat("balcony_panel", 0xD9DEE6, spec=0.3, rim=0.25, soft=0.1, outline=0.8)
    E.mat("name_plate", 0xFFFFFF, "s_haitsu", soft=0.05, rim=0.1, outline=0.5, shadow=0xE8E8EE)
    m = E.Mesher(name)
    uw = 3.6
    w = units * uw
    d = 8.0
    H = floors * 2.85
    wm = "wall_" + wall
    m.mat("foundation", uvscale=1.0)
    m.box((0, d / 2, 0.2), (w + 0.1, d + 0.1, 0.4), smooth=False)
    m.mat(wm, uvscale=WALLS[wall][2])
    m.box((0, d / 2, 0.4 + H / 2), (w, d, H), smooth=False)
    # parapet + roof
    m.mat(wm, uvscale=WALLS[wall][2])
    m.box((0, d / 2, 0.4 + H + 0.45), (w + 0.2, d + 0.2, 0.9), smooth=False)
    m.mat("trim")
    m.box((0, d / 2, 0.4 + H + 0.92), (w + 0.3, d + 0.3, 0.06), smooth=False)
    m.mat("foundation")
    m.box((0, d / 2, 0.4 + H + 0.12), (w - 0.1, d - 0.1, 0.1), smooth=False)
    # water tank on legs
    m.mat("trim")
    m.cyl((w / 2 - 2.0, d / 2 + 1, 0.4 + H + 2.0), r=0.8, h=1.3, seg=16 if lod == 0 else 8)
    m.mat("rail_metal")
    for (ox, oy) in ((-0.6, -0.6), (0.6, -0.6), (-0.6, 0.6), (0.6, 0.6)):
        m.box((w / 2 - 2.0 + ox, d / 2 + 1 + oy, 0.4 + H + 0.8), (0.08, 0.08, 1.0), smooth=False)
    # floors: slab lines, balconies with panel fronts, sliding doors, AC units, laundry
    for f in range(floors):
        z0 = 0.4 + f * 2.85
        m.mat("trim")
        m.box((0, -0.05, z0 + 0.02), (w + 0.04, 0.1, 0.18), smooth=False)
        for u in range(units):
            cx = -w / 2 + uw * (u + 0.5)
            window(m, cx - 0.2, z0 + 1.2, 2.0, 1.95, rnd.choice(("a", "b", "e", "d", "a")), sill=False, lod=lod)
            if f == 0:
                # ground-floor units get a small private yard fence instead of a balcony
                m.mat("rail_white")
                railing(m, cx - uw / 2 + 0.1, cx + uw / 2 - 0.1, -1.4, 0.0, 1.1, lod, "rail_white")
                if lod == 0 and rnd.random() < 0.7:
                    plant_pot(m, (cx + 1.2, -0.8, 0), 0.18, lod)
            else:
                # balcony slab, solid lower panel + rail
                m.mat("trim")
                m.box((cx, -0.65, z0 + 0.06), (uw - 0.06, 1.3, 0.14), smooth=False)
                m.mat("balcony_panel")
                m.box((cx, -1.28, z0 + 0.55), (uw - 0.06, 0.06, 0.85), bevel=(0.01, 1) if lod == 0 else None)
                railing(m, cx - uw / 2 + 0.03, cx + uw / 2 - 0.03, -1.28, z0 + 0.98, 0.12, lod, "rail_metal", bars=False)
                # partition between units (fire escape board)
                m.mat("balcony_panel")
                if u < units - 1:
                    m.box((cx + uw / 2, -0.65, z0 + 1.2), (0.04, 1.25, 2.1), smooth=False)
            ac_unit(m, (cx + 1.2, -0.75 if f else -0.35, z0 + (0.14 if f else 0.0)), lod)
            if f and rnd.random() < 0.75:
                laundry(m, cx - 1.6, cx + 0.6, -0.9, z0 + 2.3, rnd, lod)
            if f and lod == 0 and rnd.random() < 0.35:
                m.mat("futon", uvscale=1.0)
                m.box((cx - 0.6, -1.33, z0 + 0.9), (1.2, 0.12, 0.6), bevel=(0.04, 2))
    # external steel stairs on the left gable
    sx = -w / 2 - 0.7
    m.mat("rail_metal")
    for f in range(floors - 1):
        z0 = 0.4 + f * 2.85
        steps = 14
        for k in range(steps):
            t = k / steps
            m.box((sx, 0.6 + t * 4.0 + (f % 2) * 0, z0 + 0.2 + t * 2.85), (1.0, 0.28, 0.04), smooth=False)
        m.tube([(sx - 0.5, 0.6, z0 + 1.1), (sx - 0.5, 4.6, z0 + 2.85 + 0.9)], r=0.03, seg=6)
        m.tube([(sx + 0.5, 0.6, z0 + 1.1), (sx + 0.5, 4.6, z0 + 2.85 + 0.9)], r=0.03, seg=6)
        m.box((sx, 5.4, z0 + 2.85), (1.2, 1.6, 0.1), smooth=False)                 # landing
    for (oy) in (0.5, 5.9):
        m.box((sx - 0.55, oy, 0.4 + H / 2), (0.1, 0.1, H), smooth=False)
        m.box((sx + 0.55, oy, 0.4 + H / 2), (0.1, 0.1, H), smooth=False)
    # building name plate on the parapet
    m.mat("name_plate")
    f = m.poly([(-1.8, -0.12, 0.4 + H + 0.2), (1.8, -0.12, 0.4 + H + 0.2), (1.8, -0.12, 0.4 + H + 0.8), (-1.8, -0.12, 0.4 + H + 0.8)], uv=None)
    m.uv_rect(f, 0, 0, 1, 1, axis=((1, 0, 0), (0, 0, 1)))
    # bicycle parking roof at the front right
    m.mat("rail_metal")
    for k in range(3):
        m.box((w / 2 - 0.4 - k * 1.6, -3.4, 1.1), (0.08, 0.08, 2.2), smooth=False)
    E.mat("polycarb", 0xBFE3D9, spec=0.6, rim=0.3, soft=0.05, outline=0.6)
    m.mat("polycarb")
    m.box((w / 2 - 2.0, -3.0, 2.25), (3.6, 1.6, 0.05), smooth=False)
    if lod == 0:
        for k in range(4):
            bicycle(m, (w / 2 - 0.8 - k * 0.75, -3.0, 0), 90, rnd.choice((0x3AA3C9, 0xE8473C, 0xF2F2EE, 0x47B36B)))
    return m.obj(name + ("" if lod == 0 else "@1"), smooth_angle=35)


def bicycle(m, c, yaw=0.0, color=0x3AA3C9):
    """Mamachari (city bike) with a front basket."""
    x, y, z = c
    E.mat("bike_%06x" % color, color, spec=0.5, rim=0.3, outline=0.5)
    m.push(Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(yaw), 4, 'Z'))
    for wy in (-0.55, 0.55):
        m.mat("tyre")
        m.torus((0, wy, 0.33), R=0.31, r=0.025, seg=20, sides=6, axis='X')
        m.mat("rail_metal")
        m.cyl((0, wy, 0.33), r=0.04, h=0.08, seg=8, axis='X')
    m.mat("bike_%06x" % color)
    m.tube([(0, -0.55, 0.33), (0, -0.05, 0.36), (0, 0.42, 0.75)], r=0.022, seg=6)
    m.tube([(0, -0.05, 0.36), (0, -0.2, 0.85)], r=0.022, seg=6)
    m.tube([(0, 0.55, 0.33), (0, 0.42, 0.95)], r=0.02, seg=6)
    m.mat("tyre")
    m.box((0, -0.22, 0.88), (0.14, 0.24, 0.06), bevel=(0.02, 1))
    m.mat("rail_metal")
    m.tube([(-0.25, 0.38, 1.02), (0, 0.42, 0.98), (0.25, 0.38, 1.02)], r=0.015, seg=5)
    m.box((0, 0.68, 0.88), (0.34, 0.26, 0.2), smooth=False)                       # basket
    m.pop()


# ----------------------------------------------------------------------------- konbini

def vending_machine(m, c, face="vend_face", body="vend_red", lod=0):
    x, y, z = c
    m.mat(body)
    m.rbox((x, y + 0.36, z + 0.92), (1.0, 0.72, 1.84), r=0.03, seg=2 if lod == 0 else 1)
    m.mat(face)
    f = m.poly([(x - 0.46, y - 0.012, z + 0.04), (x + 0.46, y - 0.012, z + 0.04), (x + 0.46, y - 0.012, z + 1.8), (x - 0.46, y - 0.012, z + 1.8)], uv=None)
    m.uv_rect(f, 0, 0, 1, 1, axis=((1, 0, 0), (0, 0, 1)))
    m.mat(body)
    m.box((x, y + 0.36, z + 1.9), (1.02, 0.74, 0.08), smooth=False)
    if lod == 0:
        m.mat("ac_grill")
        m.box((x, y - 0.03, z + 0.2), (0.6, 0.05, 0.16), smooth=False)               # pickup flap lip


def konbini(name="konbini", lod=0):
    """HOSHI MART convenience store with parking, bins, ice chest and vending machines."""
    mats()
    m = E.Mesher(name)
    w, d, h = 12.0, 10.0, 4.2
    m.mat("foundation", uvscale=1.0)
    m.box((0, d / 2, 0.1), (w + 0.2, d + 0.2, 0.2), smooth=False)
    m.mat("wall_white", uvscale=2.0)
    m.box((0, d / 2, 0.2 + h / 2), (w, d, h), smooth=False)
    # glass front (most of the facade), door in the middle
    m.mat("shopfront")
    f = m.poly([(-w / 2 + 0.4, -0.012, 0.25), (w / 2 - 3.4, -0.012, 0.25), (w / 2 - 3.4, -0.012, 2.9), (-w / 2 + 0.4, -0.012, 2.9)], uv=None)
    m.uv_rect(f, 0, 0, 1, 1, axis=((1, 0, 0), (0, 0, 1)))
    m.mat("sash")
    for x in (-w / 2 + 0.4, w / 2 - 3.4):
        m.box((x, -0.04, 1.58), (0.1, 0.08, 2.7), smooth=False)
    m.box(((w / 2 - 3.4 - w / 2 + 0.4) / 2, -0.04, 2.95), (w - 3.8, 0.08, 0.1), smooth=False)
    m.box(((w / 2 - 3.4 - w / 2 + 0.4) / 2, -0.04, 0.27), (w - 3.8, 0.08, 0.06), smooth=False)
    # automatic door
    m.mat("glass_door")
    m.box((w / 2 - 2.2, -0.03, 1.3), (1.8, 0.04, 2.2), smooth=False)
    m.mat("sash")
    m.box((w / 2 - 2.2, -0.06, 1.3), (0.05, 0.05, 2.2), smooth=False)
    m.box((w / 2 - 2.2, -0.06, 2.45), (2.0, 0.1, 0.12), smooth=False)
    m.mat("road_red") if "road_red" in E._MATS else None
    # sign band: the stripes + logo panel across the front
    m.mat("konbini_sign")
    f = m.poly([(-w / 2 - 0.1, -0.16, 3.0), (w / 2 + 0.1, -0.16, 3.0), (w / 2 + 0.1, -0.16, 4.4), (-w / 2 - 0.1, -0.16, 4.4)], uv=None)
    m.uv_rect(f, 0, 0, 1, 1, axis=((1, 0, 0), (0, 0, 1)))
    m.mat("trim")
    m.box((0, -0.08, 3.7), (w + 0.2, 0.14, 1.4), smooth=False)
    m.box((0, d / 2, 4.45), (w + 0.3, d + 0.3, 0.1), smooth=False)
    # rooftop units
    m.mat("ac_unit")
    for k in range(3):
        m.rbox((-3 + k * 2.2, d * 0.65, 4.85), (1.6, 0.8, 0.7), r=0.04, seg=1)
    # inside lights on the overhang soffit
    m.mat("porch_lamp") if "porch_lamp" in E._MATS else E.mat("porch_lamp", 0xFFE6A8, emis=0.4, soft=0.1, outline=0.5, flags=E.F_NIGHT)
    m.mat("porch_lamp")
    for k in range(4):
        m.box((-4.5 + k * 3, -0.3, 2.98), (0.8, 0.12, 0.03), smooth=False)
    m.mat("trim")
    m.box((0, -0.35, 3.0), (w + 0.2, 0.7, 0.06), smooth=False)                      # small canopy
    # vending machines to the right of the door, bins and an ice chest on the left
    vending_machine(m, (w / 2 - 0.55 + 1.2, -0.8, 0.2), "vend_face", "vend_red", lod)
    vending_machine(m, (w / 2 - 0.55 + 2.3, -0.8, 0.2), "vend_face_b", "vend_blue", lod)
    m.mat("trim")
    for k in range(3):
        m.rbox((-w / 2 + 0.7 + k * 0.55, -0.45, 0.2 + 0.45), (0.5, 0.5, 0.9), r=0.04, seg=1)
    E.mat("bin_label", 0x2E7AD8, soft=0.1, rim=0.1, outline=0)
    m.mat("bin_label")
    for k in range(3):
        m.box((-w / 2 + 0.7 + k * 0.55, -0.705, 0.95), (0.3, 0.01, 0.12), smooth=False)
    m.mat("trim")
    m.rbox((-w / 2 + 3.0, -0.55, 0.2 + 0.45), (1.3, 0.65, 0.9), r=0.05, seg=1)
    E.mat("ice_blue", 0x6EC0FF, emis=0.15, soft=0.1, outline=0)
    m.mat("ice_blue")
    m.box((-w / 2 + 3.0, -0.88, 0.75), (1.0, 0.01, 0.4), smooth=False)
    # parking lot with lines and car stops
    m.mat("asphalt", uvscale=3.0) if "asphalt" in E._MATS else E.mat("asphalt", 0x6B7180, "t_asphalt", soft=0.18, outline=0)
    m.mat("asphalt", uvscale=3.0)
    m.poly([(-w / 2 - 1, -7.5, 0.02), (w / 2 + 3, -7.5, 0.02), (w / 2 + 3, -1.0, 0.02), (-w / 2 - 1, -1.0, 0.02)])
    E.mat("park_line", 0xF6F3EA, soft=0.1, outline=0)
    m.mat("park_line")
    for k in range(5):
        x = -w / 2 + k * 2.6
        m.box((x, -4.5, 0.03), (0.12, 5.0, 0.01), smooth=False)
        if k < 4:
            m.mat("foundation")
            m.box((x + 1.3, -2.4, 0.08), (1.4, 0.15, 0.12), bevel=(0.02, 1) if lod == 0 else None)
            m.mat("park_line")
    # pole sign by the road
    m.mat("rail_metal")
    m.cyl((w / 2 + 2.2, -7.0, 2.5), r=0.08, h=5.0, seg=10)
    m.mat("konbini_sign")
    for side in (-1, 1):
        f = m.poly([(w / 2 + 1.0, -7.0 + side * 0.11, 4.6), (w / 2 + 3.4, -7.0 + side * 0.11, 4.6),
                    (w / 2 + 3.4, -7.0 + side * 0.11, 5.4), (w / 2 + 1.0, -7.0 + side * 0.11, 5.4)][::side], uv=None)
        m.uv_rect(f, 0, 0, 1, 1, axis=((side, 0, 0), (0, 0, 1)))
    m.mat("trim")
    m.box((w / 2 + 2.2, -7.0, 5.0), (2.5, 0.2, 0.9), smooth=False)
    return m.obj(name + ("" if lod == 0 else "@1"), smooth_angle=35)


# ----------------------------------------------------------------------------- sakura tree

def sakura(name="sakura", seed=1, height=6.5, lod=0):
    """Cherry tree: twisting trunk, forked limbs, blossom clouds at the branch tips."""
    rnd = random.Random(seed)
    E.mat("bark", 0x5E4438, "t_wood", soft=0.15, rim=0.2, outline=1.0)
    E.mat("blossom", 0xFFFFFF, "t_blossom", soft=0.35, rim=0.35, outline=1.0, flags=E.F_FOLIAGE, sway=0.35,
          shadow=0xC79AC8)
    m = E.Mesher(name)
    tips = []

    def branch(p, d, length, r, depth):
        pts = [p]
        q = Vector(p)
        dd = Vector(d).normalized()
        n = 4 if lod == 0 else 2
        for i in range(n):
            dd = (dd + Vector(((rnd.random() - 0.5) * 0.5, (rnd.random() - 0.5) * 0.5, 0.12))).normalized()
            q = q + dd * (length / n)
            pts.append(q.copy())
        m.mat("bark", uvscale=0.6)
        m.tube([tuple(v) for v in pts], r=r, seg=10 if lod == 0 and depth < 2 else 6, taper=0.55)
        if depth >= 3 or r < 0.05:
            tips.append((q, r))
            return
        k = 2 if depth > 0 else 3
        for j in range(k):
            a = rnd.random() * 2 * math.pi
            nd = (dd * 0.6 + Vector((math.cos(a), math.sin(a), 0.35)) * 0.8).normalized()
            branch(q, nd, length * (0.62 + rnd.random() * 0.15), r * 0.58, depth + 1)

    trunk_h = height * 0.38
    branch(Vector((0, 0, -0.1)), Vector((0.05, 0.02, 1)), trunk_h, 0.24, 0)
    # root flare
    m.mat("bark", uvscale=0.6)
    m.cyl((0, 0, 0.12), r=0.42, r2=0.24, h=0.3, seg=12 if lod == 0 else 6)
    # blossom clouds: clusters of displaced icospheres around tips
    m.mat("blossom", uvscale=1.2)
    for (q, r) in tips:
        n = 3 if lod == 0 else 1
        for i in range(n):
            o = Vector(((rnd.random() - 0.5) * 1.2, (rnd.random() - 0.5) * 1.2, (rnd.random() - 0.2) * 0.6))
            rad = 0.75 + rnd.random() * 0.5
            m.ico(tuple(q + o), r=rad, sub=2 if lod == 0 else 1, s=(1.15, 1.15, 0.8))
    ob = m.obj(name + ("" if lod == 0 else "@1"), smooth_angle=60)
    return ob


# ----------------------------------------------------------------------------- level crossing

def crossing_signal(m, c, face=-1, lod=0):
    """Fumikiri warning machine: pole, crossbuck, twin red lamps, direction arrows, bell."""
    x, y, z = c
    seg = 12 if lod == 0 else 6
    m.mat("hazard_black")
    m.cyl((x, y, z + 1.9), r=0.07, h=3.8, seg=seg)
    # yellow/black striped lower part
    for k in range(6):
        m.mat("hazard_yellow" if k % 2 == 0 else "hazard_black")
        m.cyl((x, y, z + 0.15 + k * 0.25), r=0.075, h=0.25, seg=seg)
    # crossbuck (X) — two yellow boards with black stripes
    for ang in (35, -35):
        m.push(Matrix.Translation((x, y, z + 3.45)) @ Matrix.Rotation(math.radians(ang), 4, 'Y'))
        m.mat("hazard_yellow")
        m.box((0, face * 0.1, 0), (1.15, 0.03, 0.18), smooth=False)
        m.mat("hazard_black")
        for k in range(4 if lod == 0 else 0):
            m.push(Matrix.Rotation(math.radians(45), 4, 'Y'))
            m.pop()
            m.box((-0.42 + k * 0.28, face * 0.118, 0), (0.08, 0.008, 0.18), smooth=False)
        m.pop()
    # lamp bar with two red lamps and hoods, front and back
    E.mat("signal_red", 0xF0302A, emis=0.6, spec=0.6, soft=0.05, outline=0.4)
    E.mat("signal_off", 0x5A1E1E, spec=0.6, soft=0.05, outline=0.4)
    m.mat("hazard_black")
    m.box((x, y, z + 2.75), (1.0, 0.08, 0.08), smooth=False)
    for sx in (-0.38, 0.38):
        for fy in (-1, 1):
            m.mat("hazard_black")
            m.cyl((x + sx, y + fy * 0.08, z + 2.75), r=0.17, h=0.06, seg=seg, axis='Y')
            m.cyl((x + sx, y + fy * 0.16, z + 2.82), r=0.16, h=0.16, seg=seg, axis='Y')    # hood (approx)
            m.mat("signal_red" if sx < 0 else "signal_off")
            m.cyl((x + sx, y + fy * 0.12, z + 2.75), r=0.12, h=0.03, seg=seg, axis='Y')
    # direction indicator (arrows) and the bell
    m.mat("hazard_black")
    m.box((x, y, z + 2.25), (0.5, 0.1, 0.22), smooth=False)
    E.mat("arrow_lit", 0xFFE040, emis=0.6, soft=0.05, outline=0)
    m.mat("arrow_lit")
    for sx in (-1, 1):
        m.push(Matrix.Translation((x + sx * 0.12, y - 0.056, z + 2.25)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
        m.extrude([(-sx * 0.08, 0), (sx * 0.06, -0.07), (sx * 0.06, 0.07)], 0.01)
        m.pop()
    m.mat("steel")
    m.cyl((x, y, z + 3.95), r=0.12, h=0.12, r2=0.06, seg=seg)


def crossing(name="crossing", lod=0, seg=12.0):
    """Level-crossing segment: road across all three tracks with rubber panels,
    warning machines and barrier housings on both sides (barrier arms are separate)."""
    E.mat("cross_panel", 0x5A5E66, "t_asphalt", soft=0.15, rim=0.05, outline=0)
    E.mat("cross_stripe", 0xF4C431, soft=0.15, outline=0)
    import city
    m = E.Mesher(name)
    rw = 5.0                       # road width along Y
    y0 = seg / 2 - rw / 2
    m.mat("cross_panel", uvscale=2.0)
    for lx in city.LANES:
        # panels between and outside the rails, flush with rail top
        for (a, b) in ((-1.05, -0.565), (-0.505, 0.505), (0.565, 1.05)):
            m.box((lx + (a + b) / 2, seg / 2, 0.08), (b - a, rw, 0.16), smooth=False)
    for (a, b) in ((-6.4, -3.45), (-1.35, -1.05), (1.05, 1.35), (3.45, 6.4)):
        m.box(((a + b) / 2, seg / 2, (0.16 + city.GROUND) / 2), (b - a, rw, 0.16 - city.GROUND), smooth=False)
    for (a, b) in ((-1.35, -1.05),):
        pass
    # stop lines on the approach roads
    m.mat("road_line")
    for sx in (-1, 1):
        m.box((sx * 7.6, seg / 2 - 1.2, city.GROUND + 0.0), (0.3, 2.3, 0.01), smooth=False)
    # warning machines + barrier housings, one per road side/corner
    for (sx, sy) in ((1, -1), (-1, 1)):
        bx = sx * 5.9
        by = seg / 2 + sy * (rw / 2 + 0.5)
        crossing_signal(m, (bx, by, city.GROUND), face=sy, lod=lod)
        m.mat("hazard_black")
        m.rbox((bx + sx * 0.45, by, city.GROUND + 0.55), (0.5, 0.42, 1.1), r=0.04, seg=1)   # barrier housing
        m.mat("hazard_yellow")
        m.box((bx + sx * 0.45, by - sy * 0.215, city.GROUND + 0.7), (0.4, 0.01, 0.2), smooth=False)
    ob = m.obj(name + ("" if lod == 0 else "@1"), smooth_angle=30)
    return ob


def crossing_arm(name="crossing_arm", length=6.2, lod=0):
    """Barrier arm: yellow/black striped pole with counterweight; pivot at the origin, extends +X."""
    m = E.Mesher(name)
    n = int(length / 0.5)
    for k in range(n):
        m.mat("hazard_yellow" if k % 2 == 0 else "hazard_black")
        x0 = k * length / n
        m.cyl((x0 + length / n / 2, 0, 0), r=0.055 * (1 - 0.4 * k / n), r2=0.055 * (1 - 0.4 * (k + 1) / n), h=length / n, seg=8 if lod == 0 else 5, axis='X')
    m.mat("hazard_black")
    m.box((-0.45, 0, 0), (0.5, 0.12, 0.22), smooth=False)
    if lod == 0:
        # hanging fringe skirt (short black/yellow strings)
        for k in range(int(length / 0.4)):
            x = 0.6 + k * 0.4
            if x > length - 0.2:
                break
            m.mat("hazard_black")
            m.box((x, 0, -0.18), (0.015, 0.015, 0.3), smooth=False)
    return m.obj(name + ("" if lod == 0 else "@1"), smooth_angle=30)


def haitsu_sign():
    import paint as PT
    c = PT.Canvas("s_haitsu", 256, 48)
    c.rect(0, 0, 256, 48, 0xF7F4EC)
    c.text("さくらハイツ", 128, 26, 30, 0x6E4A3A, font=E.FONT_JP)
    c.rect(0, 0, 256, 3, 0xE98AAE)
    return c.save()


def design_street():
    """A full Sakura Line block: tracks, both streets, houses, apartment, konbini, sakura, crossing."""
    import studio, city
    E.reset()
    haitsu_sign()
    studio.stage(res=(1600, 900), floor=False)
    city.city_mats()
    mats()
    for i in range(5):
        y0 = (i - 1) * city.SEG
        if i == 2:
            ob = crossing(); ob.location.y = y0
            ob = city.track(); ob.location.y = y0
        else:
            for fn in (city.track, city.side, lambda: city.side(mirror=True)):
                ob = fn(); ob.location.y = y0
        ob = city.wires(); ob.location.y = y0
    for i in range(3):
        ob = city.gantry(); ob.location.y = -6 + i * 24
    arm = crossing_arm(); arm.location = (6.35, 2 * city.SEG + city.SEG / 2 - 3.0, city.GROUND + 0.9); arm.rotation_euler.z = math.radians(180)
    arm.rotation_euler.y = math.radians(-70)
    arm2 = crossing_arm(); arm2.location = (-6.35, 2 * city.SEG + city.SEG / 2 + 3.0, city.GROUND + 0.9); arm2.rotation_euler.y = math.radians(-70)
    for i in range(3):
        ob = city.utility_pole(); ob.location.y = -10 + i * 24
    # ground beyond the road
    E.mat("lot", 0xB5AFA4, "t_concrete", soft=0.2, outline=0)
    g = E.Mesher("lot").mat("lot", uvscale=4.0)
    g.poly([(-60, -20, city.GROUND - 0.04), (60, -20, city.GROUND - 0.04), (60, 80, city.GROUND - 0.04), (-60, 80, city.GROUND - 0.04)])
    g.obj()
    # right side (x > 0): buildings face -X toward the track
    right = [("house_a", lambda: house("house_a", 7.0, 7.5, 2, "cream", "ibushi", 0, 1), 7.0),
             ("konbini", lambda: konbini(), 12.0),
             ("house_c", lambda: house("house_c", 6.6, 7.0, 2, "sky", "navy", 2, 3), 6.6),
             ("house_d", lambda: house("house_d", 7.2, 7.4, 2, "mint", "green", 0, 9), 7.2)]
    y = -8.0
    for nm, fn, w in right:
        ob = fn()
        ob.rotation_euler.z = math.radians(-90)
        ob.location = (11.0 + (8.5 if nm == "konbini" else 2.6), y + w / 2, city.GROUND)
        y += w + 2.5
    left = [("apartment", lambda: apartment(), 14.4),
            ("house_b", lambda: house("house_b", 7.6, 7.0, 2, "white", "brick", 1, 2), 7.6),
            ("house_e", lambda: house("house_e", 6.8, 7.2, 2, "beige", "choco", 1, 5), 6.8)]
    y = -6.0
    for nm, fn, w in left:
        ob = fn()
        ob.rotation_euler.z = math.radians(90)
        ob.location = (-11.0 - (1.6 if nm == "apartment" else 2.6), y + w / 2, city.GROUND)
        y += w + 2.5
    for k, (x, yy) in enumerate(((7.8, 3.5), (-8.0, 18.0), (8.2, 30.0), (-8.4, 40.0))):
        t = sakura("sakura_%d" % k, seed=k + 1)
        t.location = (x + (1.5 if x > 0 else -1.5), yy, city.GROUND)
    studio.aim_sun(200)
    studio.shoot("street_overview", target=(0, 16, 1.5), dist=30, yaw=180 + 25, pitch=24, lens=30)
    studio.shoot("street_runner", target=(0, 22, 1.6), dist=7.5, yaw=180, pitch=14, lens=24)
    studio.shoot("street_konbini", target=(13, 6, 2.2), dist=14, yaw=180 + 70, pitch=10, lens=30)
