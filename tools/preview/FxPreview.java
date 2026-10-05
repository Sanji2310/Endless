import android.content.res.AssetManager;
import android.opengl.GLES20;
import com.endlessrush.app.GameRenderer;
import com.endlessrush.core.*;
import com.pongo.core.Fx;
import com.pongo.core.RenderFrame;
import com.pongo.core.Zones;

import java.io.*;

/**
 * Effect showcase clips through the real Android renderers (same recording path as PongoPreview): every effect in
 * FxLayer / Fx, staged in short scenes. Each scene is a numbered frame sequence (<scene>_000.png ...) that
 * tools/fx_clips.sh turns into MP4 and GIF clips.
 *
 * Usage: java FxPreview <gles.bin out> <width> <height> <scene>[,<scene>...]
 *   scenes: run, coins, magnet, fever, boots, rocket, board, crash, cave, river, sky, rooftops, all
 * The river and sky scenes have no kit in the game yet: they stage the effects over the Sakura Line world (the river
 * gets a flat water sheet so the splashes have something to land on).
 */
public class FxPreview {
    static GameRenderer renderer;
    static Game game;
    static FxLayer fxl;
    static final Preview.Autopilot ai = new Preview.Autopilot();
    static final float DT = 1 / 60f;
    static int frame;

    public static void main(String[] a) throws Exception {
        int w = Integer.parseInt(a[1]), h = Integer.parseInt(a[2]);
        Models.build();
        Profile prof = new Profile(null);
        prof.boards = 5;
        prof.keys = 9;
        game = new Game(prof, null);
        Scene scene = new Scene();
        renderer = new GameRenderer(game, scene, null, new AssetManager(new File(System.getProperty("pongo.assets", "assets"))));
        renderer.onSurfaceCreated(null, null);
        renderer.onSurfaceChanged(null, w, h);
        fxl = renderer.fxLayer();
        if (fxl == null) throw new IllegalStateException("pongo.bin has no fx sprites (tools/build_assets.sh)");
        String list = a.length > 3 ? a[3] : "all";
        if (list.equals("all")) list = "run,coins,magnet,fever,boots,rocket,board,crash,cave,river,sky,rooftops";
        for (String s : list.split(",")) {
            reset();
            suffix = "";
            renderer.cameraHook = null;
            hideWorld = s.startsWith("river") || s.startsWith("sky");
            if (hideWorld) renderer.cameraHook = (dl, g) -> dl.count = 0;   // staged zones: no Sakura Line world
            if (s.endsWith("_side")) {
                // a three-quarter view from beside and a little ahead of her, close in
                s = s.substring(0, s.length() - 5);
                suffix = "_side";
                final float aspect = w / (float) h;
                final boolean hw = hideWorld;
                renderer.cameraHook = (dl, g) -> {
                    if (hw) dl.count = 0;
                    float tx = g.x, ty = g.y + 1.0f, tz = -g.s - 0.6f;
                    float ex = tx + 3.8f, ey = ty + 0.9f, ez = tz - 3.2f;
                    com.endlessrush.core.Mat4.lookAt(dl.view, ex, ey, ez, tx, ty, tz + 0.8f, 0, 1, 0);
                    com.endlessrush.core.Mat4.perspective(dl.proj, 50f, aspect, 0.1f, 300f);
                    com.endlessrush.core.Mat4.mul(dl.viewProj, dl.proj, dl.view);
                    dl.camPos[0] = ex; dl.camPos[1] = ey; dl.camPos[2] = ez;
                };
            }
            switch (s) {
                case "run": run(); break;
                case "coins": coins(); break;
                case "magnet": magnet(); break;
                case "fever": fever(); break;
                case "boots": boots(); break;
                case "rocket": rocket(); break;
                case "board": board(); break;
                case "crash": crash(); break;
                case "cave": cave(); break;
                case "river": river(); break;
                case "sky": sky(); break;
                case "rooftops": rooftops(); break;
                default: throw new IllegalArgumentException(s);
            }
        }
        try (OutputStream os = new BufferedOutputStream(new FileOutputStream(a[0]))) { GLES20.save(os); }
        System.out.println("recorded " + new File(a[0]).length() / 1024 + " KB of GL commands");
    }

    static void reset() {
        game.toMenu();
        fxl.zoneOverride = -1;
        fxl.stage = null;
        fxl.night = 0;
        fxl.fx().clear();
        game.start();
        // a fixed zone plan so every render lands in the same zones (the first zone is always the Sakura Line)
        Zones.newRun(42L);
        game.zones.reset();
        game.guardGap = 30;   // the chaser starts on her heels; these clips are about the effects
    }

    /** Runs without obstacles for n frames (muted), or records them (every second frame -> 30 fps clips). */
    static void step(int n, String clip, Runnable each) {
        for (int i = 0; i < n; i++) {
            game.obstacles.clear();
            noChaser();
            if (each != null) each.run();
            game.update(DT);
            boolean rec = clip != null && (i % 2 == 0);
            boolean keep = rec && inPart(frame);
            GLES20.drawing = keep;
            renderer.drawFrame(DT);
            if (keep) GLES20.present(String.format("%s_%03d", clip, frame));
            if (rec) frame++;
        }
    }

