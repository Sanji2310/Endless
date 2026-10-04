"""
Pongo on her vehicles: poses driven by the same inputs as the game (phase, tilt, crouch), with FK for the body
and two-bone IK that locks her hands, feet and hips to the vehicle's contact points.

  ore cart   hands on the front rim, feet on the floor;  tilt = lean into the track switch, crouch = duck
  boat       kneeling on the woven mat; the paddle is a rigid prop: the top hand holds the T-grip, the lower
             hand sits 0.5 m down the shaft; tilt = lean and rudder the paddle on that side
  glider     seated in the harness, hands on the brake toggles; tilt X = bank (pull the inside toggle),
             tilt Y = climb (both toggles down, knees tucked) or dive (hands up, legs out)

Each vehicle has a pose function (pose dict, root offset, IK targets) used three ways:
  * baked into clips for pongo.bin (the game plays the FK clips and re-applies the same IK at runtime,
    see src/com/endlessrush/core/RideRig.java, so blends between clips never let a hand drift off a grip);
  * driven frame by frame in the ride showcase renders (blender/scenes/ride_showcase.py);
  * the design sheet below.

The character's origin sits at the vehicle mount point (CHAR_*): the vehicle is drawn at
character_origin - CHAR_* and tilts with her.
"""
import math
import bpy
from mathutils import Vector, Matrix
import erlib as E
import motion as MO
import vehicles as VH

V = Vector
CHAR_CART = V((0.0, 0.05, VH.FLOOR_CART))
CHAR_BOAT = V((0.0, -0.15, 0.06))
CHAR_GLIDE = V((0.0, 0.0, -0.68))
ARMS = {"R": ("upper_arm.R", "forearm.R"), "L": ("upper_arm.L", "forearm.L")}
LEGS = {"R": ("thigh.R", "shin.R"), "L": ("thigh.L", "shin.L")}
PADDLE_LOW = 0.5        # lower hand: distance down the shaft from the T-grip
PADDLE_BLADE = 1.5      # blade centre: distance down the shaft


def _lerp(a, b, t):
    return a + (b - a) * t


def _smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _mix(pa, pb, t):
    """Blend two Euler pose dicts (degrees)."""
    out = {}
    for k in set(pa) | set(pb):
        a, b = pa.get(k, (0, 0, 0)), pb.get(k, (0, 0, 0))
        out[k] = tuple(_lerp(a[i], b[i], t) for i in range(3))
    return out


# ----------------------------------------------------------------------------- FK + IK solve

class Target:
    """IK goal for one limb: position (character space), weight (0 = keep FK), pole offset from the root joint."""

    def __init__(self, pos, w=1.0, pole=None):
        self.pos, self.w, self.pole = V(pos), w, pole


def solve(arm, rig, pose, root, hands=None, feet=None):
    """FK from the Euler pose, then two-bone IK of each limb onto its Target (blended by weight)."""
    return solve_q(rig, MO.euler_pose(arm, pose, root), hands, feet)


def solve_q(rig, q, hands=None, feet=None):
    """Same as solve() for a quaternion pose {bone: (quat, loc)} (sampled clips, blends)."""
    world, basis = rig.fk(q)
    for limbs, tg, dflt in ((ARMS, hands, lambda sd: V((sd * 0.4, -0.3, -0.35))),
                            (LEGS, feet, lambda sd: V((sd * 0.05, 0.5, -0.15)))):
        if not tg:
            continue
        for sfx, sd in (("R", 1), ("L", -1)):
            t = tg.get(sfx)
            if t is None or t.w <= 0.001:
                continue
            up, lo = limbs[sfx]
            j0 = world[rig.index[up]].to_translation()
            goal = t.pos if t.w >= 0.999 else rig.point(world, lo, at_tail=True).lerp(t.pos, t.w)
            pole = j0 + (t.pole(sd) if t.pole else dflt(sd))
            world, basis = rig.ik2(world, basis, up, lo, goal, pole)
    return world, basis


