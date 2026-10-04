"""
Ride showcase: Pongo on her vehicles, driven by the same pose functions and IK as the game.

  closeups       stills of each vehicle with Pongo on it from four angles (front 3/4, side, back 3/4, face close-up)
  ride_loops     short studio clips: cart (tilt + crouch), boat (rowing + tilt), glider (tilt in every direction)
  transitions    the four boarding / vehicle-change set pieces

Usage:  blender -b -P blender/run.py -- ride_showcase closeups        (PONGO_QUICK=1 for fast previews)
Output: renders/ride/*.png, renders/anim/<name>.mp4/.gif/_strip.png
"""
import math, os
import bpy
from mathutils import Vector, Matrix, Quaternion
import erlib as E
import studio
import pongo_g as PG
import motion as MO
import vehicles as VH
import pongo_moves as PM
import ride_transitions as RT
import showcase as SC

V = Vector
FPS = 30
OUT = os.path.join(E.OUT_RENDERS, "ride")


def _pongo():
    B, arm, objs = PG.build_pongo_g()
    for o in objs:
        if o.type == 'MESH' and "face" not in o.name and "detail" not in o.name:
            E.add_outline(o, 0.0022)
    PG.girl_clips(arm)
    return arm


def _vehicles():
    v = {"cart": VH.ore_cart(), "boat": VH.boat(), "paddle": VH.paddle(), "glider": VH.glider()}
    for o in v.values():
        E.add_outline(o, 0.012)
    return v


MOUNT = {"cart": PM.CHAR_CART, "boat": PM.CHAR_BOAT, "glider": PM.CHAR_GLIDE}


def _pose_fn(veh):
    return {"cart": lambda ph, tx, ty, c: PM.cart_pose(ph, tilt=tx, crouch=c),
            "boat": lambda ph, tx, ty, c: PM.boat_pose(ph, tilt=tx),
            "glider": lambda ph, tx, ty, c: PM.glide_pose(ph, tx, ty)}[veh]


def _vehicle_tilt(veh, tx, ty):
    """How the vehicle itself rolls/pitches under her (degrees): carts barely, canoes rock, gliders bank."""
    if veh == "cart":
        return tx * 5.0, 0.0
    if veh == "boat":
        return tx * 9.0, 0.0
    return tx * 24.0, ty * 10.0


def _place(arm, objs, veh, base, roll=0.0, pitch=0.0, frame=None, paddle=None):
    """Character origin at base (world); the vehicle hangs from it at -mount; both roll about the mount.
    Gliders pivot about the canopy (they swing under the wing), the others about the mount."""
    R = Matrix.Rotation(math.radians(roll), 4, 'Y') @ Matrix.Rotation(math.radians(pitch), 4, 'X')
    if veh == "glider":
        piv = V((0, 0, 2.4)) - MOUNT[veh]           # canopy centre in character space
        M = Matrix.Translation(base) @ Matrix.Translation(piv) @ R @ Matrix.Translation(-piv)
    else:
        M = Matrix.Translation(base) @ R
    arm.matrix_world = M @ Matrix.Diagonal((PM.SCALE, PM.SCALE, PM.SCALE, 1.0))
    for k, o in objs.items():
        if k == "paddle":
            continue
        o.hide_render = (k != veh)
        o.matrix_world = M @ Matrix.Translation(-MOUNT[k])
    objs["paddle"].hide_render = paddle is None
    if paddle is not None:
        top, d = paddle
        PM.place_paddle(arm, objs["paddle"], top, d)
    if frame is not None:
        arm.keyframe_insert("location", frame=frame)
        arm.keyframe_insert("rotation_euler", frame=frame)
        for o in objs.values():
            o.keyframe_insert("location", frame=frame)
            o.keyframe_insert("rotation_euler", frame=frame)
            o.keyframe_insert("hide_render", frame=frame)
            o.keyframe_insert("scale", frame=frame)


# ----------------------------------------------------------------------------- stills

CLOSE = {
    "cart": dict(phase=0.1, tx=0.0, ty=0.0, c=0.0, tz=0.75, dist=3.3, face=(0, 0.0, 1.35)),
    "cart_duck": dict(phase=0.1, tx=0.0, ty=0.0, c=1.0, tz=0.6, dist=3.3, face=(0, 0.1, 0.95)),
    "boat": dict(phase=0.08, tx=0.0, ty=0.0, c=0.0, tz=0.5, dist=3.6, face=(0, 0.0, 0.95)),
    "glider": dict(phase=0.0, tx=0.35, ty=0.0, c=0.0, tz=1.4, dist=6.2, face=(0, 0.0, 0.85)),
}
VIEWS = [("front34", 205, 12, 1.0), ("side", 270, 8, 1.0), ("back34", 330, 16, 1.0)]


