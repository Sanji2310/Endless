"""
PONGO showcase renders: Pongo's actions in the zones with a game-like camera, spring physics and effects.

  run_showcase   Sakura Line: lane switch, jump over a barricade, slide under a hazard gantry, coin pickups,
                 dust puffs, falling sakura petals; the camera swings from the game view to the side for the
                 jump and the slide and back.

Usage:  blender -b -P blender/run.py -- showcase run_showcase        (PONGO_QUICK=1 for a fast preview)
Output: renders/anim/<name>/####.png  ->  renders/anim/<name>.mp4, <name>.gif, <name>_strip.png
"""
import math, os, random, subprocess
import bpy
from mathutils import Vector, Matrix, Quaternion
import erlib as E
import studio
import pongo_g as PG
import motion as MO
import obstacles as OB
import pickups as PK
import buildings as BL

V = Vector
FPS = 30
OUT = os.path.join(E.OUT_RENDERS, "anim")


# ----------------------------------------------------------------------------- effects

def fx_mats():
    E.mat("fx_dust", 0xF3E7D6, rim=0.1, soft=0.3, emis=0.3, outline=0.0, flags=E.F_NOCAST, shadow=0xD9CABB)
    E.mat("fx_spark", 0xFFF0A8, emis=1.4, rim=0.0, soft=0.1, outline=0.0, flags=E.F_NOCAST)
    E.mat("fx_petal", 0xF9B8CC, rim=0.2, soft=0.2, emis=0.1, outline=0.0, flags=E.F_NOCAST | E.F_DOUBLE, shadow=0xE48CAA)


class FX:
    """Keyframed effect objects: dust puffs, pickup sparkles, falling petals."""

    def __init__(self, seed=1):
        self.n = 0
        self.rnd = random.Random(seed)
        self._puff_me = None
        self._spark_me = None

    def _puff_mesh(self):
        if self._puff_me is None:
            m = E.Mesher("fx_puff_src").mat("fx_dust")
            m.ico((0, 0, 0), 1.0, 2)
            ob = m.obj(smooth_angle=180)
            self._puff_me = ob.data
            bpy.data.objects.remove(ob)
        return self._puff_me

    def _new(self, me, name):
        ob = bpy.data.objects.new("%s_%d" % (name, self.n), me)
        self.n += 1
        E.link(ob)
        return ob

    def puff(self, pos, frame, size=0.2, drift=V((0, -0.5, 0.3)), life=14, count=3, spread=0.16):
        for k in range(count):
            ob = self._new(self._puff_mesh(), "fx_puff")
            off = V((self.rnd.uniform(-spread, spread), self.rnd.uniform(-spread, spread) * 0.8, self.rnd.uniform(0, 0.06)))
            p0 = V(pos) + off
            s0 = size * self.rnd.uniform(0.6, 1.0)
            d = drift + V((off.x * 1.5, 0, 0))
            for (df, sc, dp) in ((-1, 0.0, 0.0), (0, 0.3, 0.0), (life * 0.35, 1.0, 0.45), (life, 0.0, 1.0)):
                ob.scale = (s0 * sc,) * 3
                ob.location = p0 + d * dp
                ob.keyframe_insert("scale", frame=frame + df)
                ob.keyframe_insert("location", frame=frame + df)

    def spark(self, pos, frame, size=0.35):
        if self._spark_me is None:
            m = E.Mesher("fx_spark_src").mat("fx_spark")
            for a in (0, 45, 90, 135):
                m.push(Matrix.Rotation(math.radians(a), 4, 'Y'))
                m.box((0, 0, 0), (0.06, 0.02, 1.0), smooth=False)
                m.pop()
            ob = m.obj(smooth_angle=0)
            self._spark_me = ob.data
            bpy.data.objects.remove(ob)
        ob = self._new(self._spark_me, "fx_spark")
        ob.location = pos
        for (df, sc, rot) in ((-1, 0.0, 0.0), (0, 0.2, 0.0), (3, 1.0, 20.0), (8, 0.0, 45.0)):
            ob.scale = (size * sc,) * 3
            ob.rotation_euler = (0, math.radians(rot), 0)
            ob.keyframe_insert("scale", frame=frame + df)
            ob.keyframe_insert("rotation_euler", frame=frame + df)

    def petals(self, n, xr, yr, zr, frames):
        m = E.Mesher("fx_petal_src").mat("fx_petal")
        m.poly([(-0.03, 0, -0.02), (0.0, 0, -0.026), (0.03, 0, -0.012), (0.026, 0, 0.018), (-0.01, 0, 0.024), (-0.034, 0, 0.004)])
        src = m.obj(smooth_angle=0)
        me = src.data
        bpy.data.objects.remove(src)
        for i in range(n):
            ob = self._new(me, "fx_petal")
            x0, y0, z0 = self.rnd.uniform(*xr), self.rnd.uniform(*yr), self.rnd.uniform(*zr)
            ph, sw = self.rnd.uniform(0, 6.28), self.rnd.uniform(0.2, 0.5)
            vz, vy = self.rnd.uniform(0.35, 0.7), self.rnd.uniform(-0.6, -0.2)
            sp = (self.rnd.uniform(-4, 4), self.rnd.uniform(-4, 4), self.rnd.uniform(-3, 3))
            for f in range(frames[0], frames[1] + 1, 5):
                t = (f - frames[0]) / FPS
                z = z0 - vz * t
                while z < -0.05:
                    z += zr[1] - zr[0]
                ob.location = (x0 + sw * math.sin(t * 2.2 + ph), y0 + vy * t, z)
                ob.rotation_euler = (sp[0] * t + ph, sp[1] * t, sp[2] * t)
                ob.keyframe_insert("location", frame=f)
                ob.keyframe_insert("rotation_euler", frame=f)


