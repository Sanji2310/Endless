"""
PONGO v4 — clean-topology rebuild of the hero.

Techniques (standard anime-character practice):
  * every organic part is a lofted quad grid with deliberate edge loops (no voxel remesh),
    smoothed with a subdivision level instead of sculpt noise;
  * the face takes its normals from a smooth proxy ellipsoid (masked, feathered), so the cel
    terminator draws one simple shape across the cheek instead of following small bumps;
  * hair is built from lens-section clumps (sharp edges, full centre) whose normals come from
    an expanded head proxy, so the hair shades as one mass with a clean highlight band;
  * hard parts (soles, buckles, goggles) use bevel + weighted normals;
  * secondary motion comes from spring bones (hair clumps, lace ends, goggle strap).

Blender space: Z up, character faces +Y, right side is +X.
"""
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix, Euler
import erlib as E
import studio
import characters as CH

V = Vector


def catmull(keys, x):
    """Piecewise Catmull-Rom through sorted [(x, value...)] (values tuples)."""
    xs = [k[0] for k in keys]
    if x <= xs[0]:
        return keys[0][1:]
    if x >= xs[-1]:
        return keys[-1][1:]
    i = max(j for j in range(len(xs) - 1) if xs[j] <= x)
    x0, x1 = xs[i], xs[i + 1]
    t = (x - x0) / (x1 - x0)
    p0 = keys[max(i - 1, 0)][1:]
    p1 = keys[i][1:]
    p2 = keys[i + 1][1:]
    p3 = keys[min(i + 2, len(keys) - 1)][1:]
    out = []
    for a, b, c, d in zip(p0, p1, p2, p3):
        out.append(0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (-a + 3 * b - 3 * c + d) * t ** 3))
    return tuple(out)


# ============================================================================ head

# Head profile table (units of head radius r, z measured from the head centre, top = +1).
#   w: half width, f: depth toward the face (+Y), b: depth toward the back, cy: ring centre y,
#   pf: front superellipse exponent (2 round, <2 pointed toward the chin, >2 flatter face plane)
HEAD_KEYS = [
    # z      w     f     b     cy     pf
    (-1.00, 0.10, 0.55, 0.05, 0.30, 2.2),
    (-0.97, 0.17, 0.60, 0.08, 0.29, 2.1),
    (-0.92, 0.27, 0.66, 0.14, 0.26, 1.95),
    (-0.84, 0.39, 0.73, 0.24, 0.20, 1.85),
    (-0.74, 0.53, 0.80, 0.36, 0.14, 1.85),
    (-0.62, 0.665, 0.86, 0.52, 0.08, 1.95),
    (-0.48, 0.78, 0.90, 0.70, 0.03, 2.05),
    (-0.32, 0.86, 0.93, 0.86, 0.0, 2.15),
    (-0.12, 0.89, 0.95, 0.98, -0.01, 2.2),
    (0.10, 0.89, 0.94, 1.03, -0.02, 2.1),
    (0.30, 0.86, 0.90, 1.03, -0.02, 2.0),
    (0.50, 0.80, 0.82, 0.97, -0.02, 2.0),
    (0.70, 0.67, 0.68, 0.82, -0.02, 2.0),
    (0.85, 0.51, 0.52, 0.63, -0.02, 2.0),
    (0.95, 0.32, 0.32, 0.38, -0.02, 2.0),
    (1.00, 0.0, 0.0, 0.0, -0.02, 2.0),
]


def head_pt(z, th, keys=None):
    """Single point (units of r, relative to the head centre) of the lofted head at height z, azimuth th (rad)."""
    w, f, b, cy, pf = catmull(keys or HEAD_KEYS, z)
    s, c = math.sin(th), math.cos(th)
    k = max(0.0, c)
    p = 2.0 + (pf - 2.0) * k ** 0.6
    x = w * math.copysign(abs(s) ** (2.0 / p), s)
    y = (f if c > 0 else b) * math.copysign(abs(c) ** (2.0 / p), c) + cy
    tw = abs(th if th <= math.pi else th - 2 * math.pi)
    cheek = 0.035 * math.exp(-((z + 0.48) / 0.16) ** 2) * math.exp(-((tw - 0.75) / 0.35) ** 2)
    x *= 1 + cheek
    y += cheek * 0.5 * c
    temple = 0.02 * math.exp(-((z - 0.25) / 0.2) ** 2) * abs(s) ** 4
    x *= 1 - temple
    return V((x, y, z))