def key_ik(arm, rig, frame, pose, root, hands=None, feet=None, arm_pole=None, leg_pole=None):
    """Old API: plain positions, full weight."""
    h = {k: Target(p, 1.0, arm_pole) for k, p in hands.items()} if hands else None
    f = {k: Target(p, 1.0, leg_pole) for k, p in feet.items()} if feet else None
    world, basis = solve(arm, rig, pose, root, h, f)
    rig.key(basis, frame)


# ----------------------------------------------------------------------------- ore cart

CART_AP = lambda sd: V((sd * 0.35, -0.25, -0.45))
CART_LP = lambda sd: V((sd * 0.12, 0.6, -0.1))
CART_GRIPS = {"R": VH.GRIP_CART[0] - CHAR_CART + V((-0.03, -0.06, 0.0)),
              "L": VH.GRIP_CART[1] - CHAR_CART + V((0.03, -0.06, 0.0))}
CART_FEET = {"R": V((0.11, 0.0, 0.075)), "L": V((-0.11, -0.04, 0.075))}


def _cart_body(lean, hip, roll=0.0, shift=0.0, head=14.0, twist=0.0):
    pose = {"root": (-lean * 0.4, roll, twist), "spine": (-lean * 0.45, roll * 0.3, 0), "chest": (-lean * 0.15, roll * 0.2, 0),
            "neck": (lean * 0.38, -roll * 0.3, 0), "head": (head, -roll * 0.5, 0),
            "foot.R": (8, 0, 0), "foot.L": (8, 0, 0), "hand.R": (0, 0, -10), "hand.L": (0, 0, 10)}
    return pose, (shift, 0.0, hip)


def cart_pose(phase, tilt=0.0, crouch=0.0, hop=0.0):
    """phase 0..1 (rattle bob, two bumps per cycle), tilt -1..1 (her left/right), crouch 0..1, hop 0..1 (bump)."""
    c = _smooth(crouch)
    bob = 0.0175 * (1 - math.cos(4 * math.pi * phase)) * (1 - 0.6 * c)
    lean = 34 + 40 * c + 6 * hop + 2 * abs(tilt)
    hip = -0.2 - 0.26 * c - bob - 0.1 * hop
    head = 14 - 2 * math.sin(4 * math.pi * phase) + 24 * c
    pose, root = _cart_body(lean, hip, roll=tilt * 17, shift=tilt * 0.09, head=head, twist=-tilt * 6)
    hands = {k: Target(p, 1.0, CART_AP) for k, p in CART_GRIPS.items()}
    feet = {k: Target(p + V((tilt * 0.03, 0, 0)), 1.0, CART_LP) for k, p in CART_FEET.items()}
    return pose, root, hands, feet


# ----------------------------------------------------------------------------- bamboo boat

BOAT_AP = lambda sd: V((sd * 0.45, -0.15, -0.35))
BOAT_LP = lambda sd: V((sd * 0.08, 0.6, -0.3))
BOAT_ANKLES = {"R": V((0.1, -0.36, 0.07)), "L": V((-0.1, -0.36, 0.07))}

# Paddle stroke (right side, character space): phase, T-grip (top hand), shaft direction (grip -> blade).
# The top hand stays forward of her face and out to the stroke side so the shaft never crosses her head;
# between strokes the blade swings high over the bow to the other side (cross-bow, right hand stays on top).
_STROKE_R = [
    (0.00, (0.10, 0.36, 0.98), (0.34, 0.40, -0.85)),    # catch: blade planted ahead
    (0.20, (0.17, 0.20, 0.92), (0.30, -0.42, -0.86)),   # pull back along the hull
    (0.30, (0.15, 0.22, 1.02), (0.33, -0.50, -0.55)),   # exit: blade lifts out behind
    (0.42, (0.02, 0.34, 1.10), (0.02, 0.62, -0.42)),    # recover: blade high over the bow
]


