"""
Motion player for showcase renders.

Samples baked clips (fcurves), cross-fades them with the same rules as the game's Animator
(src/com/pongo/core/Animator.java), runs the runner physics timeline (gravity, jump, slide, lane
switches, vehicle moves), does forward kinematics in Python and bakes spring bones (twin tails, wrap
panel) with the game's spring model, then writes everything into one action on the armature.
Effects can subscribe to events (takeoff, land, slide start/stop, lane switch).

Blender space: Z up, the runner faces +Y; the armature object carries the world motion (x, s, y).
"""
import math
import bpy
from mathutils import Vector, Matrix, Quaternion, Euler

V = Vector
FPS = 30


class ClipSampler:
    """Evaluates a baked action at any time (fractional frames, loop or clamp)."""

    def __init__(self, name):
        act = bpy.data.actions[name]
        self.name = name
        self.curves = {}
        frames = []
        for fc in act.fcurves:
            dp = fc.data_path
            if not dp.startswith('pose.bones["'):
                continue
            bn = dp.split('"')[1]
            prop = dp.rsplit('.', 1)[-1]
            key = 'rot' if prop == 'rotation_quaternion' else ('loc' if prop == 'location' else None)
            if key is None:
                continue
            d = self.curves.setdefault(bn, {})
            d.setdefault(key, [None] * (4 if key == 'rot' else 3))[fc.array_index] = fc
            frames += [k.co.x for k in fc.keyframe_points]
        self.f0, self.f1 = (min(frames), max(frames)) if frames else (1.0, 1.0)

    def duration(self):
        return (self.f1 - self.f0) / FPS

    def pose(self, t, loop):
        span = max(self.f1 - self.f0, 1e-6)
        f = t * FPS
        f = (f % span) if loop else max(0.0, min(span, f))
        f += self.f0
        out = {}
        for bn, d in self.curves.items():
            q = Quaternion((1, 0, 0, 0))
            l = V((0, 0, 0))
            if 'rot' in d and all(d['rot']):
                q = Quaternion([fc.evaluate(f) for fc in d['rot']])
                q.normalize()
            if 'loc' in d and all(d['loc']):
                l = V([fc.evaluate(f) for fc in d['loc']])
            out[bn] = (q, l)
        return out


def blend(pa, pb, w):
    """Per-bone slerp/lerp from pose pa to pb (w = weight of pb)."""
    out = dict(pa)
    for bn, (qb, lb) in pb.items():
        if bn in pa:
            qa, la = pa[bn]
            if qa.dot(qb) < 0:
                qb = -qb
            out[bn] = (qa.slerp(qb, w), la.lerp(lb, w))
        else:
            out[bn] = (Quaternion((1, 0, 0, 0)).slerp(qb, w), V((0, 0, 0)).lerp(lb, w))
    return out


class Layer:
    """Clip player with cross-fades (mirrors Animator.play/restart semantics)."""

    def __init__(self, clips, loops):
        self.clips = clips
        self.loops = loops
        self.cur = self.prev = None
        self.tc = self.tp = 0.0
        self.fade, self.fd = 1.0, 1e-4

    def play(self, name, fade=0.15):
        if name == self.cur:
            return
        self.restart(name, fade)

    def restart(self, name, fade=0.1):
        if self.cur is not None and fade > 0:
            self.prev, self.tp = self.cur, self.tc
            self.fade, self.fd = 0.0, fade
        self.cur, self.tc = name, 0.0

    def update(self, dt):
        self.tc += dt
        self.tp += dt
        if self.fade < 1.0:
            self.fade = min(1.0, self.fade + dt / self.fd)

    def time(self):
        return self.tc

    def pose(self, run_clock=None):
        def P(name, t):
            if name == "run" and run_clock is not None:
                t = run_clock
            return self.clips[name].pose(t, self.loops.get(name, False))
        a = P(self.cur, self.tc)
        if self.prev is not None and self.fade < 1.0:
            w = self.fade * self.fade * (3 - 2 * self.fade)
            return blend(P(self.prev, self.tp), a, w)
        return a


