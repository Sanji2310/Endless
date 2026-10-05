"""
Design audit: every ride asset alone on the studio stage from five angles (front, side, back, high 3/4, close-up),
so build faults (gaps, floating parts, clipping, wrong proportions) show before anyone sees it in a scene.
  blender -b -P blender/run.py -- audit run <group>        groups: vehicles, river, sky, all
Writes renders/audit/<asset>_<view>.png; tools/audit_sheets.sh tiles them into one sheet per asset.
"""
import math, os, random
import bpy
from mathutils import Vector
import erlib as E
import studio

V = Vector
OUT = os.path.join(E.OUT_RENDERS, "audit")
WATER = 0x8FD3E8


def _mesher_asset(name, fn, mats):
    def build():
        mats()
        m = E.Mesher(name)
        fn(m)
        return [m.obj(name, smooth_angle=40)]
    return build


def _assets():
    import vehicles as VH
    import river_kit as RK
    import sky_kit as SK
    import scenery as SC
    rnd = lambda: random.Random(3)
    RP, SP = RK.PAL, SK.PAL
    A = {}
    # vehicles (built facing +Y)
    A["ore_cart"] = ("vehicles", lambda: [VH.ore_cart()], None, 0)
    A["bamboo_boat"] = ("vehicles", lambda: [VH.boat()], WATER, 0)
    A["paddle"] = ("vehicles", lambda: [VH.paddle()], None, 0)
    A["glider"] = ("vehicles", lambda: [VH.glider()], None, 0)

    # river hazards and life
    def croc():
        bo, jo = RK.croc()
        jo.location = (0, -RK.JAW_HINGE.y, RK.JAW_HINGE.z)
        jo.rotation_euler = (math.radians(-25), 0, 0)
        return [bo, jo]
    A["croc"] = ("river", croc, WATER, 180)
    A["stone"] = ("river", lambda: [RK.stone()], WATER, 0)
    A["drift_log"] = ("river", lambda: [RK.drift_log()], WATER, 0)
    A["whirlpool"] = ("river", lambda: [RK.whirlpool()], WATER, 0)
    A["koi"] = ("river", lambda: [RK.koi()], WATER, 0)
    A["heron"] = ("river", lambda: [RK.heron()], None, 0)
    A["fork_island"] = ("river", lambda: [RK.fork_island(L=14.0)], WATER, 0)
    A["stone_lantern"] = ("river", _mesher_asset("stone_lantern", lambda m: RK.stone_lantern(m, (0, 0, 0)), RK.mats), None, 0)
    A["torii"] = ("river", _mesher_asset("torii", lambda m: RK.torii(m, (0, 0, 0)), RK.mats), None, 0)
    A["bamboo_clump"] = ("river", _mesher_asset("bamboo", lambda m: RK.bamboo_clump(m, (0, 0, 0), rnd()), RK.mats), None, 0)
    A["reeds_lilies"] = ("river", _mesher_asset("reeds", lambda m: (RK.reeds(m, (0, 0, 0), rnd()),
                                                                     RK.lily_pads(m, (0.8, -0.8, 0), rnd())), RK.mats), WATER, 0)
    A["house"] = ("river", _mesher_asset("house", lambda m: SC.house(m, RP, V((0, 0, 0)), rnd()), RK.mats), None, 180)
    A["water_mill"] = ("river", _mesher_asset("mill", lambda m: (SC.water_wheel(m, RP, (0, 0, 0.5), axle=2.4),
                                                                  SC.house(m, RP, V((2.1, 0, 0.3)), rnd(), rot=math.radians(90),
                                                                           w=2.2, d=1.8, h=1.3)), RK.mats), WATER, 0)
    A["dock"] = ("river", _mesher_asset("dock", lambda m: SC.dock(m, RP, (0, 0, 0)), RK.mats), WATER, 0)
    A["trees_shrubs"] = ("river", _mesher_asset("trees", lambda m: (SC.round_tree(m, RP, (0, 0, 0), rnd(), h=3.6, r=1.5),
                                                                     SC.pine(m, RP, (3.2, 0, 0), rnd()),
                                                                     SC.shrub(m, RP, (-2.4, -0.6, 0), rnd(), r=0.6, flowers=RP["flower"]),
                                                                     SC.fern(m, RP, (-1.6, -1.6, 0), rnd()),
                                                                     SC.bamboo_fence(m, RP, (-3, -2.2, 0), (3, -2.2, 0))), RK.mats), None, 0)
    A["grass_flowers"] = ("river", _mesher_asset("grass", lambda m: SC.grass_carpet(m, RP, -1.5, 1.5, -1.5, 1.5,
                                                                                     lambda x, y: 0.0, rnd(), density=3,
                                                                                     h=0.42, flowers=0.15), RK.mats), 0x9ACD6E, 0)
    # sky
    A["crow"] = ("sky", lambda: SK.crow_flight("crow", (0, 0, 0), flap=24), None, 0)
    A["islet"] = ("sky", lambda: [SK.islet()], None, 0)
    A["thundercloud"] = ("sky", lambda: [SK.thundercloud()], None, 0)
    A["cloud"] = ("sky", lambda: [SK.cloud(size=4.0)], None, 0)
    A["chime_cable"] = ("sky", lambda: [SK.chime_cable(span=8, pylon=3.0)], None, 0)
    A["spire"] = ("sky", lambda: [SK.spire(h=8.0)], None, 0)
    A["thermal_gust"] = ("sky", lambda: [SK.thermal_ring(), SK.wind_streak()], None, 0)
    A["windmill"] = ("sky", _mesher_asset("windmill", lambda m: SC.windmill(m, SP, V((0, 0, 0)), rnd()), SK.mats), None, 180)
    A["pagoda"] = ("sky", _mesher_asset("pagoda", lambda m: SC.pagoda(m, SP, (0, 0, 0)), SK.mats), None, 0)
    A["pillar_top"] = ("sky", _mesher_asset("cap", lambda m: SK._cap(m, rnd(), V((0, 0, 0)), 2.6), SK.mats), None, 0)
    return A