def closeups():
    E.reset()
    studio.stage(res=(640, 720))
    arm = _pongo()
    objs = _vehicles()
    rig = MO.Rig(arm)
    os.makedirs(OUT, exist_ok=True)
    arm.rotation_mode = 'XYZ'
    for name, cfg in CLOSE.items():
        veh = name.split("_")[0]
        pose, root, hands, feet = _pose_fn(veh)(cfg["phase"], cfg["tx"], cfg["ty"], cfg["c"])
        PM._new(arm, "still_" + name)
        world, basis = PM.solve(arm, rig, pose, root, hands, feet)
        rig.key(basis, 1)
        bpy.context.scene.frame_set(1)
        roll, pitch = _vehicle_tilt(veh, cfg["tx"], cfg["ty"])
        pad = PM.paddle_at(cfg["phase"], cfg["tx"]) if veh == "boat" else None
        _place(arm, objs, veh, V((0, 0, 0)), roll, pitch, paddle=pad)
        bpy.context.view_layer.update()
        for vn, yaw, pitch_c, _ in VIEWS:
            studio.shoot("../ride/close_%s_%s" % (name, vn), target=(0, 0.1, cfg["tz"]), dist=cfg["dist"], yaw=yaw,
                         pitch=pitch_c, lens=50)
        # face close-up: from the front, slightly to her right
        hz = arm.matrix_world @ rig.point(world, "head")
        fy, fp = (160, 40) if name == "cart_duck" else (200, 6)
        studio.shoot("../ride/close_%s_face" % name, target=tuple(hz + V((0, 0.02, 0.06))), dist=1.15, yaw=fy, pitch=fp,
                     lens=60)


# ----------------------------------------------------------------------------- clips

def _bake(arm, objs, frames, sample, cam_fn, name):
    """sample(fi, t) -> (veh, quat_pose, hands, feet, base, roll, pitch, paddle, vel) per frame; keys everything,
    bakes the spring chains, keys the camera from cam_fn(t, base) -> (loc, target, lens)."""
    rig = MO.Rig(arm)
    act = bpy.data.actions.new(name)
    arm.animation_data_create()
    arm.animation_data.action = act
    arm.rotation_mode = 'XYZ'
    cam_data = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_data)
    E.link(cam)
    bpy.context.scene.camera = cam
    for fi in range(frames):
        t = fi / FPS
        veh, q, hands, feet, base, roll, pitch, pad, vel, extra = sample(fi, t)
        world, basis = PM.solve_q(rig, q, hands, feet)
        world, basis = rig.springs(world, basis, 1.0 / FPS, vel)
        rig.key(basis, fi + 1)
        _place(arm, objs, veh, base, roll, pitch, frame=None, paddle=None)
        for k, o in objs.items():
            o.hide_render = (k != veh) if k != "paddle" else pad is None
        if extra:
            extra(fi + 1, t)
        if pad is not None:
            top, d = pad
            PM.place_paddle(arm, objs["paddle"], top, d)
        arm.keyframe_insert("location", frame=fi + 1)
        arm.keyframe_insert("rotation_euler", frame=fi + 1)
        for o in objs.values():
            o.rotation_mode = 'XYZ'
            o.keyframe_insert("location", frame=fi + 1)
            o.keyframe_insert("rotation_euler", frame=fi + 1)
            o.keyframe_insert("scale", frame=fi + 1)
            o.keyframe_insert("hide_render", frame=fi + 1)
        loc, tgt, lens = cam_fn(t, base)
        cam.location = loc
        cam.rotation_euler = (V(tgt) - V(loc)).to_track_quat('-Z', 'Y').to_euler()
        cam_data.lens = lens
        cam.keyframe_insert("location", frame=fi + 1)
        cam.keyframe_insert("rotation_euler", frame=fi + 1)
        cam_data.keyframe_insert("lens", frame=fi + 1)
    for o in [arm, cam] + list(objs.values()):
        if o.animation_data and o.animation_data.action:
            for fc in o.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = 'CONSTANT' if fc.data_path == "hide_render" else 'LINEAR'


