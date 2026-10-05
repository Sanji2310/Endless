"""
Sakura Line world export for the game, plus the chasers and the run effects.

The city kit (city.py, buildings.py) was built for design renders; this module cuts it into pieces the game lays
out endlessly (src/com/endlessrush/core/SakuraWorld.java):

  per 12 m segment   sl_track, sl_side_r, sl_side_l, sl_wires, sl_lot_r, sl_lot_l
  every 24 m         sl_gantry, sl_pole (cables reach the next pole 24 m on)
  plots (20 m)       sl_house_a..e (one per 10 m), sl_apartment, sl_konbini (whole plot)
  roadside           sl_sakura_1..3 (trunk + canopy + ground shadow in one piece)
  set piece          sl_crossing (replaces track + sides on its segment), sl_crossing_arm
  chasers            daigo_torso, daigo_head, daigo_arm, daigo_leg; kuro_body, kuro_head, kuro_leg
  effects            fx_speed, fx_petal, fx_puff, fx_ring, fx_glow, fx_star, fx_impact (atlas sprites)

Everything is exported at the Blender origin in the kit's own layout (x across the line, +Y along it); buildings face
-X (right side) and are mirrored by the game for the left side.
"""
import math, random
import numpy as np
import bpy
from mathutils import Vector, Matrix
import erlib as E
import gamelod as GL
import city
import buildings as B

V = Vector

HOUSES = [("sl_house_a", dict(w=7.0, d=7.5, floors=2, wall="cream", roof="ibushi", style=0, seed=1)),
          ("sl_house_b", dict(w=7.6, d=7.0, floors=2, wall="white", roof="brick", style=1, seed=2)),
          ("sl_house_c", dict(w=6.6, d=7.0, floors=2, wall="sky", roof="navy", style=2, seed=3)),
          ("sl_house_d", dict(w=7.2, d=7.4, floors=2, wall="mint", roof="green", style=0, seed=9)),
          ("sl_house_e", dict(w=6.8, d=7.2, floors=2, wall="beige", roof="choco", style=1, seed=5))]


def _join(objs, name):
    ob = E.join([o for o in objs if o is not None], name)
    return ob


def _lot(lod=0, mirror=False):
    """Ground beyond the road out to |x| = 70: lawns under the plots, then a grass field toward the horizon."""
    E.mat("lot", 0x9CCB78, "t_grass", soft=0.25, rim=0.1, outline=0)
    E.mat("field", 0xA9C98A, "t_grass", soft=0.25, rim=0.1, outline=0)
    m = E.Mesher("lot")
    if mirror:
        m.push(Matrix.Diagonal((-1, 1, 1, 1)))
    g = city.GROUND - 0.04
    m.mat("lot", uvscale=4.0)
    m.poly([(11.0, 0, g), (30.0, 0, g), (30.0, city.SEG, g), (11.0, city.SEG, g)])
    m.mat("field", uvscale=6.0)
    m.poly([(30.0, 0, g - 0.02), (70.0, 0, g - 0.3), (70.0, city.SEG, g - 0.3), (30.0, city.SEG, g - 0.02)])
    ob = m.obj(("sl_lot_l" if mirror else "sl_lot_r") + ("" if lod == 0 else "@1"), smooth_angle=0)
    if mirror:
        city._fix_winding(ob)
    return ob


def _finish_building(ob):
    E.finish_hard(ob, width=0.012, segments=2, angle=35)
    return ob


def _sakura(name, seed, height, lod, ratio=None):
    """buildings.sakura with the canopy decimated to `ratio` instead of the kit's own (the game's near tier sits
    between the kit's two LODs; the canopy still takes its normals from the smooth hull afterwards)."""
    import characters as CH
    orig = CH.sculpt_union
    if ratio is not None:
        def su(*a, **kw):
            kw["ratio"] = ratio
            return orig(*a, **kw)
        CH.sculpt_union = su
    try:
        return list(B.sakura(name, seed=seed, height=height, lod=lod))
    finally:
        CH.sculpt_union = orig


# kit LOD used for each game tier, and the LOD2 decimation ratio
_KIT = (0, 1, 1)


def export_world():
    """Three game tiers per piece (blender/lib/gamelod.py): LOD0 = kit LOD0 without the render bevel, LOD1 = kit
    LOD1, LOD2 = kit LOD1 decimated."""
    E.reset(); B.haitsu_sign()
    for lv in (0, 1, 2):
        sx, kit = GL.sfx(lv), _KIT[lv]

        def ex(ob, name, ratio=0.35):
            E.export_erm(GL.tier(ob, lv, ratio), name + sx)

        E.reset(); city.city_mats(); B.mats()
        ex(city.side(kit), "sl_side_r", 0.5)
        E.reset(); city.city_mats(); B.mats()
        ex(city.side(kit, mirror=True), "sl_side_l", 0.5)
        E.reset(); city.city_mats()
        ex(city.track(kit), "sl_track", 0.3)
        if lv < 2:
            E.reset(); city.city_mats()
            E.export_erm(city.wires(kit), "sl_wires" + sx)
            E.export_erm(_lot(kit), "sl_lot_r" + sx)
            E.export_erm(_lot(kit, True), "sl_lot_l" + sx)
        E.reset(); city.city_mats()
        ex(_finish_building(city.gantry(kit)), "sl_gantry")
        E.reset(); city.city_mats()
        ex(_finish_building(city.utility_pole(kit)), "sl_pole")
        for nm, kw in HOUSES:
            E.reset(); city.city_mats(); B.mats()
            ex(_finish_building(B.house(nm, lod=kit, **kw)), nm)
        E.reset(); city.city_mats(); B.mats()
        ex(_finish_building(B.apartment("sl_apartment", lod=kit)), "sl_apartment")
        E.reset(); city.city_mats(); B.mats()
        ex(_finish_building(B.konbini("sl_konbini", lod=kit)), "sl_konbini")
        for k in range(3):
            E.reset(); city.city_mats(); B.mats()
            parts = _sakura("sl_sakura_%d" % (k + 1), k + 1, 6.0 + k * 0.5, kit, ratio=0.12 if lv == 0 else None)
            if lv == 0:
                # blossom pattern repeats every 0.75 m instead of 0.3 m: fewer cuts in the canopy (see gamelod)
                for d in parts[1].data.uv_layers.active.data:
                    d.uv = (d.uv[0] * 0.4, d.uv[1] * 0.4)
            ex(parts, "sl_sakura_%d" % (k + 1), 0.4)
        E.reset(); city.city_mats(); B.mats()
        ex(_finish_building(B.crossing("sl_crossing", lod=kit)), "sl_crossing")
        if lv < 2:
            E.reset(); city.city_mats(); B.mats()
            E.export_erm(B.crossing_arm("sl_crossing_arm", lod=kit), "sl_crossing_arm" + sx)


# ----------------------------------------------------------------------------- chasers

def chaser_mats():
    M = E.mat
    M("ch_navy", 0x2A3A72, rim=0.4, soft=0.1, spec=0.0, shadow=0x5E5EA0)
    M("ch_navy_dark", 0x1A2348, rim=0.3, soft=0.1)
    M("ch_brass", 0xF2C35C, spec=0.95, rim=0.45, soft=0.04, flags=E.F_METAL)
    M("ch_skin", 0xF3C7A6, rim=0.35, soft=0.14, skin=1.0, shadow=0xD98A8E)
    M("ch_white", 0xF8F6F0, rim=0.35, soft=0.1)
    M("ch_shoe", 0x26232A, spec=0.6, rim=0.3, soft=0.06)
    M("ch_hair", 0x3A3038, rim=0.3, soft=0.08)
    M("ch_ink", 0x221C26, rim=0.0, soft=0.05, outline=0.0)
    M("ch_red", 0xD8403A, rim=0.35, soft=0.08)
    M("ch_cheek", 0xF29A94, rim=0.0, soft=0.2, outline=0.0)
    M("ch_shiba", 0xD98A3E, rim=0.45, soft=0.12, shadow=0xA45A6A)
    M("ch_shiba_dark", 0x2E2630, rim=0.35, soft=0.12)
    M("ch_cream", 0xFFF1DC, rim=0.35, soft=0.12, shadow=0xD6B6C8)
    M("ch_mouth", 0x5A1A2A, rim=0.0, soft=0.1, outline=0.0)
    M("ch_tongue", 0xF0708A, rim=0.1, soft=0.12, outline=0.0)
    M("ch_sole", 0x7A6A66, rim=0.1, soft=0.1)
    M("ch_lip", 0x3A2A34, rim=0.1, soft=0.08, outline=0.0)


# Daigo's joints (Blender: +Y forward, Z up; SakuraWorld.chasers uses the same numbers in game space)
DAIGO_HIP = 0.95          # hip pivots above the soles
DAIGO_HIP_X = 0.15
DAIGO_SHOULDER = (0.37, 0.6)   # shoulder pivot (x, z above the hips)
DAIGO_NECK = 0.74


def daigo_torso(name="daigo_torso"):
    """Hips at the origin, shoulders at z 0.6: a barrel chest under a broad shoulder yoke (so the arms meet it), belly,
    navy tunic with a placket of brass buttons, gold-fringed epaulettes, belt and buckle, red armband, whistle cord."""
    chaser_mats()
    m = E.Mesher(name)
    m.mat("ch_navy")
    m.lathe([(0.0, -0.02), (0.24, 0.0), (0.29, 0.1), (0.32, 0.26), (0.33, 0.42), (0.31, 0.56), (0.24, 0.66),
             (0.12, 0.72), (0.0, 0.74)], seg=28)                                         # tunic body
    m.sphere((0, 0.05, 0.22), 0.28, 24, 14, s=(1.0, 1.0, 0.8))                         # belly pushing the tunic out
    m.sphere((0, 0.0, 0.6), 0.3, 24, 12, s=(1.28, 0.8, 0.42))                          # shoulder yoke
    m.mat("ch_navy_dark")
    m.box((0, 0.278, 0.37), (0.07, 0.03, 0.36), smooth=False)                            # button placket
    m.lathe([(0.315, 0.04), (0.33, 0.06), (0.33, 0.14), (0.315, 0.16)], seg=28)         # belt
    m.mat("ch_brass")
    m.rbox((0, 0.33, 0.1), (0.12, 0.03, 0.09), r=0.012, seg=2)                          # buckle
    for k in range(4):
        m.sphere((0, 0.305, 0.24 + k * 0.1), 0.024, 10, 6, s=(1, 0.6, 1))               # buttons
    for sx in (-1, 1):
        m.mat("ch_brass")
        m.sphere((sx * 0.3, 0.0, 0.66), 0.11, 16, 8, s=(1.1, 1.0, 0.32))               # epaulette board
        for k in range(7):
            a = math.radians(-60 + k * 20)
            m.cyl((sx * (0.3 + 0.1 * math.cos(a) * 0.9), 0.1 * math.sin(a), 0.6), r=0.012, h=0.07, seg=6)  # fringe
        m.mat("ch_brass")
        m.sphere((sx * 0.13, 0.27, 0.5), 0.02, 8, 6)                                    # collar pins
    m.mat("ch_white")
    m.lathe([(0.12, 0.68), (0.125, 0.74), (0.105, 0.78)], seg=18)                        # shirt collar
    m.mat("ch_brass")
    m.tube([V((0.1, 0.27, 0.6)), V((0.02, 0.31, 0.46)), V((-0.06, 0.31, 0.38))], r=0.007, seg=5)
    m.cyl((-0.06, 0.32, 0.36), r=0.022, h=0.07, seg=10, axis='X')                       # whistle
    return m.obj(name, smooth_angle=40)


