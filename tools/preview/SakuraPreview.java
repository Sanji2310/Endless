import android.content.res.AssetManager;
import android.opengl.GLES20;
import com.endlessrush.app.GameRenderer;
import com.endlessrush.core.*;

import java.io.*;

/**
 * In-game stills of the Sakura Line art (SakuraWorld): the line with its gardens, trains and track obstacles,
 * every power-up on the track and in use, and Inspector Daigo with Kuro on Pongo's heels. Runs the real
 * GameRenderer; GL calls are recorded by the GLES20 stand-in and replayed in Chromium by tools/web/replay.mjs.
 * Usage: java -Dpongo.assets=<dir> SakuraPreview <gles.bin out> [width height]
 */
public class SakuraPreview {
    static GameRenderer renderer;
    static Game game;
    static final Preview.Autopilot ai = new Preview.Autopilot();
    static final float DT = 1 / 60f;
    static final int SETTLE = 30;

    public static void main(String[] a) throws Exception {
        int w = a.length > 2 ? Integer.parseInt(a[1]) : 540, h = a.length > 2 ? Integer.parseInt(a[2]) : 960;
        Profile prof = new Profile(null);
        prof.boards = 5;
        game = new Game(prof, null);
        Scene scene = new Scene();
        renderer = new GameRenderer(game, scene, null, new AssetManager(new File(System.getProperty("pongo.assets", "assets"))));
        renderer.onSurfaceCreated(null, null);
        renderer.onSurfaceChanged(null, w, h);
        if (!scene.toonHero) throw new IllegalStateException("toon layer did not start (is pongo.bin built?)");

        // the title screen: the camera in front of Pongo looking back down the line
        for (int i = 0; i < SETTLE; i++) {
            game.update(DT);
            GLES20.drawing = false;
            renderer.drawFrame(DT);
        }
        shot("sakura_00_menu");

        // mid-block (level crossings are every 360 m from s = 108), from the right lane to see more of that side
        game.start();
        game.s = 150;
        game.right();
        clearRun(60 * 4);
        shot("sakura_01_line");

        // the level crossing coming up
        clear();
        game.left();
        game.s = 108 + 360 - 34;
        clearRun(40);
        shot("sakura_02_crossing");

        // a parked commuter on the left, an express coming down the right, a ramp up onto a train in the middle
        game.s = 540;
        clearRun(SETTLE);
        clear();
        train(-1, 30, 2, false, 0);
        train(1, 70, 2, true, 1);
        obstacle(Game.RAMP, 0, 16, Game.RAMP_LEN);
        train(0, 16 + Game.RAMP_LEN, 2, false, 1);
        hold(20);
        shot("sakura_03_trains");

        // the track obstacles: low barricade (jump), slide gantry (roll), works block (change lanes)
        clear();
        obstacle(Game.LOW, -1, 8, 1.5f);
        obstacle(Game.HIGH, 0, 13, 1.5f);
        obstacle(Game.BLOCK, 1, 10, 3f);
        hold(4);
        shot("sakura_04_obstacles");

        // every power-up on the track
        clear();
        int[] types = {Game.MAGNET, Game.JETPACK, Game.SNEAKERS, Game.X2, Game.MYSTERY, Game.KEY};
        for (int i = 0; i < types.length; i++) pickup(types[i], (i % 3) - 1, 5 + (i / 3) * 4.5f);
        hold(2);
        shot("sakura_05_powerups");

        clear();
        game.magT = game.magMax = 10;
        clearRun(50);
        shot("sakura_06_magnet");

        clear();
        game.magT = 0;
        game.x2T = game.x2Max = 10;
        game.sneakT = game.sneakMax = 10;
        clearRun(40);
        game.jump();
        hold(12);
        shot("sakura_07_x2_sneakers");

        clear();
        game.x2T = game.sneakT = 0;
        game.hoverboard();
        clearRun(50);
        shot("sakura_08_board");

        clear();
        game.boardT = 0;
        game.jetT = game.jetMax = 6;
        clearRun(90);
        shot("sakura_09_rocket");

        // Daigo and Kuro right behind her
        clear();
        game.jetT = 0;
        clearRun(120);
        game.guardGap = 2.4f;
        game.chaseT = 3f;
        hold(1);
        shot("sakura_10_chase");

        // -Dsakura.clip=true: two seconds of the chase as the player sees it (clip_chase_00..59, 30 fps)
        if (Boolean.getBoolean("sakura.clip")) {
            for (int i = 0; i < 60; i++) {
                for (int k = 0; k < 2; k++) {
                    game.obstacles.clear();
                    game.invulnT = 1f;
                    game.chaseT = 3f;
                    game.guardGap = 2.4f;
                    game.update(DT);
                    if (k == 0) {
                        GLES20.drawing = false;
                        renderer.drawFrame(DT);
                    }
                }
                shot(String.format("clip_chase_%02d", i));
            }
        }

        try (OutputStream os = new BufferedOutputStream(new FileOutputStream(a[0]))) { GLES20.save(os); }
        System.out.println("recorded " + new File(a[0]).length() / 1024 + " KB of GL commands");
    }

