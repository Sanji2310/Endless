"""
PONGO characters: humanoid builder, anime faces, hair, clothing, rig, animation clips,
export and design renders.

Blender space: Z up, the character faces +Y, its right side is +X.
"""
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix, Euler, Quaternion
from mathutils.bvhtree import BVHTree
import erlib as E
import studio

V = Vector


# ============================================================================ proportions

class Body:
    """Joint landmarks for a humanoid (metres)."""

    def __init__(self, h=1.78, sho_x=0.175, hip_x=0.095, head_r=0.118, arm=1.0, leg=1.0, girth=1.0):
        k = h / 1.78
        self.k = k
        self.ANK = 0.085 * k
        self.KNEE = 0.47 * k
        self.HIP = 0.88 * k
        self.WAIST = 1.02 * k
        self.CHEST = 1.24 * k
        self.SHO = 1.385 * k
        self.NECK = 1.45 * k
        self.CHIN = 1.505 * k
        self.HEADC = 1.628 * k
        self.TOP = 1.785 * k
        self.head_r = head_r * (0.94 + 0.06 * k)
        self.SHOX = sho_x * k * girth
        self.HIPX = hip_x * k * girth
        self.girth = girth
        self.shoulder = V((self.SHOX, 0.0, self.SHO))
        self.elbow = V((0.285 * k * girth ** 0.5, -0.01, 1.16 * k))
        self.wrist = V((0.37 * k * girth ** 0.5, 0.0, 0.94 * k))
        self.handend = V((0.40 * k * girth ** 0.5, 0.012, 0.825 * k))
        self.hipj = V((self.HIPX, 0.0, self.HIP))
        self.knee = V((self.HIPX * 1.03, 0.012, self.KNEE))
        self.ankle = V((self.HIPX * 1.04, -0.012, self.ANK))
        self.toe = V((self.HIPX * 1.04, 0.13 * k, 0.02))
        self.headc = V((0.0, 0.012 * k, self.HEADC))

    def mirror(self, v, side):
        return V((v.x * side, v.y, v.z))


# ============================================================================ geometry helpers

def ring(c, ax, sx, rx, ry, n=16, pw=2.0, yoff=0.0):
    ax = ax.normalized()
    sx = (sx - ax * sx.dot(ax)).normalized()
    sy = ax.cross(sx).normalized()
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        ca, sa = math.cos(a), math.sin(a)
        x = rx * math.copysign(abs(ca) ** (2.0 / pw), ca)
        y = ry * math.copysign(abs(sa) ** (2.0 / pw), sa) + yoff
        pts.append(tuple(c + sx * x + sy * y))
    return pts


def limb(m, pts, radii, n=14, cap=True, sx=V((1, 0, 0)), pw=2.0, flat=1.0):
    """Tube through joint points with radius per point (rx, ry) or float."""
    rings = []
    for i, p in enumerate(pts):
        a = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        r = radii[i]
        rx, ry = (r, r * flat) if isinstance(r, (int, float)) else r
        rings.append(ring(p, a, sx, rx, ry, n, pw))
    return m.quad_strip(rings, closed=True, cap0=cap, cap1=cap)


def interp_pts(a, b, n):
    return [a.lerp(b, i / (n - 1)) for i in range(n)]


def project_decal(m, bvh, cx, cz, w, h, nx=7, nz=7, off=0.0015, mirror=False, uvrect=(0, 0, 1, 1), y0=1.0, curve_z=None, back=False):
    """Grid patch projected onto a head surface along -Y, UV-mapped for a decal texture."""
    rings = []
    uvs = []
    for j in range(nz):
        row = []
        for i in range(nx):
            u = i / (nx - 1)
            v = j / (nz - 1)
            x = cx - w / 2 + u * w
            z = cz - h / 2 + v * h
            if curve_z:
                z += curve_z(u)
            hit = bvh.ray_cast(V((x, -y0 if back else y0, z)), V((0, 1 if back else -1, 0)))
            if hit[0] is None:
                p = V((x, 0.0, z))
                n = V((0, -1 if back else 1, 0))
            else:
                p, n = hit[0], hit[1]
            row.append(tuple(p + n * off))
        rings.append(row)
    bm = m.bm
    vs = [[bm.verts.new(m.M @ V(p)) for p in row] for row in rings]
    faces = []
    for j in range(nz - 1):
        for i in range(nx - 1):
            f = bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
            faces.append(f)
    for f in faces:
        f.material_index = m.mi
        f.smooth = True
        for l in f.loops:
            # recover grid indices
            for j in range(nz):
                if l.vert in vs[j]:
                    i = vs[j].index(l.vert)
                    u = i / (nx - 1)
                    v = j / (nz - 1)
                    if mirror:
                        u = 1 - u
                    l[m.uv].uv = (uvrect[0] + u * (uvrect[2] - uvrect[0]), uvrect[1] + v * (uvrect[3] - uvrect[1]))
                    l[m.col] = m.tint
                    break
    return faces


def surface_path(bvh, pts, off=0.002):
    out = []
    for (x, z) in pts:
        hit = bvh.ray_cast(V((x, 1.0, z)), V((0, -1, 0)))
        if hit[0] is None:
            out.append(V((x, 0.1, z)))
        else:
            out.append(hit[0] + hit[1] * off)
    return out