def _stroke(phase):
    """(top, direction) for phase 0..1: right stroke in 0..0.5, mirrored left stroke in 0..0.5 + 0.5."""
    p = phase % 1.0
    sd = 1 if p < 0.5 else -1
    q = p if p < 0.5 else p - 0.5
    keys = _STROKE_R + [(0.5, None, None)]
    for i in range(len(keys) - 1):
        u0, t0, d0 = keys[i]
        u1, t1, d1 = keys[i + 1]
        if u0 <= q <= u1:
            w = _smooth((q - u0) / (u1 - u0))
            if t1 is None:      # wrap to the mirrored catch
                t1, d1 = _STROKE_R[0][1], _STROKE_R[0][2]
                t1, d1 = (-t1[0], t1[1], t1[2]), (-d1[0], d1[1], d1[2])
            a, b = V(t0), V(t1)
            da, db = V(d0).normalized(), V(d1).normalized()
            top, d = a.lerp(b, w), da.lerp(db, w).normalized()
            return V((top.x * sd, top.y, top.z)), V((d.x * sd, d.y, d.z)).normalized(), sd, q
    return V(_STROKE_R[0][1]), V(_STROKE_R[0][2]).normalized(), 1, 0.0


def _kneel(lean, twist, roll=0.0):
    pose = {"root": (-lean * 0.3, roll, twist), "spine": (-lean * 0.5, roll * 0.4, twist * 0.6), "chest": (-lean * 0.2, 0, twist * 0.4),
            "neck": (lean * 0.4, -roll * 0.4, -twist * 0.5), "head": (lean * 0.3, -roll * 0.4, -twist * 0.5),
            "foot.R": (-40, 0, 0), "foot.L": (-40, 0, 0), "hand.R": (0, 0, -6), "hand.L": (10, 0, 12)}
    return pose, (0.0, 0.0, -0.33)


def paddle_at(phase, tilt=0.0):
    """Paddle T-grip position and shaft direction (character space). Tilting blends the stroke into a rudder
    on the tilt side: blade trailing low behind her, top hand pulled in."""
    top, d, sd, q = _stroke(phase)
    r = _smooth(min(1.0, abs(tilt) * 1.25))
    if r > 0:
        s = 1 if tilt > 0 else -1
        rt = V((s * 0.06, 0.2, 0.92))
        rd = V((s * 0.42, -0.62, -0.66)).normalized()
        top = top.lerp(rt, r)
        d = d.lerp(rd, r).normalized()
    return top, d


def boat_pose(phase, tilt=0.0):
    top, d = paddle_at(phase, tilt)
    sd = 1 if (phase % 1.0) < 0.5 else -1
    blade = top + d * PADDLE_BLADE
    r = _smooth(min(1.0, abs(tilt) * 1.25))
    # torso follows the blade: reach forward at the catch, twist with the pull
    reach = max(0.0, blade.y) * 14
    twist = -sd * blade.y * 12 * (1 - r)
    lean = 8 + reach
    pose, root = _kneel(_lerp(lean, 12, r), _lerp(twist, -tilt * 10, r), roll=tilt * 15)
    low = top + d * PADDLE_LOW
    hands = {"R": Target(top, 1.0, BOAT_AP), "L": Target(low, 1.0, BOAT_AP)}
    feet = {k: Target(p, 1.0, BOAT_LP) for k, p in BOAT_ANKLES.items()}
    return pose, root, hands, feet


# ----------------------------------------------------------------------------- paraglider

GLIDE_AP = lambda sd: V((sd * 0.5, 0.05, -0.1))
GLIDE_TOGGLES = {"R": VH.TOGGLES[0] - CHAR_GLIDE + V((0, 0, -0.05)), "L": VH.TOGGLES[1] - CHAR_GLIDE + V((0, 0, -0.05))}


