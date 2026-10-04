"""
PONGO obstacles, sized to the action that clears them (collision rules in Game.java / docs/PONGO_DESIGN.md):

  Sakura Line, Express Rooftops (run):
    barricade   LOW   top bar at 0.95 m           -> jump over
    gantry      HIGH  beam underside at 1.55 m     -> slide (roll) under
  Crystal Cavern (ore cart):
    log_pile    LOW   0.55 m timber stack          -> cart hop
    beam        HIGH  timber beam at 1.25 m        -> crouch in the cart
    bat_swarm   HIGH  bats at 1.2-1.9 m, flying in -> crouch
    crystals    SIDE  cluster at the rail edge     -> tilt away
  Bamboo River (boat, tilt only):
    stone, crocodile, drift_log                    -> tilt around; Y-fork island -> swipe to pick a branch
  Sky Glide (glider, two altitudes):
    kite, balloons, crow_flock, chime_cable, spire -> climb/dive and tilt

Everything is built at the origin, facing the runner (who comes from -Y), lane width ~2.2 m.
"""
import math, random
import bpy
from mathutils import Vector, Matrix
import erlib as E

V = Vector


def mats():
    M = E.mat
    M("ob_yellow", 0xF6C431, rim=0.3, soft=0.08, spec=0.2)
    M("ob_black", 0x2A2A30, rim=0.3, soft=0.08, spec=0.2)
    M("ob_red", 0xE8473C, rim=0.3, soft=0.08, spec=0.3)
    M("ob_white", 0xF4F4F0, rim=0.25, soft=0.1)
    M("ob_steel", 0x9AA3AE, spec=0.8, rim=0.4, soft=0.05, flags=E.F_METAL)
    M("ob_lamp", 0xFF5A3C, emis=0.9, rim=0.2, soft=0.05, outline=0.3)
    M("ob_paper", 0xFFF1D6, emis=0.35, rim=0.2, soft=0.1)
    M("ob_paper_red", 0xE8473C, emis=0.25, rim=0.2, soft=0.1)


def _stripes(m, x0, x1, z0, z1, y, depth, n=8, mats_=("ob_yellow", "ob_black"), slant=0.6):
    """Diagonal hazard stripes on a bar spanning x0..x1 (front face at y - depth/2)."""
    h = z1 - z0
    w = (x1 - x0) / n
    for i in range(n):
        xa = x0 + i * w
        m.mat(mats_[i % 2])
        pts = [(xa, y, z0), (xa + w, y, z0), (xa + w + slant * h * 0.0, y, z1), (xa, y, z1)]
        m.box(((xa + xa + w) / 2, y, (z0 + z1) / 2), (w, depth, h), bevel=None, smooth=False)


def barricade(name="ob_barricade"):
    """Track barricade (LOW): striped top bar at 0.78-0.95 m on two trestle legs, red lamps, reflectors."""
    mats()
    m = E.Mesher(name)
    W = 2.1
    # trestle legs
    for sx in (-1, 1):
        m.mat("ob_white")
        for dy in (-0.22, 0.22):
            m.push(Matrix.Translation((sx * (W / 2 - 0.08), dy * 0.5, 0.45)) @ Matrix.Rotation(math.radians(-dy * 70), 4, 'X'))
            m.box((0, 0, 0), (0.07, 0.06, 0.95), smooth=False)
            m.pop()
        m.mat("ob_black")
        m.box((sx * (W / 2 - 0.08), 0, 0.02), (0.16, 0.5, 0.04), smooth=False)
        # warning lamp on top of the post
        m.mat("ob_black")
        m.cyl((sx * (W / 2 - 0.08), 0, 1.0), r=0.05, h=0.05, seg=16)
        m.mat("ob_lamp")
        m.sphere((sx * (W / 2 - 0.08), 0, 1.06), 0.055, 16, 8)
    # striped top bar (yellow/black) and a plain lower bar
    _stripes(m, -W / 2, W / 2, 0.78, 0.95, 0.0, 0.07, n=10)
    m.mat("ob_white")
    m.box((0, 0, 0.36), (W - 0.1, 0.05, 0.1), smooth=False)
    # reflectors
    m.mat("ob_red")
    for x in (-0.6, 0.0, 0.6):
        m.push(Matrix.Translation((x, -0.037, 0.865)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
        m.cyl((0, 0, 0), r=0.04, h=0.01, seg=16)
        m.pop()
    ob = m.obj(name, smooth_angle=30)
    E.finish_hard(ob, width=0.008, segments=2, angle=35)
    return ob


def gantry(name="ob_gantry"):
    """Hazard gantry (HIGH): striped box beam with its underside at 1.55 m, steel posts, a hanging warning
    board above the beam and paper lanterns at the ends (outside the lane)."""
    mats()
    m = E.Mesher(name)
    W = 2.4
    m.mat("ob_steel")
    for sx in (-1, 1):
        m.box((sx * W / 2, 0, 1.25), (0.14, 0.14, 2.5), smooth=False)
        m.box((sx * W / 2, 0, 0.03), (0.34, 0.34, 0.06), smooth=False)
    _stripes(m, -W / 2, W / 2, 1.55, 1.85, 0.0, 0.18, n=12)
    m.mat("ob_white")
    m.box((0, 0.0, 2.2), (1.3, 0.05, 0.42), smooth=False)
    m.mat("ob_red")
    m.box((0, -0.03, 2.2), (1.22, 0.01, 0.34), smooth=False)
    m.mat("ob_white")
    m.push(Matrix.Translation((0, -0.04, 2.2)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
    m.text("頭上注意", size=0.2, depth=0.01, font=E.FONT_JP, c=(0, 0, 0))
    m.pop()
    m.mat("ob_steel")
    for sx in (-0.5, 0.5):
        m.box((sx, 0.0, 1.98), (0.03, 0.03, 0.3), smooth=False)
    # paper lanterns hanging outside the lane
    for sx in (-1, 1):
        x = sx * (W / 2 + 0.28)
        m.mat("ob_black")
        m.cyl((x, 0, 1.55), r=0.006, h=0.3, seg=6)
        m.mat("ob_paper_red" if sx > 0 else "ob_paper")
        m.sphere((x, 0, 1.25), 1.0, 16, 10, s=(0.13, 0.13, 0.17))
        m.mat("ob_black")
        m.cyl((x, 0, 1.41), r=0.07, h=0.03, seg=12)
        m.cyl((x, 0, 1.09), r=0.07, h=0.03, seg=12)
    ob = m.obj(name, smooth_angle=30)
    E.finish_hard(ob, width=0.01, segments=2, angle=35)
    return ob