def bvh_of(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.transform(obj.matrix_world)
    t = BVHTree.FromBMesh(bm)
    bm.free()
    ev.to_mesh_clear()
    return t


# ============================================================================ heads

HEAD_SHAPE = dict(jaw=0.3, cheek=0.06, drop=0.05, back=1.07, width=1.03)


def deform_head(rel, r, shape=HEAD_SHAPE):
    """Anime head from a sphere: full cheeks, jaw tapering late to a small rounded chin."""
    x, y, z = rel
    if z < 0:
        t = min(1.0, -z / r)
        s = max(0.0, (t - 0.3) / 0.7)
        s = s * s * (3 - 2 * s)
        x *= (1 - shape["jaw"] * s) * (1 + shape["cheek"] * math.sin(math.pi * min(1.0, t * 1.2)))
        z *= 1 + shape["drop"] * t
        if y > 0:
            y *= 1 - 0.1 * s
        y += 0.008 * s * max(0.0, 1 - abs(x) / (0.5 * r))
    if y < 0:
        y *= shape["back"]
    if y > 0:
        y *= 1 - 0.06 * (y / r) ** 2
    x *= shape["width"]
    return V((x, y, z))


def head_mesh(B, skin_mat, name="head", ear=True, shape=HEAD_SHAPE):
    m = E.Mesher(name).mat(skin_mat)
    r = B.head_r
    c = B.headc
    res = bmesh.ops.create_uvsphere(m.bm, u_segments=32, v_segments=22, radius=r, matrix=Matrix.Translation(c))
    for v in res["verts"]:
        v.co = c + deform_head(v.co - c, r, shape)
    m._finish(res["verts"], None, 'box', True)
    if ear:
        for side in (1, -1):
            m.push(Matrix.Translation((side * r * 0.985, c.y - 0.006, c.z - 0.012)) @ Matrix.Rotation(math.radians(side * 12), 4, 'Z'))
            m.sphere((0, 0, 0), 1.0, 12, 8, s=(0.013, 0.021, 0.032))
            m.pop()
    return m


def surface_frame(bvh, x, z, off=0.001):
    hit = bvh.ray_cast(V((x, 1.0, z)), V((0, -1, 0)))
    p, n = (hit[0], hit[1]) if hit[0] is not None else (V((x, 0.1, z)), V((0, 1, 0)))
    yl = n.normalized()
    xl = V((1, 0, 0))
    xl = (xl - yl * xl.dot(yl)).normalized()
    zl = xl.cross(yl).normalized()
    R = Matrix((xl, yl, zl)).transposed().to_4x4()
    return Matrix.Translation(p + yl * off) @ R


def anime_face(B, m, head_obj, eye_tex, mouth_tex, brow_col, skin_mat, eye_w=0.07, eye_h=0.068, eye_x=0.051,
               eye_z=-0.03, brow_arch=0.007, blush=False, bandaid=False, nose=True, mouth_w=0.036):
    """Adds projected eyes, brows, nose and mouth (and optional blush/band-aid) to mesher m."""
    bvh = bvh_of(head_obj)
    c = B.headc
    E.mat("eye_" + eye_tex, 0xFFFFFF, tex=eye_tex, flags=E.F_DECAL | E.F_NOCAST, outline=0, rim=0, spec=0, soft=0.02)
    m.mat("eye_" + eye_tex)
    for side in (1, -1):
        project_decal(m, bvh, side * eye_x, c.z + eye_z, eye_w, eye_h, 8, 8, mirror=(side < 0))
    E.mat("mouth_" + mouth_tex, 0xFFFFFF, tex=mouth_tex, flags=E.F_DECAL | E.F_NOCAST, outline=0, rim=0, soft=0.02)
    m.mat("mouth_" + mouth_tex)
    project_decal(m, bvh, 0.0, c.z - 0.083, mouth_w, mouth_w * 0.5, 6, 4)
    if blush:
        E.mat("blush", 0xFFFFFF, tex="d_blush", flags=E.F_DECAL | E.F_NOCAST, outline=0, rim=0)
        m.mat("blush")
        for side in (1, -1):
            project_decal(m, bvh, side * 0.06, c.z - 0.05, 0.036, 0.018, 5, 3, off=0.001)
    # eyebrows: flat strokes following the forehead
    E.mat("brow_%06x" % brow_col, brow_col, outline=0.3, rim=0.0, soft=0.05)
    m.mat("brow_%06x" % brow_col)
    for side in (1, -1):
        pts2 = []
        for i in range(7):
            t = i / 6
            x = side * (eye_x - eye_w * 0.42 + t * eye_w * 0.95)
            z = c.z + eye_z + eye_h * 0.62 + brow_arch * math.sin(math.pi * t) - 0.004 * t
            pts2.append((x, z))
        path = surface_path(bvh, pts2, 0.002)
        m.sweep(path, [(-1, -0.25), (1, -0.25), (1, 0.25), (-1, 0.25)], closed=True, cap=True,
                scale=lambda t: (0.0045 * (1.2 - 0.6 * t), 0.004), up=(0, 1, 0))
    if nose:
        gm = E._MATS[skin_mat]
        E.mat(skin_mat + "_detail", gm.color, skin=1.0, rim=0.0, soft=0.12, outline=0.0)
        m.mat(skin_mat + "_detail")
        m.push(surface_frame(bvh, 0.0, c.z - 0.056, -0.001))
        m.sphere((0, 0, 0), 1.0, 10, 6, s=(0.0055, 0.006, 0.009))
        m.pop()
    if bandaid:
        E.mat("bandaid", 0xF6DDBE, outline=0.0, rim=0.1, soft=0.12)
        E.mat("bandaid_pad", 0xEBCBA3, outline=0.0, rim=0.0, soft=0.12)
        m.push(surface_frame(bvh, -0.066, c.z - 0.062, 0.0008) @ Matrix.Rotation(math.radians(-24), 4, 'Y'))
        m.mat("bandaid")
        m.rbox((0, 0, 0), (0.032, 0.0025, 0.012), 0.0012, 1)
        m.mat("bandaid_pad")
        m.rbox((0, 0.0012, 0), (0.01, 0.002, 0.0085), 0.001, 1)
        m.pop()


# ============================================================================ hair

def spike(m, base, direction, length, width, bend=V((0, 0, 0)), flat=0.45, twist=0.0, n=10):
    d = direction.normalized()
    p0 = base - d * length * 0.15
    p3 = base + d * length + bend
    p1 = base + d * length * 0.35
    p2 = base + d * length * 0.7 + bend * 0.5
    path = [V(p) for p in E.bezier(p0, p1, p2, p3, n)]
    prof = [(math.cos(2 * math.pi * i / 8), math.sin(2 * math.pi * i / 8) * flat) for i in range(8)]
    m.sweep(path, prof, closed=True, cap=True, scale=lambda t: width * max(0.02, (1 - t) ** 0.85) * (1.0 if t > 0.1 else 0.85 + 1.5 * t),
            twist=twist, up=(0, 0, 1))


def sph(c, r, theta, phi):
    """Point on a sphere: theta azimuth from +Y toward +X, phi elevation."""
    t, p = math.radians(theta), math.radians(phi)
    return c + V((r * math.cos(p) * math.sin(t), r * math.cos(p) * math.cos(t), r * math.sin(p)))


def hair_cap(m, B, front=0.5, back=0.95, side=-0.36, scale=1.1, zoff=0.006):
    """Shell over the skull (same deformation as the head), trimmed at the hairline."""
    r = B.head_r
    c = B.headc + V((0, 0, zoff))
    res = bmesh.ops.create_uvsphere(m.bm, u_segments=32, v_segments=20, radius=r, matrix=Matrix.Translation(c))
    kill = []
    for v in res["verts"]:
        rel = v.co - c
        y, z = rel.y / r, rel.z / r
        zmin = side + front * max(0.0, y) - back * max(0.0, -y) ** 1.2
        if z < zmin:
            kill.append(v)
        else:
            v.co = c + deform_head(rel * scale, r * scale)
    bmesh.ops.delete(m.bm, geom=kill, context='VERTS')
    verts = [v for v in res["verts"] if v.is_valid]
    m._finish(verts, None, 'box', True)


def pongo_hair(m, B):
    c = B.headc
    r = B.head_r
    rnd = random.Random(7)
    hair_cap(m, B)
    # bangs: five clumps with gaps, tips just above the eyes
    for th, L, W, lean in ((-38, 0.095, 0.052, -0.35), (-17, 0.08, 0.055, -0.15), (4, 0.09, 0.058, 0.05), (24, 0.076, 0.052, 0.2), (44, 0.09, 0.048, 0.35)):
        base = sph(c, r * 1.06, th, 50)
        d = V((lean * 0.5, 0.62, -1.0))
        spike(m, base, d, L + rnd.uniform(-0.005, 0.005), W, bend=V((lean * 0.02, 0.018, 0.004)), flat=0.4)
    # side locks framing the face
    for side in (1, -1):
        base = sph(c, r * 1.07, side * 62, 22)
        spike(m, base, V((side * 0.18, 0.35, -1.0)), 0.12, 0.04, bend=V((0, 0.012, 0)), flat=0.38)
    # front crest sweeping up and back
    for th in (-20, 8, 30):
        spike(m, sph(c, r * 1.0, th, 58), V((0.1 * th / 30, 0.2, 1.0)), 0.13, 0.036, bend=V((0, -0.05, 0.0)))
    # crown: big spikes flaring back, tips flicking up
    for th, ph, L in ((-40, 72, 0.14), (0, 80, 0.155), (40, 72, 0.14), (-80, 62, 0.125), (80, 62, 0.125)):
        d = V((math.sin(math.radians(th)) * 0.5, -0.8, 0.75))
        spike(m, sph(c, r * 1.0, th, ph), d, L, 0.047, bend=V((0, -0.01, 0.035)))
    # sides over the ears
    for side in (1, -1):
        for ph, L in ((30, 0.12), (8, 0.11)):
            base = sph(c, r * 1.04, side * 95, ph)
            spike(m, base, V((side * 0.55, -0.7, -0.35)), L, 0.038, bend=V((0, -0.02, -0.02)))
        spike(m, sph(c, r * 1.04, side * 70, 20), V((side * 0.3, 0.25, -1.0)), 0.1, 0.03)  # sideburn locks
    # back and nape
    for th in (150, 175, 200, 125, 225, 105, 245):
        for ph, L, dz, up in ((38, 0.12, 0.2, 0.03), (10, 0.1, -0.55, 0.015), (-18, 0.075, -0.95, 0.0)):
            base = sph(c, r * 1.03, th, ph)
            d = V((math.sin(math.radians(th)) * 0.45, -0.75, dz))
            spike(m, base, d, L + rnd.uniform(-0.008, 0.01), 0.044, bend=V((0, 0, up)))
    # ahoge: a single strand curling forward from the crown
    base = sph(c, r * 1.05, 5, 84)
    path = [V(p) for p in E.bezier(base, base + V((0, 0.02, 0.07)), base + V((0, 0.09, 0.09)), base + V((0, 0.1, 0.03)), 12)]
    m.sweep(path, [(math.cos(2 * math.pi * i / 6), math.sin(2 * math.pi * i / 6) * 0.4) for i in range(6)], closed=True, cap=True,
            scale=lambda t: 0.012 * (1 - t) ** 0.7 + 0.001)


# ============================================================================ bodies and clothes

def neck(m, B, r=0.043):
    limb(m, [V((0, -0.006, B.SHO + 0.01)), V((0, 0.0, B.NECK)), V((0, 0.004, B.CHIN + 0.035))], [r * 1.12, r, r * 0.95], n=14)


def hands(m, B, glove_mat, skin_mat, fingerless=True, fist=0.8):
    for side in (1, -1):
        w = B.mirror(B.wrist, side)
        e = B.mirror(B.handend, side)
        d = (e - w).normalized()
        # hand frame: z along -d (pointing to fingers is -Z_local), palm faces -X_local toward the body
        zl = -d
        xl = V((side, 0, 0))
        xl = (xl - zl * xl.dot(zl)).normalized()
        yl = zl.cross(xl).normalized()
        R = Matrix((xl, yl, zl)).transposed().to_4x4()
        M = Matrix.Translation(w) @ R
        m.push(M)
        m.mat(glove_mat)
        m.rbox((0.002, 0.0, -0.046), (0.03, 0.07, 0.064), 0.012, 2)
        m.cyl((0, 0, -0.008), 0.031, 0.026, 16, r2=0.033)
        m.mat(skin_mat if fingerless else glove_mat)
        for k in range(4):
            yy = -0.027 + k * 0.018
            L = 1.0 - 0.12 * abs(k - 1.5)
            a = V((0.0, yy, -0.078))
            b = V((-0.022 * side * 0 - 0.02, yy, -0.105 * L))
            cpt = V((-0.036, yy, -0.092 * L))
            path = [a, a.lerp(b, 0.5), b, b.lerp(cpt, 0.5), cpt]
            m.sweep(path, [(math.cos(2 * math.pi * i / 8), math.sin(2 * math.pi * i / 8)) for i in range(8)], closed=True, cap=True,
                    scale=lambda t: 0.0095 * (1 - 0.15 * t))
        # thumb
        path = [V((-0.012, 0.03, -0.022)), V((-0.028, 0.042, -0.045)), V((-0.04, 0.034, -0.066))]
        m.sweep(path, [(math.cos(2 * math.pi * i / 8), math.sin(2 * math.pi * i / 8)) for i in range(8)], closed=True, cap=True,
                scale=lambda t: 0.0105 * (1 - 0.2 * t))
        m.pop()


def sleeves(m, B, mat, cuff_mat=None, r0=0.068, rw=0.046, cuff=True):
    for side in (1, -1):
        s = B.mirror(B.shoulder, side)
        el = B.mirror(B.elbow, side)
        w = B.mirror(B.wrist, side)
        start = s + V((-side * 0.03, 0, 0.005))
        pts = [start, s.lerp(el, 0.45), el, el.lerp(w, 0.5), w + (w - el).normalized() * 0.01]
        m.mat(mat)
        d = (w - el).normalized()
        pts = [start, s.lerp(el, 0.45), el, el.lerp(w, 0.5), w - d * 0.03, w - d * 0.02, w + d * 0.01]
        fs = limb(m, pts, [r0, r0 * 0.9, r0 * 0.8, rw * 1.05, rw, rw * 1.08, rw * 1.06], n=16)
        if cuff and cuff_mat:
            # faces past the cuff line along the arm direction
            if cuff_mat not in m.mats:
                m.mats.append(cuff_mat)
            ci = m.mats.index(cuff_mat)
            for f in fs:
                if f.is_valid and (f.calc_center_median() - w).dot(d) > -0.028:
                    f.material_index = ci


def band(faces, m, mat, zmin, zmax):
    """Re-material the faces of a loft whose centre lies in [zmin, zmax]."""
    if isinstance(mat, str):
        if mat not in m.mats:
            m.mats.append(mat)
        idx = m.mats.index(mat)
    for f in faces:
        if f.is_valid and zmin <= f.calc_center_median().z <= zmax:
            f.material_index = idx


def torso_shell(m, B, mat, rings_spec, n=20, pw=2.4):
    """rings_spec: [(z, rx, ry, yoff)] bottom to top (in units of height k)."""
    rings = []
    for (z, rx, ry, yo) in rings_spec:
        rings.append(ring(V((0, yo * B.k, z * B.k)), V((0, 0, 1)), V((1, 0, 0)), rx * B.k * B.girth, ry * B.k * B.girth, n, pw))
    m.mat(mat)
    return m.quad_strip(rings, closed=True, cap0=True, cap1=True)


def legs_skin(m, B, mat, top=None):
    for side in (1, -1):
        h = B.mirror(B.hipj, side)
        k = B.mirror(B.knee, side)
        a = B.mirror(B.ankle, side)
        m.mat(mat)
        limb(m, [h + V((0, 0, 0.05)), h.lerp(k, 0.5), k, k.lerp(a, 0.35), k.lerp(a, 0.75), a + V((0, 0, 0.02))],
             [0.072 * B.girth, 0.064 * B.girth, 0.051, 0.054, 0.042, 0.035], n=14)


def shorts(m, B, mat, band_mat, hem_z=0.63, pockets=True):
    k = B.k
    torso_shell(m, B, mat, [(0.8, 0.135, 0.1, 0.0), (0.84, 0.156, 0.111, 0.0), (0.88, 0.158, 0.11, 0.0), (0.93, 0.15, 0.104, 0.002)], pw=2.3)
    for side in (1, -1):
        h = B.mirror(B.hipj, side)
        kn = B.mirror(B.knee, side)
        top = h + V((side * 0.005, 0, 0.0))
        bot = h.lerp(kn, (B.HIP - hem_z * k) / (B.HIP - B.KNEE))
        m.mat(mat)
        dn = (bot - top).normalized()
        fs = limb(m, [top + V((0, 0, 0.02)), top.lerp(bot, 0.5), bot - dn * 0.025, bot - dn * 0.012, bot],
                  [0.094 * B.girth, 0.09 * B.girth, 0.088 * B.girth, 0.091 * B.girth, 0.09 * B.girth], n=16)
        if band_mat not in m.mats:
            m.mats.append(band_mat)
        bi = m.mats.index(band_mat)
        for f in fs:
            if f.is_valid and (f.calc_center_median() - bot).dot(dn) > -0.02:
                f.material_index = bi
        if pockets:
            m.mat(mat)
            pc = top.lerp(bot, 0.62) + V((side * 0.088 * B.girth, 0, 0))
            m.push(Matrix.Translation(pc))
            m.rbox((0, 0, 0), (0.022, 0.085, 0.09), 0.008, 2)
            m.mat(band_mat)
            m.rbox((side * 0.004, 0, 0.048), (0.024, 0.088, 0.024), 0.006, 2)
            m.pop()


def socks(m, B, mat, stripe_mat, top_z=0.40, stripes=2):
    for side in (1, -1):
        kn = B.mirror(B.knee, side)
        a = B.mirror(B.ankle, side)
        top = a.lerp(kn, (top_z * B.k - B.ANK) / (B.KNEE - B.ANK))
        m.mat(mat)
        pts = [a + V((0, 0, 0.015)), a.lerp(top, 0.5)]
        for i in range(8):
            pts.append(a.lerp(top, 0.62 + 0.38 * i / 7))
        fs = limb(m, pts, [0.039, 0.056] + [0.0565 + 0.0005 * (i % 2) for i in range(8)], n=14)
        if stripe_mat not in m.mats:
            m.mats.append(stripe_mat)
        si = m.mats.index(stripe_mat)
        for f in fs:
            z = f.calc_center_median().z
            for i in range(stripes):
                zc = top.z - 0.02 - i * 0.026
                if abs(z - zc) < 0.0065:
                    f.material_index = si


def hightops(m, B, upper_mat, sole_mat, toe_mat, lace_mat, logo_mat=None, collar_h=0.2):
    k = B.k
    for side in (1, -1):
        a = B.mirror(B.ankle, side)
        ox = a.x
        m.mat(sole_mat)
        # sole: rounded slab from heel to toe
        sole = []
        for i in range(9):
            t = i / 8
            y = -0.075 + t * 0.245
            w = 0.074 + 0.022 * math.sin(math.pi * min(1, t * 1.25)) - 0.012 * max(0, t - 0.8) * 5
            z = 0.018 + 0.012 * max(0, t - 0.82) * 5
            sole.append(ring(V((ox, y, z)), V((0, 1, 0)), V((1, 0, 0)), w / 2, 0.02, 16, 3.0))
        m.quad_strip(sole, closed=True, cap0=True, cap1=True)
        # upper body along the foot
        m.mat(upper_mat)
        up = []
        for i in range(9):
            t = i / 8
            y = -0.068 + t * 0.225
            w = 0.07 + 0.018 * math.sin(math.pi * min(1, t * 1.2)) - 0.01 * max(0, t - 0.8) * 5
            hgt = 0.125 * (1 - t) ** 0.6 + 0.045 * t
            z = 0.034 + hgt / 2
            up.append(ring(V((ox, y, z)), V((0, 1, 0)), V((1, 0, 0)), w / 2, hgt / 2, 18, 2.6))
        m.quad_strip(up, closed=True, cap0=True, cap1=True)
        # high-top collar around the ankle
        col = []
        for i in range(4):
            t = i / 3
            col.append(ring(V((ox, -0.02 + 0.004 * t, 0.07 + t * (collar_h - 0.07))), V((0, 0, 1)), V((1, 0, 0)), 0.05 - 0.004 * t, 0.058 - 0.006 * t, 18, 2.4))
        m.quad_strip(col, closed=True, cap0=False, cap1=True)
        m.mat(toe_mat)
        m.push(Matrix.Translation((ox, 0.118, 0.05)))
        m.sphere((0, 0, 0), 1.0, 16, 10, s=(0.044, 0.046, 0.03))
        m.pop()
        # collar padding ring
        m.mat(toe_mat)
        m.torus((ox, -0.018, collar_h - 0.004), R=0.049, r=0.009, seg=20, sides=8)
        # tongue and laces
        m.mat(upper_mat)
        m.push(Matrix.Translation((ox, 0.038, 0.13)) @ Matrix.Rotation(math.radians(-28), 4, 'X'))
        m.rbox((0, 0, 0), (0.044, 0.02, 0.1), 0.01, 2)
        m.pop()
        m.mat(lace_mat)
        for j in range(4):
            y = 0.02 + j * 0.028
            z = 0.155 - j * 0.026
            m.push(Matrix.Translation((ox, y, z)) @ Matrix.Rotation(math.radians(-28), 4, 'X'))
            m.cyl((0, 0, 0), 0.005, 0.052, 8, axis='X')
            m.pop()
        if logo_mat:
            m.mat(logo_mat)
            m.push(Matrix.Translation((ox + side * 0.046, -0.01, 0.1)) @ Matrix.Rotation(math.radians(90 * side), 4, 'Z') @ Matrix.Rotation(math.radians(90), 4, 'X'))
            m.extrude(E.star_pts(5, 0.02, 0.009), 0.006)
            m.pop()


def scarf(m, B, mat, fringe_mat):
    """Scarf wrap around the neck plus two tails hanging down the back (rest pose)."""
    k = B.k
    m.mat(mat)
    for j, (z, rr, tilt) in enumerate(((B.NECK + 0.005, 1.0, 8), (B.NECK - 0.03, 1.08, -6))):
        path = []
        for i in range(33):
            a = 2 * math.pi * i / 32
            path.append(V((0.082 * rr * math.sin(a), 0.004 + 0.076 * rr * math.cos(a), z + math.radians(tilt) * 0.06 * math.cos(a))))
        m.sweep(path, [(math.cos(2 * math.pi * i / 10), math.sin(2 * math.pi * i / 10)) for i in range(10)], closed=True, cap=False,
                scale=lambda t: (0.024, 0.03))
    # knot at the back
    m.push(Matrix.Translation((0.012, -0.085, B.NECK - 0.02)))
    m.sphere((0, 0, 0), 1.0, 14, 10, s=(0.035, 0.024, 0.032))
    m.pop()
    tails = []
    for (dx, L) in ((0.0, 1.0), (0.038, 0.82)):
        p0 = V((0.012 + dx, -0.092, B.NECK - 0.03))
        path = [V(p) for p in E.bezier(p0, p0 + V((0.01, -0.05, -0.12 * L)), p0 + V((0.03, -0.075, -0.3 * L)), p0 + V((0.045, -0.07, -0.48 * L)), 16)]
        prof = [(-1, -0.14), (1, -0.14), (1, 0.14), (-1, 0.14)]
        m.mat(mat)
        rings = []
        m.sweep(path, prof, closed=True, cap=True, scale=lambda t: (0.042, 0.042), twist=math.radians(20), up=(0, -1, 0), rings_out=rings)
        # fringe: short tapered strands hanging from the tail's end edge
        m.mat(fringe_mat)
        last = [V(p) for p in rings[-1]]
        a = (last[0] + last[3]) * 0.5
        b = (last[1] + last[2]) * 0.5
        tdir = (path[-1] - path[-2]).normalized()
        for f in range(6):
            p0 = a.lerp(b, (f + 0.5) / 6) - tdir * 0.004
            p1 = p0 + tdir * 0.03 + V((0, 0, -0.004))
            m.tube([p0, p0.lerp(p1, 0.5), p1], r=0.0045, seg=6, taper=0.4)
        tails.append(path)
    return tails


def goggles(m, B, strap_mat, frame_mat, lens_mat):
    c = B.headc
    r = B.head_r
    m.mat(strap_mat)
    rr = r * 1.02
    m.push(Matrix.Translation(c + V((0, -0.006, 0.06))) @ Matrix.Rotation(math.radians(13), 4, 'X') @ Matrix.Diagonal((1.05, 1.12, 1.0, 1)))
    m.lathe([(rr - 0.003, -0.0085), (rr + 0.004, -0.0085), (rr + 0.006, 0.0), (rr + 0.004, 0.0085), (rr - 0.003, 0.0085), (rr - 0.003, -0.0085)], seg=48)
    m.pop()
    for side in (1, -1):
        p = c + V((side * 0.043, r * 1.02, 0.088))
        M = Matrix.Translation(p) @ Matrix.Rotation(math.radians(-58), 4, 'X') @ Matrix.Rotation(math.radians(side * 14), 4, 'Y')
        m.push(M)
        m.mat(frame_mat)
        m.lathe([(0.0, -0.012), (0.03, -0.012), (0.033, -0.004), (0.033, 0.01), (0.027, 0.013), (0.022, 0.009)], seg=24)
        m.mat(lens_mat)
        m.sphere((0, 0, 0.004), 1.0, 20, 10, s=(0.024, 0.024, 0.009))
        m.pop()
    m.mat(frame_mat)
    m.push(Matrix.Translation(c + V((0, r * 1.08, 0.082))) @ Matrix.Rotation(math.radians(-58), 4, 'X'))
    m.rbox((0, 0, 0), (0.03, 0.012, 0.012), 0.004, 1)
    m.pop()


def hoodie(m, B, body_mat, trim_mat, string_mat, patch_mat, letter_mat, letter="P"):
    k = B.k
    fs = torso_shell(m, B, body_mat, [
        (0.8, 0.168, 0.117, 0.004), (0.815, 0.176, 0.121, 0.004), (0.845, 0.178, 0.122, 0.004), (0.86, 0.176, 0.12, 0.004),
        (0.92, 0.172, 0.117, 0.005), (0.98, 0.166, 0.114, 0.006), (1.04, 0.164, 0.114, 0.008),
        (1.12, 0.173, 0.122, 0.01), (1.2, 0.186, 0.13, 0.012), (1.28, 0.19, 0.128, 0.01), (1.35, 0.184, 0.118, 0.004),
        (1.395, 0.15, 0.1, 0.0), (1.425, 0.085, 0.07, 0.0), (1.44, 0.058, 0.055, 0.0)], n=22, pw=2.5)
    band(fs, m, trim_mat, 0.0, 0.855 * k)
    # hood resting on the back
    m.mat(body_mat)
    m.push(Matrix.Translation((0, -0.118 * k, 1.345 * k)) @ Matrix.Rotation(math.radians(-18), 4, 'X'))
    m.sphere((0, 0, 0), 1.0, 20, 12, s=(0.13 * k, 0.05 * k, 0.1 * k))
    m.pop()
    m.mat(trim_mat)
    path = []
    for i in range(25):
        a = math.radians(-120 + 240 * i / 24)
        path.append(V((0.105 * math.sin(a) * k, (-0.02 - 0.075 * math.cos(a)) * k, (1.43 - 0.03 * math.cos(a)) * k)))
    m.sweep(path, [(math.cos(2 * math.pi * i / 8), math.sin(2 * math.pi * i / 8)) for i in range(8)], closed=True, cap=True, scale=lambda t: 0.016 * k)
    # kangaroo pocket
    m.mat(body_mat)
    m.push(Matrix.Translation((0, 0.121 * k, 0.94 * k)) @ Matrix.Rotation(math.radians(-90), 4, 'X'))
    pocket = [(-0.1, -0.05), (0.1, -0.05), (0.075, 0.05), (-0.075, 0.05)]
    m.extrude([(x * k, y * k) for (x, y) in pocket], 0.012 * k, bevel=(0.004, 2))
    m.pop()
    m.mat(trim_mat)
    for side in (1, -1):
        a = V((side * 0.1 * k, 0.128 * k, 0.89 * k))
        b = V((side * 0.075 * k, 0.13 * k, 0.99 * k))
        m.tube([a, b], r=0.0045 * k, seg=8)
    # drawstrings
    m.mat(string_mat)
    for side in (1, -1):
        a = V((side * 0.028 * k, 0.07 * k, 1.405 * k))
        b = V((side * 0.034 * k, 0.126 * k, 1.3 * k))
        m.tube([a, a.lerp(b, 0.3) + V((0, 0.02, 0)), b], r=0.004 * k, seg=8)
        m.mat(trim_mat)
        m.cyl(tuple(b - V((0, 0, 0.012 * k))), 0.0055 * k, 0.022 * k, 10)
        m.mat(string_mat)
    # chest patch with letter
    m.mat(patch_mat)
    m.push(Matrix.Translation((-0.085 * k, 0.131 * k, 1.27 * k)) @ Matrix.Rotation(math.radians(-90), 4, 'X') @ Matrix.Rotation(math.radians(8), 4, 'Y'))
    m.cyl((0, 0, 0), 0.042 * k, 0.006 * k, 32, axis='Z', bevel=(0.0015, 1))
    m.mat(string_mat)
    m.torus((0, 0, 0.003 * k), R=0.038 * k, r=0.0035 * k, seg=32, sides=6)
    m.mat(letter_mat)
    m.push(Matrix.Translation((0.002 * k, 0.001 * k, 0.005 * k)))
    m.text(letter, size=0.062 * k, depth=0.005 * k)
    m.pop()
    m.pop()


# ============================================================================ skeleton

HUMAN_BONES = ["root", "spine", "chest", "neck", "head",
               "clav.L", "upper_arm.L", "forearm.L", "hand.L",
               "clav.R", "upper_arm.R", "forearm.R", "hand.R",
               "thigh.L", "shin.L", "foot.L",
               "thigh.R", "shin.R", "foot.R"]


def human_rig(B, name, dyn_chains=()):
    """dyn_chains: [(prefix, parent_bone, [points...])] -> bones dyn_<prefix>1..n."""
    bones = []
    k = B.k
    bones.append(("root", (0, 0, B.HIP), (0, 0, B.HIP + 0.1 * k), None, 0))
    bones.append(("spine", (0, 0, B.HIP + 0.02 * k), (0, 0.004, B.CHEST - 0.06 * k), "root", 0))
    bones.append(("chest", (0, 0.004, B.CHEST - 0.06 * k), (0, 0, B.SHO + 0.01), "spine", 0))
    bones.append(("neck", (0, 0, B.NECK - 0.03 * k), (0, 0.004, B.CHIN + 0.01), "chest", 0))
    bones.append(("head", (0, 0.004, B.CHIN + 0.01), (0, 0.004, B.TOP + 0.02), "neck", 0))
    for sfx, sd in (("L", -1), ("R", 1)):
        sh = B.mirror(B.shoulder, sd)
        bones.append(("clav." + sfx, (sd * 0.025 * k, 0.0, B.SHO - 0.015), tuple(sh), "chest", 0))
        bones.append(("upper_arm." + sfx, tuple(sh), tuple(B.mirror(B.elbow, sd)), "clav." + sfx, 0))
        bones.append(("forearm." + sfx, tuple(B.mirror(B.elbow, sd)), tuple(B.mirror(B.wrist, sd)), "upper_arm." + sfx, 0))
        bones.append(("hand." + sfx, tuple(B.mirror(B.wrist, sd)), tuple(B.mirror(B.handend, sd)), "forearm." + sfx, 0))
    for sfx, sd in (("L", -1), ("R", 1)):
        bones.append(("thigh." + sfx, tuple(B.mirror(B.hipj, sd)), tuple(B.mirror(B.knee, sd)), "root", 0))
        bones.append(("shin." + sfx, tuple(B.mirror(B.knee, sd)), tuple(B.mirror(B.ankle, sd)), "thigh." + sfx, 0))
        bones.append(("foot." + sfx, tuple(B.mirror(B.ankle, sd)), tuple(B.mirror(B.toe, sd)), "shin." + sfx, 0))
    for (prefix, parent, pts) in dyn_chains:
        prev = parent
        for i in range(len(pts) - 1):
            bn = "dyn_%s%d" % (prefix, i + 1)
            bones.append((bn, tuple(pts[i]), tuple(pts[i + 1]), prev, 0))
            prev = bn
    arm = E.make_armature(name + "_rig", bones)
    return arm


def weight_chain(obj, arm, prefix, path_pts):
    """Assign each vertex of obj to the dyn chain by its nearest point along path_pts."""
    nb = len(path_pts) - 1
    groups = [obj.vertex_groups.get("dyn_%s%d" % (prefix, i + 1)) or obj.vertex_groups.new(name="dyn_%s%d" % (prefix, i + 1)) for i in range(nb)]
    cum = [0.0]
    for i in range(nb):
        cum.append(cum[-1] + (path_pts[i + 1] - path_pts[i]).length)
    total = cum[-1]
    for v in obj.data.vertices:
        p = obj.matrix_world @ v.co
        best, bt = 1e9, 0.0
        for i in range(nb):
            a, b = path_pts[i], path_pts[i + 1]
            ab = b - a
            t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.dot(ab), 1e-12)))
            d = (a + ab * t - p).length
            if d < best:
                best, bt = d, (cum[i] + t * ab.length) / total
        s = bt * nb
        i0 = min(int(s), nb - 1)
        f = s - i0
        if f < 0.5 or i0 == nb - 1:
            groups[i0].add([v.index], 1.0, 'REPLACE')
        else:
            w = (f - 0.5)
            groups[i0].add([v.index], 1.0 - w, 'REPLACE')
            groups[i0 + 1].add([v.index], w, 'REPLACE')


