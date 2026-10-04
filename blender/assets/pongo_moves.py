"""
Pongo's vehicle clips, authored with IK so her hands stay on the vehicle grips and her feet/knees stay planted:

  cart_ride (loop), cart_hop, cart_duck, cart_lean_L, cart_lean_R     hands on the front rim, feet on the floor
  row (loop: right stroke, cross-bow left stroke), boat_lean_L/R      right hand on the T-grip, left hand on the shaft
  glide (loop), glide_up, glide_down, glide_lean_L, glide_lean_R      hands on the brake toggles, seated in the harness

The character's origin sits at the vehicle mount point (CHAR_*): the game draws the vehicle at
character_origin - CHAR_* (and rolls both together when tilting); the paddle is drawn from hand.R toward hand.L.
"""
import math
import bpy
from mathutils import Vector, Matrix
import erlib as E
import characters as CH
import motion as MO
import vehicles as VH

V = Vector
CHAR_CART = V((0.0, 0.05, VH.FLOOR_CART))
CHAR_BOAT = V((0.0, -0.15, 0.06))
CHAR_GLIDE = V((0.0, 0.0, -0.68))
ARMS = {"R": ("upper_arm.R", "forearm.R"), "L": ("upper_arm.L", "forearm.L")}
LEGS = {"R": ("thigh.R", "shin.R"), "L": ("thigh.L", "shin.L")}


def _new(arm, name):
    old = bpy.data.actions.get(name)
    if old:
        bpy.data.actions.remove(old)
    E.new_action(arm, name)


def key_ik(arm, rig, frame, pose, root, hands=None, feet=None, arm_pole=None, leg_pole=None):
    """Key one frame: body from the Euler pose dict, arms/legs solved onto targets (character space)."""
    q = MO.euler_pose(arm, pose, root)
    world, basis = rig.fk(q)
    for sfx, sd in (("R", 1), ("L", -1)):
        if hands and sfx in hands:
            up, lo = ARMS[sfx]
            sh = world[rig.index[up]].to_translation()
            pole = sh + (arm_pole(sd) if arm_pole else V((sd * 0.4, -0.3, -0.35)))
            world, basis = rig.ik2(world, basis, up, lo, hands[sfx], pole)
        if feet and sfx in feet:
            up, lo = LEGS[sfx]
            hp = world[rig.index[up]].to_translation()
            pole = hp + (leg_pole(sd) if leg_pole else V((sd * 0.05, 0.5, -0.15)))
            world, basis = rig.ik2(world, basis, up, lo, feet[sfx], pole)
    rig.key(basis, frame)


# ----------------------------------------------------------------------------- ore cart

def _cart_body(lean, hip, roll=0.0, shift=0.0, head=14.0, twist=0.0):
    pose = {"root": (-lean * 0.4, roll, twist), "spine": (-lean * 0.45, roll * 0.3, 0), "chest": (-lean * 0.15, roll * 0.2, 0),
            "neck": (lean * 0.38, -roll * 0.3, 0), "head": (head, -roll * 0.5, 0),
            "foot.R": (8, 0, 0), "foot.L": (8, 0, 0), "hand.R": (0, 0, -10), "hand.L": (0, 0, 10)}
    return pose, (shift, 0.0, hip)