def _orbit(yaw0, yaw1, dur, dist, tz, pitch=12, lens=45):
    def f(t, base):
        y = math.radians(yaw0 + (yaw1 - yaw0) * min(1.0, t / dur))
        p = math.radians(pitch)
        tg = V(base) + V((0, 0, tz))
        loc = tg + V((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p))) * dist
        return loc, tg, lens
    return f


def _tilt_script(t, keys):
    """Piecewise-smooth input curve: keys [(t, value)]."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            return v0 + (v1 - v0) * RT._s((t - t0) / (t1 - t0))
    return keys[-1][1]


def _render(name, frames, strip_times):
    d = SC.render_frames(name, frames)
    SC.encode(name, d)
    SC.filmstrip(name, d, [int(round(t * FPS)) + 1 for t in strip_times], cols=len(strip_times) if len(strip_times) <= 5 else 5)


def ride_loop(veh="cart"):
    E.reset()
    studio.stage(res=(720, 720))
    arm = _pongo()
    objs = _vehicles()
    rate = {"cart": 1 / 0.8, "boat": 1 / 1.25, "glider": 1 / 1.4}[veh]
    dur = 4.0
    frames = int(dur * FPS)
    tx_keys = {"cart": [(0, 0), (0.5, 0), (0.8, -1), (1.3, -1), (1.6, 0), (2.0, 1), (2.4, 1), (2.7, 0)],
               "boat": [(0, 0), (0.8, 0), (1.2, -1), (1.8, -1), (2.2, 1), (2.8, 1), (3.2, 0)],
               "glider": [(0, 0), (0.4, -1), (1.0, -1), (1.4, 0), (1.8, 1), (2.4, 1), (2.8, 0)]}[veh]
    ty_keys = {"glider": [(0, 0), (2.8, 0), (3.0, 1), (3.4, 1), (3.6, -1), (3.95, -1)]}.get(veh, [(0, 0)])
    c_keys = {"cart": [(0, 0), (2.8, 0), (3.0, 1), (3.6, 1), (3.85, 0)]}.get(veh, [(0, 0)])
    fn = _pose_fn(veh)

    def sample(fi, t):
        tx, ty, c = _tilt_script(t, tx_keys), _tilt_script(t, ty_keys), _tilt_script(t, c_keys)
        ph = (t * rate) % 1.0
        pose, root, hands, feet = fn(ph, tx, ty, c)
        q = MO.euler_pose(arm, pose, root)
        roll, pitch = _vehicle_tilt(veh, tx, ty)
        base = V((0.6 * math.sin(t * 0.0), 0, 0))
        pad = PM.paddle_at(ph, tx) if veh == "boat" else None
        vel = V((tx * 2.0, 6.0, 0))
        return veh, q, hands, feet, base, roll, pitch, pad, vel, None

    tz = {"cart": 0.7, "boat": 0.45, "glider": 1.2}[veh]
    dist = {"cart": 3.6, "boat": 4.0, "glider": 6.5}[veh]
    _bake(arm, objs, frames, sample, _orbit(200, 330, dur, dist, tz), "ride_" + veh)
    _render("ride_" + veh, frames, (0.3, 1.0, 2.2, 3.2, 3.7))


def ride_loops():
    for v in ("cart", "boat", "glider"):
        ride_loop(v)


# ----------------------------------------------------------------------------- transitions

TRANS = {"board_cart": ("run", "cart"), "cart_to_boat": ("cart", "boat"), "boat_to_glider": ("boat", "glider"),
         "glide_land": ("glider", "run")}


def transition(name="board_cart"):
    E.reset()
    studio.stage(res=(720, 720))
    arm = _pongo()
    objs = _vehicles()
    # a second copy for the vehicle she leaves (A) when both are on screen
    a_veh, b_veh = TRANS[name]
    objA = None
    if a_veh not in ("run",) and a_veh != b_veh:
        objA = objs[a_veh]
    samplers = {n: MO.ClipSampler(n) for n in ("run", "jump", "fall", "land")}
    dur = RT.SPEC[name][0]
    pre, post = 0.5, 0.7
    frames = int((pre + dur + post) * FPS)
    speed = 0.0                                     # studio: the co-moving frame stays put

    def sample(fi, t):
        u = max(0.0, min(1.0, (t - pre) / dur))
        q, hands, feet, ex = RT.pose_at(arm, samplers, name, u, phase=0.0)
        if t > pre + dur and b_veh != "run":
            # settle into the ride loop
            ph = ((t - pre - dur) / {"cart": 0.8, "boat": 1.25, "glider": 1.4}[b_veh]) % 1.0
            ph = 0.0 if b_veh == "boat" else ph
            pose, root, hands, feet = _pose_fn(b_veh)(ph, 0, 0, 0)
            q = MO.euler_pose(arm, pose, root)
        if t < pre and a_veh != "run":
            pose, root, hh, ff = _pose_fn(a_veh)(0.0, 0, 0, 0)
            q = RT._root_offset(arm, MO.euler_pose(arm, pose, root), RT.SPEC[name][1])
            hands = {k: PM.Target(v.pos + RT.SPEC[name][1], 1.0, v.pole) for k, v in hh.items()}
            feet = {k: PM.Target(v.pos + RT.SPEC[name][1], 1.0, v.pole) for k, v in ff.items()} if ff else None
        if t < pre and a_veh == "run":
            q = RT._root_offset(arm, samplers["run"].pose(t * 1.35, True), RT.SPEC[name][1])
            hands = feet = None
        pad = ex.get("paddle")
        if b_veh == "boat" and t > pre + dur:
            pad = PM.paddle_at(0.0)
        if a_veh == "boat" and t < pre:
            pad = PM.paddle_at(0.0)
        veh = b_veh if b_veh != "run" else a_veh
        vel = V((0, 4.0, 0))
        tr = RT.prop_track(name, u)

        def extra(frame, t_):
            # previous vehicle on its own track; destination vehicle scale (glider burst)
            if tr.get("A") and objA is not None:
                off, pitch_a, sc = tr["A"]
                objA.hide_render = sc < 0.01
                objA.matrix_world = Matrix.Translation(off) @ Matrix.Rotation(math.radians(pitch_a), 4, 'X') @ \
                    Matrix.Diagonal((sc, sc, sc, 1))
            if b_veh != "run" and tr.get("B"):
                off, pitch_b, sc = tr["B"]
                ob = objs[b_veh]
                ob.hide_render = False
                ob.matrix_world = Matrix.Translation(off - MOUNT[b_veh]) @ Matrix.Diagonal((sc, sc, sc, 1)) if b_veh != "glider" else \
                    Matrix.Translation(-MOUNT[b_veh]) @ Matrix.Translation(V((0, 0, 0.9))) @ \
                    Matrix.Diagonal((sc, sc, sc, 1)) @ Matrix.Translation(V((0, 0, -0.9)))
            if name == "glide_land" and t_ <= pre:
                ob = objs["glider"]
                ob.hide_render = False
                ob.matrix_world = Matrix.Translation(RT.SPEC[name][1] - MOUNT["glider"])

        return (veh if veh != "run" else "cart"), q, hands, feet, V((0, 0, 0)), 0.0, 0.0, pad, vel, extra

    def place_hook(veh):
        pass

    # stand-in ground for the run-up / landing: the studio floor is at z=0 for 'run' segments
    def cam(t, base):
        yaw = 250 + 40 * min(1.0, t / (pre + dur + post))
        tz = {"board_cart": 0.6, "cart_to_boat": 0.9, "boat_to_glider": 0.4, "glide_land": 0.9}[name]
        dist = {"board_cart": 5.0, "cart_to_boat": 6.5, "boat_to_glider": 6.8, "glide_land": 5.8}[name]
        y = math.radians(yaw)
        tg = V((0, -0.9, tz))
        loc = tg + V((math.sin(y), -math.cos(y), 0.22)) * dist
        return loc, tg, 40

    _bake(arm, objs, frames, sample, cam, "tr_" + name)
    # floor: the studio floor sits at the destination's ground level
    fl = bpy.data.objects.get("floor")
    if fl:
        fl.location.z = {"board_cart": -PM.CHAR_CART.z, "cart_to_boat": -PM.CHAR_BOAT.z - 0.15,
                         "boat_to_glider": RT.SPEC["boat_to_glider"][1].z - 0.4, "glide_land": 0.0}[name]
    times = [pre + dur * u for u in (0.0, 0.25, 0.45, 0.65, 0.85)] + [pre + dur + 0.3]
    _render("tr_" + name, frames, times[:5])


def transitions():
    for n in RT.SPEC:
        transition(n)