def capsule_weights(obj, arm, allowed, falloff=4.0, maxinf=3, soft=0.025):
    """Robust skin weights: inverse distance to each allowed bone segment (no heat diffusion)."""
    bones = [arm.data.bones[b] for b in allowed if b in arm.data.bones]
    segs = [(b.head_local.copy(), b.tail_local.copy()) for b in bones]
    for vg in list(obj.vertex_groups):
        obj.vertex_groups.remove(vg)
    groups = {b.name: obj.vertex_groups.new(name=b.name) for b in bones}
    mw = obj.matrix_world
    for v in obj.data.vertices:
        p = mw @ v.co
        ws = []
        for b, (h, t) in zip(bones, segs):
            ab = t - h
            tt = max(0.0, min(1.0, (p - h).dot(ab) / max(ab.dot(ab), 1e-12)))
            d = (h + ab * tt - p).length
            ws.append((1.0 / (d + soft) ** falloff, b.name))
        ws.sort(reverse=True)
        ws = ws[:maxinf]
        tot = sum(w for w, _ in ws)
        for w, n in ws:
            if w / tot > 0.01:
                groups[n].add([v.index], w / tot, 'REPLACE')
    if not any(m.type == 'ARMATURE' for m in obj.modifiers):
        am = obj.modifiers.new("Armature", 'ARMATURE')
        am.object = arm
    obj.parent = arm


