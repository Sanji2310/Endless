"""
Zone clips: short camera runs through the zone set pieces, with the title card and the synced soundtrack.

  transition_clip   Sakura Line -> Crystal Cavern: the cutting, the portal (title card slides in, whoosh and sting),
                    the lined tunnel, the ore cart boarding point, out through the mouth into the cavern.
  bats_clip         riding in the cavern under a low beam while a bat swarm flaps toward the camera.

Usage:  blender -b -P blender/run.py -- zone_clips transition_clip      (PONGO_QUICK=1 for a fast preview)
Output: renders/anim/<name>/####.png -> renders/anim/<name>.mp4 (with sound), <name>.gif, <name>_strip.png
The soundtrack comes from tools/preview/ZoneSim.java ("track" mode), which fires the same Zones events as the game.
"""
import math, os, subprocess
import bpy
from mathutils import Vector
import erlib as E
import studio
import cave
import tunnel

V = Vector
FPS = 24
OUT = os.path.join(E.OUT_RENDERS, "anim")
SPEED = 16.0            # m/s, the cart's cruising speed in the cave
CAM_BEHIND = 4.5        # the follow camera sits this far behind Pongo
ZONE_LEN = 1440.0       # Zones.ZONE_LEN: the clip runs into the first zone boundary


def _look(cam, loc, target):
    cam.location = loc
    cam.rotation_euler = (V(target) - V(loc)).to_track_quat('-Z', 'Y').to_euler()


def _clip_look():
    """Animation render settings: fewer TAA samples and hard shadow maps (the toon ramp thresholds them anyway).
    PONGO_QUICK=1 renders at 75% with 8 samples."""
    sc = bpy.context.scene
    quick = os.environ.get("PONGO_QUICK")
    sc.render.resolution_percentage = 75 if quick else 100      # 960x540 previews: stills' 50% is too small for video
    sc.eevee.taa_render_samples = 8 if quick else 24
    sc.eevee.use_soft_shadows = False
    sc.eevee.shadow_cascade_size = '2048'
    sc.eevee.shadow_cube_size = '512'


def _render(name, frames, res):
    """Renders frames 1..frames to renders/anim/<name>/####.png. PONGO_PART=k/n renders every n-th frame from 1+k, so
    n Blender processes can share a clip (clear the folder first, then run the clip's "encode" step once they finish)."""
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = res
    part = os.environ.get("PONGO_PART")
    k, n = (int(v) for v in part.split("/")) if part else (0, 1)
    sc.frame_start, sc.frame_end, sc.frame_step = 1 + k, frames, n
    sc.render.fps = FPS
    d = os.path.join(OUT, name)
    os.makedirs(d, exist_ok=True)
    if not part:
        for f in os.listdir(d):
            if f.endswith(".png"):
                os.remove(os.path.join(d, f))
    sc.render.filepath = os.path.join(d, "")
    sc.render.image_settings.file_format = 'PNG'
    _clip_look()
    bpy.ops.render.render(animation=True)
    return d


def _soundtrack(name, d0, seconds):
    """Runs ZoneSim to mix the clip's audio (Pongo's distance d0 at frame 1, constant SPEED)."""
    root = E.ROOT
    cls = os.path.join(E.BUILD, "zonesim")
    os.makedirs(cls, exist_ok=True)
    core = os.path.join(root, "src", "com", "pongo", "core")
    srcs = [os.path.join(core, f) for f in sorted(os.listdir(core)) if f.endswith(".java")]
    subprocess.run(["javac", "-nowarn", "-encoding", "UTF-8", "--release", "8", "-d", cls] + srcs +
                   [os.path.join(root, "tools", "preview", "ZoneSim.java")], check=True)
    wav = os.path.join(OUT, name + ".wav")
    subprocess.run(["java", "-cp", cls, "ZoneSim", "track", wav, str(d0), str(SPEED), str(seconds)], check=True)
    return wav


def _encode(name, d, frames, wav=None, card=None, card_t=None, gif_width=480):
    """MP4 (with the title card slid in over the frames at card_t seconds, and the soundtrack) and a GIF."""
    mp4 = os.path.join(OUT, name + ".mp4")
    gif = os.path.join(OUT, name + ".gif")
    inputs = ["-framerate", str(FPS), "-i", os.path.join(d, "%04d.png")]
    filt = "[0:v]null[v]"
    audio_in = 1
    if card and os.path.exists(card):
        inputs += ["-loop", "1", "-i", card]
        # Zones.cardSlide(): ease-out in 0.35 s, hold 2.2 s, ease-in out 0.45 s; card is 640 px wide
        t0, t1, t2, t3 = card_t, card_t + 0.35, card_t + 2.55, card_t + 3.0
        xin = "(-w+(W*0.04+w)*(1-pow(1-(t-%.3f)/0.35,3)))" % t0
        xout = "(W*0.04-(W*0.04+w)*pow((t-%.3f)/0.45,3))" % t2
        x = "if(lt(t,%.3f),-w,if(lt(t,%.3f),%s,if(lt(t,%.3f),W*0.04,if(lt(t,%.3f),%s,-w))))" % (t0, t1, xin, t2, t3, xout)
        w = int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width",
                                "-of", "csv=p=0", os.path.join(d, "0001.png")], capture_output=True, text=True,
                               check=True).stdout.strip())
        k = 0.75 * w / 1280.0         # the 640 px card shows 480 px wide on a 1280 px frame
        filt = "[1:v]scale=iw*%.4f:-1[c];[0:v][c]overlay=x='%s':y=H*0.1:shortest=1[v]" % (k, x)
        audio_in = 2
    if wav:
        inputs += ["-i", wav]
    cmd = ["ffmpeg", "-y", "-loglevel", "error"] + inputs + ["-filter_complex", filt, "-map", "[v]"]
    if wav:
        cmd += ["-map", "%d:a" % audio_in, "-c:a", "aac", "-b:a", "128k", "-shortest"]
    cmd += ["-frames:v", str(frames), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart", mp4]
    subprocess.run(cmd, check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp4, "-vf",
                    "fps=12,scale=%d:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=160[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" % gif_width,
                    gif], check=True)
    print("encoded", mp4, gif)
    return mp4


