package com.endlessrush.app;

import android.content.res.AssetManager;
import android.opengl.GLES20;
import android.opengl.GLSurfaceView;
import android.os.SystemClock;
import android.util.Log;

import com.endlessrush.core.DrawList;
import com.endlessrush.core.Game;
import com.endlessrush.core.Mesh;
import com.endlessrush.core.Models;
import com.endlessrush.core.PongoScene;
import com.endlessrush.core.Scene;
import com.pongo.app.GLRenderer;
import com.pongo.core.PongoAssets;
import com.pongo.core.RenderFrame;

import java.io.BufferedInputStream;
import java.io.InputStream;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.FloatBuffer;
import java.util.ArrayList;
import java.util.concurrent.ConcurrentLinkedQueue;

import javax.microedition.khronos.egl.EGLConfig;
import javax.microedition.khronos.opengles.GL10;

/**
 * OpenGL ES 2.0 renderer; also drives the simulation on the GL thread.
 * The world is drawn from Scene's draw list; Pongo and the Mon coins are drawn on top by the toon renderer
 * (com.pongo) from assets/pongo.bin, sharing the depth buffer. Without that asset the old hero is drawn instead.
 */
public final class GameRenderer implements GLSurfaceView.Renderer {
    private static final String VS =
            "uniform mat4 uVP; uniform mat4 uModel; uniform vec3 uLight; uniform vec3 uCam;\n" +
            "uniform vec4 uTint; uniform float uEmis; uniform vec3 uFogColor; uniform vec2 uFog; uniform float uUnlit;\n" +
            "attribute vec3 aPos; attribute vec3 aNrm; attribute vec4 aCol;\n" +
            "varying vec4 vCol;\n" +
            "void main() {\n" +
            "  vec4 wp = uModel * vec4(aPos, 1.0);\n" +
            "  vec3 base = aCol.rgb * uTint.rgb;\n" +
            "  vec3 c;\n" +
            "  float d = length(uCam - wp.xyz);\n" +
            "  if (uUnlit > 0.5) { c = base; } else {\n" +
            "    vec3 n = normalize((uModel * vec4(aNrm, 0.0)).xyz);\n" +
            "    float diff = max(dot(n, uLight), 0.0);\n" +
            "    float amb = 0.5 + 0.18 * n.y;\n" +
            "    vec3 v = (uCam - wp.xyz) / d;\n" +
            "    float spec = pow(max(dot(n, normalize(uLight + v)), 0.0), 24.0) * 0.22;\n" +
            "    c = base * (amb + diff * 0.7) + spec + base * uEmis;\n" +
            "  }\n" +
            "  if (uFog.y > 0.0) c = mix(c, uFogColor, clamp((d - uFog.x) / (uFog.y - uFog.x), 0.0, 1.0));\n" +
            "  vCol = vec4(c, aCol.a * uTint.a);\n" +
            "  gl_Position = uVP * wp;\n" +
            "}\n";
    private static final String FS =
            "precision mediump float;\n" +
            "varying vec4 vCol;\n" +
            "void main() { gl_FragColor = vCol; }\n";

    public interface Hud { void onFrame(Game game); }

    private final Game game;
    private final Scene scene;
    private final DrawList dl = new DrawList();
    private final ConcurrentLinkedQueue<Runnable> queue = new ConcurrentLinkedQueue<Runnable>();
    private final ArrayList<Mesh> uploaded = new ArrayList<Mesh>();
    private final Hud hud;
    private final AssetManager assetManager;
    private PongoAssets pongoAssets;
    private boolean pongoTried;
    private PongoScene pongo;
    private GLRenderer toon;
    private final RenderFrame frame = new RenderFrame();
    private int prog, uVP, uModel, uLight, uCam, uTint, uEmis, uFogColor, uFog, uUnlit, aPos, aNrm, aCol;
    private int width = 1, height = 1;
    private long last;
    private final float[] light = new float[3];

