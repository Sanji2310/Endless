"""
Crystal Cavern 水晶洞窟 — zone 2 kit (docs/PONGO_DESIGN.md §4).

Same frame as the Sakura Line kit (city.py), so segments, lanes and obstacles line up across the zone change:
  Blender Z up, the runner moves toward +Y, one segment = 12 m, lanes at x = -2.4, 0, +2.4 (gauge 1.067 m),
  sleeper (tie) tops at z = 0. Lanes are clear to |x| 3.5 and up to 4.6 m.

  cave_track      three mine tracks on rough timber ties over a packed earth floor
  cave_shell      the rock vault: a swept arch with strata ledges. Each seed varies the middle of the segment
                  only (the ends share one profile), so any shell variant joins any other.
  cave_deco       crystal clusters on the walls, stalactites, stalagmites and puddles fitted to that shell
  cave_frame      mine support set: timber posts, cap beam, knee braces, roof struts, two hanging lanterns
  cave_pipe       air pipe and cable on brackets along the right wall
  bat             ambient cave bat (wings up / down poses for a two-frame flap)
  hotaru_lamp     the Hotaru Lamp zone gear (brass headlamp on a strap)

The cave is ridden in Pongo's ore cart (vehicles.ore_cart; floor 0.45 m above the rail plane). Controls there are
tilt (steer around things, take the other branch at a parting) and crouch (duck in the cart). Obstacles are built
at the origin facing the rider (who comes from -Y), sized like the Crystal Cavern rows in obstacles.py:
  ob_timber_beam     CROUCH  sagging mine set, beam underside at 1.25 m
  ob_fallen_log      CROUCH  round log laid across the track on two timber cribs, underside at 1.25 m
  ob_bat_swarm_a/b   CROUCH  bats at 1.2-1.9 m flying at the rider (two wing frames for a flip-book flap)
  ob_crystal_rock    SIDE    boulder studded with crystals, 2.4 m tall: tilt away
  ob_rockpile        SIDE    rubble from a roof fall heaped on one track: tilt away
  ob_ore_train       SIDE    mine loco + ore wagons on a track (parked or oncoming): tilt away
  cave_fork          PARTING one track splits around a crystal pillar and rejoins (24 m): pick a branch

Every obstacle stands on the ground it meets in the game (the gravel bed, its shoulder, the floor at FLOOR) and has a
soft contact shadow decal under it (s_contact, tex_cave.contact_sprite): the cave has no sun to cast one.

Small props and effects: cave_props (mine shrine, barrels, crates, tools, sacks, signs, spare rails, a parked cart,
oil drums, a cable reel, a ladder, a rest bench with a kettle, rope, a pail), fx sprites (tex_cave.fx_sprites).
Sounds for all of it: src/com/pongo/core/CaveSounds.java.
"""
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix
import erlib as E
import studio

V = Vector
SEG = 12.0
LANES = (-2.4, 0.0, 2.4)
GAUGE = 1.067
FLOOR = -0.1

# cave lighting palette (also mirrored in src/com/pongo/core/Zones.java). Same manner as the Sakura Line renders:
# a high-key lavender shadow band, warm lantern light, clean pale stone, ink outlines on the shapes.
SHADOW = 0x6E62AE          # tinted shadow band inside the cave (the Sakura Line uses 0x6A5FA8)
SHADOW_WARM = 0x8A6A8A
# natural mineral colours, muted: pale aqua quartz, amethyst and rose quartz, each with a clearer, lighter tip
CRYSTALS = (0x8CC6CF, 0x9A82C2, 0xC996B4)
CRYSTAL_TIPS = (0xB5E2E6, 0xC2B0E2, 0xE3BDD1)

# Crouch clearances, from the rider's height in the cart (the vehicle side owns Pongo's size). The crouch obstacles
# are built relative to these, so a new rider height is one edit here plus the same numbers in the game.
BEAM_UNDERSIDE = 1.25      # underside of ob_timber_beam and ob_fallen_log (obstacles.py: "beam HIGH ... at 1.25 m")
SWARM_BAND = (1.2, 1.9)    # height band ob_bat_swarm flies in


def mats():
    M = E.mat
    sh = dict(shadow=SHADOW)
    M("c_rock", 0xBDB2DC, "t_cave_rock", soft=0.12, rim=0.22, spec=0.05, outline=0.55, **sh)
    M("c_rock_wet", 0xA99ED0, "t_cave_rock", soft=0.1, rim=0.35, spec=0.45, outline=0.6, **sh)
    M("c_rock_dark", 0x8F84BC, "t_cave_rock", soft=0.1, rim=0.2, outline=0.7, **sh)
    M("c_floor", 0xD9C7AC, "t_cave_floor", soft=0.15, rim=0.05, outline=0, **sh)
    M("c_ballast", 0xF2EEE8, "t_cave_floor", soft=0.12, rim=0.05, outline=0, **sh)
    M("c_tie", 0xB98258, "t_timber", soft=0.1, rim=0.15, outline=0.6, shadow=SHADOW_WARM)
    M("c_timber", 0xDDA46C, "t_timber", soft=0.1, rim=0.25, outline=0.8, shadow=SHADOW_WARM)
    M("c_timber_dark", 0xA8724A, "t_timber", soft=0.1, rim=0.2, outline=0.8, shadow=SHADOW_WARM)
    M("c_plank", 0xC8925E, "t_timber", soft=0.1, rim=0.15, outline=0.7, shadow=SHADOW_WARM)
    M("c_rail", 0x7A7E8C, spec=0.45, rim=0.35, soft=0.08, flags=E.F_METAL, outline=0.7, **sh)
    M("c_rail_top", 0xD8DCE6, spec=1.0, rim=0.5, soft=0.05, flags=E.F_METAL, outline=0, **sh)
    M("c_rust", 0x8E4E32, spec=0.2, rim=0.2, soft=0.1, outline=0.6, **sh)
    M("c_iron", 0x4B4F58, spec=0.6, rim=0.35, soft=0.06, flags=E.F_METAL, **sh)
    M("c_iron_dark", 0x2C2F36, spec=0.5, rim=0.3, soft=0.06, flags=E.F_METAL, **sh)
    M("c_brass", 0xE0A84C, spec=0.95, rim=0.45, soft=0.04, flags=E.F_METAL, shadow=SHADOW_WARM)
    M("c_rope", 0xC9A86A, rim=0.2, soft=0.12, outline=0.5, shadow=SHADOW_WARM)
    M("c_lamp", 0xFFD27A, emis=1.2, rim=0.2, soft=0.05, outline=0.3, flags=E.F_NOCAST)
    M("c_lamp_hot", 0xFFF1C8, emis=2.0, rim=0.0, soft=0.05, outline=0.0, flags=E.F_NOCAST)
    # crystals: a faint inner glow only (emission 0.15), so they read as mineral rather than lights
    for name, body, tip in (("c_crystal", CRYSTALS[0], CRYSTAL_TIPS[0]), ("c_crystal_violet", CRYSTALS[1], CRYSTAL_TIPS[1]),
                            ("c_crystal_pink", CRYSTALS[2], CRYSTAL_TIPS[2])):
        M(name, body, emis=0.15, spec=0.8, rim=0.45, soft=0.06, flags=E.F_CRYSTAL | E.F_NOCAST, outline=0.6, **sh)
        M(name + "_tip", tip, emis=0.2, spec=1.0, rim=0.5, soft=0.05, flags=E.F_CRYSTAL | E.F_NOCAST, outline=0.6, **sh)
    M("c_contact", 0x4A3F78, "s_contact", flags=E.F_DECAL | E.F_NOCAST, outline=0.0, rim=0.0, soft=0.2, spec=0.0)
    M("c_contact_far", 0x8C80B8, "s_contact", flags=E.F_DECAL | E.F_NOCAST, outline=0.0, rim=0.0, soft=0.2, spec=0.0)
    M("c_ore", 0x6B6088, rim=0.25, soft=0.1, **sh)
    M("c_water", 0x2E5C8A, spec=1.0, rim=0.6, soft=0.05, emis=0.15, flags=E.F_WATER | E.F_NOCAST, outline=0, **sh)
    M("c_bat", 0x3A3150, rim=0.45, soft=0.1, spec=0.1, **sh)
    M("c_bat_wing", 0x6B5680, rim=0.4, soft=0.1, flags=E.F_DOUBLE, **sh)
    M("c_bat_belly", 0x8C7BB0, rim=0.4, soft=0.1, **sh)
    M("c_bat_ear", 0xD48FB8, rim=0.3, soft=0.1, outline=0.4, **sh)
    M("c_eye", 0xFFE36A, emis=1.2, rim=0.0, soft=0.05, outline=0.0)
    M("c_paint_red", 0xD9443A, rim=0.25, soft=0.1, shadow=SHADOW_WARM)
    M("c_paint_yellow", 0xF2C230, rim=0.25, soft=0.1, shadow=SHADOW_WARM)
    M("c_paint_white", 0xEFEBE2, rim=0.25, soft=0.1, shadow=SHADOW_WARM)
    M("c_paint_black", 0x2C2A34, rim=0.25, soft=0.1, outline=0.6, **sh)
    M("c_cable", 0x2A2832, rim=0.2, soft=0.1, outline=0.0, **sh)
    M("c_porcelain", 0xF4F2EC, spec=0.6, rim=0.3, soft=0.06, outline=0.5, **sh)
    M("c_moss", 0x86B394, emis=0.08, rim=0.3, soft=0.1, outline=0.4, **sh)
    M("c_mushroom", 0xE0A9C0, emis=0.15, rim=0.3, soft=0.08, outline=0.5, **sh)
    M("c_loco", 0x2F7A6A, spec=0.35, rim=0.35, soft=0.08, shadow=SHADOW)
    M("c_loco_trim", 0xF2C230, spec=0.3, rim=0.3, soft=0.08, shadow=SHADOW_WARM)
    M("c_glass", 0x9FD8F0, spec=1.0, rim=0.5, soft=0.05, emis=0.25, flags=E.F_GLASS)
    M("c_strap", 0x3A2E2A, rim=0.25, soft=0.1, shadow=SHADOW_WARM)
    M("c_canvas", 0xF2D98A, rim=0.3, soft=0.12, outline=0.6, shadow=SHADOW_WARM)          # ventilation duct
    M("c_canvas_ring", 0xC99A48, rim=0.2, soft=0.1, outline=0.4, shadow=SHADOW_WARM)
    M("c_cable_orange", 0xE58A4A, rim=0.25, soft=0.1, outline=0.0, shadow=SHADOW_WARM)
    M("c_void", 0x16122A, emis=1.0, rim=0.0, soft=0.0, outline=0, flags=E.F_NOCAST)       # a side gallery's dark


# ----------------------------------------------------------------------------- helpers

def _grid(m, rings, inward=True, smooth=True):
    """Faces between consecutive rings (open profiles) with explicit winding: no normal recalculation, so
    a vault built from rings that run left wall -> crown -> right wall faces the inside of the tunnel."""
    bm = m.bm
    vr = [[bm.verts.new(m.M @ V(p)) for p in ring] for ring in rings]
    for i in range(len(vr) - 1):
        a, b = vr[i], vr[i + 1]
        for j in range(len(a) - 1):
            q = (a[j], b[j], b[j + 1], a[j + 1]) if inward else (a[j], a[j + 1], b[j + 1], b[j])
            bm.faces.new(q)
    allv = [v for r in vr for v in r]
    for f in {f for v in allv for f in v.link_faces}:
        f.normal_update()
    return m._finish(allv, None, 'box', smooth)


def _catmull(pts, n):
    """Resample an open polyline through control points with a Catmull-Rom spline (n points total)."""
    P = [V(p) for p in pts]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    segs = len(pts) - 1
    out = []
    for k in range(n):
        t = k / (n - 1) * segs
        i = min(int(t), segs - 1)
        u = t - i
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u +
                          (-p0 + 3 * p1 - 3 * p2 + p3) * u * u * u))
    return out


def _orient(direction):
    """Rotation matrix taking +Z to `direction`."""
    d = V(direction).normalized()
    return d.to_track_quat('Z', 'Y').to_matrix().to_4x4()


def crystal(m, base, direction, length, radius, mat="c_crystal", seg=6, tip=0.32, twist=0.0):
    """One hexagonal quartz point along `direction` from `base`: a cloudy prism and a clearer pyramid tip."""
    m.mat(mat)
    m.push(Matrix.Translation(base) @ _orient(direction) @ Matrix.Rotation(twist, 4, 'Z'))
    body = length * (1 - tip)
    m.cyl((0, 0, body / 2), r=radius, r2=radius * 1.06, h=body, seg=seg, smooth=False)
    m.mat(mat + "_tip" if mat + "_tip" in E._MATS else mat)
    m.cyl((0, 0, body + length * tip * 0.15), r=radius * 1.06, r2=radius * 1.0, h=length * tip * 0.3, seg=seg,
          caps=False, smooth=False)
    m.cyl((0, 0, body + length * tip * 0.65), r=radius * 1.0, r2=0.0, h=length * tip * 0.7, seg=seg, caps=False,
          smooth=False)
    m.pop()