class Rig:
    """Python forward kinematics for an armature (armature space), plus spring chains."""

    def __init__(self, arm):
        self.arm = arm
        self.bones = list(arm.data.bones)
        self.names = [b.name for b in self.bones]
        self.index = {n: i for i, n in enumerate(self.names)}
        self.parent = [self.index[b.parent.name] if b.parent else -1 for b in self.bones]
        self.rest = [b.matrix_local.copy() for b in self.bones]
        self.rest_local = []
        for i, b in enumerate(self.bones):
            p = self.parent[i]
            self.rest_local.append(self.rest[p].inverted() @ self.rest[i] if p >= 0 else self.rest[i].copy())
        self.dyn = [n.startswith("dyn_") for n in self.names]
        self.dir = [None] * len(self.bones)
        self.vel = [V((0, 0, 0)) for _ in self.bones]

    def fk(self, pose):
        world = [None] * len(self.bones)
        basis = [None] * len(self.bones)
        for i, n in enumerate(self.names):
            q, l = pose.get(n, (Quaternion((1, 0, 0, 0)), V((0, 0, 0))))
            basis[i] = Matrix.Translation(l) @ q.to_matrix().to_4x4()
            p = self.parent[i]
            world[i] = (world[p] @ self.rest_local[i] if p >= 0 else self.rest_local[i]) @ basis[i]
        return world, basis

    def springs(self, world, basis, dt, velocity, wind=V((0, 0, 0)), gravity=0.45, k=60.0, damp=7.0, gain=0.07):
        """Game spring model: each dyn bone keeps a lagging direction pulled toward the animated direction,
        gravity and drag; the bone (and its children) is re-aimed along it."""
        dt = min(dt, 1.0 / 30.0)
        for i in range(len(self.bones)):
            if not self.dyn[i]:
                continue
            m = world[i]
            a = V((m[0][1], m[1][1], m[2][1])).normalized()
            if self.dir[i] is None:
                self.dir[i] = a.copy()
                self.vel[i] = V((0, 0, 0))
            tgt = a * 0.55 + (wind - velocity * gain) + V((0, 0, -gravity))
            if tgt.length > 1e-6:
                tgt.normalize()
            v = self.vel[i]
            v += ((tgt - self.dir[i]) * k - v * damp) * dt
            d = (self.dir[i] + v * dt).normalized()
            self.dir[i] = d
            rot = a.rotation_difference(d).to_matrix().to_4x4()
            head = m.to_translation()
            world[i] = Matrix.Translation(head) @ rot @ Matrix.Translation(-head) @ m
            # re-derive this bone's basis and propagate to descendants
            p = self.parent[i]
            parent_w = world[p] if p >= 0 else Matrix.Identity(4)
            basis[i] = (parent_w @ self.rest_local[i]).inverted() @ world[i]
            for c in range(i + 1, len(self.bones)):
                pc = self.parent[c]
                if pc >= 0 and self._descends(c, i):
                    world[c] = world[pc] @ self.rest_local[c] @ basis[c]
        return world, basis

    def _descends(self, c, i):
        p = self.parent[c]
        while p >= 0:
            if p == i:
                return True
            p = self.parent[p]
        return False

    def ik2(self, world, basis, upper, lower, target, pole):
        """Two-bone IK: aims upper/lower so the lower bone's tail reaches target, bending toward pole.
        Updates world/basis of both bones and their descendants (armature space)."""
        iu, il = self.index[upper], self.index[lower]
        S = world[iu].to_translation()
        E0 = world[il].to_translation()
        W0 = self.point(world, lower, at_tail=True)
        l1, l2 = (E0 - S).length, (W0 - E0).length
        dv = V(target) - S
        d = max(abs(l1 - l2) + 1e-4, min(l1 + l2 - 1e-4, dv.length))
        u = dv.normalized()
        pv = V(pole) - S
        v = pv - u * pv.dot(u)
        if v.length < 1e-6:
            v = (E0 - S) - u * (E0 - S).dot(u)
        v.normalize()
        a = math.acos(max(-1.0, min(1.0, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d))))
        E1 = S + (u * math.cos(a) + v * math.sin(a)) * l1
        R1 = (E0 - S).normalized().rotation_difference((E1 - S).normalized()).to_matrix().to_4x4()
        world[iu] = Matrix.Translation(S) @ R1 @ Matrix.Translation(-S) @ world[iu]
        p = self.parent[iu]
        basis[iu] = ((world[p] if p >= 0 else Matrix.Identity(4)) @ self.rest_local[iu]).inverted() @ world[iu]
        world[il] = world[iu] @ self.rest_local[il] @ basis[il]
        E2 = world[il].to_translation()
        W2 = self.point(world, lower, at_tail=True)
        T2 = S + u * d
        R2 = (W2 - E2).normalized().rotation_difference((T2 - E2).normalized()).to_matrix().to_4x4()
        world[il] = Matrix.Translation(E2) @ R2 @ Matrix.Translation(-E2) @ world[il]
        basis[il] = (world[iu] @ self.rest_local[il]).inverted() @ world[il]
        for c in range(il + 1, len(self.bones)):
            if self._descends(c, il):
                world[c] = world[self.parent[c]] @ self.rest_local[c] @ basis[c]
        return world, basis

    def key(self, basis, frame):
        """Write the bases as keyframes on the pose bones."""
        for i, n in enumerate(self.names):
            pb = self.arm.pose.bones[n]
            pb.rotation_mode = 'QUATERNION'
            loc, rot, _ = basis[i].decompose()
            pb.rotation_quaternion = rot
            pb.keyframe_insert("rotation_quaternion", frame=frame)
            if n == "root":
                pb.location = loc
                pb.keyframe_insert("location", frame=frame)

    def point(self, world, bone, local=V((0, 0, 0)), at_tail=False):
        i = self.index[bone]
        b = self.bones[i]
        p = (b.tail_local if at_tail else b.head_local) + local
        return world[i] @ self.rest[i].inverted() @ p