VIEWS = [("front", 180, 12), ("side", 270, 10), ("back", 0, 14), ("high", 215, 42)]


def _bounds(objs):
    bpy.context.view_layer.update()
    lo, hi = V((1e9,) * 3), V((-1e9,) * 3)
    for o in objs:
        if o.type != 'MESH':
            continue
        for c in o.bound_box:
            p = o.matrix_world @ V(c)
            lo = V((min(lo[i], p[i]) for i in range(3)))
            hi = V((max(hi[i], p[i]) for i in range(3)))
    return lo, hi


def run(group="all"):
    os.makedirs(OUT, exist_ok=True)
    for name, (grp, build, floor_col, face) in _assets().items():
        if group not in ("all", grp):
            continue
        E.reset()
        studio.stage(res=(560, 560), **({"floor_col": floor_col} if floor_col else {}))
        objs = build()
        for o in objs:
            if o.type == 'MESH' and "cloud" not in o.name and "streak" not in o.name:
                E.add_outline(o, 0.01)
        lo, hi = _bounds(objs)
        if floor_col is None and lo.z < -0.01:      # e.g. the paddle hangs below its grip: stand it on the floor
            for o in objs:
                if o.parent is None:
                    o.location.z -= lo.z
            lo, hi = _bounds(objs)
        c = (lo + hi) * 0.5
        size = max((hi - lo).length, 0.5)
        for vn, yaw, pitch in VIEWS:
            studio.shoot("../audit/%s_%s" % (name, vn), target=tuple(c), dist=size * 1.25, yaw=yaw + face, pitch=pitch, lens=40)
        # close-up on the busiest part: the upper front third
        cz = V((c.x, c.y, lo.z + (hi.z - lo.z) * 0.62))
        studio.shoot("../audit/%s_close" % name, target=tuple(cz), dist=max(size * 0.5, (hi - lo).length * 0.5 + 0.3), yaw=200 + face, pitch=18, lens=50)
