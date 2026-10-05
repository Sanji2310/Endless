"""
Sakura Line rolling stock and track obstacles, drawn in the same toon style as the city kit
(flat cel bands, violet-tinted shadows, ink outlines, lots of small readable detail).

Game sizes (Game.java): lane 2.4 m, train body 2.2 m wide, roof (walkable) at 3.3 m, one car = 12 m,
ramp 8 m long rising to the roof, BLOCK obstacles are hit below 3.0 m.

Blender: Z up, the runner moves toward +Y. Every obstacle starts at y = 0 (the end the runner meets first)
and extends toward +Y, centred on x = 0, sleeper tops at z = 0 (rail top 0.161).

  commuter_front / commuter_mid  : parked 4-door commuter EMU, two liveries (teal, amber)
  express_front  / express_mid   : oncoming limited express with a long nose, two liveries (crimson, cobalt)
  ramp                           : steel boarding ramp up to a train roof
  works                          : track-works barrier (dodge sideways)
"""
import math, random
import bpy
from mathutils import Vector, Matrix
import erlib as E

V = Vector
CAR = 12.0
W2 = 1.1           # half body width
FLOOR = 0.95       # body bottom
ROOF = 3.3         # walkable roof top
RAIL_TOP = 0.161
GAUGE = 1.067

LIVERIES = {
    "teal": dict(band=0x1FA39A, accent=0xF28A2E, text="各停  桜ヶ丘"),
    "amber": dict(band=0xF0A81E, accent=0x2E8B57, text="快速  水晶洞"),
    "crimson": dict(band=0xD7354A, accent=0x2A2F45, text="特急  はやて"),
    "cobalt": dict(band=0x2C63C8, accent=0xF0C33C, text="特急  そよかぜ"),
}


def mats():
    M = E.mat
    M("tr_steel", 0xDCE0E6, spec=0.55, rim=0.4, soft=0.06, flags=E.F_METAL, shadow=0xA9A6CF)
    M("tr_steel_dark", 0xB5BBC5, spec=0.5, rim=0.35, soft=0.06, flags=E.F_METAL)
    M("tr_white", 0xF6F5F1, spec=0.35, rim=0.4, soft=0.08, shadow=0xB8B2DA)
    M("tr_glass", 0x35527E, spec=1.0, rim=0.3, soft=0.04, flags=E.F_GLASS, outline=0.4)
    M("tr_mask", 0x1F222B, spec=0.9, rim=0.25, soft=0.04, flags=E.F_GLASS, outline=0.5)
    M("tr_rubber", 0x2B2C33, rim=0.15, soft=0.1, outline=0.6)
    M("tr_under", 0x3A3D46, spec=0.2, rim=0.15, soft=0.1, outline=0.7)
    M("tr_under_mid", 0x5C616D, spec=0.3, rim=0.2, soft=0.1, flags=E.F_METAL, outline=0.7)
    M("tr_wheel", 0x7E848F, spec=0.7, rim=0.3, soft=0.05, flags=E.F_METAL, outline=0.6)
    M("tr_roof", 0x9EA4AF, spec=0.2, rim=0.3, soft=0.1, shadow=0x8E88B8)
    M("tr_roof_unit", 0xC9CDD4, spec=0.3, rim=0.35, soft=0.08)
    M("tr_head", 0xFFF6D8, emis=1.0, rim=0.2, soft=0.04, outline=0.4)
    M("tr_tail", 0xFF4A3A, emis=0.8, rim=0.2, soft=0.04, outline=0.4)
    M("tr_led", 0x14161C, rim=0.1, soft=0.1, outline=0.5)
    M("tr_led_text", 0xFF9A2E, emis=1.0, rim=0.0, soft=0.0, outline=0.0)
    M("tr_text_white", 0xFFFFFF, rim=0.0, soft=0.05, outline=0.0)
    M("tr_text_dark", 0x2A2E3E, rim=0.0, soft=0.05, outline=0.0)
    M("tr_yellow", 0xF6C431, rim=0.3, soft=0.08, spec=0.2)
    M("tr_black", 0x26272E, rim=0.25, soft=0.08, spec=0.2)
    M("tr_red", 0xE8473C, rim=0.3, soft=0.08, spec=0.3)
    M("tr_plate", 0xA4ABB6, "t_concrete", spec=0.6, rim=0.35, soft=0.06, flags=E.F_METAL)
    M("tr_sign_blue", 0x2F6BDA, soft=0.12, rim=0.2, outline=0.6)
    M("tr_sign_white", 0xF8F6F0, soft=0.12, rim=0.2, outline=0.6)
    M("tr_cone", 0xFF7A2A, rim=0.3, soft=0.08, spec=0.2)
    M("tr_sandbag", 0xC9B98E, rim=0.2, soft=0.15, shadow=0x8E7FA0)
    M("tr_lamp_amber", 0xFFB23A, emis=1.0, rim=0.2, soft=0.04, outline=0.4)
    M("tr_skin", 0xF6D2B6, rim=0.3, soft=0.12)
    for k, lv in LIVERIES.items():
        M("tr_band_" + k, lv["band"], spec=0.3, rim=0.35, soft=0.06)
        M("tr_accent_" + k, lv["accent"], spec=0.3, rim=0.35, soft=0.06)