# ---------------------------------------------------------------------------- runner physics (matches Game.java)

GRAVITY, JUMP_V, ROLL_TIME, SWITCH_TIME = 58.0, 17.5, 0.65, 0.24


class Runner:
    """Lane runner: events [(t, kind, arg)] with kind in lane/jump/slide. Produces per-frame states."""

    def __init__(self, speed=6.0, lane=0, lanes=(-2.4, 0.0, 2.4), s0=0.0):
        self.speed, self.lanes = speed, lanes
        self.lane = lane
        self.x = lanes[lane + 1]
        self.s = s0
        self.y = self.vy = 0.0
        self.grounded = True
        self.slideT = 0.0
        self.sw_from = self.sw_to = self.x
        self.swT = 1.0
        self.sw_dir = 0
        self.events = []

    def step(self, dt, t, evs):
        out = []
        for (te, kind, arg) in evs:
            if not (t - dt < te <= t):
                continue
            if kind == "lane":
                nl = max(-1, min(1, self.lane + arg))
                if nl != self.lane:
                    self.lane = nl
                    self.sw_from, self.sw_to, self.swT, self.sw_dir = self.x, self.lanes[nl + 1], 0.0, arg
                    out.append("lane")
            elif kind == "jump" and self.grounded:
                self.vy, self.grounded, self.slideT = JUMP_V, False, 0.0
                out.append("takeoff")
            elif kind == "slide":
                if self.grounded:
                    self.slideT = ROLL_TIME
                    out.append("slide")
                else:
                    self.vy = min(self.vy, -38.0)
                    self.slide_queued = True
        self.s += self.speed * dt
        if self.swT < 1.0:
            self.swT = min(1.0, self.swT + dt / SWITCH_TIME)
            u = self.swT * self.swT * (3 - 2 * self.swT)
            self.x = self.sw_from + (self.sw_to - self.sw_from) * u
        if not self.grounded:
            self.vy -= GRAVITY * dt
            self.y += self.vy * dt
            if self.y <= 0.0:
                self.y, self.vy, self.grounded = 0.0, 0.0, True
                out.append("land")
                if getattr(self, "slide_queued", False):
                    self.slide_queued = False
                    self.slideT = ROLL_TIME
                    out.append("slide")
        if self.slideT > 0:
            self.slideT = max(0.0, self.slideT - dt)
            if self.slideT == 0.0:
                out.append("slide_end")
        return out


def lane_lean(runner):
    """Additive lean during a lane switch (deg): bank into the move, small hop."""
    if runner.swT >= 1.0:
        return 0.0, 0.0
    p = runner.swT
    return runner.sw_dir * 16.0 * math.sin(math.pi * p), 0.045 * math.sin(math.pi * p)


def add_root(pose, roll_deg=0.0, pitch_deg=0.0, yaw_deg=0.0, lift=0.0, rr=None):
    """Additive rotation/offset on the root (armature axes), counter-tilt on neck/head."""
    q0, l0 = pose["root"]
    qa = Quaternion(V((0, 1, 0)), math.radians(roll_deg)) @ Quaternion(V((1, 0, 0)), math.radians(pitch_deg)) @ \
        Quaternion(V((0, 0, 1)), math.radians(yaw_deg))
    if rr is not None:
        qa = rr.inverted() @ qa @ rr
        lift_v = rr.inverted() @ V((0, 0, lift))
    else:
        lift_v = V((0, 0, lift))
    pose["root"] = (qa @ q0, l0 + lift_v)
    return pose


def euler_pose(arm, pose, root_loc=(0, 0, 0)):
    """Pose dict in degrees about armature axes (characters.pose_key semantics) -> {bone: (quat, loc)}."""
    out = {}
    for b in arm.data.bones:
        e = pose.get(b.name, (0, 0, 0))
        rr = b.matrix_local.to_quaternion()
        qa = Euler([math.radians(a) for a in e], 'XYZ').to_quaternion()
        out[b.name] = (rr.inverted() @ qa @ rr, V((0, 0, 0)))
    rr = arm.data.bones["root"].matrix_local.to_quaternion()
    out["root"] = (out["root"][0], rr.inverted() @ V(root_loc))
    return out
