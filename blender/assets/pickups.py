"""Power-ups, currency and equipment for PONGO."""
import math
import bpy
from mathutils import Vector, Matrix
import erlib as E
import studio

GOLD = dict(color=0xFFC62E, shadow=0xC0601E, spec=0.9, rim=0.45, emis=0.08, soft=0.08)


def coin(lod=0):
    """Mon coin: round gold coin with a square hole, raised rim and 永楽通寶 inscription."""
    E.mat("gold", **GOLD)
    E.mat("gold_deep", color=0xE9A21C, shadow=0xA84A16, spec=0.6, rim=0.3, emis=0.05, soft=0.08)
    m = E.Mesher("coin").mat("gold")
    R, T = 0.45, 0.07
    seg = 64 if lod == 0 else 20
    circle = [(R * math.cos(2 * math.pi * i / seg), R * math.sin(2 * math.pi * i / seg)) for i in range(seg)]
    h = 0.085
    hole = [(-h, -h), (-h, h), (h, h), (h, -h)]
    # coin faces the camera: disc in the XZ plane, thickness along Y
    m.push(Matrix.Rotation(math.radians(90), 4, 'X'))
    m.mat("gold_deep")
    m.extrude(circle, T, holes=[hole], bevel=(0.01, 2) if lod == 0 else None)
    m.mat("gold")
    # raised outer rim (both faces)
    prof = [(R - 0.055, -T / 2 - 0.022), (R - 0.045, -T / 2 - 0.03), (R - 0.004, -T / 2 - 0.03), (R + 0.004, -T / 2 - 0.01),
            (R + 0.004, T / 2 + 0.01), (R - 0.004, T / 2 + 0.03), (R - 0.045, T / 2 + 0.03), (R - 0.055, T / 2 + 0.022)]
    m.lathe(prof, seg=seg)
    # raised square border around the hole
    b = 0.13
    m.extrude([(-b, -b), (b, -b), (b, b), (-b, b)], T + 0.05, holes=[[(-h, -h), (-h, h), (h, h), (h, -h)][::-1]],
              bevel=(0.008, 2) if lod == 0 else None)
    if lod == 0:
        # inscription: top, right, bottom, left of the hole (traditional reading order)
        chars = [("永", (0, 0.265)), ("楽", (0.265, 0)), ("通", (0, -0.265)), ("寶", (-0.265, 0))]
        for face in (1, -1):
            for ch, (x, y) in chars:
                m.push(Matrix.Translation((x, y, face * (T / 2 + 0.004))))
                if face < 0:
                    m.push(Matrix.Rotation(math.radians(180), 4, 'Y'))
                m.text(ch, size=0.17, depth=0.012, font=E.FONT_JP)
                if face < 0:
                    m.pop()
                m.pop()
    m.pop()
    return m.obj("coin" if lod == 0 else "coin@1", smooth_angle=35, outline=0.006)


def design_coin():
    E.reset()
    studio.stage(res=(900, 900))
    ob = coin(0)
    ob.location = (0, 0, 0.62)
    ob.rotation_euler = (0, 0, math.radians(-25))
    studio.shoot("coin", target=(0, 0, 0.6), dist=2.2, yaw=20, pitch=10, lens=60)


def export_coin():
    E.reset()
    E.mat("test_floor", 0xF3EEE6, rim=0.0, spec=0.0, soft=0.2, outline=0)
    fl = E.Mesher("test_floor").mat("test_floor")
    fl.cyl((0, 0, -0.02), r=3, h=0.04, seg=64)
    E.export_erm(fl.obj(), "test_floor")
    E.reset()
    E.export_erm(coin(0), "coin")
    E.reset()
    E.export_erm(coin(1), "coin@1")