# ----------------------------------------------------------------------------- shared car parts

# body cross-section (x, z), counter-clockwise seen from the front
PROFILE = [(-1.05, FLOOR), (1.05, FLOOR), (1.1, FLOOR + 0.2), (1.1, 2.78), (1.07, 2.96), (0.93, 3.12), (0.6, 3.24),
           (0.0, ROOF - 0.02), (-0.6, 3.24), (-0.93, 3.12), (-1.07, 2.96), (-1.1, 2.78), (-1.1, FLOOR + 0.2)]


def _ring(y, sx=1.0, zs=1.0, z0=FLOOR):
    return [(x * sx, y, z0 + (z - FLOOR) * zs) for (x, z) in PROFILE]


def _body(m, y0, y1, mat="tr_steel", cap0=True, cap1=True):
    m.mat(mat)
    m.quad_strip([_ring(y0), _ring(y1)], closed=True, cap0=cap0, cap1=cap1, smooth=False)


def _bogie(m, yc):
    """Two-axle bogie: side frames, springs, wheels on the rails, brake units."""
    zc = RAIL_TOP + 0.36
    for sx in (-1, 1):
        x = sx * GAUGE / 2
        for dy in (-1.05, 1.05):
            m.mat("tr_wheel")
            m.cyl((x, yc + dy, zc), r=0.36, h=0.1, seg=24, axis='X')
            m.mat("tr_under")
            m.cyl((x + sx * 0.08, yc + dy, zc), r=0.12, h=0.12, seg=12, axis='X')
        m.mat("tr_under")
        m.box((sx * 0.86, yc, zc + 0.06), (0.14, 2.9, 0.26), smooth=False)
        m.box((sx * 0.86, yc, zc - 0.12), (0.1, 1.2, 0.16), smooth=False)
        m.mat("tr_under_mid")
        for dy in (-0.45, 0.45):
            m.cyl((sx * 0.86, yc + dy, zc + 0.3), r=0.09, h=0.22, seg=12)
        m.mat("tr_yellow")
        m.box((sx * 0.94, yc + 1.05, zc + 0.02), (0.04, 0.14, 0.1), smooth=False)
    m.mat("tr_under")
    m.box((0, yc, zc + 0.3), (1.5, 0.5, 0.14), smooth=False)
    m.cyl((0, yc - 1.05, zc), r=0.06, h=GAUGE + 0.2, seg=10, axis='X')
    m.cyl((0, yc + 1.05, zc), r=0.06, h=GAUGE + 0.2, seg=10, axis='X')


def _underfloor(m, y0, y1, seed):
    """Equipment boxes between the bogies (inverters, air tanks, battery boxes)."""
    rnd = random.Random(seed)
    y = y0
    while y < y1 - 0.4:
        L = rnd.uniform(0.7, 1.6)
        if y + L > y1:
            break
        d = rnd.uniform(0.32, 0.5)
        m.mat("tr_under" if rnd.random() < 0.6 else "tr_under_mid")
        if rnd.random() < 0.3:
            for sx in (-1, 1):
                m.cyl((sx * 0.55, y + L / 2, FLOOR - 0.2), r=0.17, h=L, seg=14, axis='Y')
        else:
            m.box((0, y + L / 2, FLOOR - d / 2), (1.9, L, d), smooth=False)
            m.mat("tr_under_mid")
            for sx in (-1, 1):
                m.box((sx * 0.96, y + L / 2, FLOOR - d / 2), (0.02, L - 0.12, d - 0.1), smooth=False)
        y += L + rnd.uniform(0.15, 0.5)


def _side_door(m, x, yc, sx, band):
    """Double-leaf sliding door: steel leaves with tall windows, rubber seal, step plate, door lamp."""
    m.mat("tr_rubber")
    m.box((x, yc, 1.95), (0.03, 1.36, 1.92), smooth=False)
    for k in (-1, 1):
        m.mat("tr_steel_dark")
        m.box((x + sx * 0.012, yc + k * 0.33, 1.95), (0.03, 0.62, 1.84), smooth=False)
        m.mat("tr_glass")
        m.box((x + sx * 0.03, yc + k * 0.33, 2.32), (0.02, 0.4, 0.86), smooth=False)
    m.mat("tr_rubber")
    m.box((x + sx * 0.03, yc, 1.95), (0.02, 0.025, 1.84), smooth=False)
    m.mat("tr_tail")
    m.box((x + sx * 0.01, yc, 2.99), (0.04, 0.12, 0.05), smooth=False)
    m.mat("tr_band_" + band)
    m.box((x + sx * 0.01, yc, 2.9), (0.03, 1.38, 0.06), smooth=False)
    m.mat("tr_steel_dark")
    m.box((x - sx * 0.05, yc, FLOOR + 0.03), (0.12, 1.3, 0.04), smooth=False)