def cart_clips(arm):
    rig = MO.Rig(arm)
    grips = {"R": VH.GRIP_CART[0] - CHAR_CART + V((-0.03, -0.06, 0.0)), "L": VH.GRIP_CART[1] - CHAR_CART + V((0.03, -0.06, 0.0))}
    feet = {"R": V((0.11, 0.0, 0.075)), "L": V((-0.11, -0.04, 0.075))}
    ap = lambda sd: V((sd * 0.35, -0.25, -0.45))
    lp = lambda sd: V((sd * 0.12, 0.6, -0.1))
    _new(arm, "cart_ride")
    for f, hip, hd in ((1, -0.2, 14), (7, -0.235, 12), (13, -0.2, 14), (19, -0.235, 12), (25, -0.2, 14)):
        pose, root = _cart_body(34, hip, head=hd)
        key_ik(arm, rig, f, pose, root, grips, feet, ap, lp)
    _new(arm, "cart_hop")
    for f, lean, hip in ((1, 34, -0.2), (3, 42, -0.33), (7, 24, -0.07), (11, 30, -0.16), (13, 44, -0.32), (16, 34, -0.2)):
        pose, root = _cart_body(lean, hip)
        key_ik(arm, rig, f, pose, root, grips, feet, ap, lp)
    _new(arm, "cart_duck")
    for f, lean, hip, hd in ((1, 34, -0.2, 14), (5, 74, -0.45, 36), (15, 76, -0.46, 38), (20, 34, -0.2, 14)):
        pose, root = _cart_body(lean, hip, head=hd)
        key_ik(arm, rig, f, pose, root, grips, feet, ap, lp)
    for nm, sd in (("cart_lean_L", -1), ("cart_lean_R", 1)):
        _new(arm, nm)
        for f in (1, 9):
            pose, root = _cart_body(36, -0.24, roll=sd * 17, shift=sd * 0.09, twist=-sd * 6)
            ft = {"R": feet["R"] + V((sd * 0.03, 0, 0)), "L": feet["L"] + V((sd * 0.03, 0, 0))}
            key_ik(arm, rig, f, pose, root, grips, ft, ap, lp)
    return [("cart_ride", True), ("cart_hop", False), ("cart_duck", False), ("cart_lean_L", True), ("cart_lean_R", True)]


# ----------------------------------------------------------------------------- bamboo boat

def _kneel(lean, twist, roll=0.0):
    pose = {"root": (-lean * 0.3, roll, twist), "spine": (-lean * 0.5, roll * 0.4, twist * 0.6), "chest": (-lean * 0.2, 0, twist * 0.4),
            "neck": (lean * 0.4, -roll * 0.4, -twist * 0.5), "head": (lean * 0.3, -roll * 0.4, -twist * 0.5),
            "foot.R": (-40, 0, 0), "foot.L": (-40, 0, 0), "hand.R": (0, 0, -6), "hand.L": (10, 0, 12)}
    return pose, (0.0, 0.0, -0.33)


ROW_KEYS = [
    # frame, top (right) hand, lower (left) hand, lean, twist
    (1, (0.08, 0.32, 1.0), (0.3, 0.5, 0.45), 22, -14),
    (9, (0.15, 0.04, 0.95), (0.34, -0.06, 0.43), 10, 4),
    (13, (0.1, 0.0, 1.02), (0.45, 0.02, 0.8), 4, 8),
    (18, (-0.08, 0.32, 1.0), (-0.3, 0.5, 0.45), 22, 14),
    (27, (-0.15, 0.04, 0.95), (-0.34, -0.06, 0.43), 10, -4),
    (31, (-0.1, 0.0, 1.02), (-0.45, 0.02, 0.8), 4, -8),
    (37, (0.08, 0.32, 1.0), (0.3, 0.5, 0.45), 22, -14),
]


def boat_clips(arm):
    rig = MO.Rig(arm)
    ankles = {"R": V((0.1, -0.36, 0.07)), "L": V((-0.1, -0.36, 0.07))}
    ap = lambda sd: V((sd * 0.45, -0.15, -0.35))
    lp = lambda sd: V((sd * 0.08, 0.6, -0.3))
    _new(arm, "row")
    for (f, top, low, lean, twist) in ROW_KEYS:
        pose, root = _kneel(lean, twist)
        key_ik(arm, rig, f, pose, root, {"R": V(top), "L": V(low)}, ankles, ap, lp)
    for nm, sd in (("boat_lean_L", -1), ("boat_lean_R", 1)):
        _new(arm, nm)
        for f in (1, 9):
            pose, root = _kneel(12, -sd * 10, roll=sd * 15)
            top = V((sd * 0.02, 0.12, 0.88))
            low = V((sd * 0.46, 0.08, 0.5))
            key_ik(arm, rig, f, pose, root, {"R": top, "L": low}, ankles, ap, lp)
    return [("row", True), ("boat_lean_L", True), ("boat_lean_R", True)]


# ----------------------------------------------------------------------------- paraglider