def daigo_head(name="daigo_head"):
    """Neck base at the origin: a big round head (anime proportions next to Pongo), jowls, a nose, a bushy walrus
    moustache, and a furious face: heavy brows driven down into a V, narrowed eyes under hard upper lids, a mouth
    open in a shout (teeth and tongue), a throbbing anger mark at the temple, and a peaked cap with a brass badge."""
    chaser_mats()
    m = E.Mesher(name)
    m.mat("ch_skin")
    m.cyl((0, 0, 0.04), r=0.085, h=0.1, seg=14)
    m.sphere((0, 0.0, 0.22), 0.19, 28, 16, s=(1.0, 0.98, 1.0))                         # cranium
    m.sphere((0, 0.04, 0.12), 0.17, 24, 12, s=(1.05, 0.95, 0.72))                       # jowls and chin
    m.sphere((0, 0.19, 0.2), 0.044, 14, 8, s=(1.05, 1.0, 0.92))                         # nose
    # the shout: a dark mouth opening under the moustache, upper teeth, a tongue at the bottom
    m.mat("ch_mouth")
    m.sphere((0, 0.183, 0.085), 0.072, 18, 10, s=(1.0, 0.3, 0.72))
    m.mat("ch_white")
    m.sphere((0, 0.192, 0.112), 0.06, 16, 6, s=(1.0, 0.26, 0.2))                        # upper teeth
    m.sphere((0, 0.19, 0.052), 0.045, 14, 6, s=(1.0, 0.24, 0.16))                       # lower teeth
    m.mat("ch_tongue")
    m.sphere((0, 0.19, 0.066), 0.04, 12, 6, s=(1.0, 0.3, 0.42))
    for sx in (-1, 1):
        m.mat("ch_skin")
        m.sphere((sx * 0.188, -0.01, 0.21), 0.045, 12, 8, s=(0.45, 0.8, 1.15))         # ears
        m.mat("ch_cheek")
        m.sphere((sx * 0.115, 0.15, 0.16), 0.04, 12, 6, s=(1.0, 0.3, 0.6))             # flushed cheeks
        m.mat("ch_white")
        m.push(Matrix.Translation((sx * 0.066, 0.172, 0.246)) @ Matrix.Rotation(math.radians(sx * 14), 4, 'Y'))
        m.sphere((0, 0, 0), 0.028, 12, 8, s=(1.0, 0.45, 0.62))                          # eye whites, narrowed
        m.pop()
        m.mat("ch_ink")
        m.sphere((sx * 0.06, 0.184, 0.242), 0.011, 10, 6, s=(1.0, 0.5, 1.0))           # pinpoint pupils
        # hard upper lid: an ink stroke slanting down toward the nose
        m.tube([V((sx * 0.098, 0.163, 0.262)), V((sx * 0.066, 0.183, 0.256)), V((sx * 0.036, 0.181, 0.24))],
               r=0.0075, seg=6)
        m.mat("ch_hair")
        # brows: thick wedges driven down hard toward the nose, inner ends touching the lids
        m.push(Matrix.Translation((sx * 0.068, 0.172, 0.282)) @ Matrix.Rotation(math.radians(sx * 32), 4, 'Y'))
        m.sphere((0, 0, 0), 0.056, 14, 6, s=(1.0, 0.4, 0.34))
        m.pop()
        m.push(Matrix.Translation((sx * 0.075, 0.19, 0.152)) @ Matrix.Rotation(math.radians(sx * 26), 4, 'Y'))
        m.sphere((0, 0, 0), 0.07, 16, 8, s=(1.25, 0.55, 0.48))                          # moustache halves, flared
        m.sphere((sx * 0.072, -0.012, -0.02), 0.034, 10, 6, s=(1.1, 0.6, 0.6))         # tips
        m.pop()
        m.sphere((sx * 0.17, 0.02, 0.2), 0.04, 10, 6, s=(0.5, 0.9, 1.4))              # sideburns
    m.mat("ch_skin")
    m.sphere((0, 0.172, 0.27), 0.03, 10, 6, s=(1.2, 0.5, 0.5))                          # knotted brow ridge
    # anger mark (the anime cross vein) on his right temple, laid on the skull: four corner arcs, each pointing its
    # bend at the centre
    m.mat("ch_red")
    n = Vector((0.75, 0.6, 0.15)).normalized()
    u = Vector((0, 0, 1)).cross(n).normalized()
    w = n.cross(u)
    c = Vector((0, 0, 0.22)) + n * 0.196
    def at(ang, r):
        return c + (u * math.cos(ang) + w * math.sin(ang)) * r + n * (0.004 * (1 - r / 0.026))
    for k in range(4):
        a = math.radians(45 + k * 90)
        m.tube([at(a - 0.62, 0.026), at(a - 0.25, 0.014), at(a, 0.009), at(a + 0.25, 0.014), at(a + 0.62, 0.026)],
               r=0.005, seg=5)
    m.mat("ch_hair")
    m.sphere((0, -0.05, 0.22), 0.18, 22, 10, s=(1.04, 0.9, 0.62))                      # hair at the back
    # cap: crown flaring out, dark band, glossy visor, brass badge with a cherry blossom
    m.mat("ch_navy")
    m.lathe([(0.165, 0.3), (0.18, 0.36), (0.215, 0.43), (0.2, 0.46), (0.0, 0.47)], seg=28, c=(0, -0.01, 0))
    m.mat("ch_navy_dark")
    m.lathe([(0.17, 0.29), (0.178, 0.29), (0.182, 0.345), (0.172, 0.345)], seg=28, c=(0, -0.01, 0))
    m.mat("ch_shoe")
    m.push(Matrix.Translation((0, 0.15, 0.305)) @ Matrix.Rotation(math.radians(-14), 4, 'X'))
    m.sphere((0, 0, 0), 0.13, 22, 6, s=(1.0, 0.62, 0.09))                               # visor
    m.pop()
    m.mat("ch_brass")
    m.sphere((0, 0.195, 0.39), 0.035, 12, 8, s=(1, 0.35, 1))
    m.mat("ch_red")
    m.sphere((0, 0.207, 0.39), 0.016, 8, 6, s=(1, 0.3, 1))
    return m.obj(name, smooth_angle=40)


# Daigo's limb segments (pivot at the top joint, hanging down -Z, forward +Y)
DAIGO_UARM, DAIGO_FARM, DAIGO_THIGH, DAIGO_SHIN = 0.28, 0.3, 0.46, 0.49


def daigo_uarm(name="daigo_uarm"):
    """Shoulder pivot at the origin down to the elbow: puffed sleeve top, red armband."""
    chaser_mats()
    m = E.Mesher(name)
    m.mat("ch_navy")
    m.sphere((0, 0, -0.03), 0.105, 16, 10)                                               # shoulder cap
    m.cyl((0, 0, -DAIGO_UARM / 2), r=0.09, h=DAIGO_UARM, r2=0.084, seg=16)
    m.mat("ch_red")
    m.cyl((0, 0, -0.13), r=0.095, h=0.08, seg=16)                                        # armband
    return m.obj(name, smooth_angle=40)


def daigo_farm(name="daigo_farm"):
    """Elbow pivot at the origin down to a clenched white-gloved fist (thumb on the +Y side, knuckles at the end)."""
    chaser_mats()
    m = E.Mesher(name)
    m.mat("ch_navy")
    m.sphere((0, 0, 0), 0.086, 14, 8)                                                    # elbow
    m.cyl((0, 0, -0.11), r=0.084, h=0.22, r2=0.074, seg=16)
    m.mat("ch_brass")
    for z in (-0.19, -0.215):
        m.cyl((0, 0, z), r=0.079, h=0.014, seg=16)                                       # cuff rings
    m.mat("ch_white")
    m.cyl((0, 0, -0.235), r=0.062, h=0.04, seg=14)                                       # glove cuff
    m.rbox((0, 0.0, -0.3), (0.115, 0.125, 0.12), r=0.045, seg=3)                       # fist
    for k in (-1, 0, 1):
        m.sphere((k * 0.032, -0.012, -0.355), 0.022, 8, 6, s=(1, 1.2, 0.8))            # knuckles
    m.sphere((0.0, 0.07, -0.285), 0.028, 10, 6, s=(1.5, 0.8, 1.0))                     # thumb across the front
    return m.obj(name, smooth_angle=40)


def daigo_thigh(name="daigo_thigh"):
    """Hip pivot at the origin down to the knee: full trousers with the gold side stripe."""
    chaser_mats()
    m = E.Mesher(name)
    m.mat("ch_navy")
    m.sphere((0, 0, 0.0), 0.13, 16, 10, s=(1, 1, 0.8))
    m.cyl((0, 0, -DAIGO_THIGH / 2), r=0.128, h=DAIGO_THIGH, r2=0.104, seg=18)
    m.mat("ch_brass")
    for sx in (-1, 1):
        m.box((sx * 0.121, 0, -0.22), (0.012, 0.03, 0.4), smooth=False)                  # side stripes
    return m.obj(name, smooth_angle=40)