def head_ring(z, n, r, keys=None):
    w, f, b, cy, pf = catmull(keys or HEAD_KEYS, z)
    pts = []
    for i in range(n):
        th = 2 * math.pi * i / n          # 0 = front (+Y), pi/2 = +X
        s, c = math.sin(th), math.cos(th)
        p = pf if c > 0 else 2.0
        # blend exponent smoothly across the side so there is no crease at the ear
        k = max(0.0, c)
        p = 2.0 + (pf - 2.0) * k ** 0.6
        x = w * math.copysign(abs(s) ** (2.0 / p), s)
        y = (f if c > 0 else b) * math.copysign(abs(c) ** (2.0 / p), c) + cy
        # anime cheek: gentle fullness low on the front-side of the face
        cheek = 0.035 * math.exp(-((z + 0.48) / 0.16) ** 2) * math.exp(-((abs(th if th < math.pi else th - 2 * math.pi) - 0.75) / 0.35) ** 2)
        x *= 1 + cheek
        y += cheek * 0.5 * c
        # temple: very slight flattening at the sides of the forehead
        temple = 0.02 * math.exp(-((z - 0.25) / 0.2) ** 2) * abs(s) ** 4
        x *= 1 - temple
        pts.append((x * r, y * r, z * r))
    return pts


def head4(B, skin_mat, name="pongo_head", rings=34, seg=40, keys=None):
    r = B.head_r
    c = B.headc
    m = E.Mesher(name).mat(skin_mat)
    zs = []
    for i in range(rings):
        t = i / (rings - 1)
        # denser loops around the face (eyes to chin) for a clean jaw line
        z = -1.0 + 2.0 * (t ** 1.15)
        zs.append(z)
    ring_pts = [head_ring(z, seg, r, keys) for z in zs[:-1]]
    m.push(Matrix.Translation(c))
    bm = m.bm
    vr = [[bm.verts.new(m.M @ V(p)) for p in rp] for rp in ring_pts]
    top = bm.verts.new(m.M @ V((0, -0.02 * r, 1.0 * r)))
    bot_c = catmull(keys or HEAD_KEYS, -1.0)
    bot = bm.verts.new(m.M @ V((0, (bot_c[3] + 0.18) * r, -1.0 * r - 0.004)))
    faces = []
    for j in range(len(vr) - 1):
        a, b = vr[j], vr[j + 1]
        for i in range(seg):
            k = (i + 1) % seg
            faces.append(bm.faces.new((a[i], a[k], b[k], b[i])))
    for i in range(seg):
        k = (i + 1) % seg
        faces.append(bm.faces.new((vr[-1][i], vr[-1][k], top)))
        faces.append(bm.faces.new((vr[0][k], vr[0][i], bot)))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    m._finish([v for row in vr for v in row] + [top, bot], None, 'box', True)
    m.pop()
    ob = m.obj(name, smooth_angle=180)
    sub = ob.modifiers.new("subsurf", 'SUBSURF')
    sub.levels = 1
    sub.render_levels = 1
    sub.quality = 3
    E.apply_modifiers(ob)
    E.ensure_ao(ob)
    return ob


def ears(B, skin_mat, name="pongo_ears", subsurf=1):
    """Stylised ears: flattened C-shaped helix rim around a shallow concha, tilted back."""
    r = B.head_r
    c = B.headc
    m = E.Mesher(name).mat(skin_mat)
    for side in (1, -1):
        base = c + V((side * 0.875 * r, -0.08 * r, -0.22 * r))
        m.push(Matrix.Translation(base) @ Matrix.Rotation(math.radians(side * 18), 4, 'Z') @ Matrix.Rotation(math.radians(-10), 4, 'X'))
        # helix rim: C-curve from the top front, round the back, down to the lobe
        pts = []
        for i in range(15):
            a = math.radians(70 + 230 * i / 14)
            rx = 0.024 * r / 0.118 if False else 0.0
            pts.append((side * 0.012 * (1 - 0.3 * i / 14), 0.02 * math.cos(a) - 0.004, 0.034 * math.sin(a) * (1.0 if math.sin(a) > 0 else 0.85)))
        m.sweep(pts, [(math.cos(2 * math.pi * k / 8) * 0.006, math.sin(2 * math.pi * k / 8) * 0.0045) for k in range(8)],
                closed=True, cap=True, scale=lambda t: 1.0 - 0.25 * abs(t - 0.45), up=(side, 0, 0))
        # concha: shallow flattened disc set slightly inside the rim
        m.sphere((side * 0.006, -0.004, -0.002), 1.0, 14, 8, s=(0.006, 0.019, 0.028))
        # lobe
        m.sphere((side * 0.009, 0.006, -0.03), 1.0, 10, 6, s=(0.006, 0.009, 0.009))
        m.pop()
    ob = m.obj(name, smooth_angle=180, subsurf=subsurf)
    E.apply_modifiers(ob)
    return ob