def crystal_cluster(m, base, normal, size=1.0, rnd=None, mats=("c_crystal",), n=7, lod=0):
    """A natural crystal group growing out of the rock along `normal`: a lumpy matrix-rock socket hides the bases,
    one dominant point, the rest falling off in size and leaning outward, mostly one mineral."""
    rnd = rnd or random.Random(1)
    nrm = V(normal).normalized()
    t1 = nrm.orthogonal().normalized()
    t2 = nrm.cross(t1)
    main = mats[0] if rnd.random() < 0.75 else rnd.choice(mats)
    m.push(Matrix.Translation(V(base)) @ _orient(nrm))
    _rock(m, (0, 0, 0.06 * size), 0.48 * size, rnd, s=(1.0, rnd.uniform(0.75, 1.0), 0.6), mat="c_rock_dark")
    if lod == 0:
        for j in range(2):
            a = rnd.random() * 2 * math.pi
            _rock(m, (math.cos(a) * 0.45 * size, math.sin(a) * 0.45 * size, 0.0), 0.16 * size, rnd, s=(1.0, 1.0, 0.7),
                  mat=rnd.choice(("c_rock_dark", "c_rock")))
    m.pop()
    count = n if lod == 0 else max(3, n // 2)
    for k in range(count):
        a = rnd.random() * 2 * math.pi
        lean = 0.1 if k == 0 else 0.3 + 0.5 * rnd.random()
        d = (nrm + (t1 * math.cos(a) + t2 * math.sin(a)) * lean).normalized()
        off = (t1 * math.cos(a) + t2 * math.sin(a)) * (0.0 if k == 0 else rnd.uniform(0.06, 0.26)) * size
        L = size * (1.0 if k == 0 else rnd.uniform(0.35, 0.75))
        mat = main if rnd.random() < 0.85 else rnd.choice(mats)
        crystal(m, tuple(V(base) + off), d, L, L * rnd.uniform(0.11, 0.15), mat, seg=6, tip=0.24, twist=rnd.random())


# ----------------------------------------------------------------------------- track

RAIL_PROF = None   # the Sakura Line profile (city.RAIL_PROF): same rail height, so vehicles.ore_cart sits on both


def _rail(m, x, y0, y1, z0=0.0, top="c_rail_top"):
    import city
    m.mat("c_rail")
    m.sweep([(x, y0, z0), (x, y1, z0)], [(-p[0], p[1]) for p in city.RAIL_PROF], closed=True, cap=True, up=(0, 0, 1))
    m.mat(top)
    m.box((x, (y0 + y1) / 2, z0 + 0.1612), (0.05, y1 - y0, 0.003), smooth=False)


def ties(m, lx, y0, y1, rnd, lod=0, pitch=0.75):
    """Rough timber ties under one track, slightly irregular like hand-laid mine track."""
    n = int(round((y1 - y0) / pitch))
    for k in range(n):
        y = y0 + (k + 0.5) * pitch + rnd.uniform(-0.04, 0.04)
        m.mat("c_tie" if rnd.random() > 0.25 else "c_timber_dark", uvscale=1.0)
        m.push(Matrix.Translation((lx + rnd.uniform(-0.05, 0.05), y, -0.07)) @
               Matrix.Rotation(math.radians(rnd.uniform(-3, 3)), 4, 'Z'))
        L = rnd.uniform(1.75, 1.95)
        if lod == 0:
            m.extrude([(-L / 2, -0.12), (L / 2, -0.115), (L / 2 - 0.02, 0.12), (-L / 2 + 0.03, 0.115)], 0.14,
                      bevel=(0.012, 1))
        else:
            m.box((0, 0, 0), (L, 0.24, 0.14), smooth=False)
        m.pop()
        if lod == 0:
            # dog spikes and tie plates where the rails cross
            m.mat("c_iron_dark")
            for s in (-1, 1):
                rx = lx + s * GAUGE / 2
                m.box((rx, y, 0.004), (0.15, 0.16, 0.008), smooth=False)
                for side in (-1, 1):
                    m.box((rx + side * 0.045, y + side * 0.04, 0.02), (0.02, 0.02, 0.03), smooth=False)


def cave_track(lod=0, seg=SEG, seed=5, lanes=LANES, name="cave_track"):
    """Mine tracks over a packed earth floor with a gravel shoulder along each rail pair."""
    rnd = random.Random(seed)
    m = E.Mesher(name)
    m.mat("c_floor", uvscale=3.0)
    m.poly([(-6.4, 0, FLOOR), (6.4, 0, FLOOR), (6.4, seg, FLOOR), (-6.4, seg, FLOOR)])   # runs in under the vault foot
    for lx in lanes:
        # low gravel bed under each track
        m.mat("c_ballast", uvscale=1.2)
        m.poly([(lx - 0.95, 0, -0.06), (lx + 0.95, 0, -0.06), (lx + 0.95, seg, -0.06), (lx - 0.95, seg, -0.06)])
        for s in (-1, 1):
            x0, x1 = lx + s * 0.95, lx + s * 1.15
            pts = [(x0, 0, -0.06), (x1, 0, FLOOR + 0.005), (x1, seg, FLOOR + 0.005), (x0, seg, -0.06)]
            m.poly(pts if s > 0 else pts[::-1])
        ties(m, lx, 0, seg, rnd, lod)
        for s in (-1, 1):
            _rail(m, lx + s * GAUGE / 2, 0, seg)
    return m.obj(name + ("" if lod == 0 else "@1"), smooth_angle=30)


# ----------------------------------------------------------------------------- shell

# right half of the vault (x, z), floor edge -> crown; mirrored for the left half
VAULT = [(4.4, FLOOR - 0.02), (5.5, 0.05), (6.2, 0.8), (6.6, 2.2), (6.5, 3.8), (6.0, 5.3), (5.0, 6.6), (3.5, 7.6),
         (1.8, 8.2), (0.0, 8.45)]


def vault_profile(n_half=22):
    """Full section left floor -> crown -> right floor as (x, z, nx, nz) with the inward normal."""
    half = _catmull([V((x, z, 0)) for x, z in VAULT], n_half)      # right floor -> crown
    left = [V((-p.x, p.y, 0)) for p in half]                          # left floor -> crown
    pts = left + half[::-1][1:]
    out = []
    for i, p in enumerate(pts):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        t = (b - a).normalized()          # runs left floor -> crown -> right floor
        nrm = V((t.y, -t.x, 0))            # rotate +90: points inward (toward the tunnel axis)
        out.append((p.x, p.y, nrm.x, nrm.y))
    # arc length along the profile, for the displacement field
    s, acc = [0.0], 0.0
    for i in range(1, len(out)):
        acc += math.hypot(out[i][0] - out[i - 1][0], out[i][1] - out[i - 1][1])
        s.append(acc)
    return out, s


def _wave(rnd, terms):
    """Random sum of sines in (s, y): y frequencies are whole cycles per segment so the field is periodic."""
    ws = [(rnd.uniform(0.2, 0.9) * f, rnd.random() * 6.283, k, rnd.uniform(0.5, 1.0) * a) for (f, k, a) in terms]

    def fn(s, y):
        return sum(a * math.sin(f * s + ph + 2 * math.pi * k * y / SEG) for (f, ph, k, a) in ws)
    return fn


_SHARED = _wave(random.Random(7), [(1.0, 0, 0.35), (2.3, 0, 0.18), (4.1, 0, 0.08)])


def shell_point(x, z, nx, nz, s, y, seed):
    """Displaced vault surface point. The displacement pushes rock out (negative = away from the axis)
    except near the floor, adds strata ledges, and varies with the seed only in the middle of the segment."""
    var = _wave(random.Random(seed * 31 + 3), [(0.8, 1, 0.45), (1.7, 2, 0.25), (3.3, 3, 0.12), (6.0, 2, 0.05)])
    w = math.sin(math.pi * (y % SEG) / SEG) ** 2
    amp = min(1.0, max(0.0, (z - 0.1) / 1.4))
    d = amp * (_SHARED(s, 0.0) + w * var(s, y))
    # strata: a terraced step every 1.15 m of height, lips pushed in
    if z < 6.6:
        f = (z / 1.15) % 1.0
        d += amp * 0.3 * (f ** 3)
    d -= amp * 0.25          # bias outward so the lanes keep their clearance
    return V((x + nx * d, y, z + nz * d))


def cave_shell(lod=0, seed=1, seg=SEG):
    """The rock vault as big flat facets (flat shaded, ink on the ledge lips), like the chunky stone in an anime
    background rather than a smooth noisy surface."""
    prof, arc = vault_profile(15 if lod == 0 else 9)
    rows = int(seg / (1.0 if lod == 0 else 2.0)) + 1
    rings = []
    for r in range(rows):
        y = seg * r / (rows - 1)
        rings.append([tuple(shell_point(x, z, nx, nz, arc[i], y, seed)) for i, (x, z, nx, nz) in enumerate(prof)])
    m = E.Mesher("cave_shell")
    m.mat("c_rock", uvscale=2.5)
    _grid(m, rings, inward=True)
    return m.obj("cave_shell_%d" % seed + ("" if lod == 0 else "@1"), smooth_angle=18)


_PROF0 = {}


def _shell_mesh_at(i, t, y, seed):
    """Point on the LOD0 cave_shell mesh itself: between profile vertices i and i+1 (t 0..1) and between the 1 m
    rows around y. Placing deco on the facets, not on the smooth field, keeps it from floating or sinking where
    the mesh cuts across the strata steps."""
    if not _PROF0:
        _PROF0["p"] = vault_profile(15)
    prof, arc = _PROF0["p"]
    ya = math.floor(y)
    u = y - ya

    def P(k, yy):
        x, z, nx, nz = prof[k]
        return shell_point(x, z, nx, nz, arc[k], yy, seed)
    a = P(i, ya).lerp(P(i + 1, ya), t)
    b = P(i, ya + 1.0).lerp(P(i + 1, ya + 1.0), t)
    n = V(prof[i][2:]).lerp(V(prof[i + 1][2:]), t)
    return a.lerp(b, u), V((n.x, 0, n.y)).normalized()


def _surface_at(px, pz_hint, y, seed, side):
    """Point and inward normal on the shell mesh at height pz_hint on one side (+1 right, -1 left)."""
    if not _PROF0:
        _PROF0["p"] = vault_profile(15)
    prof = _PROF0["p"][0]
    for i in range(len(prof) - 1):
        (x0, z0), (x1, z1) = prof[i][:2], prof[i + 1][:2]
        if (x0 + x1 > 0) != (side > 0) or z0 == z1:
            continue
        t = (pz_hint - z0) / (z1 - z0)
        if 0.0 <= t <= 1.0:
            return _shell_mesh_at(i, t, y, seed)
    raise ValueError("no wall at z=%.2f" % pz_hint)


def _ceiling_at(x_hint, y, seed):
    if not _PROF0:
        _PROF0["p"] = vault_profile(15)
    prof = _PROF0["p"][0]
    for i in range(len(prof) - 1):
        (x0, z0), (x1, z1) = prof[i][:2], prof[i + 1][:2]
        if min(z0, z1) > 4.5 and x0 != x1:
            t = (x_hint - x0) / (x1 - x0)
            if 0.0 <= t <= 1.0:
                return _shell_mesh_at(i, t, y, seed)
    return _surface_at(0, 5.0, y, seed, 1 if x_hint > 0 else -1)


def _ledge(m, side, y, z, L, seed, rnd, palette, lod=0):
    """A rock shelf jutting from the wall at height z, L long: flat top with a jagged front lip, its back buried in
    the rock, sometimes a crystal group and glowing mushrooms on it, and glowing moss hanging over the edge."""
    ws = [abs(_surface_at(0, z, yy, seed, side)[0].x) for yy in (y - L / 2, y, y + L / 2)]
    back = max(ws) + 0.35
    front = min(ws) - rnd.uniform(0.55, 0.85)
    n = 6
    lip = []
    for j in range(n + 1):
        t = j / n
        taper = math.sin(math.pi * t) ** 0.6           # the ends tuck back into the wall
        xa = front + (1 - taper) * (back - 0.3 - front) + rnd.uniform(-0.1, 0.1) * taper
        lip.append((side * xa, y - L / 2 + L * t))
    outline = lip + [(side * back, y + L / 2), (side * back, y - L / 2)]
    th = rnd.uniform(0.22, 0.32)
    m.mat("c_rock", uvscale=1.5)
    m.extrude(outline, th, c=(0, 0, z), bevel=(0.03, 1) if lod == 0 else None)
    top = z + th / 2
    xm = side * (front + 0.35)
    if rnd.random() < 0.5:
        crystal_cluster(m, (xm, y + rnd.uniform(-L / 4, L / 4), top), (-side * 0.25, rnd.uniform(-0.3, 0.3), 1.0),
                        size=rnd.uniform(0.45, 0.8), rnd=rnd, mats=palette, n=5 if lod == 0 else 2, lod=lod)
    if lod == 0:
        _mushrooms(m, xm + side * 0.15, y + rnd.uniform(-L / 3, L / 3), top, rnd, n=rnd.randint(3, 5), spread=0.12)
        m.mat("c_moss")
        for j in range(1, n):
            if rnd.random() < 0.55:
                x0, yy = lip[j]
                h = rnd.uniform(0.25, 0.8)
                m.tube([(x0 + side * 0.03, yy, z - th / 2 + 0.02), (x0 - side * 0.02, yy + 0.03, z - th / 2 - h * 0.5),
                        (x0 - side * 0.04, yy, z - th / 2 - h)], r=0.035, seg=5, taper=0.4)
        m.ico((xm + side * 0.2, y, top), 0.22, 1, s=(1.0, 2.0, 0.25))


def cave_deco(lod=0, seed=1, seg=SEG):
    """Crystals on the walls, stalactites, stalagmites and a puddle, fitted to cave_shell(seed)."""
    rnd = random.Random(seed * 17 + 1)
    m = E.Mesher("cave_deco")
    palette = [("c_crystal",), ("c_crystal", "c_crystal_violet"), ("c_crystal_pink", "c_crystal_violet")][seed % 3]
    def outcrop(side, y, z, big):
        """Crystals the way they occur in rock: one dominant group and one to three smaller ones close by, all
        growing out of the wall, rather than single points dotted evenly about."""
        p, nrm = _surface_at(0, z, y, seed, side)
        crystal_cluster(m, tuple(p), (nrm + V((0, 0, 0.3))).normalized(), size=big, rnd=rnd, mats=palette,
                        n=rnd.randint(6, 9), lod=lod)
        for j in range(rnd.randint(1, 3) if lod == 0 else 0):
            q, qn = _surface_at(0, z + rnd.uniform(-0.5, 0.5), y + rnd.uniform(-0.9, 0.9), seed, side)
            crystal_cluster(m, tuple(q), (qn + V((0, 0, 0.2))).normalized(), size=big * rnd.uniform(0.3, 0.5),
                            rnd=rnd, mats=palette, n=rnd.randint(3, 5), lod=lod)

    # crystal outcrops above the boards, sometimes a second one higher up, and a group at the wall foot
    for side in (-1, 1):
        outcrop(side, rnd.uniform(2.0, seg - 2.0), rnd.uniform(3.0, 4.2), rnd.uniform(1.0, 1.5))
        if rnd.random() < 0.5:
            outcrop(side, rnd.uniform(1.5, seg - 1.5), rnd.uniform(4.8, 6.0), rnd.uniform(0.7, 1.0))
        if rnd.random() < 0.6:
            y = rnd.uniform(1.5, seg - 1.5)
            crystal_cluster(m, (side * rnd.uniform(4.75, 5.1), y, FLOOR), (side * -0.45, rnd.uniform(-0.2, 0.2), 1.0),
                            size=rnd.uniform(0.8, 1.3), rnd=rnd, mats=palette, n=rnd.randint(6, 9), lod=lod)
            crystal_cluster(m, (side * rnd.uniform(4.6, 5.0), y + rnd.uniform(0.5, 0.9) * rnd.choice((-1, 1)), FLOOR),
                            (side * -0.3, 0.0, 1.0), size=rnd.uniform(0.3, 0.45), rnd=rnd, mats=palette, n=4, lod=lod)
    # upper walls: rock ledges with mushrooms and hanging moss, boulders, rock bolts, a survey mark, moss
    for side in (-1, 1):
        for k in range(rnd.randint(2, 3) if lod == 0 else 1):
            _ledge(m, side, seg * (k + rnd.uniform(0.25, 0.75)) / 4, rnd.uniform(3.0, 5.4), rnd.uniform(1.6, 2.8), seed,
                   rnd, palette, lod)
        for k in range(rnd.randint(6, 9) if lod == 0 else 2):           # boulders standing out of the wall
            p, nrm = _surface_at(0, rnd.uniform(2.8, 7.0), rnd.uniform(0.3, seg - 0.3), seed, side)
            m.push(Matrix.Translation(p) @ _orient(nrm))
            _rock(m, (0, 0, 0), rnd.uniform(0.25, 0.6), rnd, s=(1.0, rnd.uniform(0.7, 1.2), 0.75),
                  mat=rnd.choice(("c_rock_dark", "c_rock_wet")))
            m.pop()
        if lod == 0:                                                   # rock bolts: plates and nuts in a loose grid
            for yb in (1.6, 4.6, 7.6, 10.6):
                for zb in (3.2, 4.6, 6.0):
                    if rnd.random() < 0.75:
                        p, nrm = _surface_at(0, zb + rnd.uniform(-0.3, 0.3), yb + rnd.uniform(-0.4, 0.4), seed, side)
                        m.push(Matrix.Translation(p) @ _orient(nrm) @ _R(rnd.uniform(-20, 20), 'Z'))
                        m.mat("c_iron_dark")
                        m.box((0, 0, 0.0), (0.18, 0.18, 0.04), smooth=False)
                        m.mat("c_rust")
                        m.cyl((0, 0, 0.04), r=0.035, h=0.05, seg=6, smooth=False)
                        m.pop()
            # a survey mark painted on the rock: a red ring round a white dot, and an arrow out
            p, nrm = _surface_at(0, rnd.uniform(3.0, 3.8), rnd.uniform(2.0, seg - 2.0), seed, side)
            m.push(Matrix.Translation(p + nrm * 0.03) @ _orient(nrm))
            m.mat("c_paint_red")
            m.cyl((0, 0, 0), r=0.16, h=0.02, seg=16)
            m.mat("c_paint_white")
            m.cyl((0, 0, 0.012), r=0.08, h=0.02, seg=12)
            m.mat("c_paint_white")
            m.poly([(0.25, -0.05, 0.01), (0.55, -0.05, 0.01), (0.55, -0.12, 0.01), (0.7, 0.0, 0.01), (0.55, 0.12, 0.01),
                    (0.55, 0.05, 0.01), (0.25, 0.05, 0.01)])
            m.pop()
        m.mat("c_moss")
        for k in range(rnd.randint(2, 4) if lod == 0 else 0):           # glowing moss up the wall
            p, nrm = _surface_at(0, rnd.uniform(2.8, 6.0), rnd.uniform(0.5, seg - 0.5), seed, side)
            m.push(Matrix.Translation(p) @ _orient(nrm))
            for j in range(3):
                m.ico((rnd.uniform(-0.2, 0.2), rnd.uniform(-0.25, 0.25), 0), rnd.uniform(0.15, 0.28), 1,
                      s=(1.0, 1.3, 0.25))
            m.pop()
        for k in range(rnd.randint(4, 7) if lod == 0 else 2):          # rubble along the wall foot
            _rock(m, (side * rnd.uniform(4.4, 5.3), rnd.uniform(0.3, seg - 0.3), FLOOR + 0.04),
                  rnd.uniform(0.08, 0.22), rnd, s=(1.0, 1.0, 0.6), mat=rnd.choice(("c_rock", "c_rock_dark")))
    # stalactites in groups from the vault
    m.mat("c_rock_wet", uvscale=1.0)
    for g in range(rnd.randint(5, 8) if lod == 0 else 3):
        xg = rnd.uniform(-5.0, 5.0)
        yg = rnd.uniform(0.5, seg - 0.5)
        for k in range(rnd.randint(2, 5) if lod == 0 else 2):
            p, nrm = _ceiling_at(xg + rnd.uniform(-0.6, 0.6), yg + rnd.uniform(-0.6, 0.6), seed)
            L = rnd.uniform(0.35, 1.5) * (1.0 if abs(p.x) > 3.6 else 0.8)
            r = L * rnd.uniform(0.13, 0.2)
            top = p - nrm * 0.25
            m.push(Matrix.Translation(top) @ Matrix.Rotation(math.radians(rnd.uniform(-6, 6)), 4, 'X'))
            n = 7 if lod == 0 else 5
            m.cyl((0, 0, -L * 0.3), r=r, r2=r * 1.15, h=L * 0.6, seg=n)
            m.cyl((0, 0, -L * 0.8), r=0.0, r2=r, h=L * 0.4, seg=n, caps=False)
            m.pop()
    # stalagmites at the wall foot
    for side in (-1, 1):
        for k in range(rnd.randint(1, 3)):
            x = side * rnd.uniform(4.65, 5.3)
            y = rnd.uniform(0.5, seg - 0.5)
            L = rnd.uniform(0.4, 1.3)
            r = L * rnd.uniform(0.2, 0.28)
            m.cyl((x, y, FLOOR + L * 0.2), r=r * 1.2, r2=r, h=L * 0.4, seg=8 if lod == 0 else 5)
            m.cyl((x, y, FLOOR + L * 0.7), r=r, r2=0.02, h=L * 0.6, seg=8 if lod == 0 else 5, caps=False)
    # glowing mushrooms and moss at the wall foot
    for side in (-1, 1):
        for k in range(rnd.randint(1, 3) if lod == 0 else 1):
            x, y = side * rnd.uniform(4.7, 5.1), rnd.uniform(0.8, seg - 0.8)
            _mushrooms(m, x, y, FLOOR, rnd, n=rnd.randint(3, 6))
        m.mat("c_moss")
        for k in range(rnd.randint(2, 4)):
            p, nrm = _surface_at(0, rnd.uniform(0.3, 2.5), rnd.uniform(0.5, seg - 0.5), seed, side)
            m.ico(tuple(p - nrm * 0.02), rnd.uniform(0.18, 0.35), 1, s=(1.0, 1.0, 0.35))
    # a puddle between the tracks (catches the crystal glow)
    if rnd.random() < 0.8:
        m.mat("c_water")
        x = rnd.choice((-1.2, 1.2))
        y = rnd.uniform(2, seg - 2)
        pts = [(x + 0.55 * math.cos(a) * (1 + 0.25 * math.sin(3 * a + seed)), y + 1.1 * math.sin(a), FLOOR + 0.012)
               for a in [2 * math.pi * i / 16 for i in range(16)]]
        m.poly(pts)
    return m.obj("cave_deco_%d" % seed + ("" if lod == 0 else "@1"), smooth_angle=35)


# ----------------------------------------------------------------------------- mine frame & services

def lantern(m, c, lod=0):
    """Mine lantern on a short chain: iron cage, glowing glass, brass cap. c = hook point."""
    x, y, z = c
    m.mat("c_iron_dark")
    for k in range(4 if lod == 0 else 1):
        m.torus((x, y, z - 0.05 - k * 0.07), R=0.022, r=0.006, seg=8, sides=4, axis='X' if k % 2 else 'Y')
    zl = z - 0.62
    m.mat("c_brass")
    m.cyl((x, y, zl + 0.2), r=0.1, r2=0.04, h=0.08, seg=12)
    m.cyl((x, y, zl - 0.15), r=0.11, h=0.04, seg=12)
    m.mat("c_lamp")
    m.cyl((x, y, zl + 0.03), r=0.075, r2=0.085, h=0.3, seg=12)
    m.mat("c_lamp_hot")
    m.sphere((x, y, zl + 0.0), 0.035, 8, 5)
    m.mat("c_iron_dark")
    for a in range(0, 360, 90 if lod == 0 else 180):
        ca, sa = math.cos(math.radians(a + 45)), math.sin(math.radians(a + 45))
        m.box((x + ca * 0.095, y + sa * 0.095, zl + 0.03), (0.014, 0.014, 0.34), smooth=False)
    m.torus((x, y, zl + 0.28), R=0.03, r=0.007, seg=8, sides=4, axis='Y')
    return V((x, y, zl + 0.03))


LANTERN_X = 3.9
LANTERN_Z = 5.25 - 0.62 + 0.03


def cave_frame(lod=0):
    """Timber support set at y = 0: posts, cap beam, knee braces, roof struts with wedges, two lanterns."""
    m = E.Mesher("cave_frame")
    top = 5.35
    for s in (-1, 1):
        x = s * 5.3
        m.mat("c_timber", uvscale=1.0)
        m.box((x, 0, (FLOOR + top) / 2), (0.3, 0.3, top - FLOOR), bevel=(0.02, 1) if lod == 0 else None, smooth=False)
        m.mat("c_rock_dark")
        m.box((x, 0, FLOOR + 0.06), (0.44, 0.44, 0.14), smooth=False)                # sill stone
        m.mat("c_timber_dark")
        m.push(Matrix.Translation((s * 4.75, 0, top - 0.45)) @ Matrix.Rotation(math.radians(s * 45), 4, 'Y'))
        m.box((0, 0, 0), (0.18, 0.18, 1.25), smooth=False)                             # knee brace
        m.pop()
        if lod == 0:
            m.mat("c_iron_dark")
            for z in (top - 0.12, top - 0.88):
                m.box((x, -0.155, z), (0.34, 0.012, 0.06), smooth=False)               # iron strap
                m.cyl((x, -0.165, z), r=0.018, h=0.02, seg=8, axis='Y')                # bolt head
    m.mat("c_timber", uvscale=1.0)
    m.box((0, 0, top + 0.17), (12.0, 0.32, 0.34), bevel=(0.02, 1) if lod == 0 else None, smooth=False)  # cap
    # roof struts with wedges up to the rock
    for x in (-3.0, 3.0):
        m.mat("c_timber_dark")
        m.box((x, 0, top + 1.2), (0.22, 0.22, 1.75), smooth=False)
        m.box((x, 0, top + 2.1), (0.6, 0.3, 0.12), smooth=False)
    # hazard bands on the posts: yellow and black, like the Sakura Line poles and crossing gates
    for s in (-1, 1):
        for k in range(5):
            m.mat("c_paint_yellow" if k % 2 == 0 else "c_paint_black")
            m.box((s * 5.3, 0, 0.7 + k * 0.16), (0.31, 0.31, 0.16), smooth=False)
    # lagging: rough boards behind the posts holding the wall back, running to the next set (6 m on)
    rnd = random.Random(23)
    for s in (-1, 1):
        z = 0.15
        while z < 2.6:
            h = rnd.uniform(0.2, 0.26)
            m.mat("c_plank" if rnd.random() > 0.3 else "c_timber_dark", uvscale=1.0)
            m.push(Matrix.Translation((s * 5.52, 3.0, z + h / 2)) @ Matrix.Rotation(math.radians(rnd.uniform(-1.2, 1.2)), 4, 'X'))
            m.box((0, 0, 0), (0.05, 5.7, h - 0.03), smooth=False)
            m.pop()
            z += h
        # cable run on porcelain insulators along the boards, sagging between the sets
        if lod == 0:
            pts = [(s * 5.12, y, 3.0 - 0.18 * math.sin(math.pi * y / 6.0)) for y in [6.0 * i / 12 for i in range(13)]]
            m.mat("c_cable")
            m.sweep(pts, [(0.018 * math.cos(a), 0.018 * math.sin(a)) for a in [2 * math.pi * i / 6 for i in range(6)]],
                    closed=True, cap=False, up=(0, 0, 1))
            m.mat("c_porcelain")
            m.cyl((s * 5.12, 0, 3.04), r=0.045, r2=0.03, h=0.09, seg=8)
            m.mat("c_iron_dark")
            m.box((s * 5.2, 0, 3.08), (0.18, 0.025, 0.025), smooth=False)
    # crown boards over the cap beams, between the struts
    for x in (-1.8, -0.6, 0.6, 1.8):
        m.mat("c_plank", uvscale=1.0)
        m.box((x, 3.0, top + 0.37), (0.9, 5.7, 0.06), smooth=False)
    # lanterns hang from the cap beam outside the lanes
    for s in (-1, 1):
        lantern(m, (s * LANTERN_X, 0, top), lod)
    ob = m.obj("cave_frame" if lod == 0 else "cave_frame@1", smooth_angle=30)
    if lod == 0:
        E.finish_hard(ob, width=0.01, segments=1, angle=35)
    return ob


def cave_pipe(lod=0, seg=SEG):
    """Compressed-air pipe with flanges and a power cable on brackets along the right wall (x ~ 5.9, z 2.6)."""
    m = E.Mesher("cave_pipe")
    x, z = 5.95, 2.6
    m.mat("c_rust")
    m.cyl((x, seg / 2, z), r=0.11, h=seg, seg=14 if lod == 0 else 8, axis='Y')
    for k in range(2):
        y = k * 6.0 + 0.2
        m.mat("c_rust", tint=0xBFA090)
        m.cyl((x, y, z), r=0.15, h=0.06, seg=14 if lod == 0 else 8, axis='Y')
        m.mat("c_iron_dark")
        m.box((x + 0.25, y + 0.5, z - 0.05), (0.5, 0.08, 0.06), smooth=False)          # bracket into the rock
        m.box((x + 0.25, y + 0.5, z + 0.5), (0.5, 0.08, 0.06), smooth=False)
    m.mat("c_strap")
    pts = []
    for k in range(3):
        a, b = V((x - 0.02, k * 6.0 + 0.5, z + 0.52)), V((x - 0.02, (k + 1) * 6.0 + 0.5, z + 0.52))
        pts += E.catenary(a, b, sag=0.18, n=10 if lod == 0 else 4)[(0 if k == 0 else 1):]
    pts = [p for p in pts if p[1] <= seg + 0.01] + [(x - 0.02, seg, z + 0.52 - 0.0)]
    m.tube(pts, r=0.03, seg=6 if lod == 0 else 4, cap=False)
    # a canvas ventilation duct hung high on the left wall, above the frames' cap beams, ribbed every 0.6 m
    dx, dz, dr = -4.6, 6.1, 0.38
    m.mat("c_canvas", uvscale=1.0)
    m.cyl((dx, seg / 2, dz), r=dr, h=seg, seg=16 if lod == 0 else 8, axis='Y')
    m.mat("c_canvas_ring")
    for k in range(int(seg / 0.6)):
        y = 0.3 + k * 0.6
        if lod == 0 or k % 3 == 0:
            m.torus((dx, y, dz), R=dr + 0.005, r=0.025, seg=16 if lod == 0 else 8, sides=4, axis='Y')
    m.mat("c_iron_dark")
    for k in range(int(seg / 1.2)):
        y = 0.6 + k * 1.2
        m.cyl((dx - 0.15, y, dz + dr + 0.45), r=0.01, h=0.9, seg=4)                     # hanger wires
    # a cable tray on the right wall above the boards: three cables on brackets
    tx, tz = 5.75, 4.3
    m.mat("c_iron_dark")
    m.box((tx, seg / 2, tz - 0.03), (0.42, seg, 0.025), smooth=False)
    m.box((tx - 0.2, seg / 2, tz + 0.02), (0.02, seg, 0.1), smooth=False)
    for k in range(int(seg / 1.5)):
        m.box((tx + 0.25, 0.75 + k * 1.5, tz - 0.08), (0.6, 0.05, 0.05), smooth=False)
    for j, mat in enumerate(("c_cable", "c_cable_orange", "c_iron") if lod == 0 else ("c_cable_orange",)):
        m.mat(mat)
        m.cyl((tx - 0.12 + j * 0.12, seg / 2, tz + 0.03), r=0.04, h=seg, seg=8 if lod == 0 else 5, axis='Y')
    return m.obj("cave_pipe" if lod == 0 else "cave_pipe@1", smooth_angle=40)


# ----------------------------------------------------------------------------- creatures & gear

def _bat_into(m, pose="up"):
    """Bat geometry into an existing Mesher at its current transform, facing -Y (0.6 m wingspan). A furry body
    longer than it is wide, a big-eared head with a snout, and real bat wings: arm and four long fingers from the
    wrist with the membrane stretched between them, scalloped between the finger tips and joined to the legs.
    pose 'up' / 'down' are the top and bottom of the wingbeat (a two-frame flip-book)."""
    m.mat("c_bat")
    m.sphere((0, 0.01, 0), 0.036, 12, 8, s=(1.0, 1.7, 1.0))                            # body
    m.sphere((0, -0.064, 0.012), 0.032, 12, 8, s=(1.05, 0.95, 0.95))                  # head
    m.sphere((0, -0.093, 0.004), 0.015, 8, 6, s=(1.1, 1.0, 0.8))                      # snout
    m.mat("c_bat_belly")
    m.sphere((0, 0.0, -0.014), 0.028, 10, 6, s=(0.9, 1.8, 0.8))                      # paler chest and belly
    m.mat("c_bat_ear")
    m.sphere((0, -0.107, 0.008), 0.006, 6, 4)                                         # nose
    for sx in (-1, 1):
        m.push(Matrix.Translation((sx * 0.019, -0.066, 0.036)) @ _orient((sx * 0.5, -0.15, 1.0)))
        m.mat("c_bat")
        m.cyl((0, 0, 0.032), r=0.02, r2=0.0, h=0.064, seg=4, smooth=False)            # tall pointed ears
        m.mat("c_bat_ear")
        m.cyl((0, -0.009, 0.026), r=0.011, r2=0.0, h=0.046, seg=4, smooth=False)
        m.pop()
        m.mat("c_eye")
        m.sphere((sx * 0.013, -0.091, 0.021), 0.0065, 6, 4)
        m.mat("c_porcelain")
        m.cyl((sx * 0.006, -0.103, -0.006), r=0.0035, r2=0.0, h=0.012, seg=4)          # fangs (pointing down)
        m.mat("c_bat")
        m.tube([(sx * 0.012, 0.05, -0.012), (sx * 0.02, 0.085, -0.022)], r=0.005, seg=4)   # legs trailing back
    m.mat("c_bat_wing")
    for tri in (((-0.02, 0.085, -0.022), (0.0, 0.055, -0.006), (0.02, 0.085, -0.022)),):   # tail membrane
        m.poly(list(tri))
    up = pose == "up"
    for sx in (-1, 1):
        S = V((sx * 0.03, -0.01, 0.012))
        E_ = V((sx * 0.10, 0.0, 0.07)) if up else V((sx * 0.10, -0.02, -0.035))
        W = V((sx * 0.17, -0.03, 0.12)) if up else V((sx * 0.17, -0.04, -0.07))
        if up:
            tips = [V((sx * 0.30, -0.02, 0.17)), V((sx * 0.31, 0.06, 0.13)), V((sx * 0.26, 0.12, 0.07)),
                    V((sx * 0.16, 0.13, 0.025))]
        else:
            tips = [V((sx * 0.29, -0.03, -0.12)), V((sx * 0.29, 0.05, -0.15)), V((sx * 0.23, 0.11, -0.13)),
                    V((sx * 0.14, 0.11, -0.07))]
        A = V((sx * 0.025, 0.06, -0.008))
        edge = [tips[0]]
        for a, b in zip(tips, tips[1:] + [A]):
            mid = (a + b) / 2
            edge += [mid + (W - mid) * 0.22, b]
        m.mat("c_bat_wing")
        faces = [(S, E_, W), (S, W, A)] + [(W, edge[i], edge[i + 1]) for i in range(len(edge) - 1)]
        for f in faces:
            m.poly([tuple(p) for p in (f if sx > 0 else f[::-1])])
        m.mat("c_bat")
        m.tube([tuple(S), tuple(E_), tuple(W)], r=0.007, seg=5)                          # arm
        for t in tips:
            m.tube([tuple(W), tuple(t)], r=0.0035, seg=4)                              # finger bones
        m.cyl(tuple(W + V((0, -0.014, 0.008))), r=0.006, r2=0.0, h=0.022, seg=4)       # thumb claw


def bat(pose="up", lod=0):
    """Ambient cave bat, facing -Y. pose: 'up' / 'down' wing frames for a flip-book flap."""
    m = E.Mesher("bat")
    _bat_into(m, pose)
    return m.obj("bat_" + pose + ("" if lod == 0 else "@1"), smooth_angle=40)


def hotaru_lamp():
    """Hotaru Lamp: brass headlamp with a ribbed reflector, warm lens, battery pack and a leather strap.
    Origin at the centre of the strap loop (her head), lamp facing -Y."""
    m = E.Mesher("hotaru_lamp")
    R = 0.105
    m.mat("c_strap")
    m.torus((0, 0, 0), R=R, r=0.012, seg=32, sides=6, axis='Z')
    m.torus((0, 0, 0.02), R=R * 0.9, r=0.008, seg=24, sides=4, axis='X', arc=180.0)   # over-the-top band
    m.push(Matrix.Translation((0, -R - 0.02, 0.005)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
    m.mat("c_brass")
    m.lathe([(0.0, 0.0), (0.03, 0.0), (0.035, 0.012), (0.042, 0.03), (0.046, 0.05), (0.04, 0.052)], seg=24)
    for k in range(6):
        m.box((0.042 * math.cos(k * math.pi / 3), 0.042 * math.sin(k * math.pi / 3), 0.03), (0.006, 0.006, 0.04))
    m.mat("c_lamp_hot")
    m.cyl((0, 0, 0.052), r=0.037, h=0.006, seg=24)
    m.mat("c_lamp")
    m.cyl((0, 0, 0.057), r=0.03, h=0.004, seg=24)
    m.pop()
    m.mat("c_brass")
    m.rbox((0, R + 0.03, 0.0), (0.08, 0.04, 0.05), r=0.01)                            # battery box on the back
    m.mat("c_iron_dark")
    m.cyl((0.03, R + 0.05, 0.0), r=0.006, h=0.01, seg=8, axis='Y')
    ob = m.obj("hotaru_lamp", smooth_angle=35)
    E.finish_hard(ob, width=0.003, segments=1, angle=35)
    return ob


# ----------------------------------------------------------------------------- obstacles

def _rock(m, c, r, rnd, s=(1, 1, 1), mat="c_rock_dark", sub=1):
    """A lumpy boulder (icosphere jittered then flattened by s)."""
    m.mat(mat, uvscale=0.8)
    faces = m.ico(c, r, sub, s=s, smooth=True)
    for v in {v for f in faces for v in f.verts}:
        d = (v.co - m.M @ V(c))
        v.co += d * rnd.uniform(-0.12, 0.12)


def _R(deg, axis):
    return Matrix.Rotation(math.radians(deg), 4, axis)


def _floor_z(x):
    """Ground height at x across a track (an obstacle's origin is on its lane centre): the gravel bed out to 0.95 m,
    its shoulder, then the earth floor. Anything an obstacle stands on the ground with goes down to this."""
    ax = abs(x)
    if ax <= 0.95:
        return -0.06
    if ax >= 1.15:
        return FLOOR
    return -0.06 + (FLOOR + 0.06) * (ax - 0.95) / 0.2


def _contact_shadow(m, cx, cy, rx, ry, mat="c_contact"):
    """A soft cel contact shadow (decal) on the ground under an obstacle: an ellipse of half-size rx, ry around
    (cx, cy) that follows the gravel bed and the floor. Over the bed it lies on the tie tops, so the ties and the
    gravel between them both darken."""
    def zs(x):
        return 0.006 if abs(x) <= 0.9 else _floor_z(x) + 0.008
    # the ground only changes height across the track, so one strip of quads split at the bed's edges is enough
    xs = sorted({cx - rx, cx + rx} | {b for b in (-1.15, -1.05, -0.95, -0.9, 0.9, 0.95, 1.05, 1.15) if cx - rx < b < cx + rx})
    y0, y1 = cy - ry, cy + ry
    m.mat(mat)
    faces = []
    for xa, xb in zip(xs, xs[1:]):
        faces += m.poly([(xa, y0, zs(xa)), (xb, y0, zs(xb)), (xb, y1, zs(xb)), (xa, y1, zs(xa))], uv=None)
    m.uv_rect(faces, 0, 0, 1, 1, axis=((1, 0, 0), (0, 1, 0)))


def _mushrooms(m, x, y, z, rnd, n=4, spread=0.18, hmin=0.06, hmax=0.16):
    """A tuft of glowing pink mushrooms: pale stalks, flat caps."""
    for j in range(n):
        h = rnd.uniform(hmin, hmax)
        px, py = x + rnd.uniform(-spread, spread), y + rnd.uniform(-spread * 1.4, spread * 1.4)
        m.mat("c_porcelain")
        m.cyl((px, py, z + h / 2), r=0.012, h=h, seg=5)
        m.mat("c_mushroom")
        m.sphere((px, py, z + h), h * 0.45, 8, 4, s=(1.0, 1.0, 0.55))


def _gravel(m, x0, x1, y0, y1, rnd, n=10, rmin=0.05, rmax=0.11):
    """Loose pebbles and chips on the floor."""
    for k in range(n):
        x, r = rnd.uniform(x0, x1), rnd.uniform(rmin, rmax)
        _rock(m, (x, rnd.uniform(y0, y1), _floor_z(x) + r * 0.2), r, rnd, s=(1.0, 1.0, 0.6),
              mat=rnd.choice(("c_rock", "c_rock_dark", "c_rock")))


def _shards(m, x0, x1, y0, y1, rnd, n=4, mats=("c_crystal", "c_crystal_violet", "c_crystal_pink")):
    """Loose crystal points lying or standing on the floor."""
    for k in range(n):
        x = rnd.uniform(x0, x1)
        crystal(m, (x, rnd.uniform(y0, y1), _floor_z(x) - 0.01),
                (rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6), 1.0), rnd.uniform(0.12, 0.26), 0.035,
                rnd.choice(mats), twist=rnd.random())


def _chain(m, top, n=5, link=0.07):
    """A short hanging chain (links alternate planes) from `top` down; returns the bottom point."""
    x, y, z = top
    for k in range(n):
        m.torus((x, y, z - link * 0.6 - k * link), R=link * 0.33, r=link * 0.085, seg=8, sides=4,
                axis='X' if k % 2 else 'Y')
    return (x, y, z - link * (n + 0.2))


def _hard_hat(m, c, yaw=0.0):
    """A miner's yellow helmet with a lamp, hung on a nail."""
    m.push(Matrix.Translation(c) @ _R(yaw, 'Z') @ _R(-12, 'X'))
    m.mat("c_paint_yellow")
    m.sphere((0, 0, 0), 0.13, 12, 6, s=(1.0, 1.12, 0.8))
    m.cyl((0, 0, -0.005), r=0.16, h=0.015, seg=14, r2=0.17)
    m.mat("c_lamp_hot")
    m.cyl((0, -0.13, 0.04), r=0.03, h=0.03, seg=10, axis='Y')
    m.pop()


def rockpile(name="ob_rockpile", seed=3):
    """SIDE: rubble from a roof fall heaped over one track (top ~0.9 m) with a broken timber and crystal shards.
    The cart cannot ride over it: tilt onto another track."""
    rnd = random.Random(seed)
    m = E.Mesher(name)
    _contact_shadow(m, 0.0, -0.08, 1.4, 0.78)
    for k in range(9):
        x = rnd.uniform(-0.8, 0.8)
        y = rnd.uniform(-0.25, 0.25)
        r = rnd.uniform(0.28, 0.42) * (1.0 - abs(x) * 0.3)
        _rock(m, (x, y, r * 0.55), r, rnd, s=(1.0, 0.9, 0.75), mat=rnd.choice(("c_rock_dark", "c_rock")))
    for k in range(4):                     # second layer: the heap peaks around 0.9 m
        x = rnd.uniform(-0.55, 0.55)
        r = rnd.uniform(0.24, 0.32)
        _rock(m, (x, rnd.uniform(-0.12, 0.12), 0.62 - abs(x) * 0.3), r, rnd, s=(1.0, 0.9, 0.8),
              mat=rnd.choice(("c_rock_dark", "c_rock")))
    for k in range(5):
        x, r = rnd.uniform(-1.0, 1.0), rnd.uniform(0.1, 0.16)
        _rock(m, (x, rnd.uniform(-0.55, -0.35), _floor_z(x) + r * 0.45), r, rnd)
    m.mat("c_timber_dark", uvscale=1.0)
    m.push(Matrix.Translation((0.15, -0.2, 0.55)) @ Matrix.Rotation(math.radians(-8), 4, 'Y') @
           Matrix.Rotation(math.radians(6), 4, 'Z'))
    m.box((0, 0, 0), (2.0, 0.2, 0.18), smooth=False)
    m.pop()
    crystal(m, (-0.45, -0.1, 0.65), (-0.3, -0.2, 1.0), 0.4, 0.06, "c_crystal")
    crystal(m, (0.55, 0.0, 0.55), (0.4, -0.1, 1.0), 0.3, 0.05, "c_crystal_violet")
    # small detail: a snapped lagging board, a crystal spray grown through the heap, a pickaxe left in it, the
    # 落石注意 (falling rocks) sign knocked over onto the rubble, and gravel and shards spilling toward the rider
    m.mat("c_plank", uvscale=1.0)
    m.push(Matrix.Translation((-0.55, 0.22, 0.78)) @ _R(24, 'Y') @ _R(-28, 'Z'))
    m.box((0, 0, 0), (1.05, 0.17, 0.05), smooth=False)
    m.pop()
    m.mat("c_timber")
    for k in range(4):                     # splinters on the snapped end
        m.push(Matrix.Translation((-0.08 + 0.02 * k, 0.0 - 0.04 * k, 1.0 - 0.02 * k)) @ _R(-60 + 12 * k, 'Y'))
        m.cyl((0, 0, 0.07), r=0.025, r2=0.0, h=0.14, seg=4, smooth=False)
        m.pop()
    crystal_cluster(m, (0.22, 0.05, 0.86), (0.15, -0.35, 1.0), size=0.5, rnd=rnd, mats=("c_crystal", "c_crystal_pink"), n=5)
    pickaxe(m, (-0.85, -0.2, 0.25), yaw=-20, lean=38)
    m.push(Matrix.Translation((1.15, -0.45, FLOOR - 0.02)) @ _R(-38, 'Y'))
    signboard(m, (0, 0, 0), "落石注意", h=1.25, w=0.72, col="c_paint_white", ink="c_paint_red")
    m.pop()
    _gravel(m, -1.25, 1.25, -0.85, -0.3, rnd, n=12)
    _shards(m, -1.1, 1.1, -0.9, -0.45, rnd, n=3)
    ob = m.obj(name, smooth_angle=40)
    return ob




def timber_beam(name="ob_timber_beam"):
    """CROUCH: a sagging mine set across the track: two leaning posts and a cap beam with its underside at 1.25 m,
    a hazard board above it and a lantern. Duck in the cart to pass."""
    m = E.Mesher(name)
    W = 2.3
    rnd = random.Random(7)
    for s in (-1, 1):
        m.mat("c_timber", uvscale=1.0)
        _contact_shadow(m, s * W / 2, 0.0, 0.5, 0.45)
        m.push(Matrix.Translation((s * W / 2, 0, 0.0)) @ Matrix.Rotation(math.radians(s * -4), 4, 'Y'))
        zf = FLOOR - 0.04                  # the post goes down through its footing stone into the floor
        m.box((0, 0, (BEAM_UNDERSIDE + 0.12 + zf) / 2), (0.24, 0.24, BEAM_UNDERSIDE + 0.12 - zf), bevel=(0.015, 1),
              smooth=False)
        for k in range(4):                 # hazard bands at the foot, like the gallery frames
            m.mat("c_paint_yellow" if k % 2 == 0 else "c_paint_black")
            m.box((0, 0, 0.2 + k * 0.14), (0.25, 0.25, 0.14), smooth=False)
        m.mat("c_iron_dark")
        for z in (BEAM_UNDERSIDE - 0.3, BEAM_UNDERSIDE - 0.08):
            m.box((0, 0, z), (0.27, 0.27, 0.05), smooth=False)                          # iron strap
            for bx in (-0.06, 0.06):
                m.cyl((bx, -0.14, z), r=0.017, h=0.02, seg=8, axis='Y')                # bolt heads
        m.pop()
        m.mat("c_rock_dark")
        m.box((s * W / 2, 0, (FLOOR - 0.04 + 0.07) / 2), (0.38, 0.38, 0.11 - FLOOR), smooth=False)   # footing stone
        for k in range(3):                 # rubble round the footing
            r = rnd.uniform(0.07, 0.13)
            _rock(m, (s * (W / 2 + rnd.uniform(0.15, 0.35)), rnd.uniform(-0.3, 0.3), FLOOR + r * 0.25), r, rnd,
                  s=(1.0, 1.0, 0.65), mat=rnd.choice(("c_rock", "c_rock_dark")))
    _mushrooms(m, W / 2 + 0.25, 0.2, FLOOR, rnd, n=5)
    # a chain and hook off the cap's end (outside the lane) and a hard hat on a nail
    m.mat("c_iron_dark")
    bx, by, bz = _chain(m, (-W / 2 - 0.2, -0.1, BEAM_UNDERSIDE), n=5)
    m.torus((bx, by, bz - 0.03), R=0.04, r=0.01, seg=10, sides=4, arc=270.0, axis='Y')
    _hard_hat(m, (W / 2 - 0.02, -0.27, BEAM_UNDERSIDE - 0.19), yaw=8)
    m.mat("c_timber", uvscale=1.0)
    m.push(Matrix.Translation((0, 0, BEAM_UNDERSIDE + 0.14)) @ Matrix.Rotation(math.radians(2), 4, 'Y'))
    m.box((0, 0, 0), (W + 0.5, 0.28, 0.28), bevel=(0.015, 1), smooth=False)       # underside at the crouch line
    for k in range(13):                    # painted yellow and black across the lane, like a crossing gate
        m.mat("c_paint_yellow" if k % 2 == 0 else "c_paint_black")
        m.box((-0.72 + k * 0.12, 0, 0), (0.12, 0.295, 0.295), smooth=False)
    m.pop()
    m.mat("c_iron_dark")
    for s in (-1, 1):
        m.box((s * W / 2, -0.13, BEAM_UNDERSIDE + 0.05), (0.3, 0.014, 0.06), smooth=False)
    # hazard board on ropes: yellow/black stripes and 頭上注意
    m.mat("c_rope")
    for x in (-0.4, 0.4):
        m.cyl((x, -0.16, BEAM_UNDERSIDE + 0.43), r=0.01, h=0.3, seg=5)
    m.mat("c_paint_yellow")
    zb = BEAM_UNDERSIDE + 0.65
    m.box((0, -0.16, zb), (1.15, 0.04, 0.34), smooth=False)
    m.mat("c_iron_dark")
    for k in range(6):
        m.push(Matrix.Translation((-0.48 + k * 0.19, -0.185, zb)) @ Matrix.Rotation(math.radians(35), 4, 'Y'))
        m.box((0, 0, 0), (0.05, 0.01, 0.42), smooth=False)
        m.pop()
    m.mat("c_paint_white")
    m.box((0, -0.19, zb), (0.66, 0.012, 0.22), smooth=False)
    m.mat("c_paint_red")
    m.push(Matrix.Translation((0, -0.2, zb)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
    m.text("頭上注意", size=0.14, depth=0.008, font=E.FONT_JP, c=(0, 0, 0))
    m.pop()
    lantern(m, (W / 2 + 0.2, 0, BEAM_UNDERSIDE + 0.28))
    ob = m.obj(name, smooth_angle=30)
    E.finish_hard(ob, width=0.008, segments=1, angle=35)
    return ob


def crystal_rock(name="ob_crystal_rock", seed=9):
    """SIDE: a boulder that fills the lane (2.4 m tall), crowned with big glowing crystals. Dodge it."""
    rnd = random.Random(seed)
    m = E.Mesher(name)
    _contact_shadow(m, 0.0, -0.1, 1.55, 1.2)
    _rock(m, (0, 0, 0.72), 1.05, rnd, s=(1.0, 0.85, 0.8), mat="c_rock_dark", sub=2)
    _rock(m, (-0.6, -0.25, 0.35), 0.55, rnd, s=(1.0, 0.9, 0.8), mat="c_rock", sub=1)
    _rock(m, (0.7, -0.2, 0.3), 0.5, rnd, s=(1.0, 0.9, 0.75), mat="c_rock", sub=1)
    crystal_cluster(m, (0.0, 0.0, 1.32), (0.0, -0.25, 1.0), size=1.2, rnd=rnd, mats=("c_crystal", "c_crystal_violet"), n=8)
    crystal_cluster(m, (-0.65, -0.45, 0.7), (-0.6, -0.6, 0.6), size=0.6, rnd=rnd, mats=("c_crystal_pink",), n=5)
    crystal_cluster(m, (0.75, -0.4, 0.65), (0.6, -0.6, 0.6), size=0.55, rnd=rnd, mats=("c_crystal",), n=5)
    # small detail: a cluster on the back shoulder, moss over the top, rubble, shards and mushrooms round the foot
    crystal_cluster(m, (0.45, 0.45, 1.22), (0.4, 0.6, 0.8), size=0.5, rnd=rnd, mats=("c_crystal_pink", "c_crystal"), n=4)

    def surf(dx, dy, dz):                  # a point on the big boulder's surface along a direction
        d = V((dx, dy, dz)).normalized()
        return V((0, 0, 0.72)) + V((d.x * 1.0, d.y * 0.84, d.z * 0.8))

    m.mat("c_moss")
    for d, rr in (((-0.5, -0.3, 0.8), 0.2), ((0.3, -0.45, 0.85), 0.16), ((-0.75, 0.2, 0.65), 0.18)):
        for j in range(4):                 # a ragged patch from a few overlapping flat blobs
            dd = V(d) + V((rnd.uniform(-0.15, 0.15), rnd.uniform(-0.15, 0.15), 0.0))
            m.push(Matrix.Translation(surf(*dd)) @ _orient(dd))
            m.ico((0, 0, -0.03), rr * rnd.uniform(0.55, 0.9), 1, s=(1.0, 0.8, 0.28))
            m.pop()
    for k in range(10):
        a = math.radians(rnd.uniform(-170, -10))
        rr = rnd.uniform(1.15, 1.5)
        x, r = math.cos(a) * rr, rnd.uniform(0.07, 0.16)
        _rock(m, (x, math.sin(a) * rr * 0.8, _floor_z(x) + r * 0.2), r, rnd, s=(1.0, 1.0, 0.65),
              mat=rnd.choice(("c_rock", "c_rock_dark")))
    _shards(m, -1.3, 1.3, -1.25, -0.9, rnd, n=5)
    _mushrooms(m, -1.05, -0.55, _floor_z(1.05), rnd, n=5)
    _mushrooms(m, 1.1, -0.3, _floor_z(1.1), rnd, n=3)
    return m.obj(name, smooth_angle=40)


def _wagon_body(m, y0, L, rnd, lod=0, cargo=True):
    """Ore wagon: riveted steel V-skip on a bogie frame, heaped with ore and crystals. Spans y0..y0+L."""
    yc = y0 + L / 2
    zc = 0.161 + 0.2
    # wheels and frame
    for yy in (y0 + 0.55, y0 + L - 0.55):
        for s in (-1, 1):
            m.push(Matrix.Translation((s * GAUGE / 2, yy, zc)) @ Matrix.Rotation(math.radians(90), 4, 'Y'))
            m.mat("c_iron_dark")
            m.cyl((0, 0, 0), r=0.2, h=0.07, seg=20 if lod == 0 else 10)
            m.cyl((0, 0, -s * 0.04), r=0.24, h=0.016, seg=20 if lod == 0 else 10)
            m.mat("c_rust")
            m.cyl((0, 0, s * 0.03), r=0.07, h=0.03, seg=10)
            m.pop()
    m.mat("c_iron_dark")
    m.box((0, yc, zc + 0.22), (1.3, L - 0.2, 0.16), smooth=False)
    for s in (-1, 1):
        m.box((s * 0.68, yc, zc + 0.05), (0.08, L - 0.5, 0.22), smooth=False)
    # V-skip: trapezoid section, wider at the top
    z0, z1 = 0.8, 1.75
    w0, w1 = 0.55, 0.78
    m.mat("c_rust", uvscale=1.0)
    sec = [(-w0, z0), (w0, z0), (w1, z1), (-w1, z1)]
    # section drawn in (x, z); Rx(+90) stands it up and extrudes along -Y
    m.push(Matrix.Translation((0, yc, 0)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
    m.extrude([(x, z) for x, z in sec], L - 0.2, bevel=(0.02, 1) if lod == 0 else None)
    m.pop()
    m.mat("c_iron")
    for yy in [y0 + 0.1 + (L - 0.2) * k / 4 for k in range(5)]:
        m.push(Matrix.Translation((0, yy, 0)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
        m.extrude([(-w0 - 0.03, z0 - 0.02), (w0 + 0.03, z0 - 0.02), (w1 + 0.03, z1 + 0.02), (-w1 - 0.03, z1 + 0.02)],
                  0.06, c=(0, 0, 0))
        m.pop()
    if cargo:
        # heap of ore with a flattish top (it can be run on) and crystals poking out
        m.mat("c_ore", uvscale=1.0)
        rings = []
        for k in range(7):
            t = k / 6
            yy = y0 + 0.15 + (L - 0.3) * t
            h = 0.12 + 0.18 * math.sin(math.pi * t)
            rings.append([(-w1 + 0.02, yy, z1 - 0.02), (-w1 * 0.6, yy, z1 + h * 0.7), (0, yy, z1 + h),
                          (w1 * 0.6, yy, z1 + h * 0.7), (w1 - 0.02, yy, z1 - 0.02)])
        _grid(m, rings, inward=False)
        for k in range(6 if lod == 0 else 2):
            _rock(m, (rnd.uniform(-0.5, 0.5), rnd.uniform(y0 + 0.4, y0 + L - 0.4), z1 + 0.15), rnd.uniform(0.1, 0.16), rnd,
                  mat="c_ore")
        for k in range(5 if lod == 0 else 1):
            crystal(m, (rnd.uniform(-0.45, 0.45), rnd.uniform(y0 + 0.4, y0 + L - 0.4), z1 + 0.1),
                    (rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4), 1.0), rnd.uniform(0.25, 0.4), 0.05,
                    rnd.choice(("c_crystal", "c_crystal_pink", "c_crystal_violet")))


def ore_train(name="ob_ore_train", wagons=3, seed=11, lod=0):
    """SIDE: a battery mine loco (front, toward -Y) pulling ore wagons, parked or oncoming on one track. Origin at the
    front buffer on the rail plane; the train extends toward +Y. Tilt onto another track to pass it."""
    rnd = random.Random(seed)
    m = E.Mesher(name)
    # loco: low hood with a cab at the back, headlamp and buffer
    L = 3.0
    zc = 0.161 + 0.2
    _contact_shadow(m, 0.0, L / 2, 0.88, L / 2 + 0.12)
    for yy in (0.6, L - 0.6):
        for s in (-1, 1):
            m.push(Matrix.Translation((s * GAUGE / 2, yy, zc)) @ Matrix.Rotation(math.radians(90), 4, 'Y'))
            m.mat("c_iron_dark")
            m.cyl((0, 0, 0), r=0.2, h=0.07, seg=20 if lod == 0 else 10)
            m.pop()
    m.mat("c_iron_dark")
    m.box((0, L / 2, zc + 0.22), (1.4, L, 0.2), smooth=False)
    m.mat("c_loco_trim")
    m.box((0, 0.05, 0.55), (1.5, 0.1, 0.3), smooth=False)                               # buffer beam
    m.mat("c_iron_dark")
    for k in range(5):
        m.box((-0.6 + k * 0.3, 0.0, 0.55), (0.12, 0.01, 0.3), smooth=False)          # hazard chevrons
    m.mat("c_loco", uvscale=1.0)
    m.rbox((0, 1.0, 1.0), (1.3, 1.6, 0.75), r=0.08)                                   # hood
    m.rbox((0, 2.35, 1.35), (1.45, 1.1, 1.45), r=0.08)                                # cab
    m.mat("c_loco_trim")
    m.box((0, 1.0, 1.4), (1.32, 1.62, 0.06), smooth=False)
    m.box((0, 2.35, 2.1), (1.55, 1.2, 0.08), smooth=False)                            # cab roof
    m.mat("c_glass")
    m.box((0, 1.79, 1.65), (1.1, 0.02, 0.5), smooth=False)                            # front window
    for s in (-1, 1):
        m.box((s * 0.73, 2.35, 1.65), (0.02, 0.8, 0.45), smooth=False)
    m.mat("c_iron_dark")
    m.box((0, 0.19, 1.2), (0.3, 0.06, 0.3), smooth=False)
    m.mat("c_lamp_hot")
    m.cyl((0, 0.15, 1.2), r=0.11, h=0.04, seg=16, axis='Y')                           # headlamp
    m.mat("c_lamp")
    for s in (-1, 1):
        m.cyl((s * 0.55, 0.04, 0.82), r=0.05, h=0.03, seg=12, axis='Y')
    m.mat("c_paint_white")
    m.push(Matrix.Translation((0.74, 1.0, 1.05)) @ Matrix.Rotation(math.radians(90), 4, 'Z') @
           Matrix.Rotation(math.radians(90), 4, 'X'))
    m.text("水晶鉱山", size=0.16, depth=0.006, font=E.FONT_JP, c=(0, 0, 0))
    m.pop()
    if lod == 0:
        # small detail: rivets and louvres on the hood, yellow handrails, a horn, a roof beacon, number plate
        m.mat("c_iron")
        for s in (-1, 1):
            for z in (0.7, 1.3):
                for k in range(8):
                    m.sphere((s * 0.655, 0.3 + k * 0.2, z), 0.016, 6, 3)
        m.mat("c_iron_dark")
        for s in (-1, 1):
            for k in range(5):
                m.box((s * 0.656, 1.4 + k * 0.09, 1.0), (0.012, 0.045, 0.3), smooth=False)
        m.mat("c_loco_trim")
        for s in (-1, 1):
            m.tube([(s * 0.76, 0.3, 1.2), (s * 0.76, 1.75, 1.2)], r=0.018, seg=6)
            for yy in (0.3, 1.0, 1.75):
                m.cyl((s * 0.76, yy, 0.94), r=0.014, h=0.52, seg=6)
        m.mat("c_brass")
        m.cyl((-0.35, 0.55, 1.45), r=0.025, r2=0.07, h=0.26, seg=10, axis='Y')                # horn
        m.mat("c_iron_dark")
        m.box((0.3, 1.25, 1.44), (0.42, 0.3, 0.1), smooth=False)                             # sand box
        m.mat("c_lamp")
        m.cyl((0.45, 2.35, 2.22), r=0.075, h=0.12, seg=12)                                    # amber beacon
        m.mat("c_iron_dark")
        m.cyl((0.45, 2.35, 2.3), r=0.08, r2=0.05, h=0.04, seg=12)
        m.mat("c_paint_white")
        m.box((0, 0.185, 0.88), (0.36, 0.012, 0.17), smooth=False)                           # number plate
        m.mat("c_paint_black")
        m.push(Matrix.Translation((0, 0.175, 0.88)) @ _R(90, 'X'))
        m.text("03", size=0.12, depth=0.006, font=E.FONT_JP, c=(0, 0, 0))
        m.pop()
    y = L + 0.3
    for k in range(wagons):
        m.mat("c_iron_dark")
        m.box((0, y - 0.15, 0.6), (0.12, 0.5, 0.08), smooth=False)                    # coupler
        _contact_shadow(m, 0.0, y + 1.45, 0.88, 1.55)
        _wagon_body(m, y, 2.9, rnd, lod)
        y += 2.9 + 0.3
    ob = m.obj(name + ("" if lod == 0 else "@1"), smooth_angle=35)
    if lod == 0:
        E.finish_hard(ob, width=0.01, segments=1, angle=35)
    return ob


def _crib(m, cx, z0, z1, rnd, L=0.72):
    """A timber crib (a cog): square timbers stacked in crossing pairs from the floor (z0) up to z1, the miners' way
    of propping a load. The top pair runs along the track, so a log laid across the track rests on both."""
    n = max(2, int(round((z1 - z0) / 0.16)))
    t = (z1 - z0) / n
    for k in range(n):
        z = z0 + t * (k + 0.5)
        across = (n - 1 - k) % 2 == 1          # the top layer (k = n - 1) runs along y
        for s in (-1, 1):
            off = s * (L / 2 - t * 0.6)
            jit = rnd.uniform(-0.03, 0.03)
            m.mat(rnd.choice(("c_timber", "c_timber", "c_timber_dark")), uvscale=1.0)
            if across:
                m.box((cx + jit, off, z), (L, t * 0.94, t), bevel=(0.01, 1), smooth=False)
            else:
                m.box((cx + off, jit, z), (t * 0.94, L, t), bevel=(0.01, 1), smooth=False)
    return cx - L / 2 + t * 0.6, cx + L / 2 - t * 0.6     # x of the two top timbers


def fallen_log(name="ob_fallen_log", seed=4):
    """CROUCH: an old prop log laid across the track on two timber cribs, its underside at BEAM_UNDERSIDE all the
    way across. Bark, broken branch stubs, a split end, moss and crystals on top, chocks against it on the cribs.
    Duck to pass."""
    rnd = random.Random(seed)
    m = E.Mesher(name)
    BU = BEAM_UNDERSIDE
    CX = 1.3                               # crib centres; their inner faces stay 0.94 m off the lane centre
    x0, x1 = -1.72, 1.66
    r0, taper = 0.21, 0.85

    def rad(x):
        return r0 * (1 + (taper - 1) * (x - x0) / (x1 - x0))

    def axis_at(x):                        # the log's centre line and radius at x: underside on the crouch line
        x = min(max(x, x0), x1)
        bow = 0.02 * max(0.0, 1 - (x / CX) ** 2)
        return V((x, 0.015 * math.sin(x * 2.1), BU + rad(x) + bow)), rad(x)

    # cribs on the floor, contact shadows under them, a few stones and gravel round their feet
    for sx in (-1, 1):
        _contact_shadow(m, sx * CX, 0.0, 0.62, 0.55)
        tops = _crib(m, sx * CX, FLOOR - 0.02, BU, rnd)
        for tx in tops:                    # chocks on the top timbers, against both flanks of the log
            c, rr = axis_at(tx)
            for sy in (-1, 1):
                m.mat("c_timber_dark", uvscale=1.0)
                m.push(Matrix.Translation((tx, sy * rr * 0.8, BU)) @ _R(90, 'Y'))
                m.extrude([(0.0, 0.0), (0.0, sy * 0.16), (-0.1, 0.0)][::sy], 0.13)
                m.pop()
        for k in range(4):
            a = math.radians(rnd.uniform(0, 360))
            x = sx * CX + math.cos(a) * rnd.uniform(0.42, 0.55)
            rr = rnd.uniform(0.08, 0.15)
            _rock(m, (x, math.sin(a) * rnd.uniform(0.4, 0.5), _floor_z(x) + rr * 0.25), rr, rnd, s=(1.0, 1.0, 0.7),
                  mat=rnd.choice(("c_rock", "c_rock_dark")))
        _gravel(m, sx * CX - 0.45, sx * CX + 0.45, -0.72, -0.42, rnd, n=5)
        _mushrooms(m, sx * (CX + 0.42), -0.35, FLOOR, rnd, n=3)
    # the log: tapering, a slight upward bow, bark-coloured timber with a pale sawn end
    xs = [x0 + (x1 - x0) * i / 8 for i in range(9)]
    pts = [tuple(axis_at(x)[0]) for x in xs]
    m.mat("c_timber_dark", uvscale=1.0)
    m.tube(pts, r=r0, seg=14, taper=lambda t: 1 + (taper - 1) * t)
    c_end, r_end = axis_at(x1)
    m.mat("c_timber")
    m.cyl(tuple(c_end), r=r_end * 0.97, h=0.02, seg=14, axis='X')                          # sawn end
    m.mat("c_tie")
    for (x, a, L) in ((-0.6, 40, 0.35), (0.3, 125, 0.28), (0.9, 70, 0.22)):             # branch stubs, all upward
        c, rr = axis_at(x)
        d = V((0.25, math.cos(math.radians(a)), math.sin(math.radians(a)))).normalized()
        b = c + d * rr * 0.8
        m.tube([tuple(b), tuple(b + d * L)], r=0.045, seg=6, taper=0.5)
    c, rr = axis_at(-0.2)
    crystal(m, tuple(c + V((0, -0.05, rr * 0.8))), (0.1, -0.3, 1.0), 0.32, 0.05, "c_crystal")
    c, rr = axis_at(-0.05)
    crystal(m, tuple(c + V((0, 0.05, rr * 0.85))), (-0.2, 0.2, 1.0), 0.22, 0.04, "c_crystal_violet")
    # bark: inked grooves broken into short runs over the front, top and back (none on the underside)
    m.mat("c_strap")
    for a in (-75, -40, -5, 30, 65, 100):
        x = x0 + rnd.uniform(0.05, 0.4)
        while x < x1 - 0.2:
            L = min(rnd.uniform(0.35, 0.9), x1 - 0.05 - x)
            run = []
            for t in (0.0, 0.5, 1.0):
                c, rr = axis_at(x + L * t)
                run.append(tuple(c + V((0, math.cos(math.radians(a)), math.sin(math.radians(a)))) * rr))
            m.tube(run, r=0.018, seg=5)
            x += L + rnd.uniform(0.15, 0.5)
    # end grain on the sawn end; the other end is snapped into splinters
    m.mat("c_timber_dark")
    for f in (0.3, 0.55, 0.8):
        m.torus(tuple(c_end + V((0.012, 0, 0))), R=r_end * 0.97 * f, r=0.007, seg=16, sides=4, axis='X')
    m.mat("c_timber")
    c0, rr0 = axis_at(x0)
    for k in range(7):
        a = 2 * math.pi * k / 7 + rnd.uniform(0, 0.5)
        rr = rr0 * rnd.uniform(0.15, 0.8)
        m.push(Matrix.Translation(tuple(c0 + V((0.02, math.cos(a) * rr, math.sin(a) * rr)))) @ _R(-90, 'Y'))
        L = rnd.uniform(0.1, 0.24)
        m.cyl((0, 0, L / 2), r=0.045, r2=0.0, h=L, seg=4, smooth=False)
        m.pop()
    # moss and glowing mushrooms on top, a little crystal spray
    for x in (-0.9, 0.1, 0.95):
        c, rr = axis_at(x)
        m.mat("c_moss")
        m.ico(tuple(c + V((0, 0.03, rr * 0.82))), rnd.uniform(0.14, 0.2), 1, s=(1.6, 1.0, 0.35))
    c, rr = axis_at(-0.55)
    _mushrooms(m, c.x, c.y, c.z + rr * 0.9, rnd, n=4, spread=0.08, hmin=0.05, hmax=0.1)
    c, rr = axis_at(0.4)
    crystal_cluster(m, tuple(c + V((0, -0.05, rr * 0.85))), (0.15, -0.35, 1.0), size=0.34, rnd=rnd,
                    mats=("c_crystal_pink", "c_crystal_violet"), n=4)
    # rope round the log with a red warning rag hanging down its front, ending on the crouch line
    c, rr = axis_at(0.55)
    m.mat("c_rope")
    m.torus(tuple(c), R=rr * 1.02, r=0.018, seg=16, sides=5, axis='X')
    m.mat("c_paint_red")
    m.push(Matrix.Translation((0.55, c.y - rr - 0.015, BU + 0.1)) @ _R(6, 'Y'))
    m.box((0, 0, 0), (0.16, 0.02, 0.2), smooth=False)
    m.pop()
    ob = m.obj(name, smooth_angle=45)
    return ob


def bat_swarm(frame=0, name=None, seed=13, n=9):
    """CROUCH: a swarm of bats flying at the rider between 1.2 and 1.9 m, spread over the track width. frame 0/1
    alternates every bat's wing pose, so swapping the two meshes each ~0.08 s flaps the whole swarm."""
    rnd = random.Random(seed)
    m = E.Mesher(name or "ob_bat_swarm_%s" % "ab"[frame])
    for k in range(n):
        x = rnd.uniform(-1.0, 1.0)
        y = rnd.uniform(-0.6, 0.9)
        z = rnd.uniform(SWARM_BAND[0] + 0.12, SWARM_BAND[1] - 0.08)
        pose = "up" if (k + frame) % 2 == 0 else "down"
        sc = rnd.uniform(1.0, 1.3)
        _contact_shadow(m, x, y, 0.2 * sc, 0.14 * sc, mat="c_contact_far")
        m.push(Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(rnd.uniform(-25, 25)), 4, 'Z') @
               Matrix.Rotation(math.radians(rnd.uniform(-15, 15)), 4, 'Y') @ _R(rnd.uniform(-38, -25), 'X') @
               Matrix.Diagonal((sc, sc, sc, 1)))             # nose up mid-flap: the wings face the rider
        _bat_into(m, pose)
        m.pop()
    return m.obj(name or "ob_bat_swarm_%s" % "ab"[frame], smooth_angle=40)


# ----------------------------------------------------------------------------- small props

def barrel(m, c, rnd, h=0.9, r=0.3):
    """A coopered barrel: bulging staves drawn as inked joints, four iron hoops, a sunk lid of two boards with a
    bung, and a bung and a rust run on the side."""
    x, y, z = c
    prof = [(r * 0.86, 0.0), (r * 0.97, h * 0.25), (r, h * 0.5), (r * 0.97, h * 0.75), (r * 0.86, h)]
    m.mat("c_timber", uvscale=0.5)
    m.lathe(prof, seg=14, c=(x, y, z))
    m.mat("c_timber_dark")
    m.cyl((x, y, z + h - 0.03), r=r * 0.82, h=0.02, seg=14)                                    # sunk lid
    m.torus((x, y, z + h - 0.008), R=r * 0.85, r=0.014, seg=14, sides=4)                    # chime
    m.mat("c_strap")
    for k in range(12):                                                                      # stave joints
        a = 2 * math.pi * (k + rnd.uniform(-0.15, 0.15)) / 12
        ca, sa = math.cos(a), math.sin(a)
        m.tube([(x + ca * (rr + 0.003), y + sa * (rr + 0.003), z + zz) for rr, zz in prof[::2]], r=0.0045, seg=4)
    m.box((x, y, z + h - 0.018), (0.008, r * 1.6, 0.006), smooth=False)                      # the lid's board joint
    m.mat("c_iron_dark")
    for t in (0.12, 0.4, 0.6, 0.88):
        rr = r * (0.9 + 0.1 * math.sin(math.pi * t)) + 0.008
        m.cyl((x, y, z + h * t), r=rr, h=0.035, seg=14, caps=False)
    m.cyl((x + r * 0.4, y + r * 0.25, z + h - 0.012), r=0.03, h=0.02, seg=8)                # lid bung
    a = rnd.uniform(0, 2 * math.pi)
    m.mat("c_timber_dark")
    m.cyl((x + math.cos(a) * (r + 0.005), y + math.sin(a) * (r + 0.005), z + h * 0.5), r=0.035, h=0.025, seg=8,
          axis='X' if abs(math.cos(a)) > abs(math.sin(a)) else 'Y')                            # side bung
    m.mat("c_rust")
    m.box((x + math.cos(a) * (r + 0.004), y + math.sin(a) * (r + 0.004), z + h * 0.4), (0.025, 0.025, 0.16),
          smooth=False)                                                                       # rust run under it


def crate(m, c, size=0.6, yaw=0.0, label=None):
    """A nailed plank crate: corner posts, plank seams on every face, nail heads, rope handles and a stencil."""
    x, y, z = c
    m.push(Matrix.Translation((x, y, z + size / 2)) @ Matrix.Rotation(math.radians(yaw), 4, 'Z'))
    m.mat("c_tie", uvscale=0.6)
    m.box((0, 0, 0), (size, size, size), smooth=False)
    m.mat("c_timber_dark")
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.box((sx * size / 2, sy * size / 2, 0), (0.05, 0.05, size + 0.01), smooth=False)
    h = size / 2 + 0.003
    m.mat("c_strap")
    for k in (1, 2):                                                       # plank seams: three boards a face
        zz = -size / 2 + size * k / 3
        for sx in (-1, 1):
            m.box((sx * h, 0, zz), (0.006, size - 0.06, 0.008), smooth=False)
            m.box((0, sx * h, zz), (size - 0.06, 0.006, 0.008), smooth=False)
        m.box((-size / 2 + size * k / 3, 0, h), (0.008, size - 0.06, 0.006), smooth=False)    # lid boards
    m.mat("c_iron_dark")
    for k in range(3):                                                     # nail heads at the board ends
        zz = -size / 2 + size * (k + 0.5) / 3
        for sx in (-1, 1):
            for sy in (-1, 1):
                m.sphere((sx * (size / 2 - 0.05), sy * (h + 0.002), zz), 0.012, 6, 3)
    m.mat("c_rope")
    for sx in (-1, 1):                                                     # rope handles on the ends
        m.torus((sx * (h + 0.012), 0, size * 0.18), R=0.07, r=0.013, seg=10, sides=4, arc=180.0, axis='X')
    if label:
        m.mat("c_paint_white")
        m.box((0, -size / 2 - 0.006, 0.05), (size * 0.62, 0.006, size * 0.28), smooth=False)
        m.mat("c_paint_red")
        m.push(Matrix.Translation((0, -size / 2 - 0.012, 0.05)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
        m.text(label, size=size * 0.19, depth=0.004, font=E.FONT_JP, c=(0, 0, 0))
        m.pop()
    m.pop()


def sack(m, c, rnd):
    """A slumped ore sack: a heavy body settled on the floor, a gathered neck tied with twine, a stitched seam and a
    stencilled mark."""
    x, y, z = c
    m.mat("c_rope", uvscale=0.5, tint=0xD8C8A8)
    m.sphere((x, y, z + 0.19), 0.25, 12, 8, s=(1.0, 0.82, 0.8))
    m.sphere((x + rnd.uniform(-0.05, 0.05), y - 0.06, z + 0.1), 0.2, 10, 6, s=(1.15, 0.9, 0.55))   # the slump
    m.cyl((x, y, z + 0.4), r=0.07, r2=0.035, h=0.1, seg=10)                                        # gathered neck
    m.sphere((x + 0.02, y, z + 0.47), 0.06, 8, 5, s=(1.2, 1.0, 0.6))                               # the ruffle
    m.mat("c_rope")
    m.torus((x, y, z + 0.4), R=0.055, r=0.013, seg=12, sides=4)
    m.tube([(x + 0.05, y - 0.03, z + 0.4), (x + 0.1, y - 0.07, z + 0.33), (x + 0.12, y - 0.09, z + 0.26)], r=0.008, seg=4)
    m.mat("c_strap")
    m.tube([(x - 0.24, y, z + 0.19), (x - 0.2, y - 0.12, z + 0.3), (x, y - 0.2, z + 0.36)], r=0.006, seg=4)  # seam
    m.mat("c_paint_red")
    m.cyl((x, y - 0.205, z + 0.2), r=0.07, h=0.006, seg=12, axis='Y')                              # stencil mark


def oil_drum(m, c, col="c_paint_red", lid=True):
    """A 200 l steel drum: rolling hoops, rim chimes, a white band with a hazard diamond, a bung and vent on top."""
    x, y, z = c
    r, h = 0.29, 0.88
    m.mat(col)
    m.cyl((x, y, z + h / 2), r=r, h=h, seg=16)
    m.mat("c_iron_dark")
    for t in (0.33, 0.67):
        m.torus((x, y, z + h * t), R=r + 0.003, r=0.014, seg=16, sides=4)                     # rolling hoops
    for t in (0.012, 0.988):
        m.torus((x, y, z + h * t), R=r - 0.004, r=0.016, seg=16, sides=4)                     # chimes
    m.mat("c_paint_white")
    m.cyl((x, y, z + h * 0.5), r=r + 0.002, h=0.13, seg=16, caps=False)
    m.mat("c_paint_red" if col != "c_paint_red" else "c_paint_black")
    m.push(Matrix.Translation((x, y - r - 0.006, z + h * 0.5)) @ _R(45, 'Y'))
    m.box((0, 0, 0), (0.075, 0.006, 0.075), smooth=False)                                     # hazard diamond
    m.pop()
    if lid:
        m.mat("c_iron")
        m.cyl((x + 0.14, y + 0.06, z + h + 0.008), r=0.035, h=0.018, seg=8)                  # bung
        m.cyl((x - 0.15, y - 0.05, z + h + 0.006), r=0.022, h=0.014, seg=8)                  # vent
    m.mat("c_rust")
    m.box((x + 0.17, y - r * 0.81, z + h * 0.8), (0.03, 0.012, 0.12), smooth=False)          # a rust run


def rope_coil(m, c, yaw=0.0):
    """A coil of hemp rope on the floor, the loose end trailing off."""
    x, y, z = c
    m.push(Matrix.Translation((x, y, z)) @ _R(yaw, 'Z'))
    m.mat("c_rope")
    for k in range(4):
        m.torus((0.01 * k, 0, 0.032 + k * 0.05), R=0.24 - k * 0.015, r=0.03, seg=18, sides=6)
    m.tube([(0.22, 0.05, 0.18), (0.3, -0.05, 0.08), (0.36, -0.2, 0.03), (0.42, -0.42, 0.028)], r=0.028, seg=6)
    m.pop()


def bucket(m, c, water=True):
    """A wooden pail (oke): tapered staves, two iron bands, a rope handle, water in it."""
    x, y, z = c
    m.mat("c_timber", uvscale=0.5)
    m.cyl((x, y, z + 0.16), r=0.13, r2=0.16, h=0.32, seg=12)
    m.mat("c_iron_dark")
    for zz, rr in ((0.06, 0.137), (0.26, 0.155)):
        m.cyl((x, y, z + zz), r=rr, h=0.03, seg=12, caps=False)
    if water:
        m.mat("c_water")
        m.cyl((x, y, z + 0.3), r=0.148, h=0.006, seg=12)
    m.mat("c_rope")
    m.tube([(x - 0.16, y, z + 0.28), (x - 0.12, y, z + 0.42), (x, y, z + 0.47), (x + 0.12, y, z + 0.42), (x + 0.16, y, z + 0.28)],
           r=0.011, seg=5)


def ladder(m, c, yaw=0.0, L=2.5, lean=15.0):
    """A timber ladder leaning on the lagging: two rails, rungs, the rails' feet on the floor."""
    x, y, z = c
    m.push(Matrix.Translation((x, y, z)) @ _R(yaw, 'Z') @ _R(lean, 'Y'))
    m.mat("c_timber", uvscale=1.0)
    for sy in (-1, 1):
        m.box((0, sy * 0.22, L / 2), (0.07, 0.06, L), smooth=False)
    m.mat("c_timber_dark", uvscale=1.0)
    for k in range(7):
        m.cyl((0, 0, 0.3 + k * 0.32), r=0.022, h=0.5, seg=6, axis='Y')
    m.mat("c_iron_dark")
    for sy in (-1, 1):
        m.box((0, sy * 0.22, 0.12), (0.08, 0.07, 0.04), smooth=False)                       # iron shoe
    m.pop()


def bench(m, c, yaw=0.0):
    """The miners' rest: a plank bench on trestles with a brass kettle (yakan), a wrapped lunch box and a cup."""
    x, y, z = c
    m.push(Matrix.Translation((x, y, z)) @ _R(yaw, 'Z'))
    m.mat("c_plank", uvscale=1.0)
    m.box((0, 0, 0.44), (1.2, 0.32, 0.05), smooth=False)
    m.mat("c_timber_dark", uvscale=1.0)
    for sx in (-1, 1):                                                     # A-frame trestles
        for sy in (-1, 1):
            m.push(Matrix.Translation((sx * 0.45, sy * 0.1, 0.21)) @ _R(sy * 12, 'X'))
            m.box((0, 0, 0), (0.06, 0.05, 0.46), smooth=False)
            m.pop()
        m.box((sx * 0.45, 0, 0.2), (0.05, 0.26, 0.04), smooth=False)
    # kettle: a squat body, lid and knob, a spout and a bail handle
    kx, kz = -0.32, 0.465
    m.mat("c_brass")
    m.sphere((kx, 0, kz + 0.08), 0.11, 12, 7, s=(1.0, 1.0, 0.72))
    m.cyl((kx, 0, kz + 0.155), r=0.06, h=0.02, seg=10)
    m.sphere((kx, 0, kz + 0.172), 0.015, 6, 3)
    m.tube([(kx + 0.08, 0, kz + 0.07), (kx + 0.14, 0, kz + 0.12), (kx + 0.17, 0, kz + 0.16)], r=0.014, seg=5, taper=0.7)
    m.mat("c_iron_dark")
    m.tube([(kx - 0.08, 0, kz + 0.12), (kx - 0.05, 0, kz + 0.22), (kx + 0.05, 0, kz + 0.22), (kx + 0.08, 0, kz + 0.12)],
           r=0.007, seg=4)
    # lunch box wrapped in a red furoshiki with the knot on top, and a tin cup
    m.mat("c_paint_red")
    m.box((0.12, 0.0, 0.5), (0.22, 0.15, 0.07), bevel=(0.012, 1), smooth=False)
    m.sphere((0.12, 0.0, 0.545), 0.026, 8, 4, s=(1.6, 1.0, 0.8))
    for sx in (-1, 1):
        m.cyl((0.12 + sx * 0.04, 0.0, 0.56), r=0.012, r2=0.002, h=0.04, seg=5)
    m.mat("c_porcelain")
    m.cyl((0.4, 0.04, 0.505), r=0.035, r2=0.04, h=0.08, seg=10)
    m.pop()


def cable_drum(m, c, yaw=0.0):
    """A wooden cable reel standing on its rims, orange cable wound on it and its end run off along the floor."""
    x, y, z = c
    R = 0.45
    m.push(Matrix.Translation((x, y, z + R)) @ _R(yaw, 'Z'))
    m.mat("c_timber", uvscale=0.6)
    for sy in (-1, 1):
        m.cyl((0, sy * 0.24, 0), r=R, h=0.05, seg=16, axis='Y')
    m.mat("c_cable_orange")
    m.cyl((0, 0, 0), r=0.34, h=0.43, seg=16, axis='Y')
    m.mat("c_cable")
    for k in range(5):                                                     # the wound turns, inked
        m.torus((0, -0.18 + k * 0.09, 0), R=0.342, r=0.006, seg=16, sides=3, axis='Y')
    m.mat("c_iron_dark")
    for sy in (-1, 1):
        m.cyl((0, sy * 0.27, 0), r=0.07, h=0.02, seg=8, axis='Y')                         # hub
        for k in range(4):
            a = math.pi / 2 * k + 0.4
            m.cyl((math.cos(a) * 0.28, sy * 0.268, math.sin(a) * 0.28), r=0.016, h=0.012, seg=6, axis='Y')
    m.mat("c_timber_dark")
    for sy in (-1, 1):
        m.box((0, sy * 0.268, 0), (0.06, 0.008, 2 * R - 0.05), smooth=False)             # board joints on the rims
    m.pop()
    m.push(Matrix.Translation((x, y, z)) @ _R(yaw, 'Z'))
    m.mat("c_cable_orange")                                                # the end paid out along the floor
    m.tube([(0.0, 0.06, 0.115), (0.0, 0.4, 0.03), (0.08, 0.8, 0.018), (0.05, 1.15, 0.018)], r=0.016, seg=6)
    m.pop()


def pickaxe(m, c, yaw=0.0, lean=18.0):
    x, y, z = c
    m.push(Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(yaw), 4, 'Z') @ Matrix.Rotation(math.radians(lean), 4, 'Y'))
    m.mat("c_timber")
    m.cyl((0, 0, 0.45), r=0.022, h=0.9, seg=8)
    m.mat("c_iron")
    m.sweep([(-0.3, 0, 0.86), (0, 0, 0.92), (0.3, 0, 0.86)], [(-0.02, -0.025), (0.02, -0.025), (0.02, 0.025), (-0.02, 0.025)],
            closed=True, cap=True, scale=lambda t: 1.0 - 0.6 * abs(t - 0.5) * 2)
    m.pop()


def shovel(m, c, yaw=0.0, lean=-15.0):
    x, y, z = c
    m.push(Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(yaw), 4, 'Z') @ Matrix.Rotation(math.radians(lean), 4, 'Y'))
    m.mat("c_timber")
    m.cyl((0, 0, 0.55), r=0.02, h=0.9, seg=8)
    m.torus((0, 0, 1.03), R=0.06, r=0.012, seg=10, sides=4, axis='Y')
    m.mat("c_iron")
    m.box((0, 0, 0.12), (0.24, 0.02, 0.3), smooth=False)
    m.pop()


def mine_shrine(m, c, yaw=0.0):
    """Yama-no-kami shrine (山の神) miners keep in the gallery: a small hokora on a stone base, a shimenawa rope with
    paper shide, a red mini torii in front and a sake cup."""
    x, y, z = c
    m.push(Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(yaw), 4, 'Z'))
    m.mat("c_rock_dark")
    m.box((0, 0, 0.2), (0.7, 0.55, 0.4), smooth=False)
    m.mat("c_timber")
    m.box((0, 0.02, 0.62), (0.42, 0.34, 0.44), smooth=False)
    m.mat("c_timber_dark")
    m.box((0, -0.15, 0.6), (0.24, 0.01, 0.3), smooth=False)                           # doors
    m.mat("c_tie")
    for sx in (-1, 1):                                                                # gabled roof
        m.push(Matrix.Translation((sx * 0.15, 0.02, 0.92)) @ Matrix.Rotation(math.radians(sx * -32), 4, 'Y'))
        m.box((0, 0, 0), (0.38, 0.5, 0.03), smooth=False)
        m.pop()
    m.mat("c_rope")
    m.tube([(-0.24, -0.19, 0.8), (0.0, -0.21, 0.76), (0.24, -0.19, 0.8)], r=0.018, seg=6)
    m.mat("c_paint_white")
    for xx in (-0.12, 0.0, 0.12):                                                     # shide zigzags
        for k in range(3):
            m.box((xx + (0.012 if k % 2 else -0.012), -0.205, 0.73 - k * 0.04), (0.03, 0.004, 0.04), smooth=False)
    m.mat("c_paint_red")
    for sx in (-1, 1):                                                                # mini torii
        m.cyl((sx * 0.16, -0.42, 0.24), r=0.018, h=0.48, seg=8)
    m.box((0, -0.42, 0.5), (0.48, 0.04, 0.035), smooth=False)
    m.box((0, -0.42, 0.42), (0.38, 0.03, 0.025), smooth=False)
    m.mat("c_paint_white")
    m.cyl((0.0, -0.22, 0.41), r=0.03, r2=0.022, h=0.03, seg=10)                       # sake cup
    m.pop()


def signboard(m, c, text, yaw=0.0, h=1.6, w=0.9, col="c_paint_yellow", ink="c_iron_dark"):
    x, y, z = c
    m.push(Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(yaw), 4, 'Z'))
    m.mat("c_timber_dark")
    m.box((0, 0, h / 2), (0.08, 0.08, h), smooth=False)
    m.mat(col)
    m.box((0, -0.05, h - 0.15), (w, 0.03, 0.3), smooth=False)
    m.mat(ink)
    m.push(Matrix.Translation((0, -0.07, h - 0.15)) @ Matrix.Rotation(math.radians(90), 4, 'X'))
    m.text(text, size=0.17, depth=0.006, font=E.FONT_JP, c=(0, 0, 0))
    m.pop()
    m.pop()


def rail_stack(m, c, n=4, L=3.0):
    import city
    x, y, z = c
    m.mat("c_timber_dark")
    for yy in (y - L / 2 + 0.3, y + L / 2 - 0.3):
        m.box((x, yy, z + 0.05), (0.7, 0.14, 0.1), smooth=False)
    m.mat("c_rust")
    for k in range(n):
        xx = x - 0.24 + k * 0.16
        m.sweep([(xx, y - L / 2, z + 0.1), (xx, y + L / 2, z + 0.1)], [(-p[0], p[1]) for p in city.RAIL_PROF],
                closed=True, cap=True)


def side_gallery(m, side, y, lod=0, name="第三坑道"):
    """A closed-off side gallery in the wall (|x| ~5.4), 1.3 m wide: a dark opening in front of the boards in a
    timber set, a rail stub running in, a yellow and black bar across it, a name board and a lantern."""
    xw = side * 5.47
    m.mat("c_void")
    pts = [(xw, y - 0.65, FLOOR), (xw, y + 0.65, FLOOR), (xw, y + 0.65, 2.25), (xw, y - 0.65, 2.25)]
    m.poly(pts[::-1] if side > 0 else pts)            # faces the tunnel axis
    m.mat("c_timber", uvscale=1.0)
    for dy in (-0.75, 0.75):
        m.box((side * 5.36, y + dy, (FLOOR + 2.35) / 2), (0.2, 0.2, 2.45 - FLOOR), smooth=False)
    m.box((side * 5.36, y, 2.42), (0.24, 1.9, 0.22), smooth=False)
    for k in range(5):                      # the bar across: closed
        m.mat("c_paint_yellow" if k % 2 == 0 else "c_paint_black")
        m.box((side * 5.3, y - 0.6 + k * 0.24 + 0.12, 0.95), (0.06, 0.24, 0.09), smooth=False)
    m.mat("c_paint_white")
    m.box((side * 5.22, y, 2.75), (0.03, 0.9, 0.28), smooth=False)
    m.mat("c_iron_dark")
    m.push(Matrix.Translation((side * 5.2, y, 2.75)) @ _R(-side * 90, 'Z') @ _R(90, 'X'))   # reads from the track
    m.text(name, size=0.17, depth=0.006, font=E.FONT_JP, c=(0, 0, 0))
    m.pop()
    m.push(Matrix.Translation((side * 4.95, y, 0)) @ _R(90, 'Z'))
    m.mat("c_tie", uvscale=1.0)
    for ty in (-0.3, 0.22):                 # ties on the floor, tops at z 0, under the rail stub
        m.box((0, ty, (FLOOR - 0.02) / 2), (1.5, 0.2, -FLOOR + 0.02), smooth=False)
    _rail(m, -GAUGE / 2, -0.5, 0.5)
    _rail(m, GAUGE / 2, -0.5, 0.5)
    m.pop()
    lantern(m, (side * 5.15, y + 0.95, 2.3), lod)


def cave_props(lod=0, seed=1, seg=SEG):
    """Small props outside the lanes (|x| 3.7 .. 5.2), one variant per seed."""
    rnd = random.Random(seed * 7 + 2)
    m = E.Mesher("cave_props")
    side = 1 if seed % 2 else -1
    if seed == 1:
        mine_shrine(m, (side * 4.7, 3.0, FLOOR), yaw=side * 90 + 180)
        bench(m, (side * 4.75, 5.2, FLOOR), yaw=90)
        bucket(m, (side * 4.25, 6.3, FLOOR))
        for k in range(3):
            barrel(m, (-side * (4.3 + 0.35 * (k % 2)), 7.5 + k * 0.7, FLOOR), rnd)
        crate(m, (-side * 4.5, 9.8, FLOOR), 0.6, 12, "鉱石")
        crate(m, (-side * 4.5, 9.8, FLOOR + 0.6), 0.45, -8)
        pickaxe(m, (-side * 4.1, 10.5, FLOOR), yaw=90, lean=side * 15)
        rope_coil(m, (-side * 4.55, 11.2, FLOOR), yaw=-side * 70)
        ladder(m, (-side * 4.83, 4.5, FLOOR), yaw=0 if side < 0 else 180)
        signboard(m, (side * 4.3, 9.0, FLOOR), "第二坑道", yaw=side * 20)
    elif seed == 2:
        rail_stack(m, (side * 4.5, 5.0, FLOOR))
        for k in range(4):
            sack(m, (-side * (4.2 + 0.4 * (k % 2)), 2.0 + k * 0.55, FLOOR), rnd)
        shovel(m, (-side * 4.0, 4.6, FLOOR), yaw=90, lean=side * 12)
        signboard(m, (-side * 4.4, 9.5, FLOOR), "落石注意", yaw=-side * 15, col="c_paint_white", ink="c_paint_red")
        barrel(m, (side * 4.4, 9.5, FLOOR), rnd, h=0.8)
        bucket(m, (side * 4.3, 2.4, FLOOR), water=False)
        cable_drum(m, (-side * 4.75, 7.6, FLOOR), yaw=0)
        oil_drum(m, (-side * 4.5, 10.6, FLOOR), "c_paint_red")
        oil_drum(m, (-side * 4.9, 11.15, FLOOR), "c_loco")
        side_gallery(m, side, 8.0, lod)
    else:
        # an old hand cart left on a stub of narrow-gauge rail by the wall, with a lantern on a crate beside it.
        # Ties on the floor (tops at z 0), the rails and the cart at 0.62 scale so its wheels sit on the rails.
        for k in range(6):
            m.mat("c_tie" if k % 3 else "c_timber_dark", uvscale=1.0)
            m.box((side * 4.45 + rnd.uniform(-0.03, 0.03), 2.25 + k * 0.56, (FLOOR - 0.02) / 2),
                  (1.05, 0.2, -FLOOR + 0.02), smooth=False)
        m.push(Matrix.Translation((side * 4.45, 3.6, 0)) @ Matrix.Diagonal((0.62, 0.62, 0.62, 1)))
        for s in (-1, 1):
            _rail(m, s * GAUGE / 2, -1.6 / 0.62, 1.6 / 0.62)
        _wagon_body(m, -1.3, 2.6, rnd, lod, cargo=True)
        m.pop()
        _contact_shadow(m, side * 4.45, 3.6, 0.55, 1.0)
        crate(m, (-side * 4.4, 7.0, FLOOR), 0.55, 20, "危険")
        lantern(m, (-side * 4.4, 7.0, FLOOR + 0.55 + 0.62), lod)
        pickaxe(m, (-side * 4.0, 8.2, FLOOR), yaw=90, lean=-side * 18)
        shovel(m, (-side * 4.0, 8.6, FLOOR), yaw=90, lean=-side * 10)
        oil_drum(m, (side * 4.55, 6.3, FLOOR), "c_loco")
        ladder(m, (side * 4.83, 9.0, FLOOR), yaw=0 if side > 0 else 180)
        rope_coil(m, (side * 4.4, 10.8, FLOOR), yaw=side * 30)
        bench(m, (-side * 4.8, 10.4, FLOOR), yaw=90)
    ob = m.obj("cave_props_%d" % seed + ("" if lod == 0 else "@1"), smooth_angle=35)
    return ob


# ----------------------------------------------------------------------------- parting (Y fork)

FORK_LEN = 24.0
FORK_OFF = 1.2


def fork_x(y, side):
    """Centre of a branch of the parting at distance y (0..FORK_LEN): out over 6 m, parallel, back over 6 m."""
    def ss(t):
        t = min(1.0, max(0.0, t))
        return t * t * (3 - 2 * t)
    return side * FORK_OFF * (ss(y / 6.0) - ss((y - (FORK_LEN - 6.0)) / 6.0))


def cave_fork(lod=0, seed=8):
    """PARTING: the centre track splits around a crystal pillar into two branches and rejoins after 24 m; the outer
    tracks run straight through. A switch stand and a 分岐 board mark the split."""
    rnd = random.Random(seed)
    base = cave_track(lod, seg=FORK_LEN, lanes=(LANES[0], LANES[2]), name="cave_fork")
    m = E.Mesher("fork_branches")
    step = 0.75
    n = int(FORK_LEN / step)
    for k in range(n):
        y = (k + 0.5) * step
        xs = [fork_x(y, -1), fork_x(y, 1)]
        if abs(xs[1] - xs[0]) < 1.9:          # branches still overlap: one long tie under both
            m.mat("c_tie", uvscale=1.0)
            m.box(((xs[0] + xs[1]) / 2, y, -0.07), (1.9 + abs(xs[1] - xs[0]), 0.24, 0.14), smooth=False)
        else:
            for x in xs:
                m.mat("c_tie" if rnd.random() > 0.25 else "c_timber_dark", uvscale=1.0)
                m.box((x, y, -0.07), (1.85, 0.24, 0.14), smooth=False)
    rows = int(FORK_LEN / (0.5 if lod == 0 else 1.5)) + 1
    for side in (-1, 1):
        for r_off in (-GAUGE / 2, GAUGE / 2):
            path = [(fork_x(FORK_LEN * i / (rows - 1), side) + r_off, FORK_LEN * i / (rows - 1), 0.0) for i in range(rows)]
            import city
            m.mat("c_rail")
            m.sweep(path, [(-p[0], p[1]) for p in city.RAIL_PROF], closed=True, cap=True, up=(0, 0, 1))
            m.mat("c_rail_top")
            m.sweep([(x, y, 0.1612) for (x, y, z) in path], [(-0.025, 0.0), (0.025, 0.0), (0.025, 0.003), (-0.025, 0.003)],
                    closed=True, cap=False, up=(0, 0, 1))
    # crystal pillar between the branches, floor to vault
    m.mat("c_rock_dark", uvscale=1.0)
    m.cyl((0, FORK_LEN / 2, 4.0), r=0.42, r2=0.32, h=8.6, seg=12 if lod == 0 else 7)
    m.cyl((0, FORK_LEN / 2, 0.3), r=0.62, r2=0.42, h=0.8, seg=12 if lod == 0 else 7)
    for (z, a) in ((0.9, 30), (2.1, 160), (3.4, 280), (5.2, 90)):
        d = V((math.cos(math.radians(a)), math.sin(math.radians(a)) * 0.3, 0.4))
        crystal_cluster(m, (d.x * 0.35, FORK_LEN / 2 + d.y * 0.6, z), d, size=0.6, rnd=rnd,
                        mats=("c_crystal", "c_crystal_pink"), n=5, lod=lod)
    # long thin crystal ridge between the branches (so the split reads from far away)
    for k in range(6):
        y = 7.5 + k * 1.8
        if abs(y - FORK_LEN / 2) < 1.0:
            continue
        crystal_cluster(m, (0, y, FLOOR), (0, rnd.uniform(-0.3, 0.3), 1.0), size=rnd.uniform(0.35, 0.6), rnd=rnd,
                        mats=("c_crystal", "c_crystal_violet"), n=4, lod=lod)
    # switch stand with a lever and a red/white target, and the 分岐 board
    m.mat("c_iron_dark")
    m.box((1.7, 1.0, 0.1), (0.3, 0.3, 0.3), smooth=False)
    m.cyl((1.7, 1.0, 0.75), r=0.03, h=1.0, seg=8)
    m.mat("c_paint_red")
    m.cyl((1.7, 1.0, 1.3), r=0.2, h=0.03, seg=16, axis='Y')
    m.mat("c_paint_white")
    m.cyl((1.7, 0.98, 1.3), r=0.1, h=0.03, seg=16, axis='Y')
    signboard(m, (0.0, 4.0, FLOOR), "分岐", h=1.0, w=0.5, col="c_paint_white", ink="c_paint_red")
    ob = m.obj("fork_branches")
    bpy.context.view_layer.update()
    return E.join([base, ob], "cave_fork" + ("" if lod == 0 else "@1"))


# ----------------------------------------------------------------------------- scene assembly

def cave_lights(segments, y0=0.0, crystal_glow=True, energy=1.0):
    """Point lights for design renders: a warm pool under every lantern and a cool glow near crystal clusters."""
    lights = []

    def point(name, loc, color, power, radius=0.15):
        ld = bpy.data.lights.new(name, 'POINT')
        ld.energy = power * energy
        ld.color = E.hexrgb(color)
        ld.shadow_soft_size = radius
        ob = bpy.data.objects.new(name, ld)
        E.link(ob)
        ob.location = V(loc)
        lights.append(ob)
        return ob
    for i in range(segments):
        for k in range(2):
            y = y0 + i * SEG + k * 6.0
            for s in (-1, 1):
                point("lantern", (s * LANTERN_X, y, LANTERN_Z - 0.1), 0xFFC27A, 170, 0.3)
    if crystal_glow:
        for ob in list(bpy.data.objects):
            if ob.type == 'MESH' and ob.name.startswith("cave_deco"):
                # one cyan fill per deco object, centred low in the segment
                c = ob.matrix_world @ V((0, SEG / 2, 1.2))
                point("crystal_glow", (c.x + 3.6, c.y, 1.6), CRYSTALS[0], 50, 0.5)
                point("crystal_glow", (c.x - 3.6, c.y - 3, 1.6), CRYSTALS[1], 40, 0.5)
    return lights


def cave_tint():
    """Lit band takes the lantern colour, shadow band the cave violet (game: Zones.CAVERN)."""
    E.set_light_tint(light=0xFFE8C8, shadow=SHADOW, rimc=0xA8ECFF)


def cave_world():
    E.world_sky(0x2B2452, 0x4A3F7A, 1.0)


def cave_run(n=4, y0=0.0, seeds=(1, 2, 3, 1), outlines=True, pipe=True, props=True, fork_at=None):
    """n cave segments from y0: track (or the parting over segments fork_at, fork_at + 1), shell, deco, props and
    frames every 6 m. Returns the objects."""
    mats()
    obs = []
    for i in range(n):
        y = y0 + i * SEG
        sd = seeds[i % len(seeds)]
        parts = [cave_shell(seed=sd), cave_deco(seed=sd)]
        if fork_at is None or i not in (fork_at, fork_at + 1):
            parts.append(cave_track())
        elif i == fork_at:
            parts.append(cave_fork())
        if props:
            parts.append(cave_props(seed=sd))
        if pipe:
            parts.append(cave_pipe())
        for ob in parts:
            ob.location.y = y
            obs.append(ob)
        for k in range(2):
            ob = cave_frame(); ob.location.y = y + k * 6.0 + 1.0; obs.append(ob)
    if outlines:
        for ob in obs:
            if not ob.name.startswith(("cave_shell", "cave_track", "cave_fork")):
                E.add_outline(ob, 0.018)
    return obs


def hotaru_beam(loc, target, power=1500.0, angle=50.0):
    """The Hotaru Lamp as a warm spot light from Pongo's head toward where she runs."""
    ld = bpy.data.lights.new("hotaru", 'SPOT')
    ld.energy = power
    ld.color = E.hexrgb(0xFFE2B0)
    ld.spot_size = math.radians(angle)
    ld.spot_blend = 0.5
    ld.shadow_soft_size = 0.05
    ob = bpy.data.objects.new("hotaru", ld)
    E.link(ob)
    ob.location = V(loc)
    ob.rotation_euler = (V(target) - V(loc)).to_track_quat('-Z', 'Y').to_euler()
    return ob


def design_cave(only=""):
    """Crystal Cavern from Pongo's ore cart (Hotaru Lamp beam on), a high view down the gallery with the parting,
    a crystal close-up, and the left wall with its side gallery."""
    import vehicles as VH
    E.reset()
    studio.stage(res=(1280, 720), floor=False)
    studio._SUN[0].data.energy = 0.0
    cave_world()
    cave_run(5, y0=-12.0, seeds=(2, 1, 3, 2, 1), fork_at=3)
    for fn, loc in ((timber_beam, (0, 9.0, 0)), (bat_swarm, (2.4, 13.0, 0)), (rockpile, (-2.4, 6.0, 0)),
                    (crystal_rock, (2.4, 4.0, 0)), (fallen_log, (-2.4, 17.0, 0)), (ore_train, (2.4, 24.0, 0))):
        ob = fn(); ob.location = loc; E.add_outline(ob, 0.015)
    VH.mats()
    cart = VH.ore_cart(); cart.location = (0, 3.2, 0); E.add_outline(cart, 0.012)
    cave_lights(5, y0=-12.0 + 1.0)
    cave_tint()
    shots = {
        "cave_runner": dict(target=(0, 10, 1.3), dist=8.6, yaw=0, pitch=10, lens=24),
        "cave_overview": dict(target=(0, 46, 0.8), dist=18.4, yaw=-10, pitch=12, lens=24),
        "cave_crystals": dict(target=(2.6, 4, 1.1), dist=4.6, yaw=-35, pitch=8, lens=30),
        "cave_sides": dict(target=(-4.6, 31, 3.0), dist=8.5, yaw=62, pitch=6, lens=24),
    }
    for name, kw in shots.items():
        if only and only not in name:
            continue
        cam_t = V(kw["target"])
        y, p = math.radians(kw["yaw"]), math.radians(kw["pitch"])
        cam = cam_t + V((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p))) * kw["dist"]
        beam = hotaru_beam(cam + V((0.3, 1.0, -0.6)), cam_t + V((0, 6, -0.4))) if name == "cave_runner" else None
        studio.shoot(name, light=False, **kw)
        if beam:
            E.delete(beam)


def _sheet_floor(z=0.0, tracks=()):
    """Studio floor for the sheets; with tracks, a strip of real cave track (gravel bed, ties, floor at FLOOR) under
    each listed lane x, so the obstacles stand on the ground they stand on in the game."""
    E.mat("studio_floor", 0xF3EEE6, rim=0.0, spec=0.0, soft=0.2, outline=0)
    fl = E.Mesher("floor").mat("studio_floor")
    fl.box((0, 4, z - 0.02), (30, 22, 0.04), smooth=False)
    fl.obj()
    if tracks:
        t = cave_track(0, lanes=tuple(tracks), name="sheet_track")
        t.location.y = -4.0


def design_cave_props(only=""):
    """Obstacle sheet and small-prop sheet on the studio floor (daylight, for shape reading)."""
    if not only or "obstacles" in only:
        E.reset()
        studio.stage(res=(1600, 900), floor=False)
        mats()
        xs = (-7.5, -4.3, -0.9, 2.2, 5.3, 8.6)
        _sheet_floor(FLOOR - 0.004, tracks=xs)
        items = [(rockpile(), (xs[0], 0, 0)), (timber_beam(), (xs[1], 0, 0)), (fallen_log(), (xs[2], 0, 0)),
                 (bat_swarm(0), (xs[3], -0.5, 0)), (crystal_rock(), (xs[4], 0, 0)), (ore_train(wagons=1), (xs[5], -1.0, 0))]
        for ob, loc in items:
            ob.location = loc
            E.add_outline(ob, 0.015)
        b1 = bat("up"); b1.location = (-6.2, -2.0, 2.4); b1.scale = (3, 3, 3)
        b2 = bat("down"); b2.location = (-5.2, -2.0, 2.8); b2.scale = (3, 3, 3)
        for ob in (b1, b2):
            E.add_outline(ob, 0.004)
        studio.shoot("cave_obstacles", target=(0.6, 0, 1.0), dist=19, yaw=18, pitch=12, lens=35)
    if not only or "small" in only:
        E.reset()
        studio.stage(res=(1600, 900), floor=False)
        mats()
        _sheet_floor()
        m = E.Mesher("smallprops")
        rnd = random.Random(3)
        mine_shrine(m, (-4.2, 0, 0), yaw=0)
        barrel(m, (-2.9, 0.2, 0), rnd)
        barrel(m, (-2.3, 0.5, 0), rnd, h=0.8)
        crate(m, (-1.4, 0, 0), 0.6, 10, "鉱石")
        crate(m, (-1.4, 0, 0.6), 0.45, -12)
        crate(m, (-0.6, 0.1, 0), 0.55, 25, "危険")
        for k in range(3):
            sack(m, (0.3 + k * 0.45, 0.2 + (k % 2) * 0.3, 0), rnd)
        pickaxe(m, (1.8, 0, 0), yaw=0, lean=15)
        shovel(m, (2.3, 0, 0), yaw=0, lean=-12)
        signboard(m, (3.2, 0, 0), "第二坑道")
        signboard(m, (4.3, 0, 0), "落石注意", col="c_paint_white", ink="c_paint_red")
        rail_stack(m, (5.6, 0.5, 0), L=2.4)
        lantern(m, (-3.4, -0.9, 1.4))
        # back row: the rest stop and the stores
        bench(m, (-3.6, 2.0, 0), yaw=0)
        cable_drum(m, (-1.9, 2.1, 0), yaw=90)
        oil_drum(m, (-0.6, 2.0, 0), "c_paint_red")
        oil_drum(m, (0.05, 2.3, 0), "c_loco")
        bucket(m, (0.9, 1.7, 0))
        rope_coil(m, (1.8, 1.9, 0), yaw=-30)
        m.mat("c_plank", uvscale=1.0)
        m.box((3.6, 2.75, 1.3), (1.6, 0.05, 2.6), smooth=False)          # a bit of lagging to lean the ladder on
        ladder(m, (3.6, 2.08, 0), yaw=90)
        ob = m.obj("smallprops", smooth_angle=35)
        E.add_outline(ob, 0.01)
        h = hotaru_lamp(); h.location = (0.6, -1.4, 0.45); h.scale = (4, 4, 4); h.rotation_euler.z = math.radians(-30)
        E.add_outline(h, 0.004)
        studio.shoot("cave_smallprops", target=(0.7, 0.8, 0.6), dist=13.5, yaw=10, pitch=20, lens=40)
    if "closeups" in only:                 # one still per obstacle, for checking the small detail
        shots = [("rockpile", rockpile, dict(target=(0.1, -0.2, 0.55), dist=4.0, yaw=22, pitch=16)),
                 ("timber_beam", timber_beam, dict(target=(0, 0, 1.1), dist=4.6, yaw=18, pitch=10)),
                 ("fallen_log", fallen_log, dict(target=(0, 0, 0.95), dist=4.8, yaw=16, pitch=12)),
                 ("crystal_rock", crystal_rock, dict(target=(0, -0.2, 0.9), dist=5.0, yaw=20, pitch=14)),
                 ("ore_train", lambda: ore_train(wagons=1), dict(target=(0, 1.8, 1.1), dist=5.6, yaw=32, pitch=12)),
                 ("bat_swarm", lambda: bat_swarm(0), dict(target=(0, 0, 1.5), dist=3.6, yaw=12, pitch=6))]
        for name, fn, cam in shots:
            E.reset()
            studio.stage(res=(1200, 900), floor=False)
            mats()
            _sheet_floor(FLOOR - 0.004, tracks=(-2.4, 0.0, 2.4))
            E.add_outline(fn(), 0.012)
            studio.shoot("cave_ob_" + name, lens=40, **cam)


def export_cave():
    """build/models/*.erm for the cave kit (LOD0 + LOD1). Kept apart from the Sakura Line names."""
    for lod in (0, 1):
        sfx = "" if lod == 0 else "@1"
        E.reset(); mats()
        E.export_erm(cave_track(lod), "cave_track" + sfx)
        for sd in (1, 2, 3):
            E.export_erm(cave_shell(lod, sd), "cave_shell_%d" % sd + sfx)
            E.export_erm(cave_deco(lod, sd), "cave_deco_%d" % sd + sfx)
            E.export_erm(cave_props(lod, sd), "cave_props_%d" % sd + sfx)
        E.export_erm(cave_frame(lod), "cave_frame" + sfx)
        E.export_erm(cave_pipe(lod), "cave_pipe" + sfx)
        E.export_erm(cave_fork(lod), "cave_fork" + sfx)
        E.export_erm(ore_train(lod=lod), "ob_ore_train" + sfx)
    E.reset(); mats()
    E.export_erm(rockpile(), "ob_rockpile")
    E.export_erm(timber_beam(), "ob_timber_beam")
    E.export_erm(fallen_log(), "ob_fallen_log")
    E.export_erm(bat_swarm(0), "ob_bat_swarm_a")
    E.export_erm(bat_swarm(1), "ob_bat_swarm_b")
    E.export_erm(crystal_rock(), "ob_crystal_rock")
    E.export_erm(hotaru_lamp(), "hotaru_lamp")
    E.export_erm(bat("up"), "bat_up")
    E.export_erm(bat("down"), "bat_down")
