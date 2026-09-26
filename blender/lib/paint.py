"""
paint — 2D vector painting through Blender (orthographic EEVEE render of flat shapes).

Used for anime textures: eyes, mouths, signs, posters, logos and particle sprites.
Coordinates are in pixels with (0, 0) at the bottom-left of the canvas.
Every call adds a flat, unlit shape; later calls draw on top.
"""
import bpy, bmesh, math, os
from mathutils import Vector
import erlib as E


class Canvas:
    def __init__(self, name, w, h, bg=None, samples=32):
        self.name, self.w, self.h = name, w, h
        self.sc = bpy.data.scenes.new("paint_" + name)
        self.z = 0.0
        self.samples = samples
        self._mats = {}
        sc = self.sc
        sc.render.engine = 'BLENDER_EEVEE'
        sc.render.resolution_x, sc.render.resolution_y = w, h
        sc.render.resolution_percentage = 100
        sc.render.film_transparent = bg is None
        sc.eevee.taa_render_samples = samples
        sc.eevee.use_bloom = False
        sc.view_settings.view_transform = 'Standard'
        sc.view_settings.look = 'None'
        sc.render.image_settings.file_format = 'PNG'
        sc.render.image_settings.color_mode = 'RGBA'
        w_ = bpy.data.worlds.new("paintworld")
        w_.use_nodes = True
        bgn = w_.node_tree.nodes["Background"]
        bgn.inputs[0].default_value = E.lin4(bg if bg is not None else 0x000000)
        bgn.inputs[1].default_value = 1.0
        sc.world = w_
        cd = bpy.data.cameras.new("paintcam")
        cd.type = 'ORTHO'
        cd.ortho_scale = max(w, h)
        cd.clip_start = 0.01
        cd.clip_end = 1000
        cam = bpy.data.objects.new("paintcam", cd)
        sc.collection.objects.link(cam)
        cam.location = (w / 2, h / 2, 500)
        sc.camera = cam
        if bg is not None:
            self.rect(0, 0, w, h, bg)

    # ------------------------------------------------------------------ materials
    def _mat(self, color, alpha=1.0, vcol=False):
        key = (color, round(alpha, 3), vcol)
        if key in self._mats:
            return self._mats[key]
        m = bpy.data.materials.new("pm")
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        em = nt.nodes.new('ShaderNodeEmission')
        if vcol:
            vc = nt.nodes.new('ShaderNodeVertexColor')
            vc.layer_name = "Col"
            nt.links.new(vc.outputs["Color"], em.inputs[0])
        else:
            em.inputs[0].default_value = E.lin4(color)
        if alpha < 1.0 or vcol:
            tr = nt.nodes.new('ShaderNodeBsdfTransparent')
            mx = nt.nodes.new('ShaderNodeMixShader')
            if vcol:
                vc2 = nt.nodes[-3] if False else [n for n in nt.nodes if n.type == 'VERTEX_COLOR'][0]
                nt.links.new(vc2.outputs["Alpha"], mx.inputs[0])
            else:
                mx.inputs[0].default_value = alpha
            nt.links.new(tr.outputs[0], mx.inputs[1])
            nt.links.new(em.outputs[0], mx.inputs[2])
            nt.links.new(mx.outputs[0], out.inputs[0])
            m.blend_method = 'BLEND'
        else:
            nt.links.new(em.outputs[0], out.inputs[0])
        self._mats[key] = m
        return m

    def _add(self, bm, color, alpha=1.0, vcol=False):
        me = bpy.data.meshes.new("pshape")
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new("pshape", me)
        self.sc.collection.objects.link(ob)
        me.materials.append(self._mat(color, alpha, vcol))
        self.z += 0.01
        ob.location.z = self.z
        return ob

    # ------------------------------------------------------------------ shapes
    def poly(self, pts, color, alpha=1.0):
        bm = bmesh.new()
        vs = [bm.verts.new((x, y, 0)) for (x, y) in pts]
        edges = [bm.edges.new((vs[i], vs[(i + 1) % len(vs)])) for i in range(len(vs))]
        bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=edges)
        return self._add(bm, color, alpha)

    def poly_holes(self, outer, holes, color, alpha=1.0):
        bm = bmesh.new()
        edges = []
        for lp in [outer] + list(holes):
            vs = [bm.verts.new((x, y, 0)) for (x, y) in lp]
            edges += [bm.edges.new((vs[i], vs[(i + 1) % len(vs)])) for i in range(len(vs))]
        bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=edges)
        return self._add(bm, color, alpha)

    def rect(self, x, y, w, h, color, alpha=1.0):
        return self.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], color, alpha)

    def ellipse(self, cx, cy, rx, ry, color, alpha=1.0, seg=64, rot=0.0):
        c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        pts = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            x, y = rx * math.cos(a), ry * math.sin(a)
            pts.append((cx + x * c - y * s, cy + x * s + y * c))
        return self.poly(pts, color, alpha)

    def circle(self, cx, cy, r, color, alpha=1.0, seg=64):
        return self.ellipse(cx, cy, r, r, color, alpha, seg)

    def gradient_poly(self, pts, colors):
        """Polygon with per-vertex colours ((0xRRGGBB, alpha) per point); fan from centroid."""
        bm = bmesh.new()
        cl = bm.loops.layers.color.new("Col")
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        vs = [bm.verts.new((x, y, 0)) for (x, y) in pts]
        cc = [sum(E.hexrgb(c[0])[k] for c in colors) / len(colors) for k in range(3)]
        ca = sum(c[1] for c in colors) / len(colors)
        vc = bm.verts.new((cx, cy, 0))
        for i in range(len(vs)):
            f = bm.faces.new((vc, vs[i], vs[(i + 1) % len(vs)]))
            for l in f.loops:
                if l.vert is vc:
                    l[cl] = (*[E.srgb_to_lin(v) for v in cc], ca)
                else:
                    j = vs.index(l.vert)
                    r, g, b = E.hexrgb(colors[j][0])
                    l[cl] = (E.srgb_to_lin(r), E.srgb_to_lin(g), E.srgb_to_lin(b), colors[j][1])
        return self._add(bm, 0xFFFFFF, 1.0, vcol=True)

    def radial(self, cx, cy, r0, r1, c0, c1, a0=1.0, a1=1.0, seg=64, sx=1.0, sy=1.0):
        """Ring/disc with a radial gradient from radius r0 (c0) to r1 (c1)."""
        bm = bmesh.new()
        cl = bm.loops.layers.color.new("Col")
        def lc(h, a):
            r, g, b = E.hexrgb(h)
            return (E.srgb_to_lin(r), E.srgb_to_lin(g), E.srgb_to_lin(b), a)
        inner = []
        outer = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            inner.append(bm.verts.new((cx + r0 * sx * math.cos(a), cy + r0 * sy * math.sin(a), 0)))
            outer.append(bm.verts.new((cx + r1 * sx * math.cos(a), cy + r1 * sy * math.sin(a), 0)))
        centre = bm.verts.new((cx, cy, 0)) if r0 <= 0 else None
        for i in range(seg):
            j = (i + 1) % seg
            f = bm.faces.new((inner[i], outer[i], outer[j], inner[j])) if r0 > 0 else None
            if f is None:
                f = bm.faces.new((centre, outer[i], outer[j]))
            for l in f.loops:
                if l.vert in outer:
                    l[cl] = lc(c1, a1)
                else:
                    l[cl] = lc(c0, a0)
        return self._add(bm, 0xFFFFFF, 1.0, vcol=True)

    def stroke(self, pts, w0, w1, color, alpha=1.0, cap=True):
        """Tapered brush stroke along a polyline (width w0 at start, w1 at end)."""
        n = len(pts)
        left, right = [], []
        for i in range(n):
            a = Vector(pts[max(i - 1, 0)])
            b = Vector(pts[min(i + 1, n - 1)])
            d = (b - a)
            d = d.normalized() if d.length > 1e-9 else Vector((1, 0))
            nrm = Vector((-d.y, d.x))
            t = i / max(n - 1, 1)
            w = (w0 + (w1 - w0) * t) / 2
            p = Vector(pts[i])
            left.append(p + nrm * w)
            right.append(p - nrm * w)
        outline = [tuple(p) for p in left] + [tuple(p) for p in reversed(right)]
        ob = self.poly(outline, color, alpha)
        if cap:
            if w0 > 0.5:
                self.z -= 0.01
                self.circle(pts[0][0], pts[0][1], w0 / 2, color, alpha, 16)
            if w1 > 0.5:
                self.circle(pts[-1][0], pts[-1][1], w1 / 2, color, alpha, 16)
        return ob

    def curve(self, p0, p1, p2, p3, w0, w1, color, alpha=1.0, n=24):
        pts = [tuple(v)[:2] for v in E.bezier((*p0, 0), (*p1, 0), (*p2, 0), (*p3, 0), n)]
        return self.stroke(pts, w0, w1, color, alpha)

    def text(self, body, x, y, size, color, font=E.FONT_LATIN, align='CENTER', alpha=1.0, spacing=1.0, outline=0, outline_color=0x000000):
        cu = bpy.data.curves.new("ptxt", 'FONT')
        cu.body = body
        cu.font = E._font(font)
        cu.size = size
        cu.align_x = align
        cu.align_y = 'CENTER'
        cu.space_character = spacing
        cu.resolution_u = 6
        if outline > 0:
            cu2 = cu.copy()
            cu2.offset = outline
            ob2 = bpy.data.objects.new("ptxt_o", cu2)
            self.sc.collection.objects.link(ob2)
            ob2.location = (x, y, self.z + 0.005)
            cu2.materials.append(self._mat(outline_color, alpha))
            self.z += 0.01
        ob = bpy.data.objects.new("ptxt", cu)
        self.sc.collection.objects.link(ob)
        self.z += 0.01
        ob.location = (x, y, self.z)
        cu.materials.append(self._mat(color, alpha))
        return ob

    # ------------------------------------------------------------------ output
    def save(self, path=None):
        path = path or E.tex_path(self.name)
        self.sc.render.filepath = path
        bpy.ops.render.render(write_still=True, scene=self.sc.name)
        # clean up the scene's objects
        for ob in list(self.sc.collection.objects):
            data = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            if isinstance(data, bpy.types.Mesh):
                bpy.data.meshes.remove(data)
            elif isinstance(data, bpy.types.Curve):
                bpy.data.curves.remove(data)
        bpy.data.scenes.remove(self.sc)
        print("painted", path)
        return path