TORSO_BONES = ["root", "spine", "chest", "neck", "clav.L", "clav.R", "upper_arm.L", "upper_arm.R"]
ARM_BONES = ["chest", "clav.L", "clav.R", "upper_arm.L", "upper_arm.R", "forearm.L", "forearm.R", "hand.L", "hand.R"]
HIP_BONES = ["root", "spine", "thigh.L", "thigh.R"]
LEG_BONES = ["root", "thigh.L", "thigh.R", "shin.L", "shin.R", "foot.L", "foot.R"]
NECK_BONES = ["chest", "neck", "head"]


def bind(weighted, rigid, arm):
    """weighted: [(obj, allowed_bones)], rigid: [(obj, bone)]."""
    for (obj, allowed) in weighted:
        capsule_weights(obj, arm, allowed)
    for (obj, bone) in rigid:
        E.bind_rigid(obj, arm, bone)


# ============================================================================ animation authoring

def rest_rot(arm, bone):
    return arm.data.bones[bone].matrix_local.to_quaternion()


def pose_key(arm, frame, pose, root_loc=None):
    """pose: {bone: (rx, ry, rz)} in degrees about armature axes (X right, Y forward, Z up)."""
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    for bn, e in pose.items():
        if bn not in arm.pose.bones:
            continue
        rr = rest_rot(arm, bn)
        qa = Euler([math.radians(a) for a in e], 'XYZ').to_quaternion()
        ql = rr.inverted() @ qa @ rr
        pb = arm.pose.bones[bn]
        pb.rotation_quaternion = ql
        pb.keyframe_insert("rotation_quaternion", frame=frame)
    if root_loc is not None:
        rr = rest_rot(arm, "root")
        pb = arm.pose.bones["root"]
        pb.location = rr.inverted() @ V(root_loc)
        pb.keyframe_insert("location", frame=frame)


def _mirror_pose(p):
    out = {}
    for bn, (rx, ry, rz) in p.items():
        if bn.endswith(".L"):
            out[bn[:-2] + ".R"] = (rx, -ry, -rz)
        elif bn.endswith(".R"):
            out[bn[:-2] + ".L"] = (rx, -ry, -rz)
        else:
            out[bn] = (rx, -ry, -rz)
    return out


def _merge(*ps):
    out = {}
    for p in ps:
        out.update(p)
    return out


ARMS_DOWN = {"upper_arm.L": (0, -14, 0), "upper_arm.R": (0, 14, 0), "forearm.L": (10, 0, 0), "forearm.R": (10, 0, 0)}


def all_bones_zero(arm):
    return {b.name: (0, 0, 0) for b in arm.data.bones if not b.name.startswith("dyn_")}