def daigo_shin(name="daigo_shin"):
    """Knee pivot at the origin down to the sole at z -0.49: knee, trouser leg, hem, polished shoe toward +Y."""
    chaser_mats()
    m = E.Mesher(name)
    m.mat("ch_navy")
    m.sphere((0, 0, 0), 0.106, 16, 10)                                                    # knee
    m.cyl((0, 0, -0.2), r=0.102, h=0.4, r2=0.09, seg=18)
    m.mat("ch_brass")
    for sx in (-1, 1):
        m.box((sx * 0.097, 0, -0.2), (0.012, 0.03, 0.36), smooth=False)
    m.mat("ch_navy_dark")
    m.lathe([(0.092, -0.4), (0.097, -0.385), (0.093, -0.37)], seg=18)                   # trouser hem
    m.mat("ch_shoe")
    m.sphere((0, 0.07, -0.437), 0.095, 16, 8, s=(0.95, 1.65, 0.6))                      # shoe
    m.box((0, -0.04, -0.467), (0.15, 0.08, 0.046), smooth=False)                         # heel
    m.mat("ch_sole")
    m.sphere((0, 0.07, -0.47), 0.092, 16, 4, s=(0.97, 1.66, 0.22))                      # sole (shows on the kick)
    return m.obj(name, smooth_angle=40)


def kuro_body(name="kuro_body"):
    """Shiba body centred at the origin, nose toward +Y, stretched for the gallop: black-and-tan coat, cream chest and
    belly, tan 'trousers' on the haunches and a cream underside to the curled tail (what the player sees from
    behind), red collar with a bell."""
    chaser_mats()
    m = E.Mesher(name)
    m.mat("ch_shiba_dark")
    m.sphere((0, 0, 0.02), 0.19, 20, 12, s=(0.95, 2.0, 0.92))
    m.mat("ch_cream")
    m.sphere((0, 0.2, -0.05), 0.15, 16, 10, s=(0.88, 1.2, 1.0))                         # chest
    m.sphere((0, 0.0, -0.08), 0.15, 16, 10, s=(0.8, 1.7, 0.55))                         # belly
    m.mat("ch_shiba")
    for sx in (-1, 1):
        m.sphere((sx * 0.1, -0.26, -0.03), 0.1, 14, 8, s=(0.7, 1.0, 1.1))              # tan haunches
        m.sphere((sx * 0.11, 0.22, 0.0), 0.07, 12, 8, s=(0.6, 1.0, 1.2))               # tan shoulders
    # curled tail over the back: dark on top, cream underneath
    m.mat("ch_shiba_dark")
    m.torus((0, -0.33, 0.2), R=0.085, r=0.05, seg=20, sides=8, axis='Y')
    m.mat("ch_cream")
    m.torus((0, -0.355, 0.2), R=0.085, r=0.032, seg=20, sides=8, axis='Y', arc=200)
    m.sphere((0.0, -0.36, 0.3), 0.04, 10, 6)
    m.sphere((0, -0.4, 0.03), 0.06, 10, 6, s=(1.3, 0.6, 1.0))                           # cream rump patch
    m.mat("ch_shiba_dark")
    for k in range(5):                                                                  # hackles up: swept fur tufts
        y = 0.3 - k * 0.07
        z = 0.02 + 0.19 * 0.92 * math.sqrt(max(0.0, 1 - (y / (0.19 * 2.0)) ** 2))
        for sx in (-1, 1):
            m.push(Matrix.Translation((sx * 0.035, y - sx * 0.018, z - 0.03)) @ Matrix.Rotation(math.radians(-42), 4, 'X')
                   @ Matrix.Rotation(math.radians(sx * 20), 4, 'Y') @ Matrix.Diagonal((1.4, 0.7, 1.0, 1.0)))
            m.cyl((0, 0, 0.04), r=0.04, h=0.09 - k * 0.008, r2=0.0, seg=6)
            m.pop()
    m.mat("ch_red")
    m.torus((0, 0.34, 0.08), R=0.11, r=0.025, seg=20, sides=6, axis='Y')
    m.mat("ch_brass")
    m.sphere((0, 0.39, -0.03), 0.035, 12, 8)
    return m.obj(name, smooth_angle=40)


def kuro_head(name="kuro_head"):
    """Neck at the origin, muzzle toward +Y, snarling: ears up and pricked forward, a dark furrow over narrowed eyes
    under angled tan brows, the muzzle wrinkled and the lips pulled back off big white fangs, the jaw dropped open on
    a pink tongue."""
    chaser_mats()
    m = E.Mesher(name)
    m.mat("ch_shiba_dark")
    m.sphere((0, 0.03, 0.08), 0.15, 20, 12, s=(1.05, 1.0, 0.92))
    m.mat("ch_cream")
    m.sphere((0, 0.17, 0.06), 0.085, 16, 10, s=(0.9, 1.3, 0.58))                        # upper muzzle
    m.sphere((0, 0.07, -0.02), 0.1, 16, 10, s=(1.1, 0.9, 0.55))                         # cheeks and throat
    m.mat("ch_mouth")
    m.sphere((0, 0.19, 0.005), 0.07, 14, 8, s=(0.78, 1.1, 0.62))                        # open mouth
    # dropped lower jaw with its fangs and the tongue
    m.push(Matrix.Translation((0, 0.12, -0.03)) @ Matrix.Rotation(math.radians(30), 4, 'X'))
    m.mat("ch_cream")
    m.sphere((0, 0.065, -0.005), 0.062, 14, 8, s=(0.78, 1.3, 0.34))
    m.mat("ch_tongue")
    m.sphere((0, 0.075, 0.016), 0.036, 12, 6, s=(0.9, 1.4, 0.3))
    m.mat("ch_white")
    for sx in (-1, 1):
        m.cyl((sx * 0.032, 0.115, 0.028), r=0.013, h=0.04, r2=0.0, seg=6)              # lower fangs
    m.pop()
    m.mat("ch_white")
    for sx in (-1, 1):
        m.cyl((sx * 0.036, 0.215, 0.0), r=0.015, h=0.055, r2=0.0, seg=6)                # upper fangs
        m.sphere((sx * 0.018, 0.238, 0.02), 0.01, 6, 4)                                   # front teeth
    m.mat("ch_lip")
    m.tube([V((-0.06, 0.17, 0.02)), V((-0.04, 0.22, 0.03)), V((0, 0.24, 0.035)), V((0.04, 0.22, 0.03)),
            V((0.06, 0.17, 0.02))], r=0.007, seg=6)                                       # curled-back lip
    m.mat("ch_ink")
    m.sphere((0, 0.255, 0.075), 0.027, 10, 6)                                             # nose
    for k in range(3):
        y, z = 0.215 - k * 0.022, 0.1 - k * 0.002
        m.tube([V((-0.032, y, z - 0.004)), V((0, y + 0.006, z)), V((0.032, y, z - 0.004))], r=0.004, seg=5)  # wrinkles
    for sx in (-1, 1):
        m.mat("ch_ink")
        m.push(Matrix.Translation((sx * 0.064, 0.163, 0.12)) @ Matrix.Rotation(math.radians(sx * 20), 4, 'Y'))
        m.sphere((0, 0, 0), 0.03, 12, 8, s=(1.1, 0.5, 0.55))                              # narrowed eyes
        m.pop()
        m.mat("ch_white")
        m.sphere((sx * 0.058, 0.178, 0.126), 0.007, 8, 6)                                  # glint
        m.mat("ch_shiba")
        m.push(Matrix.Translation((sx * 0.056, 0.152, 0.152)) @ Matrix.Rotation(math.radians(sx * 32), 4, 'Y'))
        m.sphere((0, 0, 0), 0.024, 8, 6, s=(1.7, 0.55, 0.5))                              # tan brows, slanted down
        m.pop()
        # ears up and pricked forward
        m.push(Matrix.Translation((sx * 0.08, 0.0, 0.19)) @ Matrix.Rotation(math.radians(sx * 14), 4, 'Y')
               @ Matrix.Rotation(math.radians(18), 4, 'X'))
        m.mat("ch_shiba_dark")
        m.cyl((0, 0, 0.055), r=0.058, h=0.13, r2=0.0, seg=4)
        m.mat("ch_cream")
        m.cyl((0, 0.014, 0.05), r=0.032, h=0.085, r2=0.0, seg=4)
        m.pop()
    m.mat("ch_ink")
    m.tube([V((-0.024, 0.148, 0.155)), V((0, 0.156, 0.137)), V((0.024, 0.148, 0.155))], r=0.006, seg=5)  # furrow
    return m.obj(name, smooth_angle=40)


KURO_ULEG, KURO_LLEG = 0.17, 0.18


def kuro_uleg(name="kuro_uleg"):
    """Shoulder or hip pivot at the origin down to the elbow or hock."""
    chaser_mats()
    m = E.Mesher(name)
    m.mat("ch_shiba_dark")
    m.sphere((0, 0, -0.01), 0.072, 12, 8, s=(1, 1.15, 1.2))
    m.cyl((0, 0, -KURO_ULEG / 2), r=0.06, h=KURO_ULEG, r2=0.048, seg=12)
    m.mat("ch_shiba")
    m.cyl((0, -0.022, -0.11), r=0.04, h=0.1, r2=0.036, seg=12)                          # tan stripe down the back
    return m.obj(name, smooth_angle=40)


def kuro_lleg(name="kuro_lleg"):
    """Elbow or hock pivot at the origin down to the paw sole at z -0.18: a tan leg with the cream (urajiro) down
    its front and a cream paw, so it reads as shiba markings rather than socks."""
    chaser_mats()
    m = E.Mesher(name)
    m.mat("ch_shiba")
    m.sphere((0, 0, 0), 0.05, 10, 6)
    m.cyl((0, 0, -0.065), r=0.046, h=0.13, r2=0.04, seg=12)
    m.mat("ch_cream")
    m.cyl((0, 0.014, -0.085), r=0.036, h=0.1, r2=0.034, seg=12)                         # cream down the front
    m.sphere((0, 0.022, -0.155), 0.05, 12, 6, s=(1, 1.35, 0.55))                        # paw
    return m.obj(name, smooth_angle=40)


CHASERS = [("daigo_torso", daigo_torso), ("daigo_head", daigo_head), ("daigo_uarm", daigo_uarm),
           ("daigo_farm", daigo_farm), ("daigo_thigh", daigo_thigh), ("daigo_shin", daigo_shin),
           ("kuro_body", kuro_body), ("kuro_head", kuro_head), ("kuro_uleg", kuro_uleg), ("kuro_lleg", kuro_lleg)]


# ----------------------------------------------------------------------------- the chase run
# The same numbers drive SakuraWorld.chasers in the game: angles in degrees, + swings a limb forward (+Y), knee and
# elbow flex measured from straight. The hip height is solved so the lower shoe sits on the ground.