def _seated(lean=4.0, thigh=88.0, shin=-80.0, roll=0.0, sway=0.0):
    pose = {"root": (lean * 0.4, roll, 0), "spine": (lean * 0.6, roll * 0.3, 0), "neck": (-4, -roll * 0.3, 0), "head": (-6, -roll * 0.4, 0),
            "thigh.R": (thigh + sway, 0, 4), "shin.R": (shin - sway, 0, 0), "foot.R": (24, 0, 0),
            "thigh.L": (thigh - sway, 0, -4), "shin.L": (shin + sway, 0, 0), "foot.L": (24, 0, 0),
            "hand.R": (0, 0, -15), "hand.L": (0, 0, 15)}
    return pose, (0.0, 0.0, 0.0)


def glide_pose(phase, tx=0.0, ty=0.0):
    """tx -1..1 bank left/right, ty -1 (dive) .. 1 (climb). Legs swing a little in the loop."""
    s_ = math.sin(2 * math.pi * phase)
    climb, dive = max(0.0, ty), max(0.0, -ty)
    lean = 4 + 8 * climb - 18 * dive
    thigh = 88 + 14 * climb - 46 * dive
    shin = -80 - 35 * climb + 58 * dive
    pose, root = _seated(lean=lean, thigh=thigh, shin=shin, roll=tx * 16, sway=6 * s_ * (1 - abs(tx)) + tx * 8)
    hands = {}
    for sfx, sd in (("R", 1), ("L", -1)):
        inside = max(0.0, tx * sd)          # pull the toggle on the side we bank to
        outside = max(0.0, -tx * sd)
        off = V((0, 0.02 * climb + 0.06 * dive, -0.26 * climb + 0.08 * dive - 0.28 * inside + 0.05 * outside))
        bob = V((0, 0, 0.015 * s_ * sd * (1 - abs(tx))))
        hands[sfx] = Target(GLIDE_TOGGLES[sfx] + off + bob, 1.0, GLIDE_AP)
    return pose, root, hands, None


# ----------------------------------------------------------------------------- clips for the game

def _new(arm, name):
    old = bpy.data.actions.get(name)
    if old:
        bpy.data.actions.remove(old)
    E.new_action(arm, name)


def _bake(arm, rig, name, frames, fn):
    """Key fn(u) -> (pose, root, hands, feet) for u = 0..1 over frames (loop clips end on their first pose)."""
    _new(arm, name)
    for f in range(1, frames + 1):
        u = (f - 1) / (frames - 1) if frames > 1 else 0.0
        pose, root, hands, feet = fn(u)
        world, basis = solve(arm, rig, pose, root, hands, feet)
        rig.key(basis, f)


def cart_clips(arm):
    rig = MO.Rig(arm)
    _bake(arm, rig, "cart_ride", 25, lambda u: cart_pose(u))
    _bake(arm, rig, "cart_duck", 13, lambda u: cart_pose(u, crouch=1.0))
    _bake(arm, rig, "cart_hop", 16, lambda u: cart_pose(u, hop=math.sin(math.pi * u)))
    _bake(arm, rig, "cart_lean_L", 13, lambda u: cart_pose(u, tilt=-1.0))
    _bake(arm, rig, "cart_lean_R", 13, lambda u: cart_pose(u, tilt=1.0))
    _bake(arm, rig, "cart_duck_L", 13, lambda u: cart_pose(u, tilt=-1.0, crouch=1.0))
    _bake(arm, rig, "cart_duck_R", 13, lambda u: cart_pose(u, tilt=1.0, crouch=1.0))
    return [("cart_ride", True), ("cart_duck", True), ("cart_hop", False), ("cart_lean_L", True), ("cart_lean_R", True),
            ("cart_duck_L", True), ("cart_duck_R", True)]


def boat_clips(arm):
    rig = MO.Rig(arm)
    _bake(arm, rig, "row", 37, lambda u: boat_pose(u))
    _bake(arm, rig, "boat_lean_L", 37, lambda u: boat_pose(u, tilt=-1.0))
    _bake(arm, rig, "boat_lean_R", 37, lambda u: boat_pose(u, tilt=1.0))
    return [("row", True), ("boat_lean_L", True), ("boat_lean_R", True)]


