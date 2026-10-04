package com.endlessrush.core;

import com.pongo.core.Fx;
import com.pongo.core.PongoAssets;
import com.pongo.core.RenderFrame;
import com.pongo.core.Zones;

import java.util.ArrayList;
import java.util.IdentityHashMap;

/**
 * Drives com.pongo.core.Fx from the running game: it watches the game state from frame to frame and fires the
 * effect for each thing that happened (jump, landing, lane change, slide, stumble, crash, revive, every pickup and
 * power-up), keeps the held power-ups' effects on Pongo (magnet swirl, rocket flames, boot sparkles, Fever aura, board
 * hover ribbons), adds the zone's ambient effects (sakura petals, cave dust, bamboo leaves and river mist, sky wisps
 * and wind, rooftop wind and pantograph sparks), and sets the toon screen overlay (anime speed lines, impact flash).
 *
 * It reads Game only, so it needs no hooks in the simulation. The vehicle side calls the Fx presets directly
 * (fx().boatSpray, fx().cartSparks, fx().splash ...) from its own scene, at the vehicle's position.
 *
 * Call after PongoScene.build and ZoneWorld.build (the camera, zone palette and lamp in the frame are current).
 * Pure Java: used by the Android renderer and by the desktop preview.
 */
public final class FxLayer {
    private final Fx fx;
    private final Fx.Trail podL, podR, jetL, jetR;
    private float time;

    // last frame's game state
    private boolean wasGrounded = true, wasRolling, started;
    private int lastLane, lastState = -1;
    private float lastVy, lastShake, lastBoard, lastMag, lastJet, lastSneak, lastX2;
    private final ArrayList<Game.Pickup> seen = new ArrayList<Game.Pickup>();
    private final ArrayList<float[]> seenPos = new ArrayList<float[]>();
    private final IdentityHashMap<Game.Pickup, Boolean> now = new IdentityHashMap<Game.Pickup, Boolean>();

    // screen overlay
    private float flashT, impactT, glintT;
    /** Forces the ambient effects of a zone (previews, and zones that are not in the run cycle yet); -1 = the run's. */
    public int zoneOverride = -1;
    /** 0..1 dusk/night (no time-of-day system yet: fireflies come out above 0.35). */
    public float night;

    /** Extra effects for a frame, called before the particles are drawn (the vehicle scene, preview staging). */
    public interface Stage { void frame(Fx fx, RenderFrame f, float dt); }
    public Stage stage;

    public static boolean available(PongoAssets a) { return Fx.available(a); }

    public FxLayer(PongoAssets assets) {
        fx = new Fx(assets);
        podL = new Fx.Trail(24, 0.07f, 0.35f).color(Fx.CYAN, 0.85f);
        podR = new Fx.Trail(24, 0.07f, 0.35f).color(Fx.CYAN, 0.85f);
        jetL = new Fx.Trail(20, 0.1f, 0.25f).color(Fx.ORANGE, 0.7f);
        jetR = new Fx.Trail(20, 0.1f, 0.25f).color(Fx.ORANGE, 0.7f);
    }

    /** The effect system, for the vehicle side's presets (boatSpray, cartSparks, splash, gust ...). */
    public Fx fx() { return fx; }

    /** Pongo's model scale relative to the 1.2 the effects were tuned at (the vehicle thread sizes her). */
    private static float heroK() { return PongoScene.HERO_SCALE / 1.2f; }