def _side_window(m, x, y0, y1, sx, split=2):
    """Window bay: black frame, dark blue glass panes with a sky glint stripe."""
    yc, L = (y0 + y1) / 2, y1 - y0
    m.mat("tr_rubber")
    m.box((x, yc, 2.32), (0.025, L, 0.98), smooth=False)
    pane = L / split
    for k in range(split):
        c = y0 + pane * (k + 0.5)
        m.mat("tr_glass")
        m.box((x + sx * 0.015, c, 2.32), (0.02, pane - 0.08, 0.88), smooth=False)
        m.mat("tr_text_white", tint=0xD6E8FF)
        m.push(Matrix.Translation((x + sx * 0.027, c - 0.08, 2.46)) @ Matrix.Rotation(math.radians(-35), 4, 'X'))
        m.box((0, 0, 0), (0.004, 0.035, 0.36), smooth=False)
        m.pop()


def _car_sides(m, y0, y1, band, accent, doors, seed=1):
    """Both side walls: livery band under the windows, accent pinstripe, doors and window bays."""
    for sx in (-1, 1):
        x = sx * (W2 + 0.006)
        m.mat("tr_band_" + band)
        m.box((x, (y0 + y1) / 2, 1.72), (0.02, y1 - y0 - 0.1, 0.24), smooth=False)
        m.mat("tr_accent_" + band)
        m.box((x + sx * 0.002, (y0 + y1) / 2, 1.57), (0.02, y1 - y0 - 0.1, 0.05), smooth=False)
        m.mat("tr_band_" + band)
        m.box((x, (y0 + y1) / 2, 2.92), (0.02, y1 - y0 - 0.1, 0.07), smooth=False)
        edges = [y0 + 0.25] + [d for yc in doors for d in (yc - 0.7, yc + 0.7)] + [y1 - 0.25]
        for yc in doors:
            _side_door(m, x, yc, sx, band)
        for k in range(0, len(edges), 2):
            a, b = edges[k] + 0.2, edges[k + 1] - 0.2
            if b - a > 0.6:
                _side_window(m, x, a, b, sx, split=2 if b - a > 1.6 else 1)
        # car number and the line's little sakura emblem
        m.mat("tr_text_dark")
        m.push(Matrix.Translation((x + sx * 0.02, y0 + 0.9 if sx > 0 else y1 - 0.9, 1.3)) @
               Matrix.Rotation(math.radians(90 * sx), 4, 'Z') @ Matrix.Rotation(math.radians(90), 4, 'X'))
        m.text("サクラ %d0%d" % (seed, seed + 3), size=0.11, depth=0.004, font=E.FONT_JP)
        m.pop()
        m.mat("tr_accent_" + band)
        for k in range(5):
            a = math.radians(90 + k * 72)
            m.push(Matrix.Translation((x + sx * 0.02, (y0 + y1) / 2 + 0.25 * math.cos(a) * 0.5, 1.72 + 0.25 * math.sin(a) * 0.5)))
            m.sphere((0, 0, 0), 0.05, 10, 6, s=(0.3, 1, 1))
            m.pop()


def _roof(m, y0, y1, pantograph=False, seed=1):
    """Roof walkway: gutters, low AC units, vents, an optional folded pantograph. Nothing stands above
    ROOF + 0.2 so Pongo can run along the top."""
    rnd = random.Random(seed)
    m.mat("tr_roof")
    m.box((0, (y0 + y1) / 2, ROOF - 0.03), (1.15, y1 - y0 - 0.2, 0.05), smooth=False)
    for sx in (-1, 1):
        m.mat("tr_steel_dark")
        m.box((sx * 1.0, (y0 + y1) / 2, 3.05), (0.04, y1 - y0 - 0.1, 0.05), smooth=False)
    for yc in (y0 + 2.6, y1 - 2.6):
        m.mat("tr_roof_unit")
        m.rbox((0, yc, ROOF + 0.06), (1.5, 2.0, 0.16), r=0.05, seg=2)
        m.mat("tr_under_mid")
        for k in range(3):
            m.cyl((-0.45 + k * 0.45, yc, ROOF + 0.15), r=0.17, h=0.03, seg=16)
            m.mat("tr_under")
            m.cyl((-0.45 + k * 0.45, yc, ROOF + 0.165), r=0.12, h=0.01, seg=12)
            m.mat("tr_under_mid")
    for k in range(int((y1 - y0) / 1.5)):
        if rnd.random() < 0.5:
            m.mat("tr_roof_unit")
            m.box((rnd.choice((-0.75, 0.75)), y0 + 0.75 + k * 1.5, ROOF + 0.02), (0.28, 0.4, 0.08), smooth=False)
    if pantograph:
        yc = (y0 + y1) / 2
        m.mat("tr_white")
        for sx in (-0.45, 0.45):
            m.cyl((sx, yc - 0.5, ROOF + 0.05), r=0.06, h=0.12, seg=10)
            m.cyl((sx, yc + 0.5, ROOF + 0.05), r=0.06, h=0.12, seg=10)
        m.mat("tr_under")
        m.box((0, yc, ROOF + 0.12), (1.1, 1.3, 0.04), smooth=False)
        m.mat("tr_steel_dark")
        for d in (-1, 1):
            m.push(Matrix.Translation((0, yc + d * 0.3, ROOF + 0.18)) @ Matrix.Rotation(math.radians(d * 78), 4, 'X'))
            m.box((0, 0, 0), (0.9, 0.04, 0.7), smooth=False)
            m.pop()
        m.mat("tr_tail", tint=0xC03A30)
        m.box((0, yc, ROOF + 0.22), (1.5, 0.08, 0.04), smooth=False)