    /** The chaser starts on her heels and closes in on a crash; these clips are about the effects. */
    static void noChaser() { game.chaseT = 0; game.guardGap = 30; }

    static String suffix = "";
    /** -Dfx.part=k records only clip frames [k*PART, (k+1)*PART): a whole clip in one stream can be too much for
     *  one headless page. -1 = all. */
    static final int PART = 36, part = Integer.getInteger("fx.part", -1);

    static boolean inPart(int fr) { return part < 0 || (fr >= part * PART && fr < (part + 1) * PART); }
    static boolean hideWorld;

    static void clip(String name, int n, Runnable each) { frame = 0; step(n, name + suffix, each); }

    static void warm(int n) { step(n, null, null); }

    static void coinLine(float s0, int n, int lane, float y) {
        for (int i = 0; i < n; i++) {
            Game.Pickup p = new Game.Pickup();
            p.type = Game.COIN; p.x = lane * Game.LANE_W; p.y = y; p.s = s0 + i * 2.6f;
            game.pickups.add(p);
        }
    }

    static void pickup(int type, float ahead) {
        Game.Pickup p = new Game.Pickup();
        p.type = type; p.x = game.x; p.y = 0.9f; p.s = game.s + ahead;
        game.pickups.add(p);
    }

    // ------------------------------------------------------------------ scenes

    /** Sakura Line run: petals, a lane change kick, a jump and a landing, a slide. */
    static void run() {
        game.s = 300; warm(60);
        final int[] t = {0};
        clip("run", 200, () -> {
            int k = t[0]++;
            if (k == 20) game.left();
            if (k == 60) game.jump();
            if (k == 120) game.right();
            if (k == 150) game.roll();
        });
    }

    /** A line of coins: glints, pickup starbursts. */
    static void coins() {
        game.s = 500; game.pickups.clear(); warm(30);
        coinLine(game.s + 14, 10, game.lane, 0.9f);
        final int[] t = {0};
        clip("coins", 120, () -> { if (t[0]++ == 70) game.jump(); });
    }

    /** Maneki Magnet: pickup burst, swirl at her feet, coins streaming in from both lanes. */
    static void magnet() {
        game.s = 700; game.pickups.clear(); warm(30);
        pickup(Game.MAGNET, 6);
        coinLine(game.s + 20, 8, -1, 0.9f);
        coinLine(game.s + 22, 8, 1, 0.9f);
        coinLine(game.s + 30, 6, 0, 2.2f);
        clip("magnet", 130, null);
    }

    static void fever() {
        game.s = 900; game.pickups.clear(); warm(30);
        pickup(Game.X2, 6);
        coinLine(game.s + 24, 6, 0, 0.9f);
        clip("fever", 110, null);
    }

    /** Tobi Boots: wind rings at take-off, heel sparkles. */
    static void boots() {
        game.s = 300; game.pickups.clear(); warm(30);
        pickup(Game.SNEAKERS, 5);
        final int[] t = {0};
        clip("boots", 140, () -> { int k = t[0]++; if (k == 30 || k == 100) game.jump(); });
    }

    /** Hayate Rocket: ignition burst, wind-swirl flames, smoke and flame ribbons, speed lines. */
    static void rocket() {
        game.s = 500; game.pickups.clear(); warm(30);
        pickup(Game.JETPACK, 5);
        clip("rocket", 140, null);
    }

    /** Kaze Board: summon burst, hover glows and ribbons, then the board breaks on a crash. */
    static void board() {
        game.s = 700; game.pickups.clear(); warm(30);
        game.hoverboard();
        final int[] t = {0};
        clip("board", 130, () -> {
            int k = t[0]++;
            if (k == 40) game.left();
            if (k == 95) {
                // a barrier right ahead: the board takes the hit
                Game.Obstacle o = new Game.Obstacle();
                o.type = Game.BLOCK; o.lane = game.lane; o.s0 = game.s + 1.2f; o.len = 1f; o.x = game.lane * Game.LANE_W;
                game.obstacles.add(o);
            }
        });
    }

    /** Crash: impact frame, debris, dizzy stars. */
    static void crash() {
        game.s = 900; game.pickups.clear(); warm(40);
        final int[] t = {0};
        frame = 0;
        for (int i = 0; i < 130; i++) {
            int k = t[0]++;
            if (k < 30) game.obstacles.clear();
            noChaser();
            if (k == 30) {
                Game.Obstacle o = new Game.Obstacle();
                o.type = Game.BLOCK; o.lane = game.lane; o.s0 = game.s + 2.5f; o.len = 1f; o.x = game.lane * Game.LANE_W;
                game.obstacles.add(o);
            }
            game.update(DT);
            boolean rec = i % 2 == 0;
            boolean keep = rec && inPart(frame);
            GLES20.drawing = keep;
            renderer.drawFrame(DT);
            if (keep) GLES20.present(String.format("crash%s_%03d", suffix, frame));
            if (rec) frame++;
        }
    }