    public GameRenderer(Game game, Scene scene, Hud hud, AssetManager assets) {
        this.game = game;
        this.scene = scene;
        this.hud = hud;
        this.assetManager = assets;
    }

    /** Runs r on the GL thread before the next frame (all game mutations go through here). */
    public void post(Runnable r) { queue.add(r); }

    @Override
    public void onSurfaceCreated(GL10 unused, EGLConfig config) {
        Models.build();
        for (Mesh m : uploaded) m.handle = 0; // context was (re)created
        uploaded.clear();
        prog = link(VS, FS);
        uVP = GLES20.glGetUniformLocation(prog, "uVP");
        uModel = GLES20.glGetUniformLocation(prog, "uModel");
        uLight = GLES20.glGetUniformLocation(prog, "uLight");
        uCam = GLES20.glGetUniformLocation(prog, "uCam");
        uTint = GLES20.glGetUniformLocation(prog, "uTint");
        uEmis = GLES20.glGetUniformLocation(prog, "uEmis");
        uFogColor = GLES20.glGetUniformLocation(prog, "uFogColor");
        uFog = GLES20.glGetUniformLocation(prog, "uFog");
        uUnlit = GLES20.glGetUniformLocation(prog, "uUnlit");
        aPos = GLES20.glGetAttribLocation(prog, "aPos");
        aNrm = GLES20.glGetAttribLocation(prog, "aNrm");
        aCol = GLES20.glGetAttribLocation(prog, "aCol");
        GLES20.glClearColor(0.73f, 0.87f, 0.98f, 1);
        GLES20.glDisable(GLES20.GL_CULL_FACE);
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
        } catch (RuntimeException e) {
            Log.w("EndlessRush", "toon renderer off: " + e);
            toon = null;
            scene.toonHero = scene.toonCoins = false;
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

    /** Builds the draw lists for the current game state and renders them (the desktop preview calls this too). */
    public void drawFrame(float dt) {
        scene.build(game, dl, width / (float) height, dt);
        if (toon != null) pongo.build(game, scene, dl, frame, width, height, dt);
        if (hud != null) hud.onFrame(game);

        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT | GLES20.GL_DEPTH_BUFFER_BIT);
        beginWorld();
        for (int pass = 0; pass < 3; pass++) {
            if (pass == 2 && toon != null) {
                // the heroine and coins go in after the opaque world and before its blended layer (blob shadows,
                // glows, speed lines), so those still blend over the ground around her
                toon.render(frame, true);
                beginWorld();
            }
            if (pass == 0) {
                GLES20.glDisable(GLES20.GL_DEPTH_TEST);
                GLES20.glDepthMask(false);
                GLES20.glDisable(GLES20.GL_BLEND);
            } else if (pass == 1) {
                GLES20.glEnable(GLES20.GL_DEPTH_TEST);
                GLES20.glDepthFunc(GLES20.GL_LEQUAL);
                GLES20.glDepthMask(true);
            } else {
                GLES20.glEnable(GLES20.GL_DEPTH_TEST);
                GLES20.glDepthFunc(GLES20.GL_LEQUAL);
                GLES20.glDepthMask(false);
                GLES20.glEnable(GLES20.GL_BLEND);
                GLES20.glBlendFunc(GLES20.GL_SRC_ALPHA, GLES20.GL_ONE_MINUS_SRC_ALPHA);
            }
            for (int i = 0; i < dl.count; i++) {
                int f = dl.flags[i];
                int p = (f & DrawList.F_NODEPTH) != 0 ? 0 : (f & DrawList.F_BLEND) != 0 ? 2 : 1;
                if (p != pass) continue;
                draw(i, f);
            }
        }
        GLES20.glDepthMask(true);
        GLES20.glDisable(GLES20.GL_BLEND);
    }