def make_clips(arm, style="hero"):
    """Keyframes every gameplay clip on the armature. Returns [(action_name, loop)]."""
    clips = []
    Z = all_bones_zero(arm)

    # ---------------------------------------------------------------- idle (menu), 72 frames loop
    E.new_action(arm, "idle")
    for f, br in ((1, 0.0), (19, 1.0), (37, 0.0), (55, -0.6), (73, 0.0)):
        p = _merge(Z, ARMS_DOWN, {
            "spine": (-2 - 1.5 * br, 0, 3), "chest": (1.5 * br, 0, -4), "neck": (2, 0, 4), "head": (-3 - br, 0, 6 + 2 * br),
            "clav.L": (0, 0, 1.5 * br), "clav.R": (0, 0, -1.5 * br),
            "upper_arm.R": (-4, 12 + 2 * br, 0), "forearm.R": (14, 0, 0), "hand.R": (0, 0, -8),
            "upper_arm.L": (-4, -12 - 2 * br, 0), "forearm.L": (14, 0, 0), "hand.L": (0, 0, 8),
            "thigh.L": (4, 0, -6), "shin.L": (-8, 0, 0), "foot.L": (4, 0, 0),
            "thigh.R": (-3, 0, 4), "shin.R": (-2, 0, 0)})
        pose_key(arm, f, p, (0.012 * br, 0, -0.012 + 0.006 * br))
    clips.append(("idle", True))

    # ---------------------------------------------------------------- run, 20 frames loop (0.67 s)
    E.new_action(arm, "run")
    legR = {0: (48, -14, 10), 5: (8, -32, -5), 10: (-42, -18, 30), 15: (18, -118, 35), 18: (66, -72, 0), 20: (48, -14, 10)}
    def leg_at(f):
        keys = sorted(legR)
        f = f % 20
        for i in range(len(keys) - 1):
            a, b = keys[i], keys[i + 1]
            if a <= f <= b:
                t = (f - a) / (b - a)
                return tuple(legR[a][j] + (legR[b][j] - legR[a][j]) * t for j in range(3))
        return legR[0]
    for f in range(0, 21, 1):
        th, sh, ft = leg_at(f)
        th2, sh2, ft2 = leg_at(f + 10)
        ph = 2 * math.pi * f / 20
        swing = math.sin(ph)
        bob = 0.028 * math.cos(2 * ph) - 0.01
        p = _merge(Z, {
            "root": (0, 0, -7 * swing), "spine": (-14, 0, 6 * swing), "chest": (-4, 0, 9 * swing), "neck": (8, 0, -6 * swing), "head": (10, 0, -8 * swing),
            "thigh.R": (th, 0, 0), "shin.R": (sh, 0, 0), "foot.R": (ft, 0, 0),
            "thigh.L": (th2, 0, 0), "shin.L": (sh2, 0, 0), "foot.L": (ft2, 0, 0),
            "clav.R": (0, 0, 4 * swing), "clav.L": (0, 0, 4 * swing),
            "upper_arm.R": (-50 * swing - 5, 28, 8), "forearm.R": (95 + 15 * swing, 0, 10), "hand.R": (0, 0, -10),
            "upper_arm.L": (50 * swing - 5, -28, -8), "forearm.L": (95 - 15 * swing, 0, -10), "hand.L": (0, 0, 10)})
        pose_key(arm, f + 1, p, (0, 0, bob))
    clips.append(("run", True))

    # ---------------------------------------------------------------- jump (takeoff -> apex), 12 frames
    E.new_action(arm, "jump")
    a = _merge(Z, {"spine": (-18, 0, 0), "chest": (-6, 0, 0), "thigh.R": (40, 0, 0), "shin.R": (-70, 0, 0), "thigh.L": (-10, 0, 0), "shin.L": (-40, 0, 0),
                   "upper_arm.R": (-30, 30, 0), "upper_arm.L": (-30, -30, 0), "forearm.R": (40, 0, 0), "forearm.L": (40, 0, 0)})
    b = _merge(Z, {"spine": (6, 0, 0), "head": (-8, 0, 0), "thigh.R": (80, 0, 0), "shin.R": (-110, 0, 0), "foot.R": (20, 0, 0),
                   "thigh.L": (-15, 0, 0), "shin.L": (-60, 0, 0), "foot.L": (25, 0, 0),
                   "upper_arm.R": (150, 20, 0), "forearm.R": (20, 0, 0), "upper_arm.L": (40, -60, 0), "forearm.L": (50, 0, 0), "clav.R": (0, 0, 10)})
    pose_key(arm, 1, a, (0, 0, -0.06))
    pose_key(arm, 12, b, (0, 0, 0.04))
    clips.append(("jump", False))

    # ---------------------------------------------------------------- fall (loop), 16 frames
    E.new_action(arm, "fall")
    for f, s in ((1, 0), (9, 1), (17, 0)):
        p = _merge(Z, {"spine": (-6, 0, 0), "head": (6, 0, 0), "thigh.R": (35 + 6 * s, 0, 0), "shin.R": (-55, 0, 0), "thigh.L": (-12 - 6 * s, 0, 0), "shin.L": (-35, 0, 0),
                       "upper_arm.R": (40 + 10 * s, 70, 0), "forearm.R": (20, 0, 0), "upper_arm.L": (40 - 10 * s, -70, 0), "forearm.L": (20, 0, 0)})
        pose_key(arm, f, p, (0, 0, 0))
    clips.append(("fall", True))

    # ---------------------------------------------------------------- roll, 20 frames
    E.new_action(arm, "roll")
    for f in range(0, 21):
        t = f / 20
        curl = math.sin(math.pi * min(1, t * 1.2)) if t < 0.95 else 0
        p = _merge(Z, {"root": (-360 * t, 0, 0), "spine": (45 * curl, 0, 0), "chest": (25 * curl, 0, 0), "neck": (20 * curl, 0, 0), "head": (15 * curl, 0, 0),
                       "thigh.R": (120 * curl, 0, 0), "shin.R": (-140 * curl, 0, 0), "thigh.L": (115 * curl, 0, 0), "shin.L": (-140 * curl, 0, 0),
                       "upper_arm.R": (60 * curl, 20, 0), "forearm.R": (110 * curl, 0, 0), "upper_arm.L": (60 * curl, -20, 0), "forearm.L": (110 * curl, 0, 0)})
        pose_key(arm, f + 1, p, (0, 0, -0.42 * curl))
    clips.append(("roll", False))

    # ---------------------------------------------------------------- board (hoverboard stance) loop 30
    E.new_action(arm, "board")
    for f, s in ((1, 0), (16, 1), (31, 0)):
        p = _merge(Z, {"root": (0, 0, 35), "spine": (-10, 0, -10), "chest": (0, 0, -18), "neck": (0, 0, -8), "head": (4, 0, -12),
                       "thigh.R": (30, 0, 16), "shin.R": (-52 - 6 * s, 0, 0), "foot.R": (18, 0, 0),
                       "thigh.L": (-22, 0, -14), "shin.L": (-38 - 6 * s, 0, 0), "foot.L": (16, 0, 0),
                       "upper_arm.R": (10, 76 + 6 * s, 0), "forearm.R": (20, 0, 0), "upper_arm.L": (-10, -74 - 6 * s, 0), "forearm.L": (25, 0, 0)})
        pose_key(arm, f, p, (0, 0, -0.1 - 0.02 * s))
    clips.append(("board", True))

    # ---------------------------------------------------------------- surf (river board) loop 30
    E.new_action(arm, "surf")
    for f, s in ((1, 0), (16, 1), (31, 0)):
        p = _merge(Z, {"root": (0, 0, 60), "spine": (-18, 0, -6), "chest": (-4, 0, -22), "neck": (0, 0, -15), "head": (6, 0, -18),
                       "thigh.R": (40, 0, 24), "shin.R": (-80 - 5 * s, 0, 0), "foot.R": (30, 0, 0),
                       "thigh.L": (-25, 0, -20), "shin.L": (-55 - 5 * s, 0, 0), "foot.L": (25, 0, 0),
                       "upper_arm.R": (25, 70, 10), "forearm.R": (35, 0, 0), "upper_arm.L": (-25, -68, -10), "forearm.L": (30, 0, 0)})
        pose_key(arm, f, p, (0, 0, -0.2 - 0.02 * s))
    clips.append(("surf", True))

    # ---------------------------------------------------------------- rocket (flying) loop 24
    E.new_action(arm, "rocket")
    for f, s in ((1, 0), (13, 1), (25, 0)):
        p = _merge(Z, {"root": (-55, 0, 0), "spine": (-10, 0, 3 * s), "neck": (25, 0, 0), "head": (25, 0, 0),
                       "thigh.R": (-12 + 6 * s, 0, 4), "shin.R": (-25 - 8 * s, 0, 0), "foot.R": (35, 0, 0),
                       "thigh.L": (-6 - 6 * s, 0, -4), "shin.L": (-35 + 8 * s, 0, 0), "foot.L": (35, 0, 0),
                       "upper_arm.R": (-35, 20, 0), "forearm.R": (30, 0, 0), "upper_arm.L": (-35, -20, 0), "forearm.L": (30, 0, 0)})
        pose_key(arm, f, p, (0, 0, 0))
    clips.append(("rocket", True))

    # ---------------------------------------------------------------- glide (paraglider harness) loop 40
    E.new_action(arm, "glide")
    for f, s in ((1, 0), (21, 1), (41, 0)):
        p = _merge(Z, {"root": (0, 0, 0), "spine": (-8, 0, 2 * s), "head": (-6, 0, 0),
                       "thigh.R": (75, 0, 6), "shin.R": (-70 - 6 * s, 0, 0), "thigh.L": (75, 0, -6), "shin.L": (-76 + 6 * s, 0, 0),
                       "upper_arm.R": (150, 30, 0), "forearm.R": (35, 0, 0), "hand.R": (0, 0, 0),
                       "upper_arm.L": (150, -30, 0), "forearm.L": (35, 0, 0)})
        pose_key(arm, f, p, (0, 0, 0))
    clips.append(("glide", True))

    # ---------------------------------------------------------------- stumble, 14 frames
    E.new_action(arm, "stumble")
    k0 = _merge(Z, {"spine": (-14, 0, 0), "thigh.R": (30, 0, 0), "shin.R": (-40, 0, 0), "thigh.L": (-20, 0, 0), "shin.L": (-30, 0, 0)})
    k1 = _merge(Z, {"root": (0, 18, -20), "spine": (10, 20, -10), "head": (-15, 0, 20), "thigh.R": (-10, 0, 20), "shin.R": (-30, 0, 0),
                    "thigh.L": (40, 0, -10), "shin.L": (-60, 0, 0), "upper_arm.R": (60, 80, 0), "forearm.R": (40, 0, 0),
                    "upper_arm.L": (120, -40, 0), "forearm.L": (20, 0, 0)})
    pose_key(arm, 1, k0, (0, 0, 0))
    pose_key(arm, 6, k1, (0.05, 0, -0.03))
    pose_key(arm, 14, k0, (0, 0, 0))
    clips.append(("stumble", False))

    # ---------------------------------------------------------------- crash (knocked back), 24 frames
    E.new_action(arm, "crash")
    c0 = _merge(Z, {"spine": (-10, 0, 0)})
    c1 = _merge(Z, {"root": (55, 0, 0), "spine": (15, 0, 0), "neck": (-15, 0, 0), "head": (-20, 0, 0),
                    "thigh.R": (50, 0, 10), "shin.R": (-30, 0, 0), "thigh.L": (70, 0, -10), "shin.L": (-60, 0, 0),
                    "upper_arm.R": (170, 40, 0), "forearm.R": (30, 0, 0), "upper_arm.L": (160, -50, 0), "forearm.L": (40, 0, 0)})
    c2 = _merge(Z, {"root": (88, 0, 5), "spine": (8, 0, 0), "head": (-10, 0, 10),
                    "thigh.R": (35, 0, 10), "shin.R": (-20, 0, 0), "thigh.L": (55, 0, -10), "shin.L": (-40, 0, 0),
                    "upper_arm.R": (150, 70, 0), "forearm.R": (20, 0, 0), "upper_arm.L": (150, -70, 0), "forearm.L": (20, 0, 0)})
    pose_key(arm, 1, c0, (0, 0, 0))
    pose_key(arm, 8, c1, (0, -0.35, -0.25))
    pose_key(arm, 24, c2, (0, -0.7, -0.72))
    clips.append(("crash", False))

    # ---------------------------------------------------------------- caught (surprised, arms up) loop 20
    E.new_action(arm, "caught")
    for f, s in ((1, 0), (11, 1), (21, 0)):
        p = _merge(Z, {"spine": (6, 0, 0), "head": (-10, 0, 8 * s - 4), "thigh.R": (20, 0, 8), "shin.R": (-35, 0, 0), "thigh.L": (18, 0, -8), "shin.L": (-35, 0, 0),
                       "upper_arm.R": (160, 40 + 6 * s, 0), "forearm.R": (30, 0, 0), "upper_arm.L": (160, -40 - 6 * s, 0), "forearm.L": (30, 0, 0)})
        pose_key(arm, f, p, (0, 0, -0.08))
    clips.append(("caught", True))

    # ---------------------------------------------------------------- victory (menu cheer) 36
    E.new_action(arm, "cheer")
    for f, s in ((1, 0), (10, 1), (19, 0), (28, 1), (37, 0)):
        p = _merge(Z, ARMS_DOWN, {"spine": (4 - 4 * s, 0, 0), "head": (-10 * s, 0, 0),
                                   "upper_arm.R": (165, 20 + 10 * s, 0), "forearm.R": (20, 0, 0), "hand.R": (0, 0, 0),
                                   "upper_arm.L": (10, -30, 0), "forearm.L": (60, 0, -30),
                                   "thigh.R": (10 * s, 0, 5), "shin.R": (-20 * s, 0, 0)})
        pose_key(arm, f, p, (0, 0, 0.05 * s))
    clips.append(("cheer", True))

    # reset
    arm.animation_data.action = bpy.data.actions["idle"]
    return clips


