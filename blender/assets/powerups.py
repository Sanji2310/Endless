"""
PONGO power-ups and pickups in the Sakura toon style (see docs/PONGO_DESIGN.md section 3).

Pickups float about 1 m above the track and spin; each is ~0.8 m across so it reads at runner distance.
  pu_magnet   Maneki Magnet   golden lucky cat with a raised paw and a horseshoe-magnet bib
  pu_rocket   Hayate Rocket   red twin-thruster pack with wind-swirl fins
  pu_boots    Tobi Boots      spring-soled high-tops with little white wings
  pu_x2       Fever Star      chubby golden star with a "2X" badge
  pu_gacha    Gacha Capsule   two-tone capsule toy with a prize peeking through (mystery box)
  pu_omamori  Omamori         red silk charm bag with a gold knot (revive / key)
  kaze_board  Kaze Board      hoverboard with wind fins and glowing pods (ridden)
  rocket_pack Hayate pack worn on Pongo's back while flying
  pickup_halo soft ring drawn under every floating pickup
Blender: Z up, pickups centred on the origin, facing -Y (toward the runner).
"""
import math
from mathutils import Vector, Matrix
import erlib as E

V = Vector


def mats():
    M = E.mat
    M("pu_gold", 0xFFC62E, spec=0.6, rim=0.45, emis=0.08, soft=0.08, shadow=0xC0601E)
    M("pu_gold_deep", 0xE9A21C, spec=0.6, rim=0.3, emis=0.05, soft=0.08, shadow=0xA84A16)
    M("pu_white", 0xFBF8F1, spec=0.3, rim=0.4, soft=0.1, shadow=0xB8B2DA)
    M("pu_red", 0xE8473C, spec=0.5, rim=0.4, soft=0.08, shadow=0x9A2A5A)
    M("pu_red_dark", 0xB02A33, spec=0.4, rim=0.3, soft=0.08)
    M("pu_navy", 0x22356E, spec=0.3, rim=0.35, soft=0.08)
    M("pu_teal", 0x37B4C8, spec=0.4, rim=0.4, soft=0.08)
    M("pu_pink", 0xFF9AB8, spec=0.3, rim=0.4, soft=0.1, shadow=0xB86A9A)
    M("pu_ink", 0x2A2433, rim=0.1, soft=0.05, outline=0.0)
    M("pu_etch", 0xA8620E, spec=0.25, rim=0.05, soft=0.1, outline=0.0, shadow=0x7A3A10)    # engraved line in gold
    M("pu_steel", 0xB9C1CC, spec=0.8, rim=0.4, soft=0.05, flags=E.F_METAL)
    M("pu_flame", 0xFFB23A, emis=1.0, rim=0.2, soft=0.04, outline=0.0)
    M("pu_glow_cyan", 0x7FF0FF, emis=1.0, rim=0.3, soft=0.04, outline=0.3)
    M("pu_glass", 0xBFE8FF, spec=1.0, rim=0.5, soft=0.04, flags=E.F_GLASS, outline=0.4)
    M("pu_orange", 0xFF8A2A, spec=0.3, rim=0.35, soft=0.08)
    M("pu_halo", 0xFFF3C4, emis=1.0, rim=0.0, soft=0.0, outline=0.0, flags=E.F_NOCAST | E.F_DOUBLE)


def _finish(m, name, bevel=0.006):
    ob = m.obj(name, smooth_angle=35)
    if bevel:
        E.finish_hard(ob, width=bevel, segments=1, angle=35)
    return ob


# ----------------------------------------------------------------------------- Maneki Magnet