def _drop(lt, theta, k, pts):
    """Height of the hip above the lowest of pts (y, z in the lower segment) for a two-segment limb."""
    t, ph = math.radians(theta), math.radians(theta - k)
    return lt * math.cos(t) - min(y * math.sin(ph) + z * math.cos(ph) for y, z in pts)


DAIGO_SOLE = ((0.22, -0.47), (-0.08, -0.49), (0.07, -0.49))
KURO_PAW = ((0.06, -0.175), (-0.02, -0.18))


# knee flex through the stride (phase in degrees, flex): high heel kick in mid-swing, knee drive, a reach that
# straightens just before the foot lands, a firm stance, and the push off the toe
DAIGO_KNEE = ((0, 116), (45, 102), (90, 80), (125, 36), (155, 15), (205, 15), (250, 20), (270, 26), (300, 62),
              (330, 102), (360, 116))


def keyed(deg, keys):
    """Cosine-eased lookup in a periodic (phase, value) table."""
    d = deg % 360.0
    for (a, va), (b, vb) in zip(keys, keys[1:]):
        if d <= b:
            t = (d - a) / (b - a)
            return va + (vb - va) * (0.5 - 0.5 * math.cos(math.pi * t))
    return keys[-1][1]


def daigo_pose(p, grab=False):
    """Sprint pose at cycle phase p (radians): lean, twist, head, (thigh, knee) and (upper arm, elbow) per side."""
    legs, arms = [], []
    for side in (0, 1):
        q = p + side * math.pi
        if grab:
            legs.append((22.0, 34.0))
            arms.append((84.0, 12.0))
            continue
        legs.append((18 + 48 * math.sin(q), keyed(math.degrees(q), DAIGO_KNEE)))
        a = -math.sin(q)
        arms.append((10 + 56 * a, 92 + 22 * a))
    lean = 8.0 if grab else 27 + 3 * math.cos(2 * p)
    twist = 0.0 if grab else -10 * math.sin(p)
    head = 10.0 if grab else 20 + 3 * math.cos(2 * p)
    hip = max(_drop(DAIGO_THIGH, t, k, DAIGO_SOLE) for t, k in legs)
    return dict(legs=legs, arms=arms, lean=lean, twist=twist, head=head, hip=hip)


# Kuro's legs: (x, y) on the body, phase offset
KURO_LEGS = ((-0.1, 0.25, 0.0), (0.1, 0.25, 0.35), (-0.1, -0.25, 2.5), (0.1, -0.25, 2.85))
KURO_HIP_Z = -0.06


def kuro_pose(q):
    """Gallop at phase q: body pitch, per-leg (upper, flex), and the body height that puts the lowest paw down."""
    pitch = 7 * math.sin(q + 0.6)
    legs = []
    for (lx, ly, off) in KURO_LEGS:
        u = 38 * math.sin(q + off)
        legs.append((u, 8 + 72 * max(0.0, math.cos(q + off + 0.4)) ** 2))
    pr = math.radians(pitch)
    h = 0.0
    for (lx, ly, off), (u, k) in zip(KURO_LEGS, legs):
        # the pivot drops below the body centre by the body pitch
        pz = ly * math.sin(pr) + KURO_HIP_Z * math.cos(pr)
        h = max(h, _drop(KURO_ULEG, u, k, KURO_PAW) - pz)
    return dict(pitch=pitch, legs=legs, y=h)


def _assemble_chasers(x0=0.0, phase=0.8, grab=False, kuro=True, kuro_dx=1.0, kuro_dy=0.6):
    """Poses the parts the way SakuraWorld.chasers does in the game, for the design renders and the run clip."""
    obs = []
    P = daigo_pose(phase, grab)
    R = lambda deg, ax: Matrix.Rotation(math.radians(deg), 4, ax)
    T = Matrix.Translation

    def put(fn, mw):
        ob = fn()
        ob.matrix_world = mw
        obs.append(ob)
        return mw

    root = T((x0, 0, P["hip"]))
    for side, sx in ((0, -1), (1, 1)):
        th, kn = P["legs"][side]
        hipm = put(daigo_thigh, root @ T((sx * DAIGO_HIP_X, 0, 0)) @ R(th, 'X'))
        put(daigo_shin, hipm @ T((0, 0, -DAIGO_THIGH)) @ R(-kn, 'X'))
    torso = root @ R(P["twist"], 'Z') @ R(-P["lean"], 'X')
    put(daigo_torso, torso)
    put(daigo_head, torso @ T((0, 0.02, DAIGO_NECK)) @ R(P["head"], 'X'))
    for side, sx in ((0, -1), (1, 1)):
        ua, el = P["arms"][side]
        sh = put(daigo_uarm, torso @ T((sx * DAIGO_SHOULDER[0], 0, DAIGO_SHOULDER[1])) @ R(ua, 'X') @ R(-sx * 8, 'Y'))
        put(daigo_farm, sh @ T((0, 0, -DAIGO_UARM)) @ R(el, 'X'))
    if kuro:
        K = kuro_pose(phase * 16 / 11)
        body = T((x0 + kuro_dx, kuro_dy, K["y"])) @ R(K["pitch"], 'X')
        put(kuro_body, body)
        put(kuro_head, body @ T((0, 0.36, 0.14)) @ R(-K["pitch"] * 0.6, 'X'))
        for (lx, ly, off), (u, k) in zip(KURO_LEGS, K["legs"]):
            up = put(kuro_uleg, body @ T((lx, ly, KURO_HIP_Z)) @ R(u, 'X'))
            put(kuro_lleg, up @ T((0, 0, -KURO_ULEG)) @ R(-k, 'X'))
    return obs


def design_chasers():
    """Front, side, back (the player's view), three-quarter, head close-ups, Kuro, and the grab."""
    import studio
    E.reset()
    studio.stage(res=(1200, 900))
    for o in _assemble_chasers(-0.5, phase=1.75):
        E.add_outline(o, 0.008)
    studio.shoot("chasers_front", target=(0.0, 0.3, 1.0), dist=5.0, yaw=158, pitch=6, lens=40)
    studio.shoot("chasers_side", target=(0.0, 0.3, 1.0), dist=5.0, yaw=90, pitch=4, lens=40)
    studio.shoot("chasers_three_quarter", target=(0.0, 0.3, 1.0), dist=5.0, yaw=128, pitch=10, lens=40)
    studio.shoot("chasers_player_view", target=(0.0, 1.6, 0.9), dist=7.0, yaw=0, pitch=22, lens=35)
    studio.shoot("chasers_head", target=(-0.5, 0.45, 1.7), dist=1.5, yaw=162, pitch=4, lens=50)
    studio.shoot("chasers_kuro", target=(0.5, 0.75, 0.42), dist=1.9, yaw=140, pitch=8, lens=50)
    E.reset()
    studio.stage(res=(1200, 900))
    for o in _assemble_chasers(0.0, grab=True, kuro=False):
        E.add_outline(o, 0.008)
    studio.shoot("chasers_grab", target=(0.0, 0.3, 1.2), dist=4.0, yaw=150, pitch=6, lens=40)


def chase_clip(frames=18, views="side,three_quarter,back"):
    """One stride cycle of the chase run per view, frame by frame -> build/clips/chase_<view>_NN.png (ffmpeg makes
    the clip). 18 frames at 30 fps is the game's stride rate."""
    import os, studio
    cams = {"side": dict(target=(0.0, 0.7, 0.95), dist=4.6, yaw=270, pitch=4, lens=40),
            "three_quarter": dict(target=(0.0, 0.7, 1.0), dist=4.6, yaw=215, pitch=8, lens=40),
            "back": dict(target=(0.0, 1.0, 1.0), dist=5.0, yaw=4, pitch=18, lens=35)}
    out = os.path.join(E.ROOT, "build", "clips")
    os.makedirs(out, exist_ok=True)
    for view in views.split(","):
        for i in range(frames):
            E.reset()
            studio.stage(res=(960, 720))
            bpy.context.scene.eevee.taa_render_samples = 24
            # Kuro a stride further ahead than in the game, so the side views show both of them whole
            for o in _assemble_chasers(-0.5, phase=2 * math.pi * i / frames, kuro_dy=1.5):
                E.add_outline(o, 0.008)
            c = cams[view]
            studio.aim_sun(c["yaw"])
            t = Vector(c["target"])
            y, p = math.radians(c["yaw"]), math.radians(c["pitch"])
            E.camera(t + Vector((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p))) * c["dist"], t,
                     lens=c["lens"])
            E.render(os.path.join(out, "chase_%s_%02d.png" % (view, i)))


def export_chasers():
    for nm, fn in CHASERS:
        E.reset()
        E.export_erm(fn(), nm)


# ----------------------------------------------------------------------------- run effects