    /** Program, frame uniforms and attribute arrays for the world draw list. */
    private void beginWorld() {
        GLES20.glUseProgram(prog);
        GLES20.glDisable(GLES20.GL_CULL_FACE);
        GLES20.glUniformMatrix4fv(uVP, 1, false, dl.viewProj, 0);
        float lx = dl.lightDir[0], ly = dl.lightDir[1], lz = dl.lightDir[2];
        float ll = (float) Math.sqrt(lx * lx + ly * ly + lz * lz);
        light[0] = lx / ll; light[1] = ly / ll; light[2] = lz / ll;
        GLES20.glUniform3fv(uLight, 1, light, 0);
        GLES20.glUniform3fv(uCam, 1, dl.camPos, 0);
        GLES20.glUniform3fv(uFogColor, 1, dl.fogColor, 0);
        GLES20.glEnableVertexAttribArray(aPos);
        GLES20.glEnableVertexAttribArray(aNrm);
        GLES20.glEnableVertexAttribArray(aCol);
    }

    private void draw(int i, int flags) {
        Mesh m = dl.mesh[i];
        if (m.vertexCount == 0) return;
        if (m.handle == 0) upload(m);
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, m.handle);
        int stride = Mesh.STRIDE * 4;
        GLES20.glVertexAttribPointer(aPos, 3, GLES20.GL_FLOAT, false, stride, 0);
        GLES20.glVertexAttribPointer(aNrm, 3, GLES20.GL_FLOAT, false, stride, 12);
        GLES20.glVertexAttribPointer(aCol, 4, GLES20.GL_FLOAT, false, stride, 24);
        GLES20.glUniformMatrix4fv(uModel, 1, false, dl.model[i], 0);
        GLES20.glUniform4fv(uTint, 1, dl.tint, i * 4);
        GLES20.glUniform1f(uEmis, dl.emissive[i]);
        GLES20.glUniform1f(uUnlit, (flags & DrawList.F_UNLIT) != 0 ? 1f : 0f);
        if ((flags & DrawList.F_NOFOG) != 0) GLES20.glUniform2f(uFog, 0, -1);
        else GLES20.glUniform2f(uFog, dl.fogStart, dl.fogEnd);
        GLES20.glDrawArrays(GLES20.GL_TRIANGLES, 0, m.vertexCount);
    }

    private void upload(Mesh m) {
        int[] id = new int[1];
        GLES20.glGenBuffers(1, id, 0);
        FloatBuffer fb = ByteBuffer.allocateDirect(m.data.length * 4).order(ByteOrder.nativeOrder()).asFloatBuffer();
        fb.put(m.data).position(0);
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, id[0]);
        GLES20.glBufferData(GLES20.GL_ARRAY_BUFFER, m.data.length * 4, fb, GLES20.GL_STATIC_DRAW);
        m.handle = id[0];
        uploaded.add(m);
    }

    private static int compile(int type, String src) {
        int s = GLES20.glCreateShader(type);
        GLES20.glShaderSource(s, src);
        GLES20.glCompileShader(s);
        int[] ok = new int[1];
        GLES20.glGetShaderiv(s, GLES20.GL_COMPILE_STATUS, ok, 0);
        if (ok[0] == 0) throw new RuntimeException("shader: " + GLES20.glGetShaderInfoLog(s));
        return s;
    }

    private static int link(String vs, String fs) {
        int p = GLES20.glCreateProgram();
        GLES20.glAttachShader(p, compile(GLES20.GL_VERTEX_SHADER, vs));
        GLES20.glAttachShader(p, compile(GLES20.GL_FRAGMENT_SHADER, fs));
        GLES20.glLinkProgram(p);
        int[] ok = new int[1];
        GLES20.glGetProgramiv(p, GLES20.GL_LINK_STATUS, ok, 0);
        if (ok[0] == 0) throw new RuntimeException("link: " + GLES20.glGetProgramInfoLog(p));
        return p;
    }
}