def magnet(name="pu_magnet", etched=True):
    mats()
    m = E.Mesher(name)
    # body: pear-shaped sitting cat
    m.mat("pu_gold")
    m.sphere((0, 0, -0.12), 0.26, 24, 14, s=(1.0, 0.85, 1.05))
    m.sphere((0, 0, 0.22), 0.22, 24, 14, s=(1.12, 0.95, 0.95))     # head
    for sx in (-1, 1):                                             # ears
        m.push(Matrix.Translation((sx * 0.14, 0, 0.38)) @ Matrix.Rotation(math.radians(-sx * 20), 4, 'Y'))
        m.cyl((0, 0, 0.04), r=0.07, h=0.11, r2=0.0, seg=4)
        m.mat("pu_pink")
        m.cyl((0, -0.02, 0.035), r=0.045, h=0.07, r2=0.0, seg=4)
        m.mat("pu_gold")
        m.pop()
    # face: eyes as closed happy arcs, nose, whiskers
    m.mat("pu_ink")
    for sx in (-1, 1):
        m.torus((sx * 0.085, -0.2, 0.24), R=0.035, r=0.008, seg=12, sides=6, arc=180, axis='Y')
        for dz in (-0.015, 0.015):
            m.push(Matrix.Translation((sx * 0.17, -0.19, 0.17 + dz)) @ Matrix.Rotation(math.radians(sx * dz * 400), 4, 'Y'))
            m.box((0, 0, 0), (0.1, 0.005, 0.006), smooth=False)
            m.pop()
    m.mat("pu_pink")
    m.sphere((0, -0.215, 0.19), 0.022, 10, 6)
    m.mat("pu_red")
    m.torus((0, -0.005, 0.06), R=0.19, r=0.025, seg=24, sides=8, axis='Z')        # collar
    m.mat("pu_gold_deep")
    m.sphere((0, -0.2, 0.02), 0.045, 12, 8)                                      # bell
    m.torus((0.03, 0.235, -0.2), R=0.065, r=0.028, seg=18, sides=8, arc=270, axis='Y')    # short curled tail on the back
    m.sphere((0.095, 0.235, -0.2), 0.032, 10, 6)
    # raised beckoning paw (right), clear of the head beside the cheek, pad to the front
    m.mat("pu_gold")
    m.push(Matrix.Translation((0.2, -0.07, 0.1)) @ Matrix.Rotation(math.radians(26), 4, 'Y'))
    m.cyl((0, 0, 0.12), r=0.06, h=0.24, seg=14)
    m.sphere((0, 0, 0.26), 0.078, 14, 8)
    m.mat("pu_pink")
    m.sphere((0, -0.065, 0.26), 0.032, 10, 6, s=(1, 0.5, 1))
    for k in (-1, 0, 1):
        m.sphere((k * 0.03, -0.055, 0.315), 0.013, 8, 6, s=(1, 0.6, 1))              # toe beans
    m.pop()
    if not etched:
        # the first design: a little red horseshoe magnet held in the left paw, the koban on the belly
        m.push(Matrix.Translation((-0.16, -0.24, -0.08)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
        m.mat("pu_red")
        m.torus((0, 0, 0), R=0.12, r=0.035, seg=20, sides=8, arc=180, axis='Z')
        for sx in (-1, 1):
            m.mat("pu_red")
            m.cyl((sx * 0.12, -0.04, 0), r=0.035, h=0.08, seg=10, axis='Y')
            m.mat("pu_steel")
            m.cyl((sx * 0.12, -0.1, 0), r=0.036, h=0.05, seg=10, axis='Y')
        m.pop()
        m.mat("pu_gold_deep")
        m.sphere((0.04, -0.23, -0.16), 0.11, 18, 8, s=(0.75, 0.2, 1.0))
        m.mat("pu_ink")
        m.push(Matrix.Translation((0.04, -0.255, -0.16)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
        m.text("福", size=0.09, depth=0.004, font=E.FONT_JP)
        m.pop()
        return _finish(m, name, 0)
    # the left paw holds the koban (小判) the way maneki-neko do, resting on the lap
    m.mat("pu_gold")
    m.sphere((-0.15, -0.17, -0.06), 0.065, 14, 8, s=(1.0, 1.1, 0.85))
    m.mat("pu_gold_deep")
    m.push(Matrix.Translation((-0.17, -0.235, -0.13)) @ Matrix.Rotation(math.radians(-12), 4, 'Y'))
    m.sphere((0, 0, 0), 0.085, 18, 8, s=(0.72, 0.2, 1.0))
    m.mat("pu_ink")
    m.push(Matrix.Translation((0, -0.02, 0)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
    m.text("福", size=0.07, depth=0.004, font=E.FONT_JP)
    m.pop()
    m.pop()
    # the magnet is engraved into the belly: a horseshoe groove with its two pole bands, following the curve
    belly_c, belly_r, belly_s = Vector((0, 0, -0.12)), 0.26, Vector((1.0, 0.85, 1.05))
    def on_belly(x, z, sink=0.003):
        # point on the belly surface (front, -Y) at (x, z), pushed `sink` inward
        dx, dz = x / (belly_r * belly_s.x), (z - belly_c.z) / (belly_r * belly_s.z)
        y = -belly_r * belly_s.y * math.sqrt(max(0.0, 1 - dx * dx - dz * dz))
        return V((x, y + sink, z))
    ex, ez, R, leg = 0.06, -0.07, 0.075, 0.075
    arc = [on_belly(ex + R * math.cos(math.radians(a)), ez + R * math.sin(math.radians(a))) for a in range(0, 181, 10)]
    right = [on_belly(ex + R, ez - leg * t) for t in (1.0, 0.66, 0.33)]
    left = [on_belly(ex - R, ez - leg * t) for t in (0.33, 0.66, 1.0)]
    m.mat("pu_etch")
    m.tube(right + arc + left, r=0.011, seg=8)
    # pole marks: a short cut across each leg near its end
    for x in (ex - R, ex + R):
        m.tube([on_belly(x - 0.022, ez - leg * 0.72), on_belly(x + 0.022, ez - leg * 0.72)], r=0.008, seg=6)
    return _finish(m, name, 0)


# ----------------------------------------------------------------------------- Hayate Rocket

def _thruster(m, x, z0=-0.3, h=0.62, r=0.11, flame=True):
    m.mat("pu_red")
    m.cyl((x, 0, z0 + h / 2), r=r, h=h, seg=20)
    m.cyl((x, 0, z0 + h + 0.1), r=r, h=0.2, r2=0.02, seg=20)
    m.mat("pu_white")
    m.cyl((x, 0, z0 + h * 0.7), r=r + 0.006, h=0.06, seg=20)
    m.mat("pu_steel")
    m.cyl((x, 0, z0 - 0.04), r=r * 0.8, h=0.08, r2=r * 0.95, seg=20)
    # wind-swirl fins
    for k in range(3):
        a = math.radians(90 + k * 120)
        m.mat("pu_navy")
        m.push(Matrix.Translation((x + math.cos(a) * r, math.sin(a) * r, z0 + 0.12)) @ Matrix.Rotation(a, 4, 'Z'))
        m.poly([(0, -0.012, 0), (0.1, -0.012, -0.08), (0.1, -0.012, 0.06), (0, -0.012, 0.18)])
        m.poly([(0, 0.012, 0.18), (0.1, 0.012, 0.06), (0.1, 0.012, -0.08), (0, 0.012, 0)])
        m.pop()
    if flame:
        m.mat("pu_flame")
        m.cyl((x, 0, z0 - 0.2), r=r * 0.7, h=0.26, r2=0.0, seg=12, axis='Z')


def rocket(name="pu_rocket"):
    mats()
    m = E.Mesher(name)
    for x in (-0.15, 0.15):
        _thruster(m, x, flame=False)
    m.mat("pu_white")
    m.rbox((0, 0.06, 0.02), (0.36, 0.14, 0.42), r=0.05, seg=2)
    m.mat("pu_navy")
    for sx in (-1, 1):
        m.box((sx * 0.12, -0.06, 0.05), (0.06, 0.02, 0.5), smooth=False)    # straps
    m.mat("pu_teal")
    m.cyl((0, -0.02, 0.12), r=0.07, h=0.02, seg=16, axis='Y')
    m.mat("pu_ink")
    m.push(Matrix.Translation((0, -0.035, 0.12)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
    m.text("風", size=0.08, depth=0.004, font=E.FONT_JP)
    m.pop()
    return _finish(m, name)


def rocket_pack(name="rocket_pack"):
    """The pack as worn: built at Pongo's back (origin on her spine, thrusters pointing down).
    No flame on the model: the thruster plume is the effects thread's (FxLayer)."""
    mats()
    m = E.Mesher(name)
    for x in (-0.13, 0.13):
        _thruster(m, x, z0=-0.28, h=0.5, r=0.085, flame=False)
    m.mat("pu_white")
    m.rbox((0, -0.02, 0.0), (0.3, 0.1, 0.36), r=0.04, seg=2)
    return _finish(m, name)


# ----------------------------------------------------------------------------- Tobi Boots

def _boot(m, x):
    m.mat("pu_teal")
    m.rbox((x, 0.0, 0.1), (0.15, 0.28, 0.16), r=0.06, seg=3)           # foot
    m.rbox((x, 0.07, 0.25), (0.15, 0.14, 0.26), r=0.05, seg=3)         # shaft
    m.mat("pu_white")
    m.rbox((x, -0.04, 0.03), (0.17, 0.33, 0.05), r=0.02, seg=2)        # sole
    m.cyl((x, 0.07, 0.38), r=0.085, h=0.04, seg=16)                    # collar
    m.mat("pu_orange")
    for k in range(3):
        m.box((x, -0.06 + k * 0.05, 0.19 + k * 0.03), (0.13, 0.015, 0.012), smooth=False)   # laces
    # coil spring under the sole
    m.mat("pu_steel")
    for k in range(4):
        m.torus((x, -0.02, -0.03 - k * 0.04), R=0.06, r=0.012, seg=16, sides=6, axis='Z')
    # wings on the heel
    m.mat("pu_white")
    side = 1 if x > 0 else -1
    for k, (L, a) in enumerate(((0.2, 30), (0.16, 10), (0.12, -10))):
        m.push(Matrix.Translation((x + side * 0.08, 0.12, 0.3 - k * 0.04)) @ Matrix.Rotation(math.radians(side * 25), 4, 'Z') @
               Matrix.Rotation(math.radians(a), 4, 'Y'))
        m.sphere((side * L / 2, 0.0, 0), 1.0, 12, 6, s=(L / 2, 0.012, 0.035))
        m.pop()


def boots(name="pu_boots"):
    mats()
    m = E.Mesher(name)
    _boot(m, -0.11)
    _boot(m, 0.11)
    return _finish(m, name, 0)


# ----------------------------------------------------------------------------- Fever Star (2X)

def x2(name="pu_x2"):
    mats()
    m = E.Mesher(name)
    pts = E.star_pts(5, 0.36, 0.17)
    m.push(Matrix.Rotation(math.radians(90), 4, 'X'))
    m.mat("pu_gold")
    m.extrude(pts, 0.14, bevel=(0.04, 3))
    m.mat("pu_red")
    m.cyl((0, 0, 0.075), r=0.13, h=0.02, seg=24)
    m.mat("pu_white")
    m.push(Matrix.Translation((0, -0.005, 0.088)))
    m.text("2X", size=0.13, depth=0.01)
    m.pop()
    m.pop()
    # sparkle diamonds orbiting the star
    m.mat("pu_flame")
    for k, (x, z, s) in enumerate(((0.36, 0.28, 0.06), (-0.34, -0.22, 0.05), (0.3, -0.3, 0.04))):
        m.push(Matrix.Translation((x, 0, z)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
        m.extrude(E.star_pts(4, s, s * 0.3, rot=0), 0.01)
        m.pop()
    return _finish(m, name, 0)


# ----------------------------------------------------------------------------- Gacha Capsule (mystery)

def gacha(name="pu_gacha"):
    mats()
    m = E.Mesher(name)
    r = 0.3
    m.push(Matrix.Rotation(math.radians(-18), 4, 'Y'))
    m.mat("pu_pink")
    m.lathe([(0.0, r)] + [(r * math.sin(math.radians(a)), r * math.cos(math.radians(a))) for a in range(15, 91, 15)], seg=28)
    m.mat("pu_glass")
    m.lathe([(r * math.sin(math.radians(a)), r * math.cos(math.radians(a))) for a in range(90, 166, 15)] + [(0.0, -r)], seg=28)
    m.mat("pu_white")
    m.torus((0, 0, 0), R=r + 0.004, r=0.018, seg=28, sides=6)
    # the prize inside: a little gold "?" token
    m.mat("pu_gold")
    m.sphere((0, 0, -0.1), 0.12, 16, 8, s=(1, 0.5, 1))
    m.mat("pu_red_dark")
    m.push(Matrix.Translation((0, -0.065, -0.1)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
    m.text("?", size=0.14, depth=0.01)
    m.pop()
    m.pop()
    return _finish(m, name, 0)


# ----------------------------------------------------------------------------- Omamori

def omamori(name="pu_omamori"):
    mats()
    m = E.Mesher(name)
    m.mat("pu_red")
    # flat bag with a rounded-shoulder top
    outline = [(-0.17, -0.26), (0.17, -0.26), (0.17, 0.16), (0.11, 0.24), (-0.11, 0.24), (-0.17, 0.16)]
    m.push(Matrix.Rotation(math.radians(90), 4, 'X'))
    m.extrude(outline, 0.07, bevel=(0.025, 2))
    m.mat("pu_gold")
    # woven brocade border + kanji panel
    m.box((0, -0.04, 0.037), (0.24, 0.32, 0.01), smooth=False)
    m.mat("pu_red_dark")
    m.box((0, -0.04, 0.043), (0.2, 0.28, 0.006), smooth=False)
    m.mat("pu_gold")
    m.push(Matrix.Translation((0, 0.02, 0.048)))
    m.text("御守", size=0.085, depth=0.004, font=E.FONT_JP)
    m.pop()
    m.pop()
    # cord and knot on top
    m.mat("pu_gold_deep")
    m.torus((0, 0, 0.3), R=0.06, r=0.016, seg=16, sides=6, axis='Y')
    m.sphere((0, 0, 0.24), 0.035, 12, 8)
    for sx in (-1, 1):
        m.tube([V((sx * 0.02, 0, 0.23)), V((sx * 0.06, 0.0, 0.15)), V((sx * 0.08, 0.0, 0.05))], r=0.012, seg=6)
    return _finish(m, name, 0)


# ----------------------------------------------------------------------------- Kaze Board

def kaze_board(name="kaze_board"):
    """Hoverboard, top deck at z = 0, nose toward -Y."""
    mats()
    m = E.Mesher(name)
    L, W = 1.25, 0.36
    outline = []
    for k in range(25):
        t = k / 24
        a = math.pi * t
        outline.append((W / 2 * math.sin(a) ** 0.6, -L / 2 + L * t))
    outline = [(x, y) for (x, y) in outline] + [(-x, y) for (x, y) in reversed(outline)]
    m.push(Matrix.Translation((0, 0, -0.03)))
    m.mat("pu_navy")
    m.extrude([(p[0], p[1]) for p in outline], 0.05, bevel=(0.015, 2))
    m.pop()
    m.mat("pu_teal")
    m.extrude([(p[0] * 0.8, p[1] * 0.9) for p in outline], 0.012, c=(0, 0, 0.0))
    m.mat("pu_orange")
    for k in range(3):
        m.box((0, -0.28 + k * 0.08, 0.008), (0.24 - k * 0.04, 0.03, 0.006), smooth=False)   # wind chevrons
    # hover pods with glowing rings
    for y in (-0.38, 0.38):
        m.mat("pu_steel")
        m.cyl((0, y, -0.08), r=0.09, h=0.06, seg=20)
        m.mat("pu_glow_cyan")
        m.cyl((0, y, -0.115), r=0.065, h=0.02, seg=20)
    # tail fins
    for sx in (-1, 1):
        m.mat("pu_white")
        m.push(Matrix.Translation((sx * 0.12, 0.52, -0.02)) @ Matrix.Rotation(math.radians(sx * 15), 4, 'Y'))
        m.poly([(0, -0.1, 0), (0, 0.12, 0), (0, 0.12, -0.14)])
        m.poly([(0, 0.12, -0.14), (0, 0.12, 0), (0, -0.1, 0)])
        m.pop()
    return _finish(m, name)


# ----------------------------------------------------------------------------- halo

def halo(name="pickup_halo"):
    mats()
    m = E.Mesher(name)
    m.mat("pu_halo")
    m.torus((0, 0, 0), R=0.38, r=0.025, seg=40, sides=6, axis='Z')
    for k in range(8):
        a = 2 * math.pi * k / 8
        m.push(Matrix.Translation((math.cos(a) * 0.48, math.sin(a) * 0.48, 0)) @ Matrix.Rotation(a, 4, 'Z'))
        m.box((0, 0, 0), (0.07, 0.015, 0.01), smooth=False)
        m.pop()
    return _finish(m, name, 0)


ALL = [("pu_magnet", magnet), ("pu_rocket", rocket), ("pu_boots", boots), ("pu_x2", x2), ("pu_gacha", gacha),
       ("pu_omamori", omamori), ("kaze_board", kaze_board), ("rocket_pack", rocket_pack), ("pickup_halo", halo)]


def design_powerups():
    import studio, pickups
    E.reset()
    studio.stage(res=(1600, 900))
    items = [magnet(), rocket(), boots(), x2(), gacha(), omamori(), pickups.coin(0)]
    n = len(items)
    for i, ob in enumerate(items):
        ob.location = ((i - (n - 1) / 2) * 0.85, 0, 0.75)
        ob.rotation_euler.z = math.radians(-12)
        E.add_outline(ob, 0.008)
        h = halo(); h.location = (ob.location.x, 0, 0.04)
    b = kaze_board(); b.location = (0.0, 1.3, 0.25); b.rotation_euler.z = math.radians(70)
    E.add_outline(b, 0.008)
    studio.shoot("powerups", target=(0, 0.3, 0.6), dist=8.2, yaw=0, pitch=12, lens=40)
    studio.shoot("powerups_close", target=(-1.27, 0, 0.75), dist=2.4, yaw=-15, pitch=8, lens=50)


def design_maneki():
    """Before and after for the Maneki Magnet: the held magnet replaced by one engraved into the cat."""
    import studio
    for nm, et in (("maneki_before", False), ("maneki_after", True)):
        E.reset()
        studio.stage(res=(900, 900))
        ob = magnet(etched=et)
        ob.location = (0, 0, 0.75)
        ob.rotation_euler.z = math.radians(-14)
        E.add_outline(ob, 0.008)
        h = halo(); h.location = (0, 0, 0.04)
        studio.shoot(nm, target=(0, 0, 0.78), dist=1.9, yaw=-14, pitch=8, lens=50)
        if et:
            studio.shoot("maneki_three_quarter", target=(0, 0, 0.78), dist=1.9, yaw=-50, pitch=10, lens=50)
            studio.shoot("maneki_side", target=(0, 0, 0.78), dist=1.9, yaw=-100, pitch=6, lens=50)
            studio.shoot("maneki_back", target=(0, 0, 0.78), dist=1.9, yaw=160, pitch=10, lens=50)


def export_powerups():
    for nm, fn in ALL:
        E.reset()
        E.export_erm(fn(), nm)