    public void build(Game g, RenderFrame f, float dt) {
        boolean paused = g.state == Game.PAUSED;
        if (paused) dt = 0;
        time += dt;
        fx.update(dt);
        int zone = zoneOverride >= 0 ? zoneOverride : Zones.zoneAt(g.s);
        float[] dust = zone == Zones.CAVERN ? Fx.DUST_CAVE : zone == Zones.ROOFTOPS ? Fx.DUST_ROOF : zone == Zones.RIVER ? Fx.DUST_SAND : Fx.DUST_CITY;
        // solid sprites take the zone light (dim violet in the cave, full daylight outside)
        for (int c = 0; c < 3; c++) fx.ambient[c] = Math.min(1f, f.lightCol[c] * 1.2f + 0.18f);
        fx.wind[0] = 0.6f * (float) Math.sin(time * 0.31f) + 0.4f;
        fx.wind[1] = 0;
        fx.wind[2] = 0.3f;

        boolean menu = g.state == Game.MENU;
        float px = g.x, py = g.y, pz = -g.s, vz = -g.speed;
        float k = heroK();
        if (!menu && !paused) {
            events(g, f, dt, dust, px, py, pz, vz, k);
            held(g, f, dt, dust, px, py, pz, vz, k);
            coins(g, dt);
        } else if (menu) {
            resetState(g);
        }
        ambient(g, f, dt, zone, menu);
        overlay(g, f, dt);
        if (stage != null) stage.frame(fx, f, dt);
        fx.draw(f);
        if (g.boardT > 0 && !menu) { fx.draw(f, podL); fx.draw(f, podR); }
        if (g.jetT > 0 && !menu) { fx.draw(f, jetL); fx.draw(f, jetR); }
    }

    private void resetState(Game g) {
        wasGrounded = true; wasRolling = false; lastLane = g.lane; lastState = g.state;
        lastVy = 0; lastShake = 0; lastBoard = lastMag = lastJet = lastSneak = lastX2 = 0;
        seen.clear(); seenPos.clear();
        podL.reset(); podR.reset(); jetL.reset(); jetR.reset();
        started = false;
    }

    // ------------------------------------------------------------------ one-shot events (state diffs)

    private void events(Game g, RenderFrame f, float dt, float[] dust, float px, float py, float pz, float vz, float k) {
        int st = g.state;
        if (!started) { resetState(g); started = true; lastState = st; }
        boolean running = st == Game.RUNNING;
        if (running && lastState == Game.RUNNING) {
            if (wasGrounded && !g.grounded && g.vy > 0) {
                fx.jumpPuff(px, py, pz, g.speed, dust);
                if (g.sneakT > 0) fx.bootsJump(px, py, pz, vz * 0.5f);
            }
            if (!wasGrounded && g.grounded && g.jetT <= 0) {
                float hard = Math.min(1f, Math.max(0f, (-lastVy - 6f) / 30f));
                fx.landDust(px, py, pz, hard, dust);
            }
            if (g.rolling && !wasRolling) fx.jumpPuff(px, py, pz, g.speed * 0.5f, dust);
            if (g.rolling && g.grounded) fx.slideDust(px, py, pz, g.speed, dt, dust);
            if (g.lane != lastLane && g.grounded && g.jetT <= 0) fx.dodgeKick(px, py, pz, Math.signum(g.lane - lastLane), g.speed, dust);
            if (g.shake > lastShake + 0.05f) {
                if (lastBoard > 0 && g.boardT <= 0) fx.boardBreak(px, py, pz);
                else fx.stumble(px, py, pz, g.x > g.lane * Game.LANE_W ? 1f : -1f, g.speed);
            }
        }
        if (st == Game.DYING && lastState == Game.RUNNING) {
            if (g.deathKind == 0) {
                fx.crash(px, py, pz, dust);
                flashT = 0.16f;
                impactT = 0.5f;
            } else {
                fx.landDust(px, py, pz, 0.7f, dust);
                impactT = 0.25f;
            }
        }
        if (st == Game.RUNNING && (lastState == Game.SAVE_ME || lastState == Game.DYING)) fx.revive(px, py, pz);
        // power-ups switching on (or topping up)
        if (running) {
            float hy = py + 0.9f * k;
            if (g.magT > lastMag + 0.5f) fx.powerPickup(px, hy, pz, vz, Fx.GOLD, false);
            if (g.jetT > lastJet + 0.5f) fx.powerPickup(px, hy, pz, vz, Fx.RED, false);
            if (g.sneakT > lastSneak + 0.5f) fx.powerPickup(px, hy, pz, vz, Fx.MINT, false);
            if (g.x2T > lastX2 + 0.5f) fx.powerPickup(px, hy, pz, vz, Fx.GOLD, false);
            if (g.boardT > lastBoard + 0.5f) fx.powerPickup(px, py + 0.3f, pz, vz, Fx.CYAN, false);
        }
        pickupsTaken(g, vz);
        if (st == Game.DYING && g.deathKind == 0) fx.dizzy(f, px, py + 0.55f * k, pz - 0.6f, time);

        wasGrounded = g.grounded;
        wasRolling = g.rolling;
        lastLane = g.lane;
        lastState = st;
        lastVy = g.vy;
        lastShake = g.shake;
        lastBoard = g.boardT; lastMag = g.magT; lastJet = g.jetT; lastSneak = g.sneakT; lastX2 = g.x2T;
    }