    /** Crystal Cavern: rock dust trickles, crystal chimes, cart wheel sparks on a switch, a landing in cave dust. */
    static void cave() {
        int zi = 1;
        while (Zones.zoneOf(zi) != Zones.CAVERN) zi++;
        float b = Zones.boundary(zi);
        game.s = b + 40; warm(90);
        final int[] t = {0};
        fxl.stage = (fx, f, dt) -> {
            int k = t[0];
            if (k % 24 == 0) fx.cartSparks(game.x, game.y, -game.s - 0.2f, 0.9f, game.speed);
            if (k == 50) fx.rockfall(game.x + 1.5f, 5f, -game.s - 9f, 1.2f);
        };
        clip("cave", 140, () -> { int k = t[0]++; if (k == 80) game.jump(); });
    }

    /** Bamboo River (staged on a water sheet): bow spray, foam wake, paddle splashes, a croc's snap, a koi, ripples,
     *  drifting bamboo leaves and low mist. */
    static void river() {
        game.s = 300; game.pickups.clear(); warm(30);
        fxl.zoneOverride = Zones.RIVER;
        final int[] t = {0};
        final float wy = 0.22f;
        fxl.stage = (fx, f, dt) -> {
            int k = t[0];
            water(fx, f, wy);
            float bz = -game.s;
            fx.boatSpray(game.x, wy, bz, game.speed, (float) Math.sin(k * 0.05f), dt);
            if (k % 26 == 0) fx.paddleSplash(game.x + ((k / 26) % 2 == 0 ? -0.75f : 0.75f), wy, bz + 0.2f, -game.speed * 0.9f);
            if (k == 60) fx.splash(game.x + 2.6f, wy, bz - 10f, 2f, 0);
            if (k == 100) fx.koiLeap(game.x - 2.4f, wy, bz - 12f, 0);
            if (k % 8 == 0) fx.ripple(game.x + fx.rnd(-4f, 4f), wy, bz - fx.rnd(4f, 25f), fx.rnd(0.6f, 1.2f), 0);
        };
        clip("river", 160, () -> {
            int k = t[0]++;
            game.y = 0; game.grounded = true;
            if (k == 40) game.left();
            if (k == 110) game.right();
        });
    }

    /** A flat water sheet for the staged river: one big alpha quad in river blue, paler toward the camera. */
    static void water(Fx fx, RenderFrame f, float wy) {
        float z0 = -game.s + 8;
        int deep = RenderFrame.packColor(0.4f, 0.68f, 0.86f, 0.97f), near = RenderFrame.packColor(0.6f, 0.85f, 0.95f, 0.97f);
        f.quadPts(false, -40, wy - 0.02f, z0, 40, wy - 0.02f, z0, 40, wy - 0.02f, z0 - 190, -40, wy - 0.02f, z0 - 190,
                fx.whiteUv(), near, deep);
    }

    /** Sky Glide (staged): Pongo on the rocket high above, wisps and wind streaks rushing past, a gust, a crow's
     *  feathers, a thermal column and wingtip ribbons. */
    static void sky() {
        game.s = 300; game.pickups.clear(); warm(10);
        pickup(Game.JETPACK, 3);
        warm(120);
        fxl.zoneOverride = Zones.SKY;
        final int[] t = {0};
        final Fx.Trail tipL = new Fx.Trail(28, 0.05f, 0.6f).color(Fx.WARM_WHITE, 0.8f);
        final Fx.Trail tipR = new Fx.Trail(28, 0.05f, 0.6f).color(Fx.WARM_WHITE, 0.8f);
        fxl.stage = (fx, f, dt) -> {
            int k = t[0];
            float pz = -game.s, py = game.y + 2.3f;
            tipL.push(game.x - 1.6f, py, pz + 0.2f, fx.time);
            tipR.push(game.x + 1.6f, py, pz + 0.2f, fx.time);
            fx.draw(f, tipL);
            fx.draw(f, tipR);
            if (k == 30) fx.gust(game.x + 3f, game.y + 1f, pz - 8f, -1f, 1.2f);
            if (k == 70) fx.feathers(game.x - 1.5f, game.y + 2f, pz - 6f, 10);
            if (k > 80) fx.thermal(game.x + 3.5f, game.y + 1f, pz - 14f, dt);
            if (k == 120) fx.cloudBurst(game.x, game.y + 1f, pz - 3f, -game.speed * 0.3f);
        };
        clip("sky", 160, () -> t[0]++);
    }

    /** Express Rooftops (staged over the Sakura Line): wind streaks, pantograph sparks, maple leaves. */
    static void rooftops() {
        game.s = 300; game.pickups.clear(); warm(30);
        fxl.zoneOverride = Zones.ROOFTOPS;
        final int[] t = {0};
        clip("rooftops", 120, () -> { int k = t[0]++; if (k == 50) game.jump(); });
    }
}
