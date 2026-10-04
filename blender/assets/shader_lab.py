"""
Shader lab: a small test set for the game's zone materials, exported next to the real kits so
tools/shader_lab.sh can show every shader in the real renderer before the zones that use them exist.

  lab_river    20 m of river: toon water (F_WATER) between grassy banks with a stone edging, grass tufts,
               reeds and bushes (F_FOLIAGE, rooted sway)
  lab_cloud    a big cumulus mass (F_CLOUD)
  lab_crystals crystal clusters on a rock shelf (F_CRYSTAL, the cave materials)
  lab_sakura   the Sakura Line cherry tree (foliage canopy)

None of these ship in pongo.bin; tools/build_assets.sh does not export them.
Run: blender -b -P blender/run.py -- shader_lab export_lab
"""
import math, random
from mathutils import Vector as V
import erlib as E


def mats():
    M = E.mat
    M("lab_water", 0x8FD3E8, rim=0.2, spec=0.6, soft=0.12, flags=E.F_WATER | E.F_NOCAST, outline=0.0, shadow=0x7FA6D6)
    M("lab_grass", 0x9CCB6A, rim=0.1, soft=0.25, outline=0.0, shadow=0x7E8CC0)
    M("lab_bank", 0xC9B48E, rim=0.1, soft=0.2, outline=0.0)
    M("lab_stone", 0xB8B4C0, rim=0.2, soft=0.15, outline=0.7)
    M("lab_blade", 0x86C25A, rim=0.2, soft=0.3, flags=E.F_FOLIAGE | E.F_DOUBLE | E.F_NOCAST, sway=0.55, outline=0.0)
    M("lab_blade_light", 0xB4D86E, rim=0.2, soft=0.3, flags=E.F_FOLIAGE | E.F_DOUBLE | E.F_NOCAST, sway=0.55, outline=0.0)
    M("lab_reed", 0xA8C46A, rim=0.2, soft=0.2, flags=E.F_FOLIAGE | E.F_DOUBLE, sway=0.5, outline=0.0)
    M("lab_bush", 0x6FAE5C, rim=0.3, soft=0.3, flags=E.F_FOLIAGE, sway=0.2, outline=0.6, shadow=0x6A78B0)
    M("lab_flower", 0xFFF2F6, rim=0.2, soft=0.2, flags=E.F_FOLIAGE | E.F_NOCAST, sway=0.55, outline=0.0)
    M("lab_cloud", 0xFFFFFF, rim=0.5, soft=0.35, flags=E.F_CLOUD | E.F_NOCAST, outline=0.0)


def _blade(m, rnd, x, y, z, h):
    a = rnd.random() * math.pi
    lean = V(((rnd.random() - 0.5) * 0.3, (rnd.random() - 0.5) * 0.3, 0))
    w = 0.035 + rnd.random() * 0.02
    dx, dy = math.cos(a) * w, math.sin(a) * w
    m.mat("lab_blade" if rnd.random() < 0.6 else "lab_blade_light")
    tip = V((x, y, z + h)) + lean * h
    m.poly([(x - dx, y - dy, z), (x + dx, y + dy, z), tuple(tip)], uv='box')


def tuft(m, rnd, x, y, z, n=9, h=0.35):
    for _ in range(n):
        _blade(m, rnd, x + (rnd.random() - 0.5) * 0.25, y + (rnd.random() - 0.5) * 0.25, z, h * (0.6 + 0.6 * rnd.random()))


def bush(m, rnd, x, y, z, r=0.5):
    m.mat("lab_bush")
    for k in range(5):
        a = k * 1.3 + rnd.random()
        m.ico((x + math.cos(a) * r * 0.45, y + math.sin(a) * r * 0.45, z + r * (0.45 + 0.3 * rnd.random())),
              r * (0.5 + 0.2 * rnd.random()), 2, s=(1, 1, 0.85))
    m.ico((x, y, z + r * 0.9), r * 0.6, 2)