def _gangway(m, y, sx_dir):
    """End wall of a mid car: bellows and the end door."""
    m.mat("tr_rubber")
    for k in range(4):
        m.rbox((0, y + sx_dir * (0.05 + k * 0.07), 2.0), (1.0 - k * 0.02, 0.06, 2.0), r=0.04, seg=2)
    m.mat("tr_steel_dark")
    m.box((0, y + sx_dir * 0.01, 1.95), (0.72, 0.02, 1.85), smooth=False)
    m.mat("tr_glass")
    m.box((0, y + sx_dir * 0.025, 2.35), (0.46, 0.02, 0.7), smooth=False)


# ----------------------------------------------------------------------------- commuter EMU

DOORS = (1.75, 4.6, 7.45, 10.3)


def _commuter_face(m, band):
    """Flat cab end facing -Y: black glass mask, LED destination board, headlights, skirt and coupler."""
    lv = LIVERIES[band]
    y = 0.0
    # slightly raked face panel in body colour
    m.mat("tr_steel")
    m.box((0, y + 0.04, 2.0), (2.18, 0.1, 2.1), smooth=False)
    m.mat("tr_mask")
    m.rbox((0, y - 0.03, 2.45), (2.0, 0.06, 0.95), r=0.08, seg=3)
    # through door with its own window
    m.mat("tr_steel_dark")
    m.box((0, y - 0.05, 1.8), (0.62, 0.04, 1.6), smooth=False)
    m.mat("tr_glass")
    m.box((0, y - 0.075, 2.3), (0.42, 0.02, 0.62), smooth=False)
    # destination board + run number
    m.mat("tr_led")
    m.box((0.35, y - 0.07, 2.78), (0.9, 0.03, 0.2), smooth=False)
    m.box((-0.62, y - 0.07, 2.78), (0.36, 0.03, 0.2), smooth=False)
    m.mat("tr_led_text")
    m.push(Matrix.Translation((0.35, y - 0.09, 2.78)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
    m.text(lv["text"], size=0.12, depth=0.004, font=E.FONT_JP)
    m.pop()
    m.push(Matrix.Translation((-0.62, y - 0.09, 2.78)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
    m.text("27K", size=0.12, depth=0.004)
    m.pop()
    # wiper arms
    m.mat("tr_black")
    for x in (-0.65, 0.65):
        m.push(Matrix.Translation((x, y - 0.07, 2.08)) @ Matrix.Rotation(math.radians(70 if x > 0 else -70), 4, 'Y'))
        m.box((0, 0, 0.25), (0.02, 0.02, 0.5), smooth=False)
        m.pop()
    # livery band wraps around the face
    m.mat("tr_band_" + band)
    m.box((0, y - 0.01, 1.72), (2.2, 0.06, 0.24), smooth=False)
    m.mat("tr_accent_" + band)
    m.box((0, y - 0.015, 1.57), (2.2, 0.06, 0.05), smooth=False)
    # light clusters: twin headlights + tail light per side
    for sx in (-1, 1):
        m.mat("tr_black")
        m.rbox((sx * 0.75, y - 0.04, 1.32), (0.5, 0.06, 0.2), r=0.04, seg=2)
        m.mat("tr_head")
        for dx in (-0.1, 0.08):
            m.cyl((sx * 0.75 + dx, y - 0.07, 1.32), r=0.07, h=0.02, seg=16, axis='Y')
        m.mat("tr_tail")
        m.box((sx * 0.95, y - 0.07, 1.32), (0.08, 0.02, 0.1), smooth=False)
    m.mat("tr_text_dark")
    m.push(Matrix.Translation((0.0, y - 0.03, 1.32)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
    m.text("8204", size=0.11, depth=0.004)
    m.pop()
    # anti-climber, skirt (snow plough) and coupler
    m.mat("tr_steel_dark")
    m.box((0, y - 0.08, FLOOR + 0.08), (2.1, 0.16, 0.12), smooth=False)
    m.mat("tr_under")
    m.poly([(-1.0, y - 0.12, FLOOR), (1.0, y - 0.12, FLOOR), (0.85, y - 0.42, 0.32), (-0.85, y - 0.42, 0.32)])
    m.poly([(-0.85, y - 0.42, 0.32), (0.85, y - 0.42, 0.32), (0.85, y + 0.3, 0.32), (-0.85, y + 0.3, 0.32)])
    for sx in (-1, 1):
        m.poly([(sx * 1.0, y - 0.12, FLOOR), (sx * 0.85, y - 0.42, 0.32), (sx * 0.85, y + 0.3, 0.32), (sx * 1.0, y + 0.3, FLOOR)][::sx])
    m.mat("tr_yellow")
    m.box((0, y - 0.43, 0.42), (1.6, 0.02, 0.08), smooth=False)
    m.mat("tr_under_mid")
    m.box((0, y - 0.3, 0.72), (0.22, 0.6, 0.16), smooth=False)
    m.box((0, y - 0.6, 0.72), (0.34, 0.08, 0.26), smooth=False)
    m.mat("tr_black")
    for sx in (-1, 1):
        m.cyl((sx * 0.35, y - 0.3, 0.62), r=0.03, h=0.5, seg=8, axis='Y')
    # horn grille and handrails
    m.mat("tr_under_mid")
    for x in (-0.25, 0.25):
        m.box((x, y - 0.06, 1.05), (0.3, 0.02, 0.08), smooth=False)
    m.mat("tr_steel_dark")
    for sx in (-1, 1):
        m.cyl((sx * 1.04, y - 0.06, 1.95), r=0.018, h=0.9, seg=8)


def commuter(name="commuter_front", band="teal", front=True, seed=1):
    mats()
    m = E.Mesher(name)
    y0 = 0.1 if front else 0.45
    y1 = CAR - 0.45
    _body(m, y0, y1)
    _car_sides(m, y0, y1, band, None, DOORS, seed)
    _roof(m, y0, y1, pantograph=not front, seed=seed)
    _bogie(m, 2.2)
    _bogie(m, CAR - 2.2)
    _underfloor(m, 3.8, CAR - 3.8, seed)
    if front:
        _commuter_face(m, band)
    else:
        _gangway(m, y0, -1)
    _gangway(m, y1, 1)
    ob = m.obj(name, smooth_angle=30)
    E.finish_hard(ob, width=0.008, segments=1, angle=35)
    return ob


# ----------------------------------------------------------------------------- limited express

NOSE = 5.2


def _nose(t):
    """t = 0 at the tip, 1 where the nose meets the full body: (y, width scale, height scale).
    Low pointed tip, the crown rises slowly so the cab sits well back like a real limited express."""
    s = math.sin(t * math.pi / 2)
    return NOSE * t, 0.5 + 0.5 * s ** 0.6, 0.2 + 0.8 * s ** 1.7


def _nose_ring(t, y=None):
    y, sx, zs = _nose(t)
    return _ring(y, sx, zs)


def _express_nose(m, band):
    n = 10
    n = 14
    rings = [_nose_ring(i / n) for i in range(n + 1)]
    m.mat("tr_white")
    m.quad_strip(rings, closed=True, cap0=True, cap1=False, smooth=True)
    # long livery stripe running from the nose along the body
    for sx in (-1, 1):
        pts = []
        for i in range(n + 1):
            y, ws, zs = _nose(i / n)
            pts.append((sx * (W2 * ws + 0.012), y, FLOOR + (1.72 - FLOOR) * max(zs, 0.55)))
        m.mat("tr_band_" + band)
        m.sweep([V(p) for p in pts], [(-0.006, -0.12), (0.006, -0.12), (0.006, 0.12), (-0.006, 0.12)], closed=True, cap=True)
        m.mat("tr_accent_" + band)
        m.sweep([V((p[0], p[1], p[2] - 0.17)) for p in pts], [(-0.006, -0.025), (0.006, -0.025), (0.006, 0.025), (-0.006, 0.025)],
                closed=True, cap=True)
        # headlight slit on the cheek
        y, ws, zs = _nose(0.3)
        m.mat("tr_black")
        m.push(Matrix.Translation((sx * W2 * ws * 0.9, y, FLOOR + 0.3)) @ Matrix.Rotation(math.radians(sx * 30), 4, 'Z'))
        m.rbox((0, 0, 0), (0.12, 0.62, 0.16), r=0.04, seg=2)
        m.mat("tr_head")
        m.box((sx * 0.03, -0.08, 0.0), (0.08, 0.36, 0.08), smooth=False)
        m.mat("tr_tail")
        m.box((sx * 0.03, 0.24, 0.0), (0.08, 0.1, 0.07), smooth=False)
        m.pop()
    # cab windscreen on the crown of the nose: a band of dark glass laid over every point of the body profile (so
    # the white crown never shows through it), with two anime glints across it
    m.mat("tr_mask")
    crown = [(-1.07, 2.96), (-0.93, 3.12), (-0.6, 3.24), (0.0, ROOF - 0.02), (0.6, 3.24), (0.93, 3.12), (1.07, 2.96)]
    rows = []
    for t in (0.36, 0.46, 0.56, 0.66, 0.74):
        y, sx, zs = _nose(t)
        rows.append([(px * sx * 1.025, y, FLOOR + (pz - FLOOR) * zs + 0.05) for (px, pz) in crown])
    for a, b in zip(rows[:-1], rows[1:]):
        for k in range(len(crown) - 1):
            q = [a[k], a[k + 1], b[k + 1], b[k]]
            m.poly(q)
            m.poly(q[::-1])
    m.mat("tr_text_white", tint=0xCFE4FF)
    for (t0, t1, w) in ((0.44, 0.5, 0.05), (0.53, 0.55, 0.025)):
        pts = []
        for t, px in ((t0, -0.75), (t1, 0.35)):
            y, sx, zs = _nose(t)
            cz = next(za + (zb - za) * (px - xa) / (xb - xa)
                      for (xa, za), (xb, zb) in zip(crown, crown[1:]) if xa <= px <= xb)
            pts.append(V((px * sx * 1.03, y, FLOOR + (cz - FLOOR) * zs + 0.07)))
        m.tube(pts, r=w * 0.5, seg=4)
    # name badge and tip coupler cover
    m.mat("tr_band_" + band)
    m.sphere((0, 0.02, FLOOR + 0.22), 0.2, 16, 8, s=(1.2, 0.4, 0.6))
    m.mat("tr_text_white")
    m.push(Matrix.Translation((0, -0.04, FLOOR + 0.22)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
    m.text("桜", size=0.2, depth=0.01, font=E.FONT_JP, c=(0, 0, -0.06))
    m.pop()
    m.mat("tr_under")
    m.poly([(-0.6, 0.6, 0.35), (0.6, 0.6, 0.35), (0.6, 4.0, 0.35), (-0.6, 4.0, 0.35)])
    m.poly([(-0.46, 0.02, FLOOR - 0.02), (0.46, 0.02, FLOOR - 0.02), (0.6, 0.6, 0.35), (-0.6, 0.6, 0.35)][::-1])


def express(name="express_front", band="crimson", front=True, seed=5):
    mats()
    m = E.Mesher(name)
    y0 = NOSE if front else 0.45
    y1 = CAR - 0.45
    m.mat("tr_white")
    m.quad_strip([_ring(y0), _ring(y1)], closed=True, cap0=not front, cap1=True, smooth=False)
    doors = (CAR - 1.6,) if front else (1.6, CAR - 1.6)
    _car_sides(m, y0, y1, band, None, doors, seed)
    _roof(m, y0, y1, pantograph=not front, seed=seed)
    _bogie(m, 2.6 if front else 2.2)
    _bogie(m, CAR - 2.2)
    _underfloor(m, 4.2, CAR - 3.8, seed)
    if front:
        _express_nose(m, band)
    else:
        _gangway(m, y0, -1)
    _gangway(m, y1, 1)
    # skirt panels hide the underfloor on the express
    for sx in (-1, 1):
        m.mat("tr_white")
        m.box((sx * 1.0, (y0 + 0.4 + y1) / 2, FLOOR - 0.18), (0.04, y1 - y0 - 0.8, 0.34), smooth=False)
    ob = m.obj(name, smooth_angle=30)
    E.finish_hard(ob, width=0.008, segments=1, angle=35)
    return ob


# ----------------------------------------------------------------------------- ramp

RAMP_LEN = 8.0


def ramp(name="ramp"):
    """Steel boarding ramp from the ballast up to a train roof: chequer-plate deck with yellow/black nosing,
    lattice side girders, A-frame legs and a little 'mind your step' plate."""
    mats()
    m = E.Mesher(name)
    w = 1.9
    def z_at(y):
        return 0.12 + (ROOF - 0.12) * y / RAMP_LEN
    # deck as a sloped slab
    ang = math.atan2(ROOF - 0.12, RAMP_LEN)
    Ld = math.hypot(ROOF - 0.12, RAMP_LEN)
    m.push(Matrix.Translation((0, 0, 0.12)) @ Matrix.Rotation(ang, 4, 'X'))
    m.mat("tr_plate", uvscale=0.5)
    m.box((0, Ld / 2, -0.05), (w, Ld, 0.1), smooth=False)
    # treads
    m.mat("tr_steel_dark")
    for k in range(1, int(Ld / 0.5)):
        m.box((0, k * 0.5, 0.01), (w - 0.3, 0.05, 0.03), smooth=False)
    # hazard edges
    for sx in (-1, 1):
        for k in range(int(Ld / 0.4)):
            m.mat("tr_yellow" if k % 2 == 0 else "tr_black")
            m.box((sx * (w / 2 - 0.06), k * 0.4 + 0.2, 0.01), (0.12, 0.4, 0.04), smooth=False)
    m.mat("tr_yellow")
    m.box((0, 0.05, 0.0), (w, 0.1, 0.06), smooth=False)
    m.pop()
    # lattice side girders under the deck edges
    for sx in (-1, 1):
        x = sx * (w / 2 + 0.03)
        m.mat("tr_band_amber", tint=0xE5E0D0)
        for k in range(8):
            ya, yb = k * RAMP_LEN / 8, (k + 1) * RAMP_LEN / 8
            m.sweep([V((x, ya, 0.05)), V((x, yb, z_at(yb) - 0.12))], [(-0.03, -0.03), (0.03, -0.03), (0.03, 0.03), (-0.03, 0.03)])
            m.sweep([V((x, yb, 0.05)), V((x, yb, z_at(yb) - 0.12))], [(-0.035, -0.035), (0.035, -0.035), (0.035, 0.035), (-0.035, 0.035)])
        m.sweep([V((x, 0.0, 0.05)), V((x, RAMP_LEN, 0.05))], [(-0.04, -0.04), (0.04, -0.04), (0.04, 0.04), (-0.04, 0.04)])
    # foot pads and top hooks that latch onto the roof
    m.mat("tr_black")
    for sx in (-1, 1):
        for y in (0.4, RAMP_LEN / 2, RAMP_LEN - 0.4):
            m.box((sx * (w / 2 + 0.03), y, 0.03), (0.24, 0.3, 0.06), smooth=False)
        m.box((sx * 0.6, RAMP_LEN + 0.12, ROOF + 0.02), (0.14, 0.4, 0.06), smooth=False)
    # warning plate on a post beside the foot of the ramp
    m.mat("tr_steel_dark")
    m.cyl((w / 2 + 0.25, 0.2, 0.6), r=0.025, h=1.2, seg=8)
    m.mat("tr_sign_white")
    m.box((w / 2 + 0.25, 0.17, 1.15), (0.5, 0.03, 0.3), smooth=False)
    m.mat("tr_red")
    m.push(Matrix.Translation((w / 2 + 0.25, 0.15, 1.15)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
    m.text("足元注意", size=0.1, depth=0.004, font=E.FONT_JP)
    m.pop()
    ob = m.obj(name, smooth_angle=30)
    E.finish_hard(ob, width=0.006, segments=1, angle=35)
    return ob


# ----------------------------------------------------------------------------- track works (BLOCK)

def _worker(m, c):
    """The bowing helmeted worker from Japanese 'sorry for the trouble' signs, as a flat cut-out."""
    x, y, z = c
    m.mat("tr_sign_white")
    m.rbox((x, y, z + 0.32), (0.62, 0.03, 0.8), r=0.03, seg=2)
    m.mat("tr_sign_blue")
    m.box((x, y - 0.02, z + 0.3), (0.2, 0.01, 0.34), smooth=False)       # body
    m.push(Matrix.Translation((x, y - 0.02, z + 0.5)) @ Matrix.Rotation(math.radians(-35), 4, 'Y'))
    m.box((0, 0, 0.0), (0.2, 0.01, 0.12), smooth=False)                 # bowed shoulders
    m.mat("tr_skin")
    m.cyl((0.06, 0, 0.12), r=0.07, h=0.012, seg=14, axis='Y')
    m.mat("tr_yellow")
    m.cyl((0.08, -0.004, 0.17), r=0.08, h=0.012, seg=14, axis='Y', r2=None)
    m.pop()
    m.mat("tr_sign_blue")
    for dx in (-0.05, 0.05):
        m.box((x + dx, y - 0.02, z + 0.04), (0.06, 0.01, 0.2), smooth=False)


def works(name="works"):
    """Track-works barrier filling one lane up to 2.9 m: striped posts, a big 工事中 board with the bowing
    worker, an amber arrow-light panel on top, sandbags and cones at its feet."""
    mats()
    m = E.Mesher(name)
    W = 2.1
    for sx in (-1, 1):
        for k in range(10):
            m.mat("tr_yellow" if k % 2 == 0 else "tr_black")
            m.box((sx * W / 2, 0.3, 0.145 + k * 0.29), (0.12, 0.12, 0.29), smooth=False)
        m.mat("tr_black")
        m.box((sx * W / 2, 0.3, 0.03), (0.4, 0.5, 0.06), smooth=False)
    # main board
    m.mat("tr_sign_blue")
    m.rbox((0, 0.3, 1.55), (W - 0.1, 0.06, 1.2), r=0.04, seg=2)
    m.mat("tr_sign_white")
    m.box((0.25, 0.26, 1.55), (1.3, 0.02, 1.06), smooth=False)
    m.mat("tr_red")
    m.push(Matrix.Translation((0.25, 0.232, 1.78)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
    m.text("工事中", size=0.34, depth=0.01, font=E.FONT_JP)
    m.pop()
    m.mat("tr_text_dark")
    m.push(Matrix.Translation((0.25, 0.235, 1.38)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
    m.text("ご迷惑をおかけします", size=0.1, depth=0.006, font=E.FONT_JP)
    m.pop()
    m.push(Matrix.Translation((0.25, 0.235, 1.18)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
    m.text("桜線保線区", size=0.09, depth=0.006, font=E.FONT_JP)
    m.pop()
    _worker(m, (-0.68, 0.25, 1.06))
    # lower striped rail
    for k in range(8):
        m.mat("tr_red" if k % 2 == 0 else "tr_sign_white")
        m.box((-W / 2 + 0.06 + (k + 0.5) * (W - 0.12) / 8, 0.3, 0.62), ((W - 0.12) / 8, 0.08, 0.16), smooth=False)
    # arrow light board on top
    m.mat("tr_black")
    m.rbox((0, 0.3, 2.62), (1.6, 0.14, 0.52), r=0.04, seg=2)
    m.mat("tr_lamp_amber")
    arrow = [(-0.6, 0.0), (-0.36, 0.0), (-0.12, 0.0), (0.12, 0.0), (0.36, 0.0), (0.22, 0.14), (0.22, -0.14), (0.08, 0.2), (0.08, -0.2)]
    for (ax, az) in arrow:
        m.cyl((ax, 0.225, 2.62 + az), r=0.045, h=0.02, seg=12, axis='Y')
    m.mat("tr_steel_dark")
    m.box((0, 0.36, 2.25), (0.08, 0.06, 0.3), smooth=False)
    # sandbags and cones
    rnd = random.Random(3)
    for k in range(5):
        m.mat("tr_sandbag")
        m.rbox((-0.85 + k * 0.42 + rnd.uniform(-0.03, 0.03), -0.05, 0.1), (0.38, 0.26, 0.18), r=0.07, seg=2)
    for k in range(3):
        m.mat("tr_sandbag")
        m.rbox((-0.62 + k * 0.42, -0.04, 0.27), (0.38, 0.24, 0.16), r=0.07, seg=2)
    for x in (-0.95, 0.95):
        m.mat("tr_cone")
        m.cyl((x, -0.45, 0.32), r=0.15, h=0.6, r2=0.03, seg=18)
        m.mat("tr_sign_white")
        m.cyl((x, -0.45, 0.36), r=0.105, h=0.1, r2=0.085, seg=18)
        m.mat("tr_black")
        m.box((x, -0.45, 0.02), (0.36, 0.36, 0.04), smooth=False)
    ob = m.obj(name, smooth_angle=30)
    E.finish_hard(ob, width=0.006, segments=1, angle=35)
    return ob


# ----------------------------------------------------------------------------- design renders / export

ALL = [("commuter_front", lambda: commuter("commuter_front", "teal", True, 1)),
       ("commuter_mid", lambda: commuter("commuter_mid", "teal", False, 2)),
       ("commuter_front_b", lambda: commuter("commuter_front_b", "amber", True, 3)),
       ("commuter_mid_b", lambda: commuter("commuter_mid_b", "amber", False, 4)),
       ("express_front", lambda: express("express_front", "crimson", True, 5)),
       ("express_mid", lambda: express("express_mid", "crimson", False, 6)),
       ("express_front_b", lambda: express("express_front_b", "cobalt", True, 7)),
       ("express_mid_b", lambda: express("express_mid_b", "cobalt", False, 8)),
       ("ramp", ramp),
       ("works", works)]


def _track_bed(n=6, y0=-12.0):
    import city
    city.city_mats()
    for i in range(n):
        for fn in (city.track, city.side, lambda: city.side(mirror=True)):
            ob = fn()
            ob.location.y = y0 + i * city.SEG


def design_trains():
    import studio, city
    E.reset()
    studio.stage(res=(1600, 900), floor=False)
    _track_bed(6)
    obs = []
    a = commuter("commuter_front", "teal", True, 1); a.location = (-2.4, 0, 0); obs.append(a)
    b = commuter("commuter_mid", "teal", False, 2); b.location = (-2.4, CAR, 0); obs.append(b)
    c = express("express_front", "crimson", True, 5); c.location = (2.4, 6, 0); obs.append(c)
    d = express("express_mid", "crimson", False, 6); d.location = (2.4, 6 + CAR, 0); obs.append(d)
    r = ramp(); r.location = (0, -8 + 2, 0); obs.append(r)
    t = commuter("commuter_front_b", "amber", True, 3); t.location = (0, 2, 0); obs.append(t)
    for o in obs:
        E.add_outline(o, 0.02)
    studio.aim_sun(20)
    studio.shoot("trains_overview", target=(0, 8, 1.6), dist=17, yaw=28, pitch=16, lens=30)
    studio.shoot("trains_runner", target=(0, 10, 1.4), dist=14, yaw=0, pitch=10, lens=28)
    studio.shoot("trains_express_nose", target=(2.4, 7.5, 1.7), dist=7, yaw=40, pitch=10, lens=35)
    studio.shoot("trains_commuter_face", target=(-2.4, 0.5, 1.9), dist=5.5, yaw=30, pitch=6, lens=35)


def design_obstacles():
    import studio, obstacles
    E.reset()
    studio.stage(res=(1600, 900), floor=False)
    _track_bed(3)
    w = works(); w.location = (-2.4, 4, 0)
    r = ramp(); r.location = (0, 0, 0)
    t = commuter("commuter_front", "teal", True, 1); t.location = (0, RAMP_LEN, 0)
    b = obstacles.barricade(); b.location = (2.4, 2, 0)
    g = obstacles.gantry(); g.location = (2.4, 9, 0)
    for o in (w, r, t, b, g):
        E.add_outline(o, 0.018)
    studio.aim_sun(20)
    studio.shoot("track_obstacles", target=(0, 6, 1.3), dist=12, yaw=22, pitch=14, lens=32)
    studio.shoot("works_close", target=(-2.4, 4, 1.5), dist=4.2, yaw=15, pitch=4, lens=35)


def export_trains():
    """Three game tiers (blender/lib/gamelod.py). The cab ends and the track obstacles keep their edge bevel up
    close, where the highlight still reads; the middle cars are flat-shaded at every tier."""
    import obstacles, gamelod as GL
    for nm, fn in ALL + [("ob_barricade", obstacles.barricade), ("ob_gantry", obstacles.gantry)]:
        for lv in (0, 1, 2):
            E.reset()
            E.export_erm(GL.tier(fn(), lv, 0.3, keep_bevel="_mid" not in nm), nm + GL.sfx(lv))