# ----------------------------------------------------------------------------- character motion bake

def bake_runner(arm, runner, events, frames, fx, run_rate=1.35, extra=None):
    """Drives the clips from the runner physics like the game does, keys the armature (pose + world motion),
    bakes the spring bones and emits effects. Returns per-frame states [(t, x, s, y, cur_clip)]."""
    names = ("run", "jump", "fall", "land", "slide", "idle")
    clips = {n: MO.ClipSampler(n) for n in names}
    layer = MO.Layer(clips, {"run": True, "fall": True, "idle": True})
    layer.restart("run", 0)
    rig = MO.Rig(arm)
    rr = arm.data.bones["root"].matrix_local.to_quaternion()
    act = bpy.data.actions.new("showcase")
    arm.animation_data_create()
    arm.animation_data.action = act
    dt = 1.0 / FPS
    run_clock = 0.0
    px = runner.x
    states = []
    land_t = -9.0
    for fi in range(frames):
        t = fi * dt
        evs = runner.step(dt, t, events) if fi else []
        frame = fi + 1
        for e in evs:
            if e == "takeoff":
                layer.restart("jump", 0.06)
                fx.puff(V((runner.x, runner.s, 0.02)), frame, size=0.16, count=3)
            elif e == "land":
                layer.restart("land", 0.05)
                land_t = t
                for sx in (-0.12, 0.12):
                    fx.puff(V((runner.x + sx, runner.s + 0.1, 0.02)), frame, size=0.24, count=3,
                            drift=V((sx * 4, -0.4, 0.2)))
            elif e == "slide":
                layer.restart("slide", 0.08)
            elif e == "slide_end":
                layer.play("run", 0.16)
        if not runner.grounded and layer.cur == "jump" and runner.vy < 2.5:
            layer.play("fall", 0.22)
        if layer.cur == "land" and t - land_t > 0.2:
            layer.play("run", 0.14)
        if runner.slideT > 0 and fi % 2 == 0:
            fx.puff(V((runner.x + 0.15, runner.s + 0.55, 0.03)), frame, size=0.13, count=2, drift=V((0.1, -0.9, 0.25)),
                    life=12)
        layer.update(dt)
        run_clock += dt * run_rate
        pose = layer.pose(run_clock)
        roll, hop = MO.lane_lean(runner)
        pose = MO.add_root(pose, roll_deg=roll, lift=hop, rr=rr)
        if extra:
            pose = extra(pose, t, runner)
        world, basis = rig.fk(pose)
        vel = V(((runner.x - px) / dt, runner.speed, runner.vy if not runner.grounded else 0.0))
        px = runner.x
        world, basis = rig.springs(world, basis, dt, vel)
        rig.key(basis, frame)
        arm.location = (runner.x, runner.s, runner.y)
        arm.keyframe_insert("location", frame=frame)
        states.append((t, runner.x, runner.s, runner.y, layer.cur, world))
    return states