    static void clear() {
        game.obstacles.clear();
        game.pickups.clear();
    }

    static void train(int lane, float ahead, int cars, boolean moving, int variant) {
        Game.Obstacle o = obstacle(Game.TRAIN, lane, ahead, cars * Game.CAR_LEN);
        o.cars = cars;
        o.moving = moving;
        o.variant = variant;
    }

    static Game.Obstacle obstacle(int type, int lane, float ahead, float len) {
        Game.Obstacle o = new Game.Obstacle();
        o.type = type;
        o.lane = lane;
        o.x = lane * Game.LANE_W;
        o.s0 = o.prevS0 = game.s + ahead;
        o.len = len;
        o.cars = 1;
        game.obstacles.add(o);
        return o;
    }

    static void pickup(int type, int lane, float ahead) {
        Game.Pickup p = new Game.Pickup();
        p.type = type;
        p.x = lane * Game.LANE_W;
        p.y = 1.0f;
        p.s = game.s + ahead;
        game.pickups.add(p);
    }

    /** Runs with nothing on the track (invulnerable); the last SETTLE frames are drawn muted. */
    static void clearRun(int frames) {
        for (int i = 0; i < frames; i++) {
            game.obstacles.clear();
            game.invulnT = 1f;
            game.update(DT);
            if (i >= frames - SETTLE) {
                GLES20.drawing = false;
                renderer.drawFrame(DT);
            }
        }
    }

    /** Draws a few frames without advancing the run, so scripted obstacles stay where they were put. */
    static void hold(int frames) {
        for (int i = 0; i < frames; i++) {
            float s = game.s;
            game.invulnT = 1f;
            game.update(DT);
            game.s = s;
            GLES20.drawing = false;
            renderer.drawFrame(DT);
        }
    }

    static void shot(String name) {
        GLES20.drawing = true;
        renderer.drawFrame(DT);
        GLES20.present(name);
        PongoPreview.stats(renderer, name);
        for (String pr : System.getProperty("probe", "").split(";")) {
            String[] kv = pr.split(":");
            if (kv.length == 2 && kv[0].equals(name)) {
                String[] xy = kv[1].split(",");
                probe(Float.parseFloat(xy[0]), Float.parseFloat(xy[1]));
            }
        }
    }

    /** Debug: lists the draws whose bounding box covers screen pixel (px, py) of a 540 x 960 shot, nearest first. */
    static void probe(float px, float py) {
        com.pongo.core.RenderFrame f = renderer.frame();
        com.pongo.core.PongoAssets as = renderer.assets();
        float nx = px / 540f * 2 - 1, ny = 1 - py / 960f * 2;
        java.util.List<String> hits = new java.util.ArrayList<String>();
        for (int d = 0; d < f.count; d++) {
            com.pongo.core.PongoAssets.Mesh me = as.meshes[f.mesh[d]];
            float[] m = f.model[d];
            float x0 = 9, x1 = -9, y0 = 9, y1 = -9;
            boolean behind = false;
            float cx = 0, cy = 0, cz = 0;
            for (int c = 0; c < 8; c++) {
                float lx = (c & 1) == 0 ? me.bmin[0] : me.bmax[0], ly = (c & 2) == 0 ? me.bmin[1] : me.bmax[1], lz = (c & 4) == 0 ? me.bmin[2] : me.bmax[2];
                float wx = m[0] * lx + m[4] * ly + m[8] * lz + m[12], wy = m[1] * lx + m[5] * ly + m[9] * lz + m[13], wz = m[2] * lx + m[6] * ly + m[10] * lz + m[14];
                cx += wx / 8; cy += wy / 8; cz += wz / 8;
                float[] v = f.viewProj;
                float X = v[0] * wx + v[4] * wy + v[8] * wz + v[12], Y = v[1] * wx + v[5] * wy + v[9] * wz + v[13], W = v[3] * wx + v[7] * wy + v[11] * wz + v[15];
                if (W < 0.05f) { behind = true; continue; }
                x0 = Math.min(x0, X / W); x1 = Math.max(x1, X / W); y0 = Math.min(y0, Y / W); y1 = Math.max(y1, Y / W);
            }
            if (behind || (nx >= x0 && nx <= x1 && ny >= y0 && ny <= y1)) {
                float dx = cx - f.camPos[0], dy = cy - f.camPos[1], dz = cz - f.camPos[2];
                hits.add(String.format("%7.1f  %-22s flags %2d %s centre (%.1f %.1f %.1f)", Math.sqrt(dx * dx + dy * dy + dz * dz),
                        me.name, f.flags[d], behind ? "[crosses camera]" : "", cx, cy, cz));
            }
        }
        java.util.Collections.sort(hits);
        System.out.println("  probe " + px + "," + py + " cam (" + f.camPos[0] + " " + f.camPos[1] + " " + f.camPos[2] + ")");
        for (String h : hits) System.out.println("    " + h);
    }
}
