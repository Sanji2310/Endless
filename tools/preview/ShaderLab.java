import android.opengl.GLES20;
import com.pongo.app.GLRenderer;
import com.pongo.core.*;

import java.io.*;

/**
 * Shader lab: the toon renderer (GLRenderer, the same code as the game) on the lab set from blender/assets/shader_lab.py
 * plus Pongo, the coin and the cave crystals, through every time of day and the cavern palette. GL calls are
 * recorded by the GLES20 stand-in and replayed in headless Chromium (tools/shader_lab.sh).
 * Usage: java ShaderLab <pongo.bin> <gles.bin out> [width height]
 */
public class ShaderLab {
    static PongoAssets a;
    static GLRenderer r;
    static RenderFrame f = new RenderFrame();
    static Animator anim;
    static int W, H, river, cloud, crystals, sakura, pongo, coin;
    static float time;

    public static void main(String[] args) throws Exception {
        W = args.length > 3 ? Integer.parseInt(args[2]) : 540;
        H = args.length > 3 ? Integer.parseInt(args[3]) : 960;
        try (InputStream in = new BufferedInputStream(new FileInputStream(args[0]))) { a = PongoAssets.load(in, true); }
        river = need("lab_river"); cloud = need("lab_cloud"); crystals = need("lab_crystals"); sakura = need("lab_sakura");
        pongo = need("pongo"); coin = need("coin");
        anim = new Animator(a.skeletons[a.meshes[pongo].skeleton]);
        anim.play("idle", 0);
        r = new GLRenderer(a);
        r.onSurfaceCreated();

        for (int p = 0; p < Lighting.PHASES; p++) {
            int ph = (Lighting.HIRU + p) % Lighting.PHASES;
            riverShot("lab_river_" + (p + 1) + "_" + Lighting.NAME[ph].toLowerCase(), ph);
        }
        skyShot("lab_sky_hiru", Lighting.HIRU, 0f);
        skyShot("lab_sky_yuyake", Lighting.YUYAKE, 0f);
        skyShot("lab_sky_glide", Lighting.HIRU, 0.8f);
        sakuraShot("lab_sakura_hiru", Lighting.HIRU);
        sakuraShot("lab_sakura_yuyake", Lighting.YUYAKE);
        sakuraShot("lab_sakura_yoru", Lighting.YORU);
        caveShot("lab_crystals_cave");
        try (OutputStream os = new BufferedOutputStream(new FileOutputStream(args[1]))) { GLES20.save(os); }
        System.out.println("recorded " + new File(args[1]).length() / 1024 + " KB of GL commands");
    }

    static int need(String g) {
        int m = a.lod(g, 0);
        if (m < 0) throw new IllegalStateException("pongo.bin has no " + g + " (tools/shader_lab.sh exports the lab set)");
        return m;
    }

    static void camera(float ex, float ey, float ez, float cx, float cy, float cz, float fov) {
        f.clear();
        f.screenW = W; f.screenH = H;
        Mat4.lookAt(f.view, ex, ey, ez, cx, cy, cz, 0, 1, 0);
        Mat4.perspective(f.proj, fov, W / (float) H, 0.3f, 420f);
        Mat4.mul(f.viewProj, f.proj, f.view);
        Mat4.invert(f.invViewProj, f.viewProj);
        f.camPos[0] = ex; f.camPos[1] = ey; f.camPos[2] = ez;
        f.outlinePx = Math.max(1.4f, Math.min(3.2f, 2.2f * H / 900f));
        time += 1.7f;
        f.time = time;
        f.wind[3] = time;
        f.lamp[3] = 0;
        f.skyOverlay = false;
    }

    static void light(int phase) {
        Lighting.apply(f, phase + 0.3f);
    }

    static void hero(float x, float y, float z, float yaw) {
        anim.update(1 / 30f);
        float[] m = f.draw(pongo);
        Mat4.translate(m, x, y, z);
        Mat4.rotY(m, yaw);
        Mat4.scale(m, 1.2f, 1.2f, 1.2f);
        f.bonesForLast(anim.palette, anim.n);
    }

    static void present(String name) {
        r.render(f, false);
        GLES20.present(name);
        System.out.println("shot " + name);
    }

    /** The river from behind and above, like the canoe camera: banks, grass and the water flowing away. */
    static void riverShot(String name, int phase) {
        camera(0.6f, 3.2f, 6f, 0f, 0.4f, -12f, 62);
        light(phase);
        f.water[0] = 0; f.water[1] = -1.4f;
        for (int k = 0; k < 4; k++) {
            float[] m = f.draw(river);
            Mat4.translate(m, 0, 0, -k * 20f + 8f);
        }
        float[] m = f.draw(sakura);
        Mat4.translate(m, -9f, 0.5f, -14f);
        m = f.draw(sakura);
        Mat4.translate(m, 10f, 0.5f, -30f);
        hero(-5.6f, 0.45f, -1.5f, 200);
        for (int i = 0; i < 5; i++) {
            m = f.draw(coin);
            Mat4.translate(m, 0, 0.6f, -4f - i * 2.5f);
            Mat4.rotY(m, i * 30f + time * 40f);
        }
        Lighting.fitShadow(f, 0, 0, -6f, 16f, 1024);
        present(name);
    }

    /** Looking out over the horizon: painted sky, clouds, and lab clouds as meshes. glide: the sea of clouds. */
    static void skyShot(String name, int phase, float glide) {
        camera(0, glide > 0 ? 30f : 1.6f, 0, 0, glide > 0 ? 26f : 6f, -40f, 66);
        light(phase);
        f.cloud[3] = glide;
        float[] m = f.draw(cloud);
        Mat4.translate(m, -18f, glide > 0 ? 22f : 18f, -70f);
        Mat4.scale(m, 2.2f, 2.2f, 2.2f);
        m = f.draw(cloud);
        Mat4.translate(m, 26f, glide > 0 ? 30f : 26f, -110f);
        Mat4.rotY(m, 70);
        Mat4.scale(m, 3f, 3f, 3f);
        if (glide == 0) {
            m = f.draw(river);
            Mat4.translate(m, 0, -0.2f, 8f);
            m = f.draw(river);
            Mat4.translate(m, 0, -0.2f, -12f);
        }
        f.shadowOn = false;
        present(name);
        f.cloud[3] = 0;
    }

    /** Pongo under the cherry tree: cel bands, ink, cast shadows, rim light, canopy sway, at three hours. */
    static void sakuraShot(String name, int phase) {
        camera(3.2f, 1.9f, 5.2f, -0.4f, 1.6f, -1f, 45);
        light(phase);
        float[] m = f.draw(river);
        Mat4.translate(m, 9.5f, -0.4f, 10f);
        m = f.draw(sakura);
        Mat4.translate(m, -2.2f, 0, -2.5f);
        hero(0.2f, 0, 0.4f, 25);
        Lighting.fitShadow(f, 0, 0, -1f, 7f, 1024);
        present(name);
    }

    /** Crystals in the cavern palette with the Hotaru Lamp: muted mineral colour, faint inner glow. */
    static void caveShot(String name) {
        camera(0.4f, 1.7f, 3.4f, 0f, 0.4f, -1f, 50);
        light(Lighting.HIRU);
        Zones z = new Zones();
        z.paletteZone = Zones.CAVERN;
        z.blend = 1f;
        float[] m = f.draw(crystals);
        Mat4.translate(m, 0, 0, -1f);
        hero(0.75f, 0, -0.2f, 160);
        f.shadowOn = false;
        z.apply(f, 1.0f, 1.9f, 1.2f);
        present(name);
    }
}