# ============================================================================ character: PONGO

PONGO_COLORS = dict(
    skin=0xFFE1C9, hair=0x243B7A, hoodie=0xF5F6FB, blue=0x2F6BDA, shorts=0x30343F, sock=0xFBFBFB,
    shoe=0xE8403A, shoe_white=0xF7F4EC, glove=0x26282F, strap=0xFF8A2A, scarf=0xFF7A1F, fringe=0xE65A12,
    goggle_strap=0x3A2E2A, goggle_frame=0xC9CED6, lens=0xFFA23A, brow=0x1E2E5E, patch=0x1E2B55, letter=0xFF7A1F)


def pongo_mats():
    C = PONGO_COLORS
    E.mat("pongo_skin", C["skin"], skin=1.0, rim=0.22, soft=0.1)
    E.mat("pongo_hair", C["hair"], flags=E.F_HAIR, spec=0.22, rim=0.4, soft=0.06)
    E.mat("pongo_hoodie", C["hoodie"], rim=0.3, soft=0.1)
    E.mat("pongo_blue", C["blue"], rim=0.3, soft=0.1)
    E.mat("pongo_shorts", C["shorts"], rim=0.35, soft=0.1)
    E.mat("pongo_sock", C["sock"], rim=0.25, soft=0.1)
    E.mat("pongo_shoe", C["shoe"], spec=0.35, rim=0.35, soft=0.08)
    E.mat("pongo_shoe_white", C["shoe_white"], rim=0.25, soft=0.08)
    E.mat("pongo_glove", C["glove"], spec=0.2, rim=0.35, soft=0.08)
    E.mat("pongo_strap", C["strap"], rim=0.3)
    E.mat("pongo_scarf", C["scarf"], rim=0.35, soft=0.14)
    E.mat("pongo_fringe", C["fringe"], rim=0.3, outline=0.5)
    E.mat("pongo_gstrap", C["goggle_strap"], rim=0.3, outline=0.7)
    E.mat("pongo_gframe", C["goggle_frame"], flags=E.F_METAL, spec=0.9, rim=0.4, outline=0.7)
    E.mat("pongo_lens", C["lens"], flags=E.F_GLASS, spec=1.0, rim=0.5, outline=0.5)
    E.mat("pongo_patch", C["patch"], rim=0.2, outline=0.4)
    E.mat("pongo_letter", C["letter"], rim=0.1, outline=0.0)
    E.mat("pongo_lining", 0x2F6BDA, rim=0.2, soft=0.12, outline=0.6)
    E.mat("pongo_scarf_stripe", 0xFFF3E4, rim=0.3, soft=0.14)
    E.mat("pongo_sole_stripe", 0x3A3F4E, rim=0.1, outline=0.0)
    E.mat("pongo_heel", 0xC7302C, spec=0.35, rim=0.35, soft=0.08)
    E.mat("pongo_tab", 0xFF8A2A, rim=0.3, outline=0.4)


def build_pongo(lod=0):
    B = Body(1.78)
    pongo_mats()
    parts = {}
    # head (rigid to 'head')
    hm = head_mesh(B, "pongo_skin")
    head = hm.obj("pongo_head", subsurf=1)
    fm = E.Mesher("pongo_face")
    anime_face(B, fm, head, "d_eye_pongo", "d_mouth_grin", PONGO_COLORS["brow"], "pongo_skin", bandaid=True)
    face = fm.obj("pongo_face", smooth_angle=60)
    hr = E.Mesher("pongo_hair").mat("pongo_hair")
    pongo_hair(hr, B)
    hair = hr.obj("pongo_hair", smooth_angle=50)
    gg = E.Mesher("pongo_goggles")
    goggles(gg, B, "pongo_gstrap", "pongo_gframe", "pongo_lens")
    gog = gg.obj("pongo_goggles", smooth_angle=45)
    # body parts (auto weights)
    nk = E.Mesher("pongo_neck").mat("pongo_skin")
    neck(nk, B)
    neck_o = nk.obj("pongo_neck", subsurf=1)
    hd = E.Mesher("pongo_hoodie")
    hoodie2(hd, B, "pongo_hoodie", "pongo_blue", "pongo_hoodie", "d_pongo_logo", "d_pongo_back")
    hood = hd.obj("pongo_hoodie", subsurf=1, smooth_angle=50)
    dt = E.Mesher("pongo_hoodie_det")
    hoodie2_details(dt, B, hood, "pongo_hoodie", "pongo_blue", "pongo_hoodie", "d_pongo_logo", "d_pongo_back")
    det_o = dt.obj("pongo_hoodie_det", smooth_angle=50)
    hh = E.Mesher("pongo_hood")
    hood2(hh, B, "pongo_hoodie", "pongo_lining")
    hood_o = hh.obj("pongo_hood", subsurf=1, smooth_angle=60)
    sl = E.Mesher("pongo_sleeves")
    sleeves(sl, B, "pongo_hoodie", "pongo_blue")
    sleeves_o = sl.obj("pongo_sleeves", subsurf=1, smooth_angle=50)
    sh = E.Mesher("pongo_shorts")
    shorts(sh, B, "pongo_shorts", "pongo_strap")
    shorts_o = sh.obj("pongo_shorts", subsurf=1, smooth_angle=50)
    lg = E.Mesher("pongo_legs")
    legs_skin(lg, B, "pongo_skin")
    socks(lg, B, "pongo_sock", "pongo_blue")
    legs_o = lg.obj("pongo_legs", subsurf=1)
    sc = E.Mesher("pongo_scarf")
    tails = scarf2(sc, B, "pongo_scarf", "pongo_scarf_stripe", "pongo_fringe")
    scarf_o = sc.obj("pongo_scarf", subsurf=1, smooth_angle=50)
    # rigid parts
    hn = E.Mesher("pongo_hands")
    hands(hn, B, "pongo_glove", "pongo_skin")
    hands_o = hn.obj("pongo_hands", subsurf=1, smooth_angle=50)
    shoes = E.Mesher("pongo_shoes")
    sneakers(shoes, B, "pongo_shoe", "pongo_shoe_white", "pongo_sole_stripe", "pongo_shoe_white", "pongo_shoe_white",
             "pongo_tab", "pongo_shoe_white", "pongo_heel")
    shoes_o = shoes.obj("pongo_shoes", subsurf=1, smooth_angle=45)
    # split hands/shoes per side for rigid binding
    handL, handR = split_by_side(hands_o)
    shoeL, shoeR = split_by_side(shoes_o)
    # scarf: separate the tails for chain weights
    wrap_o, tails_o = split_scarf(scarf_o, B)
    chain = [tails[0][0] + V((0, 0.004, 0.02))] + [tails[0][i] for i in (5, 10, 15, 20)]
    arm = human_rig(B, "pongo", dyn_chains=[("scarf", "neck", chain)])
    for o in (head, face, hair, gog, neck_o, hood, det_o, hood_o, sleeves_o, shorts_o, legs_o, wrap_o, tails_o, handL, handR, shoeL, shoeR):
        E.apply_modifiers(o, skip=('SOLIDIFY',))
    bind([(neck_o, NECK_BONES), (hood, TORSO_BONES), (det_o, TORSO_BONES), (hood_o, ["spine", "chest", "neck"]),
          (sleeves_o, ARM_BONES), (shorts_o, HIP_BONES), (legs_o, LEG_BONES), (wrap_o, ["chest", "neck"])],
         [(head, "head"), (face, "head"), (hair, "head"), (gog, "head"),
          (handL, "hand.L"), (handR, "hand.R"), (shoeL, "foot.L"), (shoeR, "foot.R")], arm)
    weight_chain(tails_o, arm, "scarf", chain)
    am = tails_o.modifiers.new("Armature", 'ARMATURE')
    am.object = arm
    tails_o.parent = arm
    objs = [head, face, hair, gog, neck_o, hood, det_o, hood_o, sleeves_o, shorts_o, legs_o, wrap_o, tails_o, handL, handR, shoeL, shoeR]
    return B, arm, objs


def split_by_side(obj):
    """Split a mesh object into two objects by the sign of X (character left = -X)."""
    activate_edit(obj)
    bm = bmesh.from_edit_mesh(obj.data)
    for f in bm.faces:
        f.select = f.calc_center_median().x < 0
    bmesh.update_edit_mesh(obj.data)
    bpy.ops.mesh.separate(type='SELECTED')
    bpy.ops.object.mode_set(mode='OBJECT')
    new = [o for o in bpy.context.selected_objects if o != obj][0]
    new.name = obj.name + ".L"
    obj.name = obj.name + ".R"
    return new, obj