def face_normals_gfn(head, B, bend=20.0, bend_top=-0.4, xs_mid=1.05, xs_low=0.92, depth_scale=0.95, width=0.89, flat_z=1.0):
    """'Generated face normals' (after aVersionOfReality's object-coordinate method):
    throw the mesh normals away and build new ones from coordinates in a box that fits the head,
    which shades like a sphere; then bend the lower half around X so the cheek/jaw/chin curve
    reads as one clean arc, and widen X through the cheeks. Topology-independent and clean
    from every light angle."""
    r = B.head_r
    c = B.headc
    me = head.data
    ext = V((width * r, 1.0 * r * depth_scale, 1.0 * r))
    nrm = []
    for v in me.vertices:
        p = head.matrix_world @ v.co - c
        q = V((p.x / ext.x, p.y / ext.y, p.z / ext.z))
        # widen the middle of the face (cheeks), slim toward the chin
        zz = q.z
        sx = 1.0
        sx *= 1.0 + (xs_mid - 1.0) * math.exp(-((zz + 0.3) / 0.35) ** 2)
        sx *= 1.0 + (xs_low - 1.0) * max(0.0, min(1.0, (-zz - 0.55) / 0.4))
        q.x /= sx
        # bend the lower face toward the chin (rotation about X, front part only)
        if zz < bend_top and q.y > -0.2:
            t = min(1.0, (bend_top - zz) / (1.0 + bend_top))
            ang = math.radians(bend) * (t * t * (3 - 2 * t)) * min(1.0, (q.y + 0.2) / 0.5)
            ca, sa = math.cos(ang), math.sin(ang)
            y, z = q.y, q.z
            q.y, q.z = y * ca + z * sa, -y * sa + z * ca
        # Genshin-style: the face reacts mostly to the horizontal light angle; flatten the vertical
        # curvature on the face front (below the brow), keep the skull round above it
        if flat_z < 1.0 and q.y > 0:
            k = min(1.0, q.y / 0.5) * min(1.0, max(0.0, (0.3 - zz) / 0.3))
            q.z *= 1.0 - (1.0 - flat_z) * k
        n = q.normalized() if q.length > 1e-6 else V((0, 1, 0))
        # keep the true normals at the very back/top of the skull (under the hair anyway)
        nrm.append(n)
    E.set_smooth(head, 180.0)
    me.normals_split_custom_set_from_vertices([tuple(n) for n in nrm])
    me.update()


def face_normals(head, B):
    """Transfer smooth normals from a proxy onto the face area (feathered mask)."""
    r = B.head_r
    c = B.headc
    proxy = E.proxy_ellipsoid("pongo_face_proxy", c + V((0, 0.02 * r, -0.1 * r)), (1.0 * r, 1.0 * r, 1.12 * r))

    def wfn(co):
        p = head.matrix_world @ co - c
        fy = (p.y / r - 0.05) / 0.35                 # front of the head
        fz = (0.22 - p.z / r) / 0.2                  # below the brow line
        return min(1.0, max(0.0, fy)) * min(1.0, max(0.0, fz))
    E.mask_group(head, "face_mask", wfn)
    E.transfer_normals(head, proxy, 1.0, "face_mask")
    return proxy


def nose4(B, m, bvh):
    """Small anime nose: a soft wedge whose lit side reads as a single highlight/shadow pair."""
    c = B.headc
    r = B.head_r
    M = CH.surface_frame(bvh, 0.0, c.z - 0.47 * r, -0.0008)
    m.push(M)
    m.sweep([(0, 0, 0.012), (0, 0.003, 0.004), (0, 0.0065, -0.002), (0, 0.004, -0.0055)],
            [(math.cos(2 * math.pi * k / 8), math.sin(2 * math.pi * k / 8) * 0.8) for k in range(8)],
            closed=True, cap=True, scale=lambda t: 0.001 + 0.0032 * t ** 1.4, up=(0, 1, 0))
    m.pop()


# ============================================================================ design renders

def _stage():
    E.reset()
    studio.stage(res=(1200, 1200))


def design_head():
    _stage()
    B = CH.Body(1.70, head_r=0.124)
    CH.pongo_mats()
    head = head4(B, "pongo_skin")
    ear = ears(B, "pongo_skin")
    face_normals_gfn(head, B)
    fm = E.Mesher("pongo_face")
    bvh = CH.bvh_of(head)
    CH.anime_face(B, fm, head, "d_eye_pongo", "d_mouth_grin", CH.PONGO_COLORS["brow"], "pongo_skin",
                  bandaid=True, nose=False, eye_w=0.084, eye_h=0.08, eye_x=0.046, eye_z=-0.03, mouth_w=0.032)
    E.mat("pongo_skin_detail", CH.PONGO_COLORS["skin"], skin=1.0, rim=0.0, soft=0.12, outline=0.0)
    fm.mat("pongo_skin_detail")
    nose4(B, fm, bvh)
    face = fm.obj("pongo_face", smooth_angle=60)
    for o in (head, ear):
        E.add_outline(o, 0.0022)
    c = B.headc
    sc = bpy.context.scene
    studio.shoot("p4_head_front", target=(0, 0.05, c.z - 0.01), dist=0.95, yaw=180, pitch=2, lens=70)
    studio.shoot("p4_head_34", target=(0, 0.05, c.z - 0.01), dist=0.95, yaw=215, pitch=4, lens=70)
    studio.shoot("p4_head_side", target=(0, 0.0, c.z - 0.01), dist=0.95, yaw=270, pitch=2, lens=70)
