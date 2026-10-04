"""
Pongo's boarding and vehicle-to-vehicle transitions, one per zone change:

  board_cart      Sakura Line -> Crystal Cavern   runs up behind the waiting ore cart, jumps, lands in it, grabs the rim
  cart_to_boat    Cavern -> Bamboo River          the cart slams the buffer at the underground dock; she is thrown
                                                  forward in a tucked front flip, lands kneeling in the canoe and
                                                  picks up the paddle stowed along the right gunwale
  boat_to_glider  River -> Sky Glide              the canoe tips over the waterfall lip; she springs up, the canopy
                                                  bursts open above her, she catches the brake toggles and folds
                                                  into the harness
  glide_land      Sky Glide -> Express Rooftops   flare, touch down running on the train roof, the glider is released,
                                                  collapses and floats away

Everything is expressed in the co-moving frame of the DESTINATION mount (origin = where she ends up, +Y forward).
The clip carries her root motion from the previous mount to that origin, so the game only has to place the
destination vehicle at the mount and move the previous vehicle with prop_track() (mirrored in
src/com/endlessrush/core/RideTransitions.java).
Body: blends of the gameplay clips (run, jump, fall, land) and the vehicle pose functions, then the same
weighted IK as the rides, so contacts lock on as she arrives and release as she leaves.
"""
import math
from mathutils import Vector, Quaternion
import motion as MO
import pongo_moves as PM

V = Vector
FPS = 30

# name: (duration s, start offset of the previous mount relative to the destination mount)
SPEC = {
    "board_cart": (0.9, V((0.0, -1.7, -PM.CHAR_CART.z))),
    "cart_to_boat": (1.2, V((0.0, -3.4, 1.55))),
    "boat_to_glider": (1.4, V((0.0, -0.6, -1.7))),
    "glide_land": (1.0, V((0.0, -2.4, 1.35))),
}


