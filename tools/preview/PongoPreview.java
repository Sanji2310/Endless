import android.content.res.AssetManager;
import android.opengl.GLES20;
import com.endlessrush.app.GameRenderer;
import com.endlessrush.core.*;

import java.io.*;

/**
 * Runs the real Android renderers (GameRenderer with the Pongo toon layer) on the desktop: GL calls are recorded
 * by the GLES20 stand-in in tools/preview/stubs and replayed in headless Chromium by tools/web/replay.mjs.
 * Usage: java PongoPreview <gles.bin out> [width height] [zones]
 *   zones: a run through the Sakura Line -> Crystal Cavern tunnel, the cavern and the way back out (zone_*.png)
 *   -Dpongo.assets=<dir> loads pongo.bin from another folder than assets/ (e.g. a local build in build/)
 */
public class PongoPreview {
    static GameRenderer renderer;
    static Game game;
    static final Preview.Autopilot ai = new Preview.Autopilot();
    static final float DT = 1 / 60f;
    static final int SETTLE = 30; // frames drawn (muted) before each shot so the camera and clips settle

    public static void main(String[] a) throws Exception {
        int w = a.length > 2 ? Integer.parseInt(a[1]) : 540, h = a.length > 2 ? Integer.parseInt(a[2]) : 960;
        Profile prof = new Profile(null);
        prof.boards = 5;
        game = new Game(prof, null);
        Scene scene = new Scene();
        renderer = new GameRenderer(game, scene, null, new AssetManager(new File(System.getProperty("pongo.assets", "assets"))));
        renderer.onSurfaceCreated(null, null);
        renderer.onSurfaceChanged(null, w, h);
        if (!scene.toonHero) throw new IllegalStateException("toon layer did not start (is assets/pongo.bin built?)");
        if (a.length > 3 && a[3].equals("zones")) {
            if (!scene.toonWorld) throw new IllegalStateException("pongo.bin has no zone pieces (tools/build_assets.sh)");
            zones();
            try (OutputStream os = new BufferedOutputStream(new FileOutputStream(a[0]))) { GLES20.save(os); }
            System.out.println("recorded " + new File(a[0]).length() / 1024 + " KB of GL commands");
            return;
        }

        sim(30, false);
        shot("pongo_01_menu");
        game.start();
        sim(60 * 14, true);
        shot("pongo_02_run");
        sim(60 * 6, true);
        shot("pongo_03_run");
        game.jump();
        sim(9, false);
        shot("pongo_04_jump");
        sim(14, false);
        shot("pongo_05_fall");
        sim(60, true);
        game.roll();
        sim(14, false);
        shot("pongo_06_slide");
        game.hoverboard();
        sim(40, true);
        shot("pongo_07_board");
        Game.Pickup jp = new Game.Pickup();
        jp.type = Game.JETPACK; jp.x = game.x; jp.y = game.y + 0.9f; jp.s = game.s + 2;
        game.pickups.add(jp);
        sim(90, true);
        shot("pongo_08_jetpack");
        try (OutputStream os = new BufferedOutputStream(new FileOutputStream(a[0]))) { GLES20.save(os); }
        System.out.println("recorded " + new File(a[0]).length() / 1024 + " KB of GL commands");
    }

    /** Sakura Line -> tunnel -> Crystal Cavern -> back out. Obstacles are cleared every frame: the cave's own
     *  obstacles belong to the vehicle side, and these shots are about the set piece and the cavern. */
    static void zones() {
        game.start();                                   // lays out this run's zones: Sakura Line, then the cavern
        float b = com.pongo.core.Zones.boundary(1), b2 = com.pongo.core.Zones.boundary(2);
        game.s = b - 110;
        runTo(b - 80); shot("zone_01_approach");
        runTo(b - 36); shot("zone_02_portal");
        runTo(b - 12); shot("zone_03_tunnel");
        runTo(b + 3); shot("zone_04_mouth");
        runTo(b + 30); shot("zone_05_cavern");
        runTo(b + 54); shot("zone_06_parting");
        runTo(b + 400); shot("zone_07_deep");
        game.s = b2 - 90;
        runTo(b2 - 32); shot("zone_08_way_out");
        runTo(b2 + 6); shot("zone_09_daylight");
    }

    /** Runs (no obstacles, invulnerable) until distance s; the last SETTLE frames are drawn muted. */
    static void runTo(float s) {
        int n = 0;
        while (game.s < s) {
            game.obstacles.clear();
            game.invulnT = 1f;
            ai.drive(game);
            game.update(DT);
            n++;
            if (game.s + game.speed * DT * SETTLE >= s) {
                GLES20.drawing = false;
                renderer.drawFrame(DT);
            }
        }
    }

    /** Advances the game; only the last SETTLE frames are drawn (without draw calls) to keep the stream short. */
    static void sim(int frames, boolean autopilot) {
        for (int i = 0; i < frames; i++) {
            if (autopilot) ai.drive(game);
            game.update(DT);
            if (i >= frames - SETTLE) {
                GLES20.drawing = false;
                renderer.drawFrame(DT);
            }
        }
    }

    static void shot(String name) {
        GLES20.drawing = true;
        game.update(DT);
        renderer.drawFrame(DT);
        GLES20.present(name);
        stats(renderer, name);
    }

    /** Draw calls and triangles in the shot's frame (the colour pass; outlines and shadows draw subsets again). */
    static void stats(GameRenderer r, String name) {
        com.pongo.core.RenderFrame f = r.frame();
        com.pongo.core.PongoAssets as = r.assets();
        long tris = 0, chunks = 0;
        for (int d = 0; d < f.count; d++) {
            com.pongo.core.PongoAssets.Mesh me = as.meshes[f.mesh[d]];
            for (com.pongo.core.PongoAssets.Part p : me.parts)
                for (com.pongo.core.PongoAssets.Chunk c : p.chunks) { tris += c.nIdx / 3; chunks++; }
        }
        System.out.printf("%-20s draws %4d  chunks %5d  tris %8d  quads %4d%n", name, f.count, chunks, tris,
                f.alphaCount + f.addCount);
        if (Boolean.getBoolean("pongo.stats")) {
            java.util.Map<String, long[]> by = new java.util.TreeMap<String, long[]>();
            for (int d = 0; d < f.count; d++) {
                com.pongo.core.PongoAssets.Mesh me = as.meshes[f.mesh[d]];
                long[] v = by.get(me.name);
                if (v == null) by.put(me.name, v = new long[2]);
                v[0]++;
                for (com.pongo.core.PongoAssets.Part p : me.parts) for (com.pongo.core.PongoAssets.Chunk c : p.chunks) v[1] += c.nIdx / 3;
            }
            java.util.List<java.util.Map.Entry<String, long[]>> l = new java.util.ArrayList<java.util.Map.Entry<String, long[]>>(by.entrySet());
            java.util.Collections.sort(l, new java.util.Comparator<java.util.Map.Entry<String, long[]>>() {
                public int compare(java.util.Map.Entry<String, long[]> x, java.util.Map.Entry<String, long[]> y) { return Long.compare(y.getValue()[1], x.getValue()[1]); }
            });
            for (int i = 0; i < Math.min(18, l.size()); i++)
                System.out.printf("    %-22s x%-3d %8d%n", l.get(i).getKey(), l.get(i).getValue()[0], l.get(i).getValue()[1]);
        }
    }
}