def _seated(lean=4.0, thigh=80.0, shin=-75.0, roll=0.0, sway=0.0):
    pose = {"root": (lean * 0.4, roll, 0), "spine": (lean * 0.6, roll * 0.3, 0), "neck": (-4, -roll * 0.3, 0), "head": (-6, -roll * 0.4, 0),
            "thigh.R": (thigh + sway, 0, 4), "shin.R": (shin - sway, 0, 0), "foot.R": (24, 0, 0),
            "thigh.L": (thigh - sway, 0, -4), "shin.L": (shin + sway, 0, 0), "foot.L": (24, 0, 0),
            "hand.R": (0, 0, -15), "hand.L": (0, 0, 15)}
    return pose, (0.0, 0.0, 0.0)


def glide_clips(arm):
    rig = MO.Rig(arm)
    tg = {"R": VH.TOGGLES[0] - CHAR_GLIDE + V((0, 0, -0.05)), "L": VH.TOGGLES[1] - CHAR_GLIDE + V((0, 0, -0.05))}
    ap = lambda sd: V((sd * 0.5, 0.05, -0.1))
    _new(arm, "glide")
    for f, s_ in ((1, 0.0), (11, 1.0), (21, 0.0), (31, -1.0), (41, 0.0)):
        pose, root = _seated(sway=6 * s_)
        bob = V((0, 0, 0.015 * s_))
        key_ik(arm, rig, f, pose, root, {"R": tg["R"] + bob, "L": tg["L"] - bob}, None, ap)
    _new(arm, "glide_up")
    for f in (1, 9):
        pose, root = _seated(lean=12, thigh=100, shin=-115)
        key_ik(arm, rig, f, pose, root, {"R": tg["R"] + V((0, 0.02, -0.26)), "L": tg["L"] + V((0, 0.02, -0.26))}, None, ap)
    _new(arm, "glide_down")
    for f in (1, 9):
        pose, root = _seated(lean=-14, thigh=42, shin=-22)
        key_ik(arm, rig, f, pose, root, {"R": tg["R"] + V((0, 0.06, 0.08)), "L": tg["L"] + V((0, 0.06, 0.08))}, None, ap)
    for nm, sd in (("glide_lean_L", -1), ("glide_lean_R", 1)):
        _new(arm, nm)
        for f in (1, 9):
            pose, root = _seated(roll=sd * 16, sway=sd * 8)
            down, up = ("L", "R") if sd < 0 else ("R", "L")
            key_ik(arm, rig, f, pose, root, {down: tg[down] + V((0, 0.0, -0.28)), up: tg[up] + V((0, 0, 0.05))}, None, ap)
    return [("glide", True), ("glide_up", True), ("glide_down", True), ("glide_lean_L", True), ("glide_lean_R", True)]


def vehicle_clips(arm):
    return cart_clips(arm) + boat_clips(arm) + glide_clips(arm)


# ----------------------------------------------------------------------------- design sheet

def place_paddle(arm, paddle_ob, origin=V((0, 0, 0))):
    """Paddle grip in the right hand, shaft aimed through the left hand."""
    pr = arm.pose.bones["hand.R"]
    pl = arm.pose.bones["hand.L"]
    top = arm.matrix_world @ pr.tail
    low = arm.matrix_world @ (pl.head.lerp(pl.tail, 0.5))
    d = (low - top).normalized()
    paddle_ob.matrix_world = Matrix.Translation(top) @ (-d).to_track_quat('Z', 'Y').to_matrix().to_4x4()


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
    shots = [("cart_ride", 1, "cart"), ("cart_hop", 3, "cart"), ("cart_duck", 8, "cart"), ("cart_lean_L", 1, "cart"),
             ("row", 1, "boat"), ("row", 9, "boat"), ("row", 18, "boat"), ("boat_lean_R", 1, "boat"),
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
            bpy.context.view_layer.update()
            place_paddle(arm, pad)
        if veh == "glider":
            arm.location = (0, 0, 0)
            gl.location = -CHAR_GLIDE
        tz = {"cart": 0.6, "boat": 0.45, "glider": 0.9}[veh]
        dist = {"cart": 3.6, "boat": 3.8, "glider": 5.6}[veh]
        studio.shoot("vp_%s_%02d" % (act, f), target=(0, 0.1, tz), dist=dist, yaw=215, pitch=12, lens=50)
