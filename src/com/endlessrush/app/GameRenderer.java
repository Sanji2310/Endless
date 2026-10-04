package com.endlessrush.app;

import android.content.res.AssetManager;
import android.opengl.GLES20;
import android.opengl.GLSurfaceView;
import android.os.SystemClock;
import android.util.Log;

import com.endlessrush.core.DrawList;
import com.endlessrush.core.Game;
import com.endlessrush.core.PongoScene;
import com.endlessrush.core.SakuraWorld;
import com.endlessrush.core.Scene;
import com.endlessrush.core.ZoneWorld;
import com.pongo.app.GLRenderer;
import com.pongo.core.PongoAssets;
import com.pongo.core.RenderFrame;

import java.io.BufferedInputStream;
import java.io.InputStream;

import java.util.concurrent.ConcurrentLinkedQueue;

import javax.microedition.khronos.egl.EGLConfig;
import javax.microedition.khronos.opengles.GL10;

/**
 * OpenGL ES 2.0 renderer; also drives the simulation on the GL thread.
 * Everything on screen goes through the toon renderer (com.pongo) from assets/pongo.bin: Scene sets the camera,
 * PongoScene draws Pongo and the Mon coins, ZoneWorld the tunnel and the Crystal Cavern, and SakuraWorld the
 * Sakura Line, trains, barriers, power-ups, chasers and effects. Without pongo.bin only the sky colour is cleared.
 */
public final class GameRenderer implements GLSurfaceView.Renderer {
    public interface Hud { void onFrame(Game game); }

    private final Game game;
    private final Scene scene;
    private final DrawList dl = new DrawList();
    private final ConcurrentLinkedQueue<Runnable> queue = new ConcurrentLinkedQueue<Runnable>();
    private final Hud hud;
    private final AssetManager assetManager;
    private PongoAssets pongoAssets;
    private boolean pongoTried;
    private PongoScene pongo;
    private ZoneWorld zoneWorld;
    private SakuraWorld sakuraWorld;
    private GLRenderer toon;
    private final RenderFrame frame = new RenderFrame();
    private int width = 1, height = 1;
    private long last;

    public GameRenderer(Game game, Scene scene, Hud hud, AssetManager assets) {
        this.game = game;
        this.scene = scene;
        this.hud = hud;
        this.assetManager = assets;
    }

    /** The toon frame last built (the desktop preview reads its draw counts). */
    public RenderFrame frame() { return frame; }

    /** The toon assets, or null when pongo.bin did not load. */
    public PongoAssets assets() { return pongoAssets; }

    /** Runs r on the GL thread before the next frame (all game mutations go through here). */
    public void post(Runnable r) { queue.add(r); }

    @Override
    public void onSurfaceCreated(GL10 unused, EGLConfig config) {
        GLES20.glClearColor(0.86f, 0.93f, 1.0f, 1);
        setupToon();
        last = SystemClock.elapsedRealtime();
    }

    /** Loads assets/pongo.bin once and (re)builds the toon renderer's GL objects for this context. */
    private void setupToon() {
        if (!pongoTried) {
            pongoTried = true;
            InputStream in = null;
            try {
                in = new BufferedInputStream(assetManager.open("pongo.bin"), 1 << 16);
                pongoAssets = PongoAssets.load(in, true);
                pongo = new PongoScene(pongoAssets);
                if (ZoneWorld.available(pongoAssets)) zoneWorld = new ZoneWorld(pongoAssets);
                if (SakuraWorld.available(pongoAssets)) sakuraWorld = new SakuraWorld(pongoAssets, zoneWorld != null);
            } catch (Exception e) {
                Log.w("EndlessRush", "toon renderer off: " + e);
                pongoAssets = null;
                pongo = null;
            } finally {
                if (in != null) try { in.close(); } catch (Exception ignored) { }
            }
        }
        if (pongo == null) return;
        try {
            toon = new GLRenderer(pongoAssets);
            toon.onSurfaceCreated();
            pongo.attach(scene);
            if (zoneWorld != null) zoneWorld.attach(scene);
            game.zoneScenery = zoneWorld != null;
        } catch (RuntimeException e) {
            Log.w("EndlessRush", "toon renderer off: " + e);
            toon = null;
            scene.toonHero = scene.toonCoins = scene.toonWorld = false;
            game.zoneScenery = false;
        }
    }

    @Override
    public void onSurfaceChanged(GL10 unused, int w, int h) {
        width = Math.max(1, w);
        height = Math.max(1, h);
        GLES20.glViewport(0, 0, width, height);
    }

    @Override
    public void onDrawFrame(GL10 unused) {
        long now = SystemClock.elapsedRealtime();
        float dt = Math.min(0.05f, (now - last) / 1000f);
        last = now;
        Runnable r;
        while ((r = queue.poll()) != null) r.run();

        // fixed sub-steps keep collisions stable on slow frames
        int steps = dt > 0.02f ? 2 : 1;
        for (int i = 0; i < steps; i++) game.update(dt / steps);
        drawFrame(dt);
    }

    /** Builds the frame for the current game state and renders it (the desktop preview calls this too). */
    public void drawFrame(float dt) {
        scene.build(game, dl, width / (float) height, dt);
        if (toon != null) {
            pongo.build(game, scene, dl, frame, width, height, dt);
            // the Sakura Line palette goes in first so the zone palette blends from it
            if (sakuraWorld != null) sakuraWorld.palette(frame);
            if (zoneWorld != null) zoneWorld.build(game, dl, frame, dt);
            if (sakuraWorld != null) sakuraWorld.build(game, frame, dt);
        }
        if (hud != null) hud.onFrame(game);

        if (toon != null) toon.render(frame, false);
        else GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT | GLES20.GL_DEPTH_BUFFER_BIT);
    }
}
