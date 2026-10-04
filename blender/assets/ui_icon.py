"""
Launcher icon: Pongo's head and shoulders on a transparent background. tools/icon/compose.html frames the render
(sky-to-sakura tile, petals, ink rim) and writes the res/mipmap-*/ic_launcher.png sizes.
"""
import bpy
import erlib as E
import studio
import pongo_g as PG


def render_icon_bust():
    E.reset()
    studio.stage(res=(1024, 1024), floor=False)
    B, arm, objs = PG.build_pongo_g()
    for o in objs:
        if o.type == 'MESH' and "face" not in o.name:
            E.add_outline(o, 0.0032)
    PG.girl_clips(arm)
    sc = bpy.context.scene
    arm.animation_data.action = bpy.data.actions["idle"]
    sc.frame_set(10)
    sc.render.film_transparent = True
    studio.shoot("icon_bust", target=(0, 0, 1.32), dist=1.05, yaw=196, pitch=2, lens=55)
