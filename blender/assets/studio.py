"""Studio setup for single-asset design renders (EEVEE toon)."""
import math
import bpy
from mathutils import Vector
import erlib as E


_SUN = []


def stage(res=(900, 900), sky_top=0x7EC8F8, sky_hor=0xE8F6FF, floor=True, floor_col=0xF3EEE6):
    E.setup_eevee(res=res, samples=48, bloom=True)
    E.world_sky(sky_top, sky_hor, 1.0)
    _SUN.clear()
    _SUN.append(E.sun(rot=(48, 12, 38), energy=4.0, color=0xFFF4E2))
    if floor:
        E.mat("studio_floor", floor_col, rim=0.0, spec=0.0, soft=0.2, outline=0)
        m = E.Mesher("floor").mat("studio_floor")
        m.cyl((0, 0, -0.02), r=6, h=0.04, seg=64)
        m.obj()


def aim_sun(yaw, elev=48.0, side=35.0):
    """Key light from the camera side (yaw measured like shoot()), offset by `side` degrees."""
    if not _SUN:
        return
    y = math.radians(yaw + side)
    d = Vector((math.sin(y) * math.cos(math.radians(elev)), -math.cos(y) * math.cos(math.radians(elev)), math.sin(math.radians(elev))))
    _SUN[0].rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()


def shoot(name, target=(0, 0, 0.5), dist=3.0, yaw=35.0, pitch=18.0, lens=50, light=True):
    if light:
        aim_sun(yaw)
    t = Vector(target)
    y, p = math.radians(yaw), math.radians(pitch)
    loc = t + Vector((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p))) * dist
    E.camera(loc, t, lens=lens)
    import os
    os.makedirs(os.path.join(E.OUT_RENDERS, "design"), exist_ok=True)
    E.render(os.path.join(E.OUT_RENDERS, "design", name + ".png"))