def fx_sprites(n=64):
    """RGBA sprites for the run effects, white-ish so the particle colour tints them. Listed in _extra.txt."""
    import os
    import texgen as T
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float64) + 0.5
    c = n / 2
    dx, dy = (xs - c) / c, (ys - c) / c
    r = np.sqrt(dx * dx + dy * dy)
    ang = np.arctan2(dy, dx)

    def save(name, a, col=(1, 1, 1), hl=None):
        img = np.zeros((n, n, 4))
        img[..., :3] = np.array(col)[None, None, :]
        if hl is not None:
            img[..., :3] = img[..., :3] * (1 - hl[..., None]) + np.array((1, 1, 1))[None, None, :] * hl[..., None]
        img[..., 3] = np.clip(a, 0, 1)
        T.write_png(name, img)

    # anime speed line: long thin streak, fat in the middle, sharp ends
    save("fx_speed", np.clip(1 - np.abs(dy) / (0.16 * (1 - np.abs(dx)) ** 0.7 + 1e-3), 0, 1) * (np.abs(dx) < 0.98))
    # sakura petal: notched teardrop with a pale centre
    px, py = dx, dy * 1.25
    body = (px / 0.55) ** 2 + ((py + 0.1) / 0.8) ** 2 < 1.0
    notch = ((px / 0.14) ** 2 + ((py - 0.75) / 0.25) ** 2) < 1.0
    petal = body & ~notch
    centre = np.exp(-((px / 0.25) ** 2 + ((py + 0.4) / 0.35) ** 2))
    save("fx_petal", petal.astype(float), (1.0, 0.72, 0.84), np.clip(centre * 0.8, 0, 1))
    # dust puff: three overlapping soft circles with a cel edge
    puff = np.zeros_like(r)
    for (cx, cy, rr) in ((-0.3, 0.15, 0.45), (0.25, 0.2, 0.5), (0.0, -0.2, 0.55)):
        puff = np.maximum(puff, 1 - T.smooth(np.sqrt((dx - cx) ** 2 + (dy - cy) ** 2), rr - 0.08, rr))
    shade = np.clip((dy + 0.2) * 1.5, 0, 1)
    save("fx_puff", puff * 0.9, (1, 1, 1), None)
    # wind ring (Tobi Boots jump, landing)
    save("fx_ring", np.exp(-((r - 0.78) / 0.07) ** 2) * (0.7 + 0.3 * np.cos(ang * 8) ** 2))
    # soft glow
    save("fx_glow", np.exp(-(r / 0.5) ** 2))
    # four-point anime star
    star = np.exp(-(r / (0.06 + 0.9 * np.abs(np.cos(2 * ang)) ** 24)) ** 2)
    save("fx_star", np.clip(star + np.exp(-(r / 0.12) ** 2), 0, 1))
    # impact frame burst: radial spikes
    spikes = (np.cos(ang * 14 + np.sin(ang * 5) * 1.5) > 0.55) & (r > 0.25)
    save("fx_impact", spikes.astype(float) * np.clip(1.2 - r, 0, 1) * 1.5)
    path = os.path.join(E.OUT_TEX, "_extra.txt")
    have = open(path).read().split() if os.path.exists(path) else []
    with open(path, "a") as f:
        for nm in ("fx_speed", "fx_petal", "fx_puff", "fx_ring", "fx_glow", "fx_star", "fx_impact"):
            if nm not in have:
                f.write(nm + "\n")


def fx_sheet():
    """Contact sheet of the effect sprites on a mid-grey background -> renders/design/fx_sheet.png."""
    import os, struct, zlib
    fx_sprites(128)
    names = ("fx_speed", "fx_petal", "fx_puff", "fx_ring", "fx_glow", "fx_star", "fx_impact")
    cell = 128
    sheet = np.ones((cell, len(names) * cell, 3)) * np.array((0.42, 0.5, 0.72))
    for i, nm in enumerate(names):
        img = bpy.data.images.load(os.path.join(E.OUT_TEX, nm + ".png"))
        px = np.array(img.pixels[:]).reshape(cell, cell, 4)[::-1]
        a = px[..., 3:4]
        sheet[:, i * cell:(i + 1) * cell] = sheet[:, i * cell:(i + 1) * cell] * (1 - a) + px[..., :3] * a
    import texgen as T
    T.write_png("_fx_sheet", sheet)
    import shutil
    shutil.copy(os.path.join(E.OUT_TEX, "_fx_sheet.png"), os.path.join(E.OUT_RENDERS, "design", "fx_sheet.png"))
    os.remove(os.path.join(E.OUT_TEX, "_fx_sheet.png"))


# ----------------------------------------------------------------------------- roadside density

def street_mats():
    M = E.mat
    M("st_orange", 0xF08A2E, spec=0.3, rim=0.3, soft=0.08, outline=0.8)
    M("st_mirror", 0xDDE8F2, spec=1.0, rim=0.5, soft=0.04, flags=E.F_GLASS, outline=0.6)
    M("st_sign_blue", 0x2F6BDA, soft=0.12, rim=0.2, outline=0.6)
    M("st_sign_red", 0xD8403A, soft=0.12, rim=0.2, outline=0.6)
    M("st_white", 0xF6F4EE, soft=0.12, rim=0.2, outline=0.6)
    M("st_green_net", 0x3E9A5A, soft=0.15, rim=0.2, outline=0.6)
    M("st_cabinet", 0xC9CCC4, spec=0.3, rim=0.25, soft=0.1, outline=0.8)
    M("st_wood", 0xB07A4E, "t_wood", soft=0.15, rim=0.2, outline=0.8)
    M("st_stone", 0xB9B6AE, "t_concrete", soft=0.2, rim=0.2, outline=0.8)
    M("st_red_bib", 0xD8403A, soft=0.15, rim=0.2, outline=0.5)
    M("st_paper", 0xFFF1D6, emis=0.4, rim=0.2, soft=0.1, flags=E.F_NIGHT, outline=0.5)
    M("st_planter", 0x8C7A6A, soft=0.15, rim=0.2, outline=0.8)
    M("st_flower_p", 0xF2A6C8, soft=0.3, rim=0.3, outline=0.4)
    M("st_flower_y", 0xF6D35A, soft=0.3, rim=0.3, outline=0.4)


def _traffic_mirror(m, x, y):
    m.mat("st_orange")
    m.cyl((x, y, city.GROUND + 1.4), r=0.04, h=2.8, seg=10)
    m.push(Matrix.Translation((x, y, city.GROUND + 2.75)) @ Matrix.Rotation(math.radians(80), 4, 'Z') @ Matrix.Rotation(math.radians(90), 4, 'X'))
    m.mat("st_orange")
    m.cyl((0, 0, 0), r=0.36, h=0.06, seg=24)
    m.mat("st_mirror")
    m.sphere((0, 0, -0.035), 0.32, 20, 8, s=(1, 1, 0.12))
    m.pop()


def _road_sign(m, x, y, kind):
    m.mat("rail_metal")
    m.cyl((x, y, city.GROUND + 1.3), r=0.035, h=2.6, seg=8)
    m.push(Matrix.Translation((x, y, city.GROUND + 2.45)) @ Matrix.Rotation(math.radians(90), 4, 'Z') @ Matrix.Rotation(math.radians(90), 4, 'X'))
    if kind == 0:                     # blue round "pedestrians" sign
        m.mat("st_white"); m.cyl((0, 0, 0), r=0.32, h=0.03, seg=24)
        m.mat("st_sign_blue"); m.cyl((0, 0, 0.018), r=0.29, h=0.01, seg=24)
        m.mat("st_white"); m.box((0, 0.02, 0.026), (0.06, 0.26, 0.005), smooth=False)
    elif kind == 1:                   # red inverted triangle 止まれ
        m.mat("st_sign_red")
        m.extrude([(0, -0.34), (0.38, 0.3), (-0.38, 0.3)], 0.03)
        m.mat("st_white")
        m.push(Matrix.Translation((0, 0.08, 0.02)))
        m.text("止まれ", size=0.13, depth=0.004, font=E.FONT_JP)
        m.pop()
    else:                             # street-name plate
        m.mat("st_sign_blue"); m.box((0, 0, 0), (0.9, 0.26, 0.03), smooth=False)
        m.mat("st_white")
        m.push(Matrix.Translation((0, 0, 0.02)))
        m.text("桜丘二丁目", size=0.12, depth=0.004, font=E.FONT_JP)
        m.pop()
    m.pop()


def _garbage_station(m, x, y):
    m.mat("st_green_net")
    m.rbox((x, y, city.GROUND + 0.45), (1.0, 1.6, 0.9), r=0.05, seg=1)
    m.mat("rail_metal")
    m.box((x - 0.51, y, city.GROUND + 0.45), (0.02, 1.6, 0.92), smooth=False)
    m.mat("st_white")
    m.box((x - 0.53, y, city.GROUND + 0.7), (0.01, 0.6, 0.3), smooth=False)


def _cabinet(m, x, y):
    m.mat("st_cabinet")
    m.rbox((x, y, city.GROUND + 0.7), (0.55, 0.8, 1.4), r=0.03, seg=1)
    m.mat("st_sign_red")
    m.box((x - 0.28, y, city.GROUND + 1.15), (0.01, 0.2, 0.08), smooth=False)


def _hydrant(m, x, y):
    m.mat("st_sign_red")
    m.cyl((x, y, city.GROUND + 0.35), r=0.11, h=0.7, seg=14)
    m.sphere((x, y, city.GROUND + 0.72), 0.12, 14, 8, s=(1, 1, 0.6))
    m.cyl((x, y, city.GROUND + 0.45), r=0.05, h=0.34, seg=10, axis='Y')


def _bench(m, x, y):
    m.mat("st_wood")
    m.box((x, y, city.GROUND + 0.45), (0.45, 1.6, 0.06), smooth=False)
    m.box((x + 0.2, y, city.GROUND + 0.75), (0.05, 1.6, 0.3), smooth=False)
    m.mat("rail_metal")
    for dy in (-0.65, 0.65):
        m.box((x, y + dy, city.GROUND + 0.22), (0.4, 0.05, 0.45), smooth=False)


def _jizo(m, x, y):
    """Little roadside jizō statue with a red bib under a tiny wooden roof."""
    m.mat("st_stone")
    m.box((x, y, city.GROUND + 0.15), (0.5, 0.5, 0.3), smooth=False)
    m.cyl((x, y, city.GROUND + 0.55), r=0.13, h=0.5, r2=0.11, seg=12)
    m.sphere((x, y, city.GROUND + 0.88), 0.12, 12, 8)
    m.mat("st_red_bib")
    m.cyl((x, y, city.GROUND + 0.7), r=0.14, h=0.14, r2=0.1, seg=12)
    m.mat("st_wood")
    for dx in (-0.22, 0.22):
        m.box((x + dx, y - 0.22, city.GROUND + 0.6), (0.05, 0.05, 1.2), smooth=False)
        m.box((x + dx, y + 0.22, city.GROUND + 0.6), (0.05, 0.05, 1.2), smooth=False)
    m.mat("roof_ibushi")
    m.push(Matrix.Translation((x, y, city.GROUND + 1.25)))
    m.poly([(-0.35, -0.4, 0), (0.35, -0.4, 0), (0.0, -0.4, 0.22)])
    m.poly([(0.0, 0.4, 0.22), (0.35, 0.4, 0), (-0.35, 0.4, 0)])
    m.poly([(-0.35, -0.4, 0), (0.0, -0.4, 0.22), (0.0, 0.4, 0.22), (-0.35, 0.4, 0)])
    m.poly([(0.0, -0.4, 0.22), (0.35, -0.4, 0), (0.35, 0.4, 0), (0.0, 0.4, 0.22)])
    m.pop()


