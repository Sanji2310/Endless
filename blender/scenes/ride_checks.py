"""
Numeric checks for the ride poses (no rendering):
  paddle   samples the stroke and the rudder and reports how close the shaft/blade come to the canoe hull,
           and whether anything but the blade goes under the water
  reach    solves every vehicle pose and reports how far each hand/foot ends up from its IK target
  heights  head top above the cart floor standing and ducked, in world metres (Pongo scaled)
Run: blender -b -P blender/run.py -- ride_checks all
"""
import math
from mathutils import Vector
import vehicles as VH
import pongo_moves as PM

V = Vector
L = 1.75
BLADE_TOP = 1.24
SHAFT_END = 1.76


def _hull_hit(pw):
    """Clearance (m, negative = inside) of a world point (boat space) from the hull solid incl. gunwale."""
    if abs(pw.y) > L * 0.99:
        return 1.0
    w, d, rise = VH._hull(pw.y, L)
    top = 0.2 + rise + 0.055
    bottom = 0.16 - d * 0.95 + rise - 0.05
    if pw.z < bottom:
        return 1.0
    dx, dz = abs(pw.x) - (w + 0.075), pw.z - top
    if dx > 0 and dz > 0:
        return math.hypot(dx, dz)
    return max(dx, dz)


def paddle(*_):
    worst, wet = 9.0, []
    for tilt in (0.0, 1.0, -1.0):
        for i in range(200):
            ph = i / 200
            top, d = PM.paddle_at(ph, tilt)
            for k in range(0, 89):
                s = SHAFT_END * k / 88
                p = top + d * s
                r = 0.02 if s < BLADE_TOP else 0.1
                pw = p * PM.SCALE + PM.CHAR_BOAT
                c = _hull_hit(pw) - r
                if c < worst:
                    worst, at = c, (tilt, ph, s, tuple(round(x, 2) for x in pw))
                if pw.z < 0.0 and s < BLADE_TOP - 0.12:
                    wet.append((tilt, round(ph, 3), round(s, 2)))
    print("PADDLE worst hull clearance %.3f m at tilt/phase/s/pt %s" % (worst, at))
    print("PADDLE shaft under water samples: %d %s" % (len(wet), wet[:6]))


def reach(*_):
    import bpy
    import erlib as E
    import pongo_g as PG
    import motion as MO
    E.reset()
    B, arm, objs = PG.build_pongo_g()
    rig = MO.Rig(arm)
    cases = []
    for c in (0.0, 1.0):
        for tx in (-1.0, 0.0, 1.0):
            cases.append(("cart c%.0f t%.0f" % (c, tx), PM.cart_pose(0.1, tilt=tx, crouch=c)))
    for i in range(10):
        cases.append(("boat %.1f" % (i / 10), PM.boat_pose(i / 10)))
    for tx in (-1.0, 1.0):
        cases.append(("boat t%.0f" % tx, PM.boat_pose(0.1, tilt=tx)))
    for tx, ty in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
        cases.append(("glide %d %d" % (tx, ty), PM.glide_pose(0.0, tx, ty)))
    for name, (pose, root, hands, feet) in cases:
        world, basis = PM.solve(arm, rig, pose, root, hands, feet)
        errs = []
        for grp, bones in ((hands or {}, PM.ARMS), (feet or {}, PM.LEGS)):
            for sfx, tg in grp.items():
                tip = rig.point(world, bones[sfx][1], at_tail=True)
                errs.append("%s%s %.3f" % ("h" if grp is hands else "f", sfx, (tip - tg.pos).length * tg.w))
        print("REACH %-12s %s" % (name, "  ".join(errs)))


def heights(*_):
    import erlib as E
    import pongo_g as PG
    import motion as MO
    E.reset()
    B, arm, objs = PG.build_pongo_g()
    rig = MO.Rig(arm)
    for c in (0.0, 1.0):
        pose, root, hands, feet = PM.cart_pose(0.1, crouch=c)
        world, basis = PM.solve(arm, rig, pose, root, hands, feet)
        hz = rig.point(world, "head", at_tail=True).z
        print("HEIGHT cart crouch=%.0f head bone %.3f local -> %.3f m above rails (floor %.2f)" %
              (c, hz, PM.CHAR_CART.z + hz * PM.SCALE, PM.CHAR_CART.z))


def all(*_):
    paddle()
    heights()
    reach()