# ----------------------------------------------------------------------------- camera

def _ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def camera_path(states, side_in=(1.25, 1.8), side_out=(3.95, 4.5)):
    cam_data = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_data)
    E.link(cam)
    bpy.context.scene.camera = cam
    xc = states[0][1]
    for fi, (t, x, s, y, cur, world) in enumerate(states):
        xc += (x - xc) * 0.22
        w = _ease((t - side_in[0]) / (side_in[1] - side_in[0])) * (1 - _ease((t - side_out[0]) / (side_out[1] - side_out[0])))
        cb = V((xc * 0.75 + 0.35, s - 4.4, 2.35 + 0.35 * y))
        tb = V((xc * 0.85, s + 3.5, 1.05 + 0.45 * y))
        cs = V((x + 4.3, s + 2.1, 1.25 + 0.55 * y))
        ts = V((x, s + 0.35, 0.95 + 0.62 * y))
        c = cb.lerp(cs, w)
        tg = tb.lerp(ts, w)
        cam.location = c
        cam.rotation_euler = (tg - c).to_track_quat('-Z', 'Y').to_euler()
        cam_data.lens = 26 + 9 * w
        cam.keyframe_insert("location", frame=fi + 1)
        cam.keyframe_insert("rotation_euler", frame=fi + 1)
        cam_data.keyframe_insert("lens", frame=fi + 1)
    return cam


# ----------------------------------------------------------------------------- output

def render_frames(name, frames):
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, frames
    sc.render.fps = FPS
    d = os.path.join(OUT, name)
    os.makedirs(d, exist_ok=True)
    for f in os.listdir(d):
        if f.endswith(".png"):
            os.remove(os.path.join(d, f))
    sc.render.filepath = os.path.join(d, "")
    sc.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(animation=True)
    return d


def encode(name, d, gif_width=480):
    mp4 = os.path.join(OUT, name + ".mp4")
    gif = os.path.join(OUT, name + ".gif")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(d, "%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart", mp4], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(d, "%04d.png"),
                    "-vf", "fps=15,scale=%d:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=160[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" % gif_width,
                    gif], check=True)
    print("encoded", mp4, gif)


def filmstrip(name, d, frames, cols=5, width=1600):
    import numpy as np
    ims = []
    for f in frames:
        img = bpy.data.images.load(os.path.join(d, "%04d.png" % f))
        w, h = img.size
        ims.append(np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4))
        bpy.data.images.remove(img)
    h, w = ims[0].shape[:2]
    rows = (len(ims) + cols - 1) // cols
    sheet = np.ones((rows * h, cols * w, 4), np.float32)
    for k, im in enumerate(ims):
        r, c = k // cols, k % cols
        sheet[(rows - 1 - r) * h:(rows - r) * h, c * w:(c + 1) * w] = im
    H, W = sheet.shape[:2]
    s = min(1.0, width / W)
    if s < 1.0:
        yi = (np.arange(int(H * s)) / s).astype(int)
        xi = (np.arange(int(W * s)) / s).astype(int)
        sheet = sheet[yi][:, xi]
    out = bpy.data.images.new("strip", sheet.shape[1], sheet.shape[0], alpha=True)
    out.pixels[:] = sheet.ravel()
    out.filepath_raw = os.path.join(OUT, name + "_strip.png")
    out.file_format = 'PNG'
    out.save()
    print("strip", out.filepath_raw)


