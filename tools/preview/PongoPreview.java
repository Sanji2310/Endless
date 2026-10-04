import android.content.res.AssetManager;
import android.opengl.GLES20;
import com.endlessrush.app.GameRenderer;
import com.endlessrush.core.*;

import java.io.*;

/**
 * Runs the real Android renderers (GameRenderer with the Pongo toon layer) on the desktop: GL calls are recorded
 * by the GLES20 stand-in in tools/preview/stubs and replayed in headless Chromium by tools/web/replay.mjs.
 * Usage: java PongoPreview <gles.bin out> [width height]
 */
public class PongoPreview {
    static GameRenderer renderer;
    static Game game;
    static final Preview.Autopilot ai = new Preview.Autopilot();
    static final float DT = 1 / 60f;
    static final int SETTLE = 30; // frames drawn (muted) before each shot so the camera and clips settle

    public static void main(String[] a) throws Exception {
        int w = a.length > 2 ? Integer.parseInt(a[1]) : 540, h = a.length > 2 ? Integer.parseInt(a[2]) : 960;
        Models.build();
        Profile prof = new Profile(null);
        prof.boards = 5;
        game = new Game(prof, null);
        Scene scene = new Scene();
        renderer = new GameRenderer(game, scene, null, new AssetManager(new File("assets")));
        renderer.onSurfaceCreated(null, null);
        renderer.onSurfaceChanged(null, w, h);
        if (!scene.toonHero) throw new IllegalStateException("toon layer did not start (is assets/pongo.bin built?)");

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
    }
}