def _flower_planter(m, x, y, L=2.0, rnd=None):
    rnd = rnd or random.Random(1)
    m.mat("st_planter")
    m.box((x, y, city.GROUND + 0.2), (0.5, L, 0.4), smooth=False)
    for k in range(int(L / 0.22)):
        m.mat("bush", uvscale=0.6)
        yy = y - L / 2 + 0.12 + k * 0.22
        m.ico((x + rnd.uniform(-0.1, 0.1), yy, city.GROUND + 0.48), r=0.16, sub=1, s=(1, 1, 0.8))
        if rnd.random() < 0.7:
            m.mat("st_flower_p" if rnd.random() < 0.6 else "st_flower_y")
            m.ico((x + rnd.uniform(-0.12, 0.12), yy + rnd.uniform(-0.05, 0.05), city.GROUND + 0.62), r=0.05, sub=1)


def _lantern(m, x, y):
    """Paper shop lantern on a bracket (lights up at dusk)."""
    m.mat("st_wood")
    m.box((x, y, city.GROUND + 1.25), (0.08, 0.08, 2.5), smooth=False)
    m.box((x - 0.25, y, city.GROUND + 2.4), (0.5, 0.06, 0.06), smooth=False)
    m.mat("st_paper")
    m.sphere((x - 0.45, y, city.GROUND + 2.05), 1.0, 14, 8, s=(0.17, 0.17, 0.26))
    m.mat("st_red_bib")
    m.cyl((x - 0.45, y, city.GROUND + 2.3), r=0.1, h=0.04, seg=12)
    m.cyl((x - 0.45, y, city.GROUND + 1.8), r=0.1, h=0.04, seg=12)


STREET_KINDS = 4


def street(variant, lod=0):
    """10 m of roadside clutter between the road (x 11) and the house fronts, built for the right side.
    Each variant mixes vending machines, bikes, pots, bushes, signs, mirrors, a jizō, a garbage station."""
    street_mats()
    rnd = random.Random(100 + variant)
    m = E.Mesher("sl_street_%d" % variant)
    # kerb + pavement strip
    m.mat("curb", uvscale=1.0)
    m.box((11.6, 5.0, city.GROUND + 0.02), (1.2, 10.0, 0.08), smooth=False)
    g = city.GROUND + 0.06
    layouts = {
        0: [("vend", 1.2), ("vend_b", 2.25), ("bike", 3.6), ("bike", 4.3), ("pot", 5.3), ("mirror", 6.5), ("planter", 8.4)],
        1: [("garbage", 1.4), ("sign0", 3.0), ("bush", 4.2), ("bush", 5.0), ("jizo", 6.6), ("lantern", 8.0), ("pot", 9.2)],
        2: [("bench", 1.5), ("hydrant", 3.0), ("cabinet", 4.0), ("sign2", 5.4), ("bike", 6.6), ("pot", 7.6), ("pot", 8.1), ("mirror", 9.3)],
        3: [("planter", 1.8), ("sign1", 3.4), ("vend", 4.6), ("pot", 5.7), ("bush", 6.8), ("garbage", 8.6)],
    }
    for kind, y in layouts[variant % STREET_KINDS]:
        x = 12.2 + rnd.uniform(-0.1, 0.15)
        if kind == "vend":
            m.push(Matrix.Translation((x + 0.3, y, g)) @ Matrix.Rotation(math.radians(90), 4, 'Z'))
            B.vending_machine(m, (0, 0, 0), lod=lod)
            m.pop()
        elif kind == "vend_b":
            m.push(Matrix.Translation((x + 0.3, y, g)) @ Matrix.Rotation(math.radians(90), 4, 'Z'))
            B.vending_machine(m, (0, 0, 0), face="vend_face_b", body="vend_blue", lod=lod)
            m.pop()
        elif kind == "bike":
            B.bicycle(m, (x, y, g), yaw=rnd.uniform(-20, 20), color=rnd.choice((0x3AA3C9, 0xE8473C, 0xF6F3EA, 0x2BA35A)))
        elif kind == "pot":
            B.plant_pot(m, (x, y, g), r=rnd.uniform(0.16, 0.24), lod=lod)
        elif kind == "bush":
            B.bush(m, (x + 0.3, y, g), r=rnd.uniform(0.45, 0.65), lod=lod, rnd=rnd)
        elif kind == "mirror":
            _traffic_mirror(m, 11.3, y)
        elif kind.startswith("sign"):
            _road_sign(m, 11.3, y, int(kind[-1]))
        elif kind == "garbage":
            _garbage_station(m, x + 0.2, y)
        elif kind == "cabinet":
            _cabinet(m, x, y)
        elif kind == "hydrant":
            _hydrant(m, 11.4, y)
        elif kind == "bench":
            _bench(m, x, y)
        elif kind == "jizo":
            _jizo(m, x + 0.2, y)
        elif kind == "planter":
            _flower_planter(m, x, y, 2.4, rnd)
        elif kind == "lantern":
            _lantern(m, x + 0.4, y)
    return m.obj("sl_street_%d" % variant + ("" if lod == 0 else "@1"), smooth_angle=35)


# ----------------------------------------------------------------------------- far town and hills

def far_town(variant, lod=1):
    """24 m of the town behind the front houses (x 26..60): rows of simple roofs, a few taller apartment blocks,
    rooftop water tanks, trees and a temple roof, all low-poly but in the same palette and outline style."""
    import buildings as B2
    rnd = random.Random(300 + variant)
    E.mat("far_wall_a", 0xEDE3D2, soft=0.2, rim=0.2, outline=0.8)
    E.mat("far_wall_b", 0xD7E3EE, soft=0.2, rim=0.2, outline=0.8)
    E.mat("far_wall_c", 0xF2D9CF, soft=0.2, rim=0.2, outline=0.8)
    E.mat("far_wall_d", 0xE0E9D8, soft=0.2, rim=0.2, outline=0.8)
    E.mat("far_win", 0x7E95B8, spec=0.5, soft=0.1, rim=0.1, emis=0.2, flags=E.F_NIGHT, outline=0)
    E.mat("far_tree", 0x6FA86A, "t_leaves", soft=0.3, rim=0.25, outline=0.8, flags=E.F_FOLIAGE)
    E.mat("far_tree_pink", 0xF6C6DA, "t_blossom", soft=0.3, rim=0.25, outline=0.6, flags=E.F_FOLIAGE)
    m = E.Mesher("sl_far_%d" % variant)
    walls = ("far_wall_a", "far_wall_b", "far_wall_c", "far_wall_d")
    roofs = ("roof_ibushi", "roof_navy", "roof_brick", "roof_green", "roof_choco")
    y = 0.0
    while y < 24.0:
        w = rnd.uniform(5.0, 8.0)
        if y + w > 24.0:
            break
        x = rnd.uniform(26.0, 30.0)
        d = rnd.uniform(5.5, 7.5)
        tall = rnd.random() < 0.1
        h = (rnd.uniform(8.5, 12.0) if tall else rnd.uniform(4.6, 6.0))
        m.mat(rnd.choice(walls))
        m.box((x + d / 2, y + w / 2, city.GROUND + h / 2), (d, w, h), smooth=False)
        m.mat("far_win")
        floors = int(h / 2.8)
        for f in range(floors):
            for k in range(int(w / 2.2)):
                m.box((x - 0.02, y + 1.0 + k * 2.2, city.GROUND + 1.6 + f * 2.8), (0.04, 1.1, 0.9), smooth=False)
        if tall:
            m.mat("rail_white")
            m.box((x + d / 2, y + w / 2, city.GROUND + h + 0.5), (d - 0.4, w - 0.4, 1.0), smooth=False)
            m.mat("st_cabinet")
            m.cyl((x + d * 0.7, y + w * 0.3, city.GROUND + h + 1.4), r=0.8, h=1.4, seg=12)
        else:
            m.mat(rnd.choice(roofs))
            z0 = city.GROUND + h
            m.poly([(x - 0.4, y - 0.3, z0), (x + d / 2, y - 0.3, z0 + 1.8), (x + d / 2, y + w + 0.3, z0 + 1.8), (x - 0.4, y + w + 0.3, z0)])
            m.poly([(x + d / 2, y - 0.3, z0 + 1.8), (x + d + 0.4, y - 0.3, z0), (x + d + 0.4, y + w + 0.3, z0), (x + d / 2, y + w + 0.3, z0 + 1.8)])
            m.poly([(x - 0.4, y - 0.3, z0), (x + d + 0.4, y - 0.3, z0), (x + d / 2, y - 0.3, z0 + 1.8)])
            m.poly([(x + d / 2, y + w + 0.3, z0 + 1.8), (x + d + 0.4, y + w + 0.3, z0), (x - 0.4, y + w + 0.3, z0)])
        y += w + rnd.uniform(0.6, 2.0)
    # round trees in the gaps and over the roofs, then a forest band closing the view (no bare field left)
    import greenery as G
    G.mats()
    cl = G.Clumps()
    for k in range(9):
        G.tree(m, cl, rnd.uniform(24.0, 36.0), rnd.uniform(0.5, 23.5), city.GROUND, rnd, h=rnd.uniform(5.0, 8.0),
               lod=2, pink=rnd.random() < 0.3)
    if rnd.random() < 0.5:
        m.mat(rnd.choice(walls))
        h = rnd.uniform(10.0, 16.0)
        x, yy, w = rnd.uniform(42.0, 50.0), rnd.uniform(0.0, 16.0), rnd.uniform(6.0, 9.0)
        m.box((x, yy + w / 2, city.GROUND + h / 2), (8.0, w, h), smooth=False)
        m.mat("far_win")
        for f in range(int(h / 3.0)):
            m.box((x - 4.02, yy + w / 2, city.GROUND + 2.0 + f * 3.0), (0.04, w - 1.2, 0.8), smooth=False)
    for k in range(14):
        G.tree(m, cl, rnd.uniform(38.0, 72.0), rnd.uniform(0.0, 24.0), city.GROUND, rnd, h=rnd.uniform(7.0, 12.0),
               lod=2, mat=rnd.choice(("gr_leaf", "gr_leaf_dark", "gr_leaf_dark")), pink=rnd.random() < 0.15)
    for k in range(6):
        G.bush(m, cl, rnd.uniform(30.0, 40.0), rnd.uniform(0.0, 24.0), city.GROUND, rnd, r=rnd.uniform(0.8, 1.4), lod=2)
    return cl.soften(m.obj("sl_far_%d" % variant, smooth_angle=0))