def _strip(name, d, frames, cols=4):
    """Contact strip of a few frames (ffmpeg tile)."""
    sel = "+".join("eq(n\\,%d)" % (f - 1) for f in frames)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(d, "%04d.png"),
                    "-vf", "select='%s',scale=400:-1,tile=%dx%d" % (sel, cols, (len(frames) + cols - 1) // cols),
                    "-frames:v", "1", os.path.join(OUT, name + "_strip.png")], check=True)


TRANSITION_Y0 = -40.0       # the transition clip's camera starts 40 m before the portal (portal at y = 0)


def transition_clip(seconds="6.5", step="all"):
    """step: "all", "render" (frames only, e.g. one PONGO_PART of several) or "encode" (sound, card and video from the
    rendered frames)."""
    seconds = float(seconds)
    frames = int(seconds * FPS)
    d = os.path.join(OUT, "transition")
    if step in ("all", "render"):
        E.reset()
        studio.stage(res=(1280, 720), floor=False)
        tunnel.transition_scene(cave_segments=7)       # the camera ends 40 m into the cavern and sees 44 m on
        tunnel.transition_lights(7)
        studio.aim_sun(0)
        cam = E.camera((0, TRANSITION_Y0, 2.5), (0, TRANSITION_Y0 + 10, 1.4), lens=26)
        cart = [o for o in bpy.data.objects if o.name.startswith("ore_cart")][0]
        board_y = cart.location.y
        for f in range(1, frames + 1):
            t = (f - 1) / FPS
            y = TRANSITION_Y0 + SPEED * t
            sway = 0.12 * math.sin(t * 2.3)
            loc = V((sway, y, 2.5 + 0.06 * math.sin(t * 5.1)))
            _look(cam, loc, (sway * 0.5, y + 10.0, 1.4))
            cam.keyframe_insert("location", frame=f)
            cam.keyframe_insert("rotation_euler", frame=f)
            # the cart waits at the boarding point; once Pongo reaches it, it runs CAM_BEHIND ahead of the camera
            cart.location.y = max(board_y, y + CAM_BEHIND)
            cart.keyframe_insert("location", frame=f)
        for fc in list(cam.animation_data.action.fcurves) + list(cart.animation_data.action.fcurves):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
        _render("transition", frames, (1280, 720))
    if step not in ("all", "encode"):
        return
    # Pongo's distance at frame 1: the mouth is the zone boundary and the portal sits LINED before it
    d0 = ZONE_LEN - tunnel.LINED + (TRANSITION_Y0 + CAM_BEHIND)
    card_t = (ZONE_LEN - tunnel.LINED - d0) / SPEED
    wav = _soundtrack("transition", d0, seconds)
    card = os.path.join(E.OUT_TEX, "ui_zone_cavern.png")
    if not os.path.exists(card):
        tunnel.title_cards()
    _encode("transition", d, frames, wav, card, card_t)
    _strip("transition", d, [1, int(frames * 0.3), int(frames * 0.42), int(frames * 0.55), int(frames * 0.68),
                             int(frames * 0.8), int(frames * 0.9), frames])


def bats_clip(seconds="3.0"):
    """In the cart under the Hotaru Lamp: a bat swarm flaps toward the rider (wing frames swap every 2 frames)."""
    import vehicles as VH
    seconds = float(seconds)
    E.reset()
    studio.stage(res=(1280, 720), floor=False)
    studio._SUN[0].data.energy = 0.0
    cave.cave_world()
    cave.cave_run(4, y0=-12.0, seeds=(2, 1, 3, 2))
    cave.cave_lights(4, y0=-11.0)
    cave.cave_tint()
    VH.mats()
    cart = VH.ore_cart(); E.add_outline(cart, 0.012)
    swarm = [cave.bat_swarm(0), cave.bat_swarm(1)]
    beam = cave.timber_beam(); E.add_outline(beam, 0.015)
    beam.location = (0, 26.0, 0)
    frames = int(seconds * FPS)
    cam = E.camera((0, 0, 2.3), (0, 10, 1.2), lens=26)
    spot = cave.hotaru_beam((0.3, 1.0, 1.9), (0, 8, 1.0))
    speed = 9.0
    for f in range(1, frames + 1):
        t = (f - 1) / FPS
        y = -6.0 + speed * t
        _look(cam, V((0.1 * math.sin(t * 2), y, 2.3)), (0, y + 10, 1.2))
        cam.keyframe_insert("location", frame=f); cam.keyframe_insert("rotation_euler", frame=f)
        cart.location.y = y + 3.2
        cart.keyframe_insert("location", frame=f)
        spot.location = V((0.3, y + 3.0, 1.9))
        spot.keyframe_insert("location", frame=f)
        # swarm flies at 6 m/s toward the rider, weaving; the two wing frames alternate
        sy = 30.0 - 6.0 * t
        for k, ob in enumerate(swarm):
            ob.location = (0.4 * math.sin(t * 3.0), sy, 0.15 * math.sin(t * 7.0))
            ob.keyframe_insert("location", frame=f)
            ob.hide_render = ((f // 2) % 2) != k
            ob.keyframe_insert("hide_render", frame=f)
    d = _render("bats", frames, (1280, 720))
    _encode("bats", d, frames)
    _strip("bats", d, [1, int(frames * 0.35), int(frames * 0.7), frames], cols=4)