# ----------------------------------------------------------------------------- Sakura Line run

def run_showcase():
    E.reset()
    studio.stage(res=(960, 540), floor=False)
    BL.street_scene()
    studio.aim_sun(200)
    fx_mats()
    B, arm, objs = PG.build_pongo_g()
    for o in objs:
        if o.type == 'MESH' and "face" not in o.name and "detail" not in o.name:
            E.add_outline(o, 0.0022)
    PG.girl_clips(arm)
    speed, s0 = 4.6, -6.0
    runner = MO.Runner(speed=speed, lane=0, s0=s0)
    events = [(0.75, "lane", -1), (1.95, "jump", None), (3.4, "slide", None), (4.55, "lane", 1)]
    t_apex = 1.95 + MO.JUMP_V / MO.GRAVITY
    s_bar = s0 + speed * t_apex
    s_gan = s0 + speed * (3.4 + MO.ROLL_TIME * 0.5)
    bar = OB.barricade()
    bar.location = (-2.4, s_bar, 0.0)
    gan = OB.gantry()
    gan.location = (-2.4, s_gan, 0.0)
    for o in (bar, gan):
        E.add_outline(o, 0.012)
    frames = int(5.6 * FPS)
    fx = FX(seed=3)
    states = bake_runner(arm, runner, events, frames, fx)
    # coins: arc over the barricade, a line under the gantry, singles in the middle lane
    src = PK.coin(0)
    E.add_outline(src, 0.012)
    coins = []
    for k in range(5):
        u = (k - 2) * 0.55
        t = t_apex + u / speed
        y = MO.JUMP_V * (t - 1.95) - 0.5 * MO.GRAVITY * (t - 1.95) ** 2
        coins.append((-2.4, s_bar + u, max(0.9, y + 0.95)))
    coins += [(-2.4, s_gan + d, 0.42) for d in (-1.4, -0.45, 0.45, 1.4)]
    coins += [(0.0, s0 + d, 0.95) for d in (2.2, 3.6)] + [(0.0, s0 + speed * 5.0 + d, 0.95) for d in (0.0, 1.2)]
    objs_c = [src] + [src.copy() for _ in coins[1:]]
    for ob in objs_c[1:]:
        E.link(ob)
    for ob, (x, s, z) in zip(objs_c, coins):
        ob.location = (x, s, z)
        ob.rotation_euler = (0, 0, 0)
        ob.keyframe_insert("rotation_euler", frame=1)
        ob.rotation_euler = (0, 0, math.radians(360 * 5.6 * 0.8))
        ob.keyframe_insert("rotation_euler", frame=frames)
        for fc in ob.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
        # collected when Pongo passes through it
        for (t, px, ps, py, cur, world) in states:
            hip_z = py + (0.45 if cur == "slide" else 0.85)
            if abs(px - x) < 0.6 and abs(ps - s) < 0.35 and abs(hip_z - z) < 0.9:
                f = int(round(t * FPS)) + 1
                ob.scale = (1, 1, 1)
                ob.keyframe_insert("scale", frame=f - 1)
                ob.scale = (1.35, 1.35, 1.35)
                ob.keyframe_insert("scale", frame=f + 1)
                ob.scale = (0, 0, 0)
                ob.keyframe_insert("scale", frame=f + 4)
                fx.spark(V((x, s, z)), f + 1)
                break
    fx.petals(110, (-7, 7), (s0 - 2, s0 + speed * 5.6 + 6), (0.3, 6.5), (1, frames))
    camera_path(states)
    name = "run_showcase"
    d = render_frames(name, frames)
    encode(name, d)
    f_of = lambda t: int(round(t * FPS)) + 1
    filmstrip(name, d, [f_of(t) for t in (0.85, 1.95, 2.1, 2.25, 2.45, 2.62, 3.45, 3.72, 4.0, 4.7)], cols=5)