    /** Pickups vanish from the list the frame they're taken; one that disappears near Pongo was collected. */
    private void pickupsTaken(Game g, float vz) {
        now.clear();
        for (int i = 0; i < g.pickups.size(); i++) {
            Game.Pickup p = g.pickups.get(i);
            if (!p.taken) now.put(p, Boolean.TRUE);
        }
        for (int i = 0; i < seen.size(); i++) {
            Game.Pickup p = seen.get(i);
            if (now.containsKey(p)) continue;
            float[] q = seenPos.get(i);
            if (q[2] < g.s - 3f || q[2] > g.s + 4f) continue;   // scrolled away behind, not taken
            switch (p.type) {
                case Game.COIN: fx.coinPickup(q[0], q[1], -q[2], vz * 0.6f); break;
                case Game.MYSTERY: fx.powerPickup(q[0], q[1], -q[2], vz * 0.6f, Fx.PINK, true); break;
                case Game.KEY: fx.powerPickup(q[0], q[1], -q[2], vz * 0.6f, Fx.VIOLET, false); break;
                default: break;  // the power-ups burst when their timer starts (events)
            }
        }
        seen.clear();
        int n = 0;
        for (int i = 0; i < g.pickups.size(); i++) {
            Game.Pickup p = g.pickups.get(i);
            if (p.taken || p.s > g.s + 30f || p.s < g.s - 3f) continue;
            seen.add(p);
            float[] q;
            if (seenPos.size() > n) q = seenPos.get(n);
            else { q = new float[3]; seenPos.add(q); }
            q[0] = p.x; q[1] = p.y; q[2] = p.s;
            n++;
        }
    }

    // ------------------------------------------------------------------ held power-ups

    private void held(Game g, RenderFrame f, float dt, float[] dust, float px, float py, float pz, float vz, float k) {
        boolean alive = g.state == Game.RUNNING;
        if (!alive) return;
        if (g.magT > 0) {
            float fade = Math.min(1f, g.magT / 0.6f);
            fx.magnetAura(f, px, py, pz, fade * k);
        }
        if (g.jetT > 0) {
            // thrusters sit on her back, about at the shoulder blades
            float ty = py + 1.0f * k, tz = pz + 0.36f * k;
            fx.rocketThrust(f, px, ty, tz, vz, dt);
            jetL.push(px - 0.16f, ty - 0.55f, tz, fx.time);
            jetR.push(px + 0.16f, ty - 0.55f, tz, fx.time);
        } else { jetL.reset(); jetR.reset(); }
        if (g.sneakT > 0 && g.jetT <= 0) fx.bootsTrail(px, py, pz, dt);
        if (g.x2T > 0) fx.feverAura(f, px, py, pz, dt, Math.min(1f, g.x2T / 0.6f) * k);
        if (g.boardT > 0) {
            float by = py + 0.32f;
            fx.boardHover(f, px, by, pz);
            podL.push(px - 0.18f, by - 0.05f, pz + 0.5f, fx.time);
            podR.push(px + 0.18f, by - 0.05f, pz + 0.5f, fx.time);
        } else { podL.reset(); podR.reset(); }
        if (g.grounded && !g.rolling && g.boardT <= 0) fx.runDust(px, py, pz, g.speed, dt, dust);
    }