def river(length=20.0, half=4.0, seed=3):
    rnd = random.Random(seed)
    m = E.Mesher("lab_river")
    # water: a grid so the flat surface still gets fine per-vertex AO and fog
    m.mat("lab_water")
    n = 10
    for i in range(n):
        y0, y1 = length * i / n, length * (i + 1) / n
        m.poly([(-half, y0, -0.15), (half, y0, -0.15), (half, y1, -0.15), (-half, y1, -0.15)], uv='box')
    for side in (-1, 1):
        # stone edging course along the water
        for i in range(int(length / 0.7)):
            y = i * 0.7 + rnd.random() * 0.1
            m.mat("lab_stone")
            m.ico((side * (half + 0.15), y, -0.05), 0.32 + rnd.random() * 0.08, 1, s=(1.0, 1.1, 0.6))
        # bank slope and the field beyond
        x0, x1, x2 = side * half, side * (half + 2.5), side * (half + 14)
        m.mat("lab_bank")
        m.poly([(x0, 0, -0.3), (x0, length, -0.3), (x1, length, 0.4), (x1, 0, 0.4)][::-side], uv='box')
        m.mat("lab_grass")
        m.poly([(x1, 0, 0.4), (x1, length, 0.4), (x2, length, 0.6), (x2, 0, 0.6)][::-side], uv='box')
        # grass, flowers, reeds and bushes: the sides fully covered
        for k in range(160):
            x = side * (half + 1.0 + rnd.random() * 12.5)
            y = rnd.random() * length
            z = 0.4 + 0.2 * (abs(x) - half - 2.5) / 11.5 if abs(x) > half + 2.5 else -0.3 + 0.7 * (abs(x) - half) / 2.5
            tuft(m, rnd, x, y, z, n=7, h=0.32 + rnd.random() * 0.2)
            if rnd.random() < 0.15:
                m.mat("lab_flower")
                m.ico((x + 0.1, y, z + 0.28), 0.05, 1)
        for k in range(24):
            y = rnd.random() * length
            x = side * (half + 0.45 + rnd.random() * 0.4)
            for j in range(5):
                m.mat("lab_reed")
                bx, by = x + (rnd.random() - 0.5) * 0.3, y + (rnd.random() - 0.5) * 0.3
                h = 0.8 + rnd.random() * 0.35
                m.poly([(bx - 0.02, by, -0.2), (bx + 0.02, by, -0.2), (bx + side * 0.08, by + 0.05, -0.2 + h)], uv='box')
        for k in range(10):
            bush(m, rnd, side * (half + 3.5 + rnd.random() * 9), rnd.random() * length, 0.45, 0.45 + rnd.random() * 0.35)
    return m.obj("lab_river", smooth_angle=50)


def cloud(seed=5):
    rnd = random.Random(seed)
    m = E.Mesher("lab_cloud")
    m.mat("lab_cloud")
    for k in range(26):
        a = rnd.random() * 2 * math.pi
        rr = rnd.random() ** 0.6 * 4.5
        x, y = math.cos(a) * rr * 1.4, math.sin(a) * rr * 0.7
        z = (4.5 - rr) * 0.55 + rnd.random() * 0.8
        m.ico((x, y, z), 1.4 + rnd.random() * 1.2, 3, s=(1, 1, 0.8))
    return m.obj("lab_cloud", smooth_angle=180)


def crystals(seed=9):
    import cave
    cave.mats()
    rnd = random.Random(seed)
    m = E.Mesher("lab_crystals")
    m.mat("c_rock")
    m.box((0, 0, -0.2), (5, 2.5, 0.4))
    for k in range(5):
        cave.crystal_cluster(m, (-2.0 + k * 1.0, rnd.uniform(-0.6, 0.6), 0.0), (0, 0, 1), size=0.6 + rnd.random() * 0.5,
                             rnd=rnd, mats=("c_crystal", "c_crystal_violet", "c_crystal_pink"))
    return m.obj("lab_crystals", smooth_angle=20)


def export_lab():
    E.reset(); mats()
    E.export_erm(river(), "lab_river")
    E.reset(); mats()
    E.export_erm(cloud(), "lab_cloud")
    E.reset(); mats()
    E.export_erm(crystals(), "lab_crystals")
    E.reset()
    import buildings
    trunk, canopy, shadow = buildings.sakura("lab_sakura", seed=2)
    E.export_erm([trunk, canopy], "lab_sakura")