def hills():
    """Horizon: soft layered hills and a Fuji-like peak, centred on the origin, spanning y -200..200 at |x| 110..260.
    The game keeps it centred on the camera so it never runs out."""
    E.mat("hill_near", 0x8DB98A, soft=0.3, rim=0.2, outline=0.0, shadow=0x7A8EB8)
    E.mat("hill_far", 0xA9C4D8, soft=0.3, rim=0.1, outline=0.0, shadow=0x9AA6CE)
    E.mat("hill_snow", 0xF6F7FB, soft=0.2, rim=0.1, outline=0.0, shadow=0xB8BEDC)
    E.mat("hill_tree", 0x76A97A, soft=0.35, rim=0.2, outline=0.0, shadow=0x6A86A8)
    E.mat("hill_tree_far", 0x9DBFD0, soft=0.35, rim=0.1, outline=0.0, shadow=0x96A2CA)
    rnd = random.Random(9)
    m = E.Mesher("sl_hills")
    for side in (-1, 1):
        for layer, (mat, x0, hmax) in enumerate((("hill_far", 230.0, 55.0), ("hill_near", 140.0, 26.0))):
            pts = []
            n = 40
            for i in range(n + 1):
                y = -260 + 520 * i / n
                h = hmax * (0.45 + 0.35 * math.sin(i * 0.7 + layer + side) + 0.2 * rnd.random())
                pts.append((y, h))
            m.mat(mat)
            for (ya, ha), (yb, hb) in zip(pts[:-1], pts[1:]):
                q = [(side * x0, ya, city.GROUND - 1), (side * x0, yb, city.GROUND - 1), (side * x0, yb, city.GROUND + hb), (side * x0, ya, city.GROUND + ha)]
                m.poly(q if side < 0 else q[::-1])
            # forest along the crest: rounded tree crowns break the line like the wooded hills in Genshin
            m.mat("hill_tree" if layer else "hill_tree_far")
            for (ya, ha), (yb, hb) in zip(pts[:-1], pts[1:]):
                yy, hh = (ya + yb) * 0.5, (ha + hb) * 0.5
                r = rnd.uniform(5.0, 8.0) * (1.0 if layer else 1.6)
                m.sphere((side * (x0 + 2.0), yy, city.GROUND + hh - r * 0.3), r, 7, 4, s=(0.5, 1.0, 0.8))
    # the mountain far ahead
    m.mat("hill_far")
    m.cyl((40.0, 380.0, city.GROUND + 45), r=150, r2=26, h=90, seg=32)
    m.mat("hill_snow")
    m.cyl((40.0, 380.0, city.GROUND + 98), r=34, r2=12, h=16, seg=32)
    return m.obj("sl_hills", smooth_angle=0)


# ----------------------------------------------------------------------------- greenery (blender/assets/greenery.py)

def verge(lod=0):
    """12 m of the line fence and its verge (right side): tall grass and pampas on both sides of the footing, weeds
    between the cable troughs and the ditch, shrubs along the street side, ivy and morning glories climbing the mesh
    and wildflowers, so the edge of the line reads as one overgrown green band, never bare ground.
    lod 2 keeps only the shrubs (from 90 m the grass is below a pixel)."""
    import greenery as G
    G.mats()
    rnd = random.Random(40)
    m = E.Mesher("sl_verge")
    cl = G.Clumps()
    z = city.GROUND + 0.06
    seg = city.SEG
    if lod < 2:
        # weeds in the gap between the cable-trough lids and the ditch
        step = (0.5, 1.2)[lod]
        for k in range(int(seg / step)):
            G.tuft(m, 4.91 + rnd.uniform(-0.03, 0.03), k * step + rnd.uniform(0, 0.3), -0.02, rnd,
                   h=rnd.uniform(0.16, 0.26), blades=(5, 3)[lod], light=rnd.random() < 0.5)
        # track side of the fence and the strip under it: tall grass
        G.meadow(m, 5.5, 5.74, 0.0, seg, z + 0.04, rnd, density=13.0, bloom=0.2, lod=lod, light=0.4, h=0.4)
        G.meadow(m, 5.86, 6.3, 0.0, seg, z, rnd, density=10.0, bloom=0.45, lod=lod, light=0.35, h=0.36)
        # pampas clumps on both sides
        for k in range((6, 3)[lod]):
            G.susuki(m, rnd.choice((5.6, 6.05, 6.15)), rnd.uniform(0.3, seg - 0.3), z, rnd, lod=lod)
    # shrubs on the street side, kept clear of the fence mesh (x 5.8) and the kerb (x 6.38)
    srnd = random.Random(41)
    y = srnd.uniform(0.2, 1.2)
    while y < seg - 0.4:
        L = srnd.uniform(0.45, 0.75)
        hyd = srnd.random() < 0.3
        cl.lobes(m, "gr_leaf_dark" if hyd else srnd.choice(("gr_leaf", "gr_hedge", "gr_leaf_light")),
                 (6.1, y, z + L * 0.5), (0.24, L, L * 0.62), (4, 2, 0)[lod], srnd, lod=max(lod, 1), spread=0.5)
        if hyd and lod == 0:
            for j in range(3):
                cl.lobes(m, "gr_hydrangea", (6.1 + srnd.uniform(-0.08, 0.12), y + srnd.uniform(-L, L) * 0.6,
                                             z + L * 0.75 + srnd.uniform(0, 0.12)), (0.14, 0.15, 0.13), 1, srnd, lod=2)
        y += L * 2 + srnd.uniform(0.8, 2.6)
    # ivy up the mesh on both faces, with morning glories
    if lod == 0:
        for k in range(5):
            G.ivy(m, 5.8, rnd.uniform(0.3, seg - 0.3), city.GROUND + 0.28, rnd, face=rnd.choice((-1, 1)),
                  h=rnd.uniform(0.7, 1.5), leaves=rnd.randint(9, 14))
        for k in range(4):
            G.flowers(m, rnd.uniform(5.95, 6.25), rnd.uniform(0.5, seg - 0.5), z, rnd)
    return cl.soften(m.obj("sl_verge", smooth_angle=35))


def greenbed(lod=0):
    """12 m planted bed along the line side of the lane (right side, x 6.48..8.3, laid over the asphalt): a low stone
    edge to the road, dense grass, mounded azaleas in bloom, hydrangeas, round shrubs and wildflowers, so the strip
    between the line and the houses reads as a garden, never bare road. Everything stays under 1.4 m: the sakura on
    the far kerb are the trees. lod 2 keeps the bed and the shrubs."""
    import greenery as G
    G.mats()
    E.mat("gb_soil", 0x6F8C52, soft=0.2, rim=0.0, outline=0)
    E.mat("gb_edge", 0xD9D1C4, soft=0.2, rim=0.2, outline=0.6, shadow=0x9C94B4)
    rnd = random.Random(70)
    m = E.Mesher("sl_greenbed")
    cl = G.Clumps()
    seg, g = city.SEG, city.GROUND
    x0, x1 = 6.48, 8.3
    z = g + 0.1
    m.mat("gb_soil")
    m.box(((x0 + x1) / 2, seg / 2, g + 0.05), (x1 - x0, seg, 0.1), smooth=False)
    m.mat("gb_edge")
    m.box((x1 + 0.07, seg / 2, g + 0.09), (0.14, seg, 0.18), bevel=(0.02, 1) if lod == 0 else None, smooth=False)
    if lod < 2:
        G.meadow(m, x0 + 0.04, x1 - 0.04, 0.0, seg, z, rnd, density=9.0, bloom=0.5, lod=lod, light=0.4, h=0.3)
    # shrubs in a staggered double row; some azaleas so covered in flowers that the green barely shows
    srnd = random.Random(71)
    y, row = srnd.uniform(0.0, 0.6), 0
    while y < seg - 0.3:
        r = srnd.uniform(0.42, 0.66)
        x = (7.0, 7.8)[row % 2] + srnd.uniform(-0.12, 0.12)
        kind = srnd.random()
        if kind < 0.4:
            cl.lobes(m, "gr_leaf_dark", (x, y, z + r * 0.5), (r * 1.1, r, r * 0.68), (3, 2, 0)[lod], srnd, lod=max(lod, 1))
            if lod < 2:
                fl = "gr_azalea" if srnd.random() < 0.7 else "gr_azalea_w"
                for k in range((5, 3)[lod]):
                    a = srnd.uniform(0, 2 * math.pi)
                    b = srnd.uniform(0.25, 1.1)
                    p = (x + math.cos(a) * math.cos(b) * r * 0.95, y + math.sin(a) * math.cos(b) * r * 0.85,
                         z + r * 0.5 + math.sin(b) * r * 0.62)
                    cl.lobes(m, fl, p, (0.26, 0.24, 0.17), 1 if lod == 0 else 0, srnd, lod=max(lod, 1))
        elif kind < 0.65:
            G.bush(m, cl, x, y, z, srnd, r=r, lod=max(lod, 1), mat="gr_hydrangea")
        else:
            G.bush(m, cl, x, y, z, srnd, r=r, lod=max(lod, 1), mat=srnd.choice(("gr_leaf", "gr_leaf_light", "gr_hedge")))
        y += r * 1.25 + srnd.uniform(0.1, 0.7)
        row += 1
    if lod == 0:
        for k in range(6):
            G.flowers(m, srnd.uniform(x0 + 0.1, x1 - 0.1), srnd.uniform(0.3, seg - 0.3), z, srnd)
    return cl.soften(m.obj("sl_greenbed", smooth_angle=35))


def garden(variant, lod=0):
    """20 m behind a pair of houses (right side; plots at y 0..10 and 10..20, houses x 11..21.8): hedges and shrubs
    in the gaps between the houses, and back gardens out to x 30 with lawn tufts, flower beds and round trees."""
    import greenery as G
    G.mats()
    rnd = random.Random(60 + variant * 7)
    m = E.Mesher("sl_garden_%d" % variant)
    cl = G.Clumps()
    z = city.GROUND - 0.04
    for y in (0.0, 10.0):
        G.hedge(m, cl, 13.8, 21.4, y, z, rnd, h=rnd.uniform(0.9, 1.3), w=0.75, lod=lod)
        G.bush(m, cl, 12.6, y + rnd.uniform(-0.3, 0.3), z, rnd, r=0.55, lod=lod)
        if lod < 2:
            G.meadow(m, 11.4, 13.4, y - 0.7, y + 0.7, z + 0.08, rnd, density=4.0, bloom=0.5, lod=lod)
    # back gardens
    for k in range(rnd.randint(2, 3)):
        G.tree(m, cl, rnd.uniform(23.5, 28.5), rnd.uniform(1.5, 18.5), z, rnd, h=rnd.uniform(7.5, 10.5), lod=lod,
               pink=rnd.random() < 0.3)
    for k in range(rnd.randint(3, 5)):
        G.bush(m, cl, rnd.uniform(22.4, 29.0), rnd.uniform(0.5, 19.5), z, rnd, r=rnd.uniform(0.5, 0.9), lod=lod)
    # low hedges between neighbouring back gardens
    for y in (0.0, 10.0):
        if rnd.random() < 0.5:
            G.hedge(m, cl, 22.0, 30.0, y, z, rnd, h=0.9, w=0.6, lod=lod)
    if lod < 2:
        G.meadow(m, 22.0, 30.0, 0.0, 20.0, z + 0.04, rnd, density=0.8, bloom=0.4, lod=lod)
        for k in range(3 if lod == 0 else 1):
            G.flowers(m, rnd.uniform(22.5, 29.5), rnd.uniform(1.0, 19.0), z + 0.04, rnd, n=6)
    return cl.soften(m.obj("sl_garden_%d" % variant, smooth_angle=35))