def split_scarf(obj, B):
    activate_edit(obj)
    bm = bmesh.from_edit_mesh(obj.data)
    for f in bm.faces:
        c = f.calc_center_median()
        f.select = c.y < -0.095 and c.z < B.NECK - 0.045
    bmesh.update_edit_mesh(obj.data)
    bpy.ops.mesh.separate(type='SELECTED')
    bpy.ops.object.mode_set(mode='OBJECT')
    new = [o for o in bpy.context.selected_objects if o != obj][0]
    new.name = obj.name + "_tails"
    return obj, new


def activate_edit(obj):
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    E.activate(obj)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')


# ============================================================================ entry points

def design_pongo(pose="idle", frame=10, yaw=205, name=None):
    E.reset()
    studio.stage(res=(900, 1200))
    B, arm, objs = build_pongo()
    for o in objs:
        if o.type == 'MESH':
            E.add_outline(o, 0.006)
    make_clips(arm)
    arm.animation_data.action = bpy.data.actions[pose]
    bpy.context.scene.frame_set(frame)
    studio.shoot(name or ("pongo_" + pose), target=(0, 0, 0.92), dist=4.2, yaw=yaw, pitch=8, lens=60)


def outline_all(objs):
    for o in objs:
        if o.type != 'MESH':
            continue
        n = o.name
        w = 0.0018 if "face" in n else 0.0045 if ("hair" in n or "goggles" in n or "hands" in n) else 0.006
        E.add_outline(o, w)


def design_pongo_sheet():
    E.reset()
    studio.stage(res=(1000, 1400))
    B, arm, objs = build_pongo()
    outline_all(objs)
    make_clips(arm)
    sc = bpy.context.scene
    arm.animation_data.action = bpy.data.actions["idle"]
    sc.frame_set(10)
    studio.shoot("pongo_front", target=(0, 0, 0.95), dist=3.3, yaw=205, pitch=6, lens=50)
    sc.render.resolution_x, sc.render.resolution_y = 1200, 900
    studio.shoot("pongo_face", target=(0, 0.04, 1.62), dist=0.95, yaw=200, pitch=3, lens=70)
    studio.shoot("pongo_profile", target=(0, 0.0, 1.6), dist=1.05, yaw=270, pitch=3, lens=70)
    sc.render.resolution_x, sc.render.resolution_y = 1000, 1400
    arm.animation_data.action = bpy.data.actions["run"]
    sc.frame_set(4)
    studio.shoot("pongo_run", target=(0, 0, 0.95), dist=3.3, yaw=250, pitch=6, lens=50)
    sc.frame_set(14)
    studio.shoot("pongo_back", target=(0, 0, 0.98), dist=3.3, yaw=20, pitch=14, lens=50)
    arm.animation_data.action = bpy.data.actions["idle"]
    sc.frame_set(10)
    sc.render.resolution_x, sc.render.resolution_y = 1200, 900
    studio.shoot("pongo_shoes", target=(0, 0.02, 0.1), dist=0.9, yaw=230, pitch=18, lens=60)
    studio.shoot("pongo_hood", target=(0, -0.05, 1.25), dist=1.3, yaw=15, pitch=12, lens=60)
    studio.shoot("pongo_chest", target=(0, 0.05, 1.12), dist=1.3, yaw=200, pitch=6, lens=60)


def export_pongo():
    E.reset()
    B, arm, objs = build_pongo()
    clips = make_clips(arm)
    body = E.join(objs, "pongo")
    E.export_erm(body, "pongo", arm=arm, clips=clips)
    dec = body.modifiers.new("dec", 'DECIMATE')
    dec.ratio = 0.35
    E.export_erm(body, "pongo@1", arm=arm, clips=clips)



# ============================================================================ v2 clothing (Pongo)

def foot_outline(side, n=28):
    """Sneaker footprint (x across, y forward), arch narrowed on the inner side."""
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        ca, sa = math.cos(a), math.sin(a)
        yy = sa
        w = 1 + 0.13 * math.exp(-((yy - 0.45) / 0.35) ** 2)
        inner = (ca * side) < 0
        w -= 0.12 * math.exp(-((yy + 0.05) / 0.32) ** 2) * (1.0 if inner else 0.25)
        pts.append((0.047 * ca * w, 0.045 + 0.124 * sa))
    return pts


def sneakers(m, B, upper, sole, stripe, toe, lace, tab, logo, heel):
    for side in (1, -1):
        a = B.mirror(B.ankle, side)
        ox = a.x
        m.push(Matrix.Translation((ox, a.y + 0.012, 0.0)))
        out = foot_outline(side)
        # rubber sole with toe spring and a dark foxing stripe
        m.mat(sole)
        fs = m.extrude(out, 0.026, bevel=(0.004, 2), c=(0, 0, 0.013))
        for v in {v for f in fs for v in f.verts}:
            lp = m.M.inverted() @ v.co
            if lp.y > 0.12:
                v.co.z += (lp.y - 0.12) * 0.35
        m.mat(stripe)
        big = [(x * 1.012, y * 1.004 + 0.0002) for (x, y) in out]
        fs2 = m.extrude(big, 0.004, c=(0, 0, 0.02))
        for v in {v for f in fs2 for v in f.verts}:
            lp = m.M.inverted() @ v.co
            if lp.y > 0.12:
                v.co.z += (lp.y - 0.12) * 0.35
        # upper: dome over the footprint, low toe box rising to the heel
        def hgt(y):
            t = max(0.0, min(1.0, (y + 0.04) / 0.2))
            return 0.098 * (1 - t) + 0.044 * t
        rings = []
        for k in range(8):
            s_ = k / 7
            ring = []
            for (x, y) in out:
                yc = 0.05
                xx = x * (1.0 - 0.8 * s_ ** 2.2) * 0.985
                yy = yc + (y - yc) * (1.0 - 0.28 * s_ ** 2.2)
                zz = 0.024 + hgt(y) * math.sin(s_ * math.pi / 2) ** 0.85 + (max(0.0, y - 0.12) * 0.3)
                ring.append((xx, yy, zz))
            rings.append(ring)
        m.mat(upper)
        dome = m.quad_strip(rings, closed=True, cap0=False, cap1=True)
        # heel counter + white toe cap by region
        hi = m.mats.index(heel) if heel in m.mats else (m.mats.append(heel) or len(m.mats) - 1)
        ti = m.mats.index(toe) if toe in m.mats else (m.mats.append(toe) or len(m.mats) - 1)
        for f in dome:
            if not f.is_valid:
                continue
            lp = m.M.inverted() @ f.calc_center_median()
            if lp.y < -0.035 and lp.z < 0.1:
                f.material_index = hi
            elif lp.y > 0.135 and lp.z < 0.058:
                f.material_index = ti
        # high-top collar
        m.mat(upper)
        col = []
        for k in range(5):
            t = k / 4
            z0 = 0.07 + t * 0.082
            tilt = 0.014 * t
            ring = []
            for i in range(20):
                an = 2 * math.pi * i / 20
                ring.append((0.049 * math.cos(an) * (1 - 0.06 * t), -0.02 + 0.058 * math.sin(an) * (1 - 0.05 * t), z0 - tilt * math.sin(an)))
            col.append(ring)
        m.quad_strip(col, closed=True, cap0=False, cap1=False)
        # padded rolled top edge
        m.mat(toe)
        top = col[-1]
        path = [V(p) for p in top] + [V(top[0])]
        m.sweep(path, [(math.cos(2 * math.pi * i / 8), math.sin(2 * math.pi * i / 8)) for i in range(8)], closed=True, cap=False,
                scale=lambda t: 0.0085)
        # pull tab at the back, tongue at the front
        m.mat(tab)
        m.push(Matrix.Translation((0, -0.076, 0.156)) @ Matrix.Rotation(math.radians(12), 4, 'X'))
        m.rbox((0, 0, 0), (0.02, 0.008, 0.03), 0.004, 1)
        m.pop()
        m.mat(upper)
        m.push(Matrix.Translation((0, 0.03, 0.146)) @ Matrix.Rotation(math.radians(-24), 4, 'X'))
        m.rbox((0, 0, 0), (0.04, 0.012, 0.056), 0.009, 2)
        m.pop()
        # criss-cross laces with eyelets
        eyes = []
        for i in range(4):
            y = 0.0 + i * 0.03
            z = 0.024 + hgt(y) * 0.985 + 0.004
            eyes.append((V((-0.021, y, z)), V((0.021, y, z))))
        m.mat(lace)
        for i in range(3):
            (l0, r0), (l1, r1) = eyes[i], eyes[i + 1]
            for p0, p1 in ((l0, r1), (r0, l1)):
                mid = p0.lerp(p1, 0.5) + V((0, 0, 0.005))
                m.tube([p0, mid, p1], r=0.004, seg=8)
        # little bow on top
        tb = eyes[0][0].lerp(eyes[0][1], 0.5) + V((0, -0.004, 0.006))
        for sd in (1, -1):
            m.tube([tb, tb + V((sd * 0.012, -0.006, 0.01)), tb + V((sd * 0.02, 0.002, 0.004)), tb], r=0.0032, seg=6)
        # ankle logo on the outer side
        m.mat(logo)
        m.push(Matrix.Translation((side * 0.05, -0.02, 0.12)) @ Matrix.Rotation(math.radians(90 * side), 4, 'Z') @ Matrix.Rotation(math.radians(90), 4, 'X'))
        m.cyl((0, 0, -0.001), 0.02, 0.003, 24)
        m.mat(heel)
        m.extrude(E.star_pts(5, 0.016, 0.007), 0.005, c=(0, 0, 0.002))
        m.pop()
        m.pop()


def project_panel(m, bvh, pts2d, depth, back=False, rows=6):
    """Raised patch on a surface: 2D outline (x, z) projected along Y and thickened outward."""
    xs = [p[0] for p in pts2d]
    zs = [p[1] for p in pts2d]
    # build a polar grid from the centroid to the outline
    cx, cz = sum(xs) / len(xs), sum(zs) / len(zs)
    top, base = [], []
    for k in range(rows + 1):
        t = k / rows
        rt, rb = [], []
        for (x, z) in pts2d:
            px, pz = cx + (x - cx) * t, cz + (z - cz) * t
            hit = bvh.ray_cast(V((px, -1.0 if back else 1.0, pz)), V((0, 1 if back else -1, 0)))
            p, n = (hit[0], hit[1]) if hit[0] is not None else (V((px, 0.0, pz)), V((0, 1, 0)))
            rt.append(p + n * depth)
            rb.append(p + n * 0.0005)
        top.append(rt)
        base.append(rb)
    bm = m.bm
    vt = [[bm.verts.new(m.M @ p) for p in ring] for ring in top]
    n = len(pts2d)
    faces = []
    # centre fan + rings
    for k in range(rows):
        for i in range(n):
            j = (i + 1) % n
            if k == 0:
                try:
                    faces.append(bm.faces.new((vt[0][i], vt[1][i], vt[1][j])))
                except ValueError:
                    pass
            else:
                faces.append(bm.faces.new((vt[k][i], vt[k + 1][i], vt[k + 1][j], vt[k][j])))
    vb = [bm.verts.new(m.M @ p) for p in base[-1]]
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((vb[i], vb[j], vt[-1][j], vt[-1][i])))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    for f in faces:
        f.material_index = m.mi
        f.smooth = True
        for l in f.loops:
            l[m.col] = m.tint
    m._box_uv(faces)
    return faces, top[-1]