    /** Coins glint now and then as they spin; coins pulled by the magnet leave a gold sparkle stream. */
    private void coins(Game g, float dt) {
        glintT -= dt;
        boolean glint = glintT <= 0;
        if (glint) glintT = 0.12f;
        for (int i = 0; i < g.pickups.size(); i++) {
            Game.Pickup p = g.pickups.get(i);
            if (p.type != Game.COIN || p.taken) continue;
            if (p.pulled) fx.magnetStream(p.x, p.y, -p.s, dt);
            else if (glint && p.s > g.s + 4 && p.s < g.s + 60 && fx.rnd() < 0.12f) fx.coinGlint(p.x, p.y, -p.s);
        }
    }

    // ------------------------------------------------------------------ zone ambience

    private void ambient(Game g, RenderFrame f, float dt, int zone, boolean menu) {
        float ps = g.s, vz = menu ? 0 : -g.speed;
        switch (zone) {
            case Zones.SAKURA: {
                // petals drifting down from the trees on both sides, carried across the tracks by the breeze
                for (int n = 0; n < count(dt * 16); n++) {
                    float side = fx.rnd() < 0.5f ? -1 : 1;
                    fx.drifter(Fx.PETAL, side * fx.rnd(2.5f, 10f), fx.rnd(2f, 8f), -(ps + fx.rnd(menu ? -4 : 6, 70)), 0.15f, Fx.WARM_WHITE);
                }
                airFill(g, dt, menu, Fx.WARM_WHITE, 1f);
                if (night > 0.35f) fireflies(g, dt, 4f);
                break;
            }
            case Zones.CAVERN: {
                // a trickle of grit from the vault now and then, and a crystal chime somewhere ahead
                if (fx.rnd() < dt * 0.7f) fx.rockfall(fx.rnd(-4.5f, 4.5f), fx.rnd(4.2f, 5.5f), -(ps + fx.rnd(14, 50)), fx.rnd(0.4f, 0.8f));
                if (fx.rnd() < dt * 0.2f) {
                    float side = fx.rnd() < 0.5f ? -1 : 1;
                    fx.crystalChime(side * fx.rnd(4.4f, 5.4f), fx.rnd(0.8f, 3.5f), -(ps + fx.rnd(10, 40)),
                            fx.rnd() < 0.5f ? Fx.CYAN : Fx.VIOLET);
                }
                break;
            }
            case Zones.RIVER: {
                for (int n = 0; n < count(dt * 10); n++) {
                    float side = fx.rnd() < 0.5f ? -1 : 1;
                    fx.drifter(Fx.LEAF_BAMBOO, side * fx.rnd(2f, 9f), fx.rnd(2f, 7f), -(ps + fx.rnd(6, 60)), 0.2f, Fx.WARM_WHITE);
                }
                if (fx.rnd() < dt * 2.2f) fx.wisp(fx.rnd(-8f, 8f), fx.rnd(0.15f, 0.6f), -(ps + fx.rnd(20, 70)), fx.rnd(1.2f, 2.2f), 0.45f, 0);
                if (fx.rnd() < dt * 0.25f) fx.koiLeap(fx.rnd(-4f, 4f), 0f, -(ps + fx.rnd(18, 40)), 0);
                if (fx.rnd() < dt * 3f) fx.ripple(fx.rnd(-4f, 4f), 0f, -(ps + fx.rnd(4, 40)), fx.rnd(0.6f, 1.2f), 0);
                airFill(g, dt, menu, Fx.MINT, 0.8f);
                if (night > 0.2f) fireflies(g, dt, 8f);
                break;
            }
            case Zones.SKY: {
                if (fx.rnd() < dt * 5f) {
                    float side = fx.rnd() < 0.5f ? -1 : 1;
                    fx.wisp(side * fx.rnd(2.5f, 12f), g.y + fx.rnd(-4f, 4f), -(ps + fx.rnd(25, 80)), fx.rnd(1.6f, 3.4f), 0.8f, -g.speed * 0.15f);
                }
                for (int n = 0; n < count(dt * 18); n++)
                    fx.windStreak(g.x + fx.rnd(-6f, 6f), g.y + fx.rnd(-3f, 4f), -(ps + fx.rnd(6, 30)), vz * 0.6f - 14f, 0.45f);
                break;
            }
            case Zones.ROOFTOPS: {
                for (int n = 0; n < count(dt * 14); n++)
                    fx.windStreak(g.x + fx.rnd(-6f, 6f), fx.rnd(0.3f, 4f), -(ps + fx.rnd(4, 26)), vz * 0.5f - 12f, 0.4f);
                if (fx.rnd() < dt * 1.2f) fx.pantoSparks(fx.rnd(-3f, 3f), 4.6f, -(ps + fx.rnd(8, 30)), g.speed);
                for (int n = 0; n < count(dt * 4); n++) {
                    float side = fx.rnd() < 0.5f ? -1 : 1;
                    fx.drifter(Fx.LEAF_MAPLE, side * fx.rnd(2f, 9f), fx.rnd(1.5f, 6f), -(ps + fx.rnd(6, 50)), 0.17f, Fx.WARM_WHITE);
                }
                break;
            }
            default:
                break;
        }
    }

