package com.endlessrush.core;

import com.pongo.core.Animator;
import com.pongo.core.PongoAssets;
import com.pongo.core.RenderFrame;

/**
 * Sakura Line toon layer: turns the game state into a com.pongo.core RenderFrame that draws Pongo (skinned,
 * animated, ink-outlined) and the Mon coins with the cel shader, on top of the world Scene draws.
 * It reuses Scene's camera, sun and fog so both layers share one view and one depth buffer.
 * Pure Java: used by the Android renderer and by the desktop preview.
 */
public final class PongoScene {
    /** Pongo is modelled at 1.55 m; the runner world is built around a ~1.9 m hero. */
    public static final float HERO_SCALE = 1.2f, COIN_SCALE = 0.95f;
    /** The hero slot she replaces (the free starter). */
    public static final int HERO_SLOT = 0;

    private final PongoAssets assets;
    private final Animator anim;
    private final int heroNear, heroFar, coinNear, coinFar;
    private final float slideLen;

    private boolean wasGrounded = true, wasRolling;
    private int lastState = -1;
    private float lastShake, time;

    public PongoScene(PongoAssets assets) {
        this.assets = assets;
        heroNear = assets.lod("pongo", 0);
        heroFar = assets.lod("pongo", 1);
        coinNear = assets.lod("coin", 0);
        coinFar = assets.lod("coin", 1);
        if (heroNear < 0 || coinNear < 0) throw new IllegalArgumentException("pongo.bin has no pongo/coin meshes");
        anim = new Animator(assets.skeletons[assets.meshes[heroNear].skeleton]);
        PongoAssets.Clip slide = anim.sk.clip("slide");
        slideLen = slide != null ? slide.duration() : Game.ROLL_TIME;
        anim.play("idle", 0);
    }

    /** Hides the parts of the world scene this layer replaces. */
    public void attach(Scene scene) {
        scene.toonHero = true;
        scene.toonCoins = true;
    }

    /**
     * Fills f for this frame. Call after scene.build(g, dl, ...) so the camera in dl is current.
     * w/h are the viewport size in pixels.
     */
    public void build(Game g, Scene scene, DrawList dl, RenderFrame f, int w, int h, float dt) {
        f.clear();
        boolean paused = g.state == Game.PAUSED;
        if (!paused) time += dt;
        camera(dl, f, w, h);
        if (scene.heroIndex(g) == HERO_SLOT) hero(g, f, paused ? 0 : dt);
        coins(g, f);
    }

    private void camera(DrawList dl, RenderFrame f, int w, int h) {
        f.screenW = Math.max(1, w);
        f.screenH = Math.max(1, h);
        System.arraycopy(dl.view, 0, f.view, 0, 16);
        System.arraycopy(dl.proj, 0, f.proj, 0, 16);
        System.arraycopy(dl.viewProj, 0, f.viewProj, 0, 16);
        com.pongo.core.Mat4.invert(f.invViewProj, f.viewProj);
        System.arraycopy(dl.camPos, 0, f.camPos, 0, 3);
        float lx = dl.lightDir[0], ly = dl.lightDir[1], lz = dl.lightDir[2];
        float ll = (float) Math.sqrt(lx * lx + ly * ly + lz * lz);
        f.sunDir[0] = lx / ll; f.sunDir[1] = ly / ll; f.sunDir[2] = lz / ll;
        System.arraycopy(dl.fogColor, 0, f.fogCol, 0, 3);
        f.fogStart = dl.fogStart;
        f.fogEnd = dl.fogEnd;
        f.fogMax = 1;
        f.heightFog = 0;
        f.night = 0;
        f.time = time;
        f.wind[3] = time;
        // the world layer has no shadow receivers yet; her blob shadow comes from Scene
        f.shadowOn = false;
        // screen overlays belong to the world layer
        f.vignette[3] = 0;
        f.speed[0] = 0;
        f.flash[3] = 0;
        // ink width tuned at 760 px tall, kept readable on small and large screens
        f.outlinePx = Math.max(1.4f, Math.min(3.2f, 2.2f * f.screenH / 900f));
    }