def backyard(lod=0):
    """20 m behind an apartment block (right side, x 21..30): trees, shrubs and lawn."""
    import greenery as G
    G.mats()
    rnd = random.Random(90)
    m = E.Mesher("sl_backyard")
    cl = G.Clumps()
    z = city.GROUND - 0.04
    for k in range(3):
        G.tree(m, cl, rnd.uniform(23.5, 28.5), 3.0 + k * 6.5 + rnd.uniform(-1, 1), z, rnd, h=rnd.uniform(8.0, 11.0), lod=lod)
    for k in range(4):
        G.bush(m, cl, rnd.uniform(22.0, 29.5), rnd.uniform(0.5, 19.5), z, rnd, r=rnd.uniform(0.5, 0.9), lod=lod)
    if lod < 2:
        G.meadow(m, 21.5, 30.0, 0.0, 20.0, z + 0.04, rnd, density=0.8, bloom=0.4, lod=lod)
    return cl.soften(m.obj("sl_backyard", smooth_angle=35))


def clouds():
    """The sky ahead (centred on the origin; the game keeps it on the camera): a bank of big soft cumulus along the
    horizon behind the hills, towering clouds above it and a few small high ones, all inside the view ahead so the
    sky is never an empty gradient."""
    import greenery as G
    E.mat("cloud", 0xFFFFFF, soft=0.45, rim=0.4, emis=0.35, outline=0.0, shadow=0xB9C4EA, flags=E.F_NOCAST)
    E.mat("cloud_shade", 0xE6EAFA, soft=0.45, rim=0.3, emis=0.3, outline=0.0, shadow=0xA8B2E0, flags=E.F_NOCAST)
    E.mat("cloud_warm", 0xFFF6EC, soft=0.45, rim=0.4, emis=0.35, outline=0.0, shadow=0xC2BEE6, flags=E.F_NOCAST)
    rnd = random.Random(12)
    m = E.Mesher("sl_clouds")
    cl = G.Clumps()

    def cloud(a_deg, dist, z, w, n, lod):
        a = math.radians(a_deg)
        x, y = math.sin(a) * dist, math.cos(a) * dist
        for j in range(n):
            c = (x + rnd.uniform(-w, w) * 0.5, y + rnd.uniform(-8, 8), z + rnd.uniform(-0.1, 0.25) * w)
            cl.lobes(m, ("cloud_shade", "cloud", "cloud_warm")[j % 3], c, (w * 0.5, w * 0.3, w * 0.3), 5, rnd,
                     lod=lod, squash=0.8)

    # horizon bank: overlapping heaps from edge to edge, low over the hills
    a = -46.0
    while a < 46:
        cloud(a, rnd.uniform(360, 390), rnd.uniform(18, 34), rnd.uniform(30, 48), 3, 1)
        a += rnd.uniform(6, 9)
    # towering cumulus
    for k in range(9):
        cloud(-40 + k * 10 + rnd.uniform(-3, 3), rnd.uniform(290, 340), rnd.uniform(60, 120), rnd.uniform(26, 46),
              rnd.randint(3, 4), 0)
    # small high puffs
    for k in range(6):
        cloud(rnd.uniform(-38, 38), rnd.uniform(260, 300), rnd.uniform(130, 165), rnd.uniform(12, 20), 2, 1)
    return cl.soften(m.obj("sl_clouds", smooth_angle=35))


def export_density():
    for lv in (0, 1, 2):
        for v in range(STREET_KINDS):
            E.reset(); city.city_mats(); B.mats()
            E.export_erm(GL.tier(street(v, _KIT[lv]), lv, 0.3), "sl_street_%d" % v + GL.sfx(lv))
    for v in range(3):
        E.reset(); city.city_mats(); B.mats(); street_mats()
        E.export_erm(GL.squash_uv(GL.bake(far_town(v))), "sl_far_%d" % v)
    E.reset()
    E.export_erm(hills(), "sl_hills")
    export_greens()


def export_greenbed():
    """Only the garden beds (quick to re-export while tuning them)."""
    for lv in (0, 1, 2):
        E.reset(); city.city_mats()
        E.export_erm(greenbed(lv), "sl_greenbed" + GL.sfx(lv))


def export_greens():
    """The sky and the greenery only (quick to re-export while tuning them)."""
    E.reset()
    E.export_erm(clouds(), "sl_clouds")
    for lv in (0, 1, 2):
        sx = GL.sfx(lv)
        E.reset(); city.city_mats()
        E.export_erm(verge(lv), "sl_verge" + sx)
        E.reset(); city.city_mats()
        E.export_erm(greenbed(lv), "sl_greenbed" + sx)
        for v in range(3):
            E.reset(); city.city_mats()
            E.export_erm(garden(v, lv), "sl_garden_%d" % v + sx)
        E.reset(); city.city_mats()
        E.export_erm(backyard(lv), "sl_backyard" + sx)


# ----------------------------------------------------------------------------- layout (mirrors SakuraWorld.java)

PLOT = 10.0
BLD = ["sl_house_a", "sl_house_b", "sl_house_c", "sl_house_d", "sl_house_e"]


def hash32(k):
    h = (k * 0x45d9f3b) & 0xFFFFFFFF
    h = (((h >> 16) ^ h) * 0x45d9f3b) & 0xFFFFFFFF
    h = (h >> 16) ^ h
    return h & 0x7fffffff


def plots(side, p0, p1):
    """Yields (name, y_start, plot_count) for building plots of one side between plot indices p0..p1.
    Plots come in pairs (20 m): either one apartment/konbini, or two houses."""
    out = []
    for pair in range(p0 // 2, p1 // 2 + 1):
        h = hash32(pair * 2 + (7 if side > 0 else 13))
        if h % 5 == 0:
            out.append(("sl_konbini" if (h >> 5) % 3 == 0 else "sl_apartment", pair * 2 * PLOT, 2))
        else:
            out.append((BLD[(h >> 3) % 5], pair * 2 * PLOT, 1))
            out.append((BLD[(h >> 9) % 5], (pair * 2 + 1) * PLOT, 1))
    return out


BLD_X = {"sl_konbini": 19.5, "sl_apartment": 12.6}
BLD_W = {"sl_house_a": 7.0, "sl_house_b": 7.6, "sl_house_c": 6.6, "sl_house_d": 7.2, "sl_house_e": 6.8,
         "sl_konbini": 12.0, "sl_apartment": 14.4}


def _make(name, lod=0):
    for nm, kw in HOUSES:
        if nm == name:
            return [_finish_building(B.house(nm, lod=lod, **kw))]
    if name == "sl_apartment":
        return [_finish_building(B.apartment(name, lod=lod))]
    if name == "sl_konbini":
        return [_finish_building(B.konbini(name, lod=lod))]
    if name.startswith("sl_sakura_"):
        k = int(name[-1])
        return list(B.sakura(name, seed=k, height=6.0 + (k - 1) * 0.5, lod=lod))
    raise KeyError(name)


def design_world(length=96.0):
    """The Sakura Line laid out the way the game lays it out (SakuraWorld.java), seen from the runner camera."""
    import studio, trains, obstacles
    E.reset()
    studio.stage(res=(900, 1600), floor=False)
    city.city_mats(); B.mats(); street_mats()
    nseg = int(length / city.SEG)
    for i in range(-1, nseg):
        y0 = i * city.SEG
        for fn in (city.track, city.side, lambda: city.side(mirror=True), city.wires, _lot, lambda: _lot(0, True)):
            ob = fn(); ob.location.y += y0
        if i % 2 == 0:
            g = city.gantry(); g.location.y = y0 + 6
            p = city.utility_pole(); p.location.y = y0 + 2
            if i % 4 == 2:
                p.scale.x = -1
    for side in (1, -1):
        for nm, ys, n in plots(side, -2, int(length / PLOT)):
            for ob in _make(nm, 1 if ys > 60 else 0):
                ob.rotation_euler.z = math.radians(-90 if side > 0 else 90)
                w = BLD_W[nm]
                ob.location = (side * BLD_X.get(nm, 13.6), ys + n * PLOT / 2, city.GROUND)
        for k in range(-1, int(length / PLOT)):
            h = hash32(k * 31 + (3 if side > 0 else 5))
            ob = street(h % STREET_KINDS)
            ob.location.y = k * PLOT
            if side < 0:
                ob.scale.x = -1
            if (h >> 4) % 3 == 0:
                for t in _make("sl_sakura_%d" % (1 + (h >> 6) % 3)):
                    t.location = (side * 9.9, k * PLOT + 5.0, city.GROUND)
        for v in range(int(length / 24) + 1):
            ob = far_town((v + (0 if side > 0 else 1)) % 3)
            ob.location.y = v * 24
            if side < 0:
                ob.scale.x = -1
    hills()
    t = trains.commuter("commuter_front", "teal", True, 1); t.location = (-2.4, 30, 0)
    t2 = trains.commuter("commuter_mid", "teal", False, 2); t2.location = (-2.4, 42, 0)
    e = trains.express("express_front", "crimson", True, 5); e.location = (2.4, 52, 0)
    b = obstacles.barricade(); b.location = (0, 22, 0)
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and not any(k in o.name for k in ("side", "lot", "wires", "track", "hills", "shadow", "canopy")):
            if "_outline" not in o.modifiers:
                E.add_outline(o, 0.02)
    studio.aim_sun(200)
    studio.shoot("world_runner", target=(0, 8, 1.3), dist=15, yaw=0, pitch=13, lens=20)
    studio.shoot("world_side", target=(8, 30, 2.0), dist=26, yaw=-35, pitch=18, lens=30)