def _s(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _ramp(u, a, b):
    return _s((u - a) / (b - a))


def _arc(p0, p1, h, t):
    t = max(0.0, min(1.0, t))
    return p0.lerp(p1, t) + V((0, 0, h * 4 * t * (1 - t)))


def prop_track(name, u):
    """Previous vehicle (A) and destination vehicle (B) placement in the destination mount frame at u 0..1:
    dict with 'A': (offset, pitch_deg, scale), 'B': (offset, pitch_deg, scale), 'paddle': stowed weight."""
    dur, a0 = SPEC[name]
    t = u * dur
    if name == "board_cart":
        # the cart waits on the line (it is the co-moving frame); she comes from the ground behind it
        return {"A": None, "B": (V((0, 0, 0)), 0.0, 1.0)}
    if name == "cart_to_boat":
        # the cart stops dead at the buffer: in the co-moving frame it slides back, nose-dips on impact
        back = 3.2 * t * t
        dip = -9.0 * math.sin(math.pi * min(1.0, t / 0.25))
        return {"A": (a0 - PM.CHAR_CART + V((0, -back, 0)), dip, 1.0), "B": (V((0, 0, 0)), 0.0, 1.0)}
    if name == "boat_to_glider":
        # the canoe goes over the lip: drops away and pitches nose down
        drop = 0.5 * 9.8 * max(0.0, t - 0.15) ** 2
        pitch = -55.0 * _ramp(u, 0.1, 0.6)
        g = _ramp(u, 0.28, 0.62)
        burst = g * (1 + 0.12 * math.sin(math.pi * g))
        return {"A": (a0 - PM.CHAR_BOAT + V((0, -0.8 * t, -drop)), pitch, 1.0),
                "B": (V((0, 0, 0)), 0.0, max(0.02, burst))}
    if name == "glide_land":
        # the glider stays on her until touchdown, then floats up/back and packs away
        rel = _ramp(u, 0.55, 0.98)
        pos = _arc(a0, V((0, 0, 0)), 0.15, _ramp(u, 0.0, 0.55))
        return {"A": (pos - PM.CHAR_GLIDE + V((0, -2.5 * rel, 1.6 * rel)), 0.0, 1.0 - rel), "B": None}
    raise KeyError(name)


def _clip(samplers, name, t, loop):
    return samplers[name].pose(t, loop)


def _root_offset(arm, q, off, pitch=0.0):
    """Adds a character-space offset (and an additive pitch, for flips) to a quaternion pose's root."""
    rr = arm.data.bones["root"].matrix_local.to_quaternion()
    q0, l0 = q["root"]
    qa = rr.inverted() @ Quaternion(V((1, 0, 0)), math.radians(pitch)) @ rr
    q = dict(q)
    q["root"] = (qa @ q0, l0 + rr.inverted() @ off)
    return q


def _tuck(arm):
    """Tucked flip pose (Euler degrees)."""
    p = {"root": (-10, 0, 0), "spine": (-30, 0, 0), "chest": (-10, 0, 0), "neck": (20, 0, 0), "head": (10, 0, 0),
         "thigh.R": (120, 0, 6), "shin.R": (-135, 0, 0), "thigh.L": (120, 0, -6), "shin.L": (-135, 0, 0),
         "upper_arm.R": (60, 0, 40), "forearm.R": (0, 0, 70), "upper_arm.L": (60, 0, -40), "forearm.L": (0, 0, -70)}
    return MO.euler_pose(arm, p, (0, 0, -0.12))


def pose_at(arm, samplers, name, u, phase=0.0):
    """Returns (quat pose with root motion, hands {sfx: Target}, feet, extras) for transition `name` at u 0..1."""
    dur, a0 = SPEC[name]
    t = u * dur
    E = lambda pose_root: MO.euler_pose(arm, pose_root[0], pose_root[1])
    if name == "board_cart":
        run = _clip(samplers, "run", t * 1.35, True)
        jump = _clip(samplers, "jump", max(0.0, t - 0.18), False)
        fall = _clip(samplers, "fall", max(0.0, t - 0.4), True)
        cp, croot, ch, cf = PM.cart_pose(phase, crouch=0.65 * (1 - _ramp(u, 0.72, 1.0)))
        cart = E((cp, croot))
        q = MO.blend(run, jump, _ramp(u, 0.16, 0.28))
        q = MO.blend(q, fall, _ramp(u, 0.42, 0.58))
        q = MO.blend(q, cart, _ramp(u, 0.6, 0.76))
        off = _arc(a0, V((0, 0, 0)), 0.55, _ramp(u, 0.2, 0.74))
        q = _root_offset(arm, q, off)
        hw, fw = _ramp(u, 0.55, 0.74), _ramp(u, 0.66, 0.73)
        hands = {k: PM.Target(v.pos, hw, v.pole) for k, v in ch.items()}
        feet = {k: PM.Target(v.pos, fw, v.pole) for k, v in cf.items()}
        return q, hands, feet, {}
    if name == "cart_to_boat":
        cp, croot, ch, cf = PM.cart_pose(0.0, crouch=0.7 * _ramp(u, 0.0, 0.12))
        cart = E((cp, croot))
        bp, broot, bh, bfeet = PM.boat_pose(phase)
        land_dip = 0.12 * math.sin(math.pi * _ramp(u, 0.7, 0.92))
        boat = E((bp, (broot[0], broot[1], broot[2] - land_dip)))
        tuck = _tuck(arm)
        q = MO.blend(cart, tuck, _ramp(u, 0.12, 0.26))
        q = MO.blend(q, boat, _ramp(u, 0.6, 0.76))
        # cart mount -> boat mount: low fast arc with a tucked front flip
        k = _ramp(u, 0.12, 0.72)
        off = _arc(a0, V((0, 0, 0)), 1.1, k)
        flip = -360.0 * _ramp(u, 0.16, 0.66)
        q = _root_offset(arm, q, off, flip)
        # hands leave the rim at launch; reach for the stowed paddle on landing and lift it into the stroke
        lift = _ramp(u, 0.84, 1.0)
        top_s, d_s = V((0.36, 0.42, -0.02)), V((0.0, -1.0, -0.03)).normalized()
        top_r, d_r = PM.paddle_at(phase)
        top = top_s.lerp(top_r, lift)
        d = d_s.lerp(d_r, lift).normalized()
        cw = 1 - _ramp(u, 0.1, 0.16)
        pw = _ramp(u, 0.7, 0.84)
        if cw > 0.001:
            hands = {k: PM.Target(v.pos + a0 - V((0, 0, 0)), cw, v.pole) for k, v in ch.items()}
        else:
            hands = {"R": PM.Target(top, pw, PM.BOAT_AP), "L": PM.Target(top + d * PM.PADDLE_LOW, pw, PM.BOAT_AP)}
        fw = 1 - _ramp(u, 0.1, 0.14) if u < 0.4 else _ramp(u, 0.68, 0.75)
        feet = ({k: PM.Target(v.pos + a0, fw, v.pole) for k, v in cf.items()} if u < 0.4 else
                {k: PM.Target(v.pos, fw, v.pole) for k, v in bfeet.items()})
        return q, hands, feet, {"paddle": (top, d)}
    if name == "boat_to_glider":
        bp, broot, bh, bfeet = PM.boat_pose(phase)
        boat = E((bp, broot))
        land = _clip(samplers, "land", 0.06, False)            # crouched spring
        jump = _clip(samplers, "jump", max(0.0, t - 0.32), False)
        gp, groot, gh, _ = PM.glide_pose(phase, 0.0, 0.35 * (1 - _ramp(u, 0.75, 1.0)))
        glide = E((gp, groot))
        q = MO.blend(boat, land, _ramp(u, 0.04, 0.2))
        q = MO.blend(q, jump, _ramp(u, 0.2, 0.32))
        q = MO.blend(q, glide, _ramp(u, 0.5, 0.78))
        off = _arc(a0, V((0, 0, 0)), 1.0, _ramp(u, 0.22, 0.78))
        q = _root_offset(arm, q, off)
        hw = _ramp(u, 0.42, 0.62)
        hands = {k: PM.Target(v.pos, hw, v.pole) for k, v in gh.items()}
        bw = 1 - _ramp(u, 0.08, 0.16)
        if bw > 0.001:
            hands = {k: PM.Target(v.pos + a0, bw, v.pole) for k, v in bh.items()}
        top, d = PM.paddle_at(phase)
        return q, hands, None, {"paddle_hand": bw}
    if name == "glide_land":
        gp, groot, gh, _ = PM.glide_pose(phase, 0.0, 1.0 * _ramp(u, 0.0, 0.25))
        glide = E((gp, groot))
        fall = _clip(samplers, "fall", t, True)
        land = _clip(samplers, "land", max(0.0, t - 0.55), False)
        run = _clip(samplers, "run", max(0.0, t - 0.8) * 1.35, True)
        q = MO.blend(glide, fall, _ramp(u, 0.3, 0.5))
        q = MO.blend(q, land, _ramp(u, 0.5, 0.58))
        q = MO.blend(q, run, _ramp(u, 0.78, 0.98))
        off = _arc(a0, V((0, 0, 0)), 0.15, _ramp(u, 0.0, 0.55))
        q = _root_offset(arm, q, off)
        hw = 1 - _ramp(u, 0.5, 0.62)
        hands = {k: PM.Target(v.pos + off, hw, v.pole) for k, v in gh.items()}
        return q, hands, None, {}
    raise KeyError(name)


def transition_clips(arm):
    """Bakes the four transitions as one-shot clips with root motion."""
    import pongo_moves as PMm
    rig = MO.Rig(arm)
    samplers = {n: MO.ClipSampler(n) for n in ("run", "jump", "fall", "land")}
    out = []
    for name, (dur, _) in SPEC.items():
        frames = int(round(dur * FPS)) + 1
        PMm._new(arm, name)
        for f in range(1, frames + 1):
            u = (f - 1) / (frames - 1)
            q, hands, feet, _ = pose_at(arm, samplers, name, u)
            world, basis = PM.solve_q(rig, q, hands, feet)
            rig.key(basis, f)
        out.append((name, False))
    return out