def glide_clips(arm):
    rig = MO.Rig(arm)
    out = []
    for nm, tx, ty in (("glide", 0, 0), ("glide_up", 0, 1), ("glide_down", 0, -1), ("glide_lean_L", -1, 0),
                       ("glide_lean_R", 1, 0)):
        _bake(arm, rig, nm, 41, lambda u, tx=tx, ty=ty: glide_pose(u, tx, ty))
        out.append((nm, True))
    return out


def vehicle_clips(arm):
    import ride_transitions as RT
    return cart_clips(arm) + boat_clips(arm) + glide_clips(arm) + RT.transition_clips(arm)


# ----------------------------------------------------------------------------- design sheet

def place_paddle(arm, paddle_ob, top=None, d=None):
    """Paddle T-grip at `top` (character space), shaft along d; default: from the posed right hand toward the left."""
    if top is None:
        pr = arm.pose.bones["hand.R"]
        pl = arm.pose.bones["hand.L"]
        top = arm.matrix_world @ pr.tail
        low = arm.matrix_world @ (pl.head.lerp(pl.tail, 0.5))
        d = (low - top).normalized()
        paddle_ob.matrix_world = Matrix.Translation(top) @ (-d).to_track_quat('Z', 'Y').to_matrix().to_4x4()
        return
    w = arm.matrix_world
    tw = w @ V(top)
    dw = (w.to_3x3() @ V(d)).normalized()
    paddle_ob.matrix_world = Matrix.Translation(tw) @ (-dw).to_track_quat('Z', 'Y').to_matrix().to_4x4()


def design_vehicle_poses():
    import studio
    import pongo_g as PG
    E.reset()
    studio.stage(res=(480, 560))
    B, arm, objs = PG.build_pongo_g()
    for o in objs:
        if o.type == 'MESH' and "face" not in o.name and "detail" not in o.name:
            E.add_outline(o, 0.0022)
    PG.girl_clips(arm)
    vehicle_clips(arm)
    cart = VH.ore_cart()
    boat = VH.boat()
    pad = VH.paddle()
    gl = VH.glider()
    for o in (cart, boat, pad, gl):
        E.add_outline(o, 0.012)
    sc = bpy.context.scene
    shots = [("cart_ride", 1, "cart"), ("cart_hop", 8, "cart"), ("cart_duck", 1, "cart"), ("cart_lean_L", 1, "cart"),
             ("row", 1, "boat"), ("row", 8, "boat"), ("row", 19, "boat"), ("boat_lean_R", 1, "boat"),
             ("glide", 1, "glider"), ("glide_up", 1, "glider"), ("glide_down", 1, "glider"), ("glide_lean_R", 1, "glider")]
    for (act, f, veh) in shots:
        arm.animation_data.action = bpy.data.actions[act]
        sc.frame_set(f)
        arm.location = (0, 0, 0)
        for o, k, off in ((cart, "cart", CHAR_CART), (boat, "boat", CHAR_BOAT), (gl, "glider", CHAR_GLIDE)):
            o.hide_render = (k != veh)
            o.location = -off
        pad.hide_render = veh != "boat"
        if veh == "boat":
            n = {"row": 37, "boat_lean_L": 37, "boat_lean_R": 37}[act]
            tilt = {"row": 0, "boat_lean_L": -1, "boat_lean_R": 1}[act]
            top, d = paddle_at((f - 1) / (n - 1), tilt)
            place_paddle(arm, pad, top, d)
        tz = {"cart": 0.6, "boat": 0.45, "glider": 0.9}[veh]
        dist = {"cart": 3.6, "boat": 3.8, "glider": 5.6}[veh]
        studio.shoot("vp_%s_%02d" % (act, f), target=(0, 0.1, tz), dist=dist, yaw=215, pitch=12, lens=50)