    /** Pollen motes and the odd dandelion seed hanging in the air on both sides: fills the open space the way
     *  Genshin's scenery does, without drawing the eye. */
    private void airFill(Game g, float dt, boolean menu, float[] c, float k) {
        float ps = g.s;
        for (int n = 0; n < count(dt * 30 * k); n++) {
            float side = fx.rnd() < 0.5f ? -1 : 1;
            fx.pollen(side * fx.rnd(1.5f, 9f), fx.rnd(0.4f, 4.5f), -(ps + fx.rnd(menu ? -2 : 3, 45)), c);
        }
        for (int n = 0; n < count(dt * 2.5f * k); n++)
            fx.seed(fx.rnd(-7f, 7f), fx.rnd(1f, 4f), -(ps + fx.rnd(8, 45)));
    }

    private void fireflies(Game g, float dt, float rate) {
        for (int n = 0; n < count(dt * rate * night); n++) {
            float side = fx.rnd() < 0.5f ? -1 : 1;
            fx.firefly(side * fx.rnd(2.5f, 8f), fx.rnd(0.6f, 3f), -(g.s + fx.rnd(4, 40)));
        }
    }

    private int count(float c) {
        int k = (int) c;
        return k + (fx.rnd() < c - k ? 1 : 0);
    }

    // ------------------------------------------------------------------ screen overlay

    /** Anime speed lines at high speed and on the rocket, and the white impact frame with radial lines on a crash. */
    private void overlay(Game g, RenderFrame f, float dt) {
        float sp = 0f;
        if (g.state == Game.RUNNING) {
            sp = Math.max(0f, (g.speed - 23f) / 8f) * 0.55f;
            if (g.jetT > 0) sp = Math.max(sp, 0.75f);
            if (g.boardT > 0) sp = Math.max(sp, 0.25f);
        }
        if (impactT > 0) {
            impactT = Math.max(0, impactT - dt);
            sp = Math.max(sp, 1.2f * impactT / 0.5f);
        }
        f.speed[0] = Math.min(1.2f, sp);
        f.speed[1] = time;
        f.speed[3] = 3.7f;
        if (flashT > 0) {
            flashT = Math.max(0, flashT - dt);
            float a = flashT / 0.16f;
            f.flash[0] = 1f; f.flash[1] = 0.98f; f.flash[2] = 0.94f;
            f.flash[3] = 0.85f * a * a;
        } else {
            f.flash[3] = 0;
        }
    }
}
