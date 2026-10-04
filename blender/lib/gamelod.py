"""
Distance tiers for the game. SakuraWorld draws LOD0 near the runner, LOD1 in the middle distance and LOD2 far out
(src/com/endlessrush/core/SakuraWorld.java: LOD1_DIST, LOD2_DIST).

The design renders finish hard surfaces with a 1 cm bevel and weighted normals; on a phone screen that bevel is far
below a pixel at the distances buildings sit at, and it multiplies the triangle count by about seven. The game tiers
drop it and shade flat faces by angle instead (one clean tone per face, which is what the renders read as anyway),
and the far tier is also decimated.

The texture atlas cannot wrap, so the asset builder cuts every triangle at each repeat of a tiled texture: a wall
that spans six repeats becomes six times the triangles. Up close that is what the detail costs, but in the middle
and far tiers the repeats are smaller than a pixel, so squash_uv shrinks each such face into a single repeat.
"""
import math
import bpy
import erlib as E


def flat(ob):
    """No bevel, no weighted normals: flat faces split at 35 degrees."""
    had = False
    for m in list(ob.modifiers):
        if m.name in ("finish_bevel", "finish_wn"):
            ob.modifiers.remove(m)
            had = True
    if had:
        E.set_smooth(ob, 35.0)
    return ob


def decimate(ob, ratio):
    """Collapse-decimate (non-destructive; applied at export)."""
    if ratio < 1.0:
        d = ob.modifiers.new("game_decimate", 'DECIMATE')
        d.ratio = ratio
        d.use_collapse_triangulate = True
    return ob


def bake(ob):
    """Applies the modifiers (the design-render outline shell stays as it was) so the final faces can be edited."""
    dg = bpy.context.evaluated_depsgraph_get()
    outline = ob.modifiers.get("_outline")
    vis = outline.show_viewport if outline else False
    if outline:
        outline.show_viewport = False
    dg.update()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    for m in list(ob.modifiers):
        if m.name != "_outline":
            ob.modifiers.remove(m)
    ob.data = me
    if outline:
        outline.show_viewport = vis
    return ob


def squash_uv(ob):
    """Shrinks every face whose UVs cross a texture repeat into one repeat around its own centre."""
    me = ob.data
    uvl = me.uv_layers.active
    if uvl is None:
        return ob
    uv = uvl.data
    for poly in me.polygons:
        li = list(poly.loop_indices)
        us = [uv[i].uv[0] for i in li]
        vs = [uv[i].uv[1] for i in li]
        u0, u1, v0, v1 = min(us), max(us), min(vs), max(vs)
        if math.floor(u0 + 1e-5) >= math.ceil(u1 - 1e-5) - 1 and math.floor(v0 + 1e-5) >= math.ceil(v1 - 1e-5) - 1:
            continue
        cu, cv = (u0 + u1) * 0.5, (v0 + v1) * 0.5
        k = min(1.0, 0.9 / max(u1 - u0, 1e-6), 0.9 / max(v1 - v0, 1e-6))
        bu, bv = math.floor(cu) + 0.5, math.floor(cv) + 0.5
        for i, u, v in zip(li, us, vs):
            uv[i].uv = (bu + (u - cu) * k, bv + (v - cv) * k)
    return ob


def tier(objs, level, ratio=0.35, keep_bevel=False):
    """Prepares objs for game tier `level`: LOD0 keeps the bevel only when keep_bevel (pieces right beside the
    runner, like the trains), LOD1 and LOD2 are flat with their texture repeats squashed, LOD2 is also decimated
    to `ratio`."""
    single = not isinstance(objs, (list, tuple))
    objs = [objs] if single else list(objs)
    for ob in objs:
        if ob is None:
            continue
        if level >= 1 or not keep_bevel:
            flat(ob)
        if level >= 2:
            decimate(ob, ratio)
        if level >= 1:
            squash_uv(bake(ob))
    return objs[0] if single else objs


def sfx(level):
    return "" if level == 0 else "@%d" % level