def hoodie2(m, B, body_mat, trim_mat, string_mat, logo_tex, back_tex):
    k = B.k
    fs = torso_shell(m, B, body_mat, [
        (0.852, 0.161, 0.112, 0.004), (0.872, 0.165, 0.115, 0.004), (0.896, 0.166, 0.116, 0.004), (0.912, 0.177, 0.122, 0.005),
        (0.97, 0.175, 0.121, 0.006), (1.04, 0.169, 0.118, 0.008), (1.12, 0.177, 0.124, 0.01), (1.2, 0.186, 0.13, 0.012),
        (1.28, 0.19, 0.128, 0.01), (1.35, 0.184, 0.118, 0.004), (1.395, 0.15, 0.1, 0.0), (1.425, 0.085, 0.07, 0.0),
        (1.44, 0.058, 0.055, 0.0)], n=24, pw=2.5)
    band(fs, m, trim_mat, 0.0, 0.9 * k)
    return fs


def hoodie2_details(m, B, body_obj, body_mat, trim_mat, string_mat, logo_tex, back_tex):
    """Pocket, drawstrings and printed art projected onto the finished hoodie body."""
    k = B.k
    bvh = bvh_of(body_obj)
    # kangaroo pocket: raised panel with piped openings
    m.mat(body_mat)
    zb, zm, zt = 0.915 * k, 0.975 * k, 1.005 * k
    bottom = [(-0.1 + 0.2 * i / 9, zb) for i in range(10)]
    right = [(0.086, zm), (0.078, zt)]
    top = [(0.078 - 0.156 * i / 8, zt) for i in range(1, 8)]
    left = [(-0.078, zt), (-0.086, zm)]
    outline = bottom + right + top + left
    faces, rim = project_panel(m, bvh, outline, 0.007)
    m.mat(trim_mat)
    i_r0 = len(bottom) - 1
    i_rt = len(bottom) + 1
    i_lt = len(bottom) + len(right) + len(top)
    m.tube([rim[i] for i in range(i_rt, i_lt + 1)], r=0.0032, seg=6)
    m.tube([rim[i_r0], rim[i_r0 + 1], rim[i_rt]], r=0.0035, seg=6)
    m.tube([rim[0], rim[-1], rim[i_lt]], r=0.0035, seg=6)
    # printed chest logo (wearer's left chest) and back print
    E.mat("print_" + logo_tex, 0xFFFFFF, tex=logo_tex, flags=E.F_DECAL | E.F_NOCAST, outline=0, rim=0.0, soft=0.1)
    m.mat("print_" + logo_tex)
    project_decal(m, bvh, -0.075, 1.255 * k, 0.085, 0.085, 7, 7, off=0.0012, mirror=True)
    E.mat("print_" + back_tex, 0xFFFFFF, tex=back_tex, flags=E.F_DECAL | E.F_NOCAST, outline=0, rim=0.0, soft=0.1)
    m.mat("print_" + back_tex)
    project_decal(m, bvh, 0.0, 1.075 * k, 0.26, 0.13, 11, 6, off=0.0012, back=True)
    # drawstrings from the collar
    m.mat(string_mat)
    for side in (1, -1):
        p0 = surface_path(bvh, [(side * 0.03, 1.4 * k)], 0.004)[0]
        p1 = surface_path(bvh, [(side * 0.036, 1.33 * k)], 0.006)[0]
        p2 = surface_path(bvh, [(side * 0.038, 1.27 * k)], 0.006)[0]
        m.tube([p0, p1, p2], r=0.004, seg=8)
        m.mat(trim_mat)
        m.cyl(tuple(p2 - V((0, 0, 0.011))), 0.0055, 0.022, 10)
        m.mat(string_mat)


def hood2(m, B, outer_mat, lining_mat):
    """Hood lying folded on the upper back: scoop shell with a rolled rim showing the lining."""
    k = B.k
    nu, nv = 17, 9
    def P(u, v, inset=0.0):
        a = math.radians(u * 112)
        rim = V((0.122 * math.sin(a), 0.018 - 0.126 * math.cos(a), 1.452 - 0.03 * (1 - math.cos(a))))
        tip = V((0.052 * u, -0.148 + 0.012 * abs(u), 1.222 + 0.03 * abs(u)))
        p = rim.lerp(tip, v ** 0.9)
        bulge = 0.034 * math.sin(math.pi * min(1.0, v * 1.1)) * (1 - 0.6 * u * u)
        p.y -= bulge
        p.z += 0.01 * math.sin(math.pi * v)
        p.y += inset
        return V((p.x * k, p.y * k, p.z * k))
    outer = [[P(-1 + 2 * i / (nu - 1), j / (nv - 1)) for i in range(nu)] for j in range(nv)]
    inner = [[P(-1 + 2 * i / (nu - 1), j / (nv - 1), 0.013) + V((0, 0, -0.006 * (1 - j / (nv - 1)))) for i in range(nu)] for j in range(nv)]
    bm = m.bm
    vo = [[bm.verts.new(m.M @ p) for p in row] for row in outer]
    vi = [[bm.verts.new(m.M @ p) for p in row] for row in inner]
    fo, fi, fr = [], [], []
    for j in range(nv - 1):
        for i in range(nu - 1):
            fo.append(bm.faces.new((vo[j][i], vo[j + 1][i], vo[j + 1][i + 1], vo[j][i + 1])))
            fi.append(bm.faces.new((vi[j][i], vi[j][i + 1], vi[j + 1][i + 1], vi[j + 1][i])))
    # close the side edges and the rim
    for i in range(nu - 1):
        fr.append(bm.faces.new((vo[0][i], vo[0][i + 1], vi[0][i + 1], vi[0][i])))
        fr.append(bm.faces.new((vo[-1][i + 1], vo[-1][i], vi[-1][i], vi[-1][i + 1])))
    for j in range(nv - 1):
        fr.append(bm.faces.new((vo[j + 1][0], vo[j][0], vi[j][0], vi[j + 1][0])))
        fr.append(bm.faces.new((vo[j][-1], vo[j + 1][-1], vi[j + 1][-1], vi[j][-1])))
    allf = fo + fi + fr
    bmesh.ops.recalc_face_normals(bm, faces=allf)
    oi = m.mats.index(outer_mat) if outer_mat in m.mats else (m.mats.append(outer_mat) or len(m.mats) - 1)
    li = m.mats.index(lining_mat) if lining_mat in m.mats else (m.mats.append(lining_mat) or len(m.mats) - 1)
    for f in allf:
        f.material_index = li if f in fi else oi
        f.smooth = True
        for l in f.loops:
            l[m.col] = (1, 1, 1, 1)
    m._box_uv(allf)
    # rolled rim with lining peeking out
    m.mat(lining_mat)
    rim_path = [V(p) + V((0, 0.006 * k, 0.002 * k)) for p in outer[0]]
    m.tube(rim_path, r=0.0105 * k, seg=10)


def scarf2(m, B, mat, stripe_mat, fringe_mat):
    """Loose single wrap, knot at the back-left, two wide wavy tails down the back."""
    k = B.k
    m.mat(mat)
    path = []
    for i in range(49):
        a = 2 * math.pi * i / 48
        rr = 1 + 0.035 * math.sin(6 * a)
        path.append(V((0.081 * rr * math.sin(a) * k, (0.006 + 0.077 * rr * math.cos(a)) * k, (1.432 - 0.014 * math.cos(a)) * k)))
    prof = [(math.cos(2 * math.pi * i / 12) * 1.0, math.sin(2 * math.pi * i / 12) * 0.55) for i in range(12)]
    m.sweep(path, prof, closed=True, cap=False, scale=lambda t: (0.03 * k, 0.03 * k), twist=math.radians(8), up=(0, 0, 1))
    # knot
    kn = V((-0.048 * k, -0.074 * k, 1.425 * k))
    m.push(Matrix.Translation(kn) @ Matrix.Rotation(math.radians(-25), 4, 'Z'))
    m.sphere((0, 0, 0), 1.0, 16, 10, s=(0.034 * k, 0.026 * k, 0.03 * k))
    m.sphere((0.012 * k, -0.008 * k, -0.018 * k), 1.0, 12, 8, s=(0.022 * k, 0.018 * k, 0.02 * k))
    m.pop()
    tails = []
    for (dx, L, ph) in ((0.0, 1.0, 0.0), (0.042, 0.84, 1.3)):
        p0 = kn + V((dx * 0.5 * k, -0.012 * k, -0.02 * k))
        pts = [V(p) for p in E.bezier(p0, p0 + V((-0.02 * k, -0.06 * k, -0.12 * L * k)), p0 + V((-0.045 * k, -0.08 * k, -0.3 * L * k)),
                                      p0 + V((-0.05 * k + dx * k, -0.07 * k, -0.47 * L * k)), 40)]
        for i, p in enumerate(pts):
            t = i / (len(pts) - 1)
            p.x += 0.012 * k * math.sin(t * math.pi * 2.4 + ph) * t
        rings = []
        m.mat(mat)
        fs = m.sweep(pts, [(-1, -0.14), (1, -0.14), (1, 0.14), (-1, 0.14)], closed=True, cap=True,
                     scale=lambda t: (0.042 * k * (1 + 0.14 * t), 0.042 * k), twist=math.radians(14), up=(0, -1, 0), rings_out=rings)
        # two crisp white stripes near the end (faces are created ring by ring, 4 per ring)
        si = m.mats.index(stripe_mat) if stripe_mat in m.mats else (m.mats.append(stripe_mat) or len(m.mats) - 1)
        nr = len(pts)
        for fi, f in enumerate(fs):
            if not f.is_valid:
                continue
            ring = fi // 4
            if ring >= nr - 1:
                continue
            t = (ring + 0.5) / (nr - 1)
            if 0.8 <= t <= 0.84 or 0.875 <= t <= 0.915:
                f.material_index = si
        m.mat(fringe_mat)
        last = [V(p) for p in rings[-1]]
        a_ = (last[0] + last[3]) * 0.5
        b_ = (last[1] + last[2]) * 0.5
        tdir = (pts[-1] - pts[-2]).normalized()
        for f in range(7):
            q0 = a_.lerp(b_, (f + 0.5) / 7) - tdir * 0.004
            q1 = q0 + tdir * 0.032 * k
            m.tube([q0, q0.lerp(q1, 0.5), q1], r=0.0042 * k, seg=6, taper=0.4)
        tails.append(pts)
    return tails