    private void hero(Game g, RenderFrame f, float dt) {
        boolean menu = g.state == Game.MENU;
        boolean dying = g.state == Game.DYING || g.state == Game.SAVE_ME || g.state == Game.GAME_OVER;
        choose(g, menu, dying);
        // spring chains (twin tails, wrap panel) trail a little behind the motion; the full run speed would
        // blow them out flat, so only a fraction of it drives the drag
        anim.velocity[0] = 0;
        anim.velocity[1] = menu ? 0 : g.vy * 0.12f;
        anim.velocity[2] = menu || dying ? 0 : -g.speed * 0.12f;
        anim.wind[0] = 0.06f * (float) Math.sin(time * 1.3f);
        anim.wind[2] = 0.04f;
        anim.update(dt);

        float px = g.x, py = g.y, pz = -g.s;
        boolean blink = g.invulnT > 0 && ((int) (g.invulnT * 12)) % 2 == 0;
        float[] m = f.draw(menu ? heroNear : heroFar, 0, 1, 1, 1, 1, blink ? 0.6f : 0);
        com.pongo.core.Mat4.translate(m, px, py, pz);
        if (!menu && !dying) com.pongo.core.Mat4.rotZ(m, (g.lane * Game.LANE_W - g.x) * -6f);
        if (g.boardT > 0 && !menu) com.pongo.core.Mat4.translate(m, 0, 0.4f, 0);
        com.pongo.core.Mat4.scale(m, HERO_SCALE, HERO_SCALE, HERO_SCALE);
        f.bonesForLast(anim.palette, anim.n);
    }

    /** Picks the clip from the game state; one-shot clips (jump, land, slide, stumble) run to their end. */
    private void choose(Game g, boolean menu, boolean dying) {
        int st = g.state;
        boolean stateChanged = st != lastState;
        boolean leftGround = wasGrounded && !g.grounded;
        boolean landed = !wasGrounded && g.grounded;
        boolean rollStart = g.rolling && !wasRolling;
        boolean stumbled = g.shake > lastShake + 0.05f && st == Game.RUNNING;
        lastState = st;
        wasGrounded = g.grounded;
        wasRolling = g.rolling;
        lastShake = g.shake;
        anim.speed = 1f;

        if (menu) { anim.play("idle", 0.25f); return; }
        if (dying) {
            String c = g.deathKind == 0 ? "crash" : "caught";
            if (stateChanged && st == Game.DYING) anim.restart(c, 0.08f);
            else anim.play(c, 0.1f);
            return;
        }
        if (g.jetT > 0) { anim.play("rocket", 0.2f); return; }
        if (g.rolling) {
            // stretch the slide to the game's roll window
            anim.speed = slideLen / Game.ROLL_TIME;
            if (rollStart) anim.restart("slide", 0.06f);
            else anim.play("slide", 0.06f);
            return;
        }
        if (!g.grounded) {
            if (leftGround && g.vy > 0) anim.restart("jump", 0.06f);
            else if (!(anim.playing("jump") && !anim.finished())) anim.play("fall", 0.2f);
            return;
        }
        if (landed) { anim.restart("land", 0.05f); return; }
        if (stumbled) { anim.restart("stumble", 0.05f); return; }
        if ((anim.playing("land") || anim.playing("stumble")) && !anim.finished()) return;
        if (g.boardT > 0) { anim.play("board", 0.2f); return; }
        anim.play("run", 0.15f);
        // legacy runner legs cycle at speed * 0.55 rad/s, which is the clip's own rate at base speed
        anim.speed = Math.max(0.8f, Math.min(1.8f, g.speed / Game.BASE_SPEED));
    }

    private void coins(Game g, RenderFrame f) {
        float spinBase = time * 180;
        for (int i = 0; i < g.pickups.size(); i++) {
            Game.Pickup p = g.pickups.get(i);
            if (p.type != Game.COIN || p.taken || p.s > g.s + 170 || p.s < g.s - 10) continue;
            float dx = p.x - f.camPos[0], dy = p.y - f.camPos[1], dz = -p.s - f.camPos[2];
            boolean near = dx * dx + dy * dy + dz * dz < 35 * 35;
            float[] m = f.draw(near ? coinNear : coinFar, 0, 1, 1, 1, 1, 0.15f);
            com.pongo.core.Mat4.translate(m, p.x, p.y, -p.s);
            com.pongo.core.Mat4.rotY(m, (spinBase + p.s * 7) % 360);
            com.pongo.core.Mat4.scale(m, COIN_SCALE, COIN_SCALE, COIN_SCALE);
        }
    }

    public PongoAssets assets() { return assets; }
}
