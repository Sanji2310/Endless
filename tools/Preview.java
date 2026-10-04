import com.endlessrush.core.*;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.File;

/**
 * Desktop preview: software-rasterises the game's draw lists (same lighting maths as the GLSL shader)
 * and runs headless autopilot simulations to sanity-check level generation.
 *
 * Usage: java Preview <outDir> [sim]
 */
public class Preview {
    static int W, H;
    static float[] zbuf;
    static float[] cr, cg, cb;

    public static void main(String[] args) throws Exception {
        Models.build();
        File out = new File(args.length > 0 ? args[0] : "preview");
        out.mkdirs();
        if (args.length > 1 && args[1].equals("gif")) { gif(new File(out, "gameplay.gif")); return; }
        if (args.length > 1 && args[1].equals("icon")) { icon(out); return; }
        if (args.length > 1 && args[1].equals("sim")) { simulate(Integer.parseInt(args.length > 2 ? args[2] : "20")); return; }

        Profile prof = new Profile(null);
        prof.boards = 5;
        prof.keys = 0;
        Scene scene = new Scene();
        DrawList dl = new DrawList();
        int w = 540, h = 960;

        // menu
        Game g = new Game(prof, null);
        for (int i = 0; i < 30; i++) { g.update(1 / 30f); scene.build(g, dl, w / (float) h, 1 / 30f); }
        render(dl, w, h, new File(out, "01_menu.png"));

        // gameplay
        g.start();
        Autopilot ai = new Autopilot();
        simFrames(g, scene, dl, ai, w, h, 60 * 14);
        render(dl, w, h, new File(out, "02_run.png"));
        simFrames(g, scene, dl, ai, w, h, 60 * 6);
        render(dl, w, h, new File(out, "03_run.png"));

        // hoverboard
        g.hoverboard();
        simFrames(g, scene, dl, ai, w, h, 40);
        render(dl, w, h, new File(out, "04_board.png"));

        // jetpack
        Game.Pickup jp = new Game.Pickup();
        jp.type = Game.JETPACK; jp.x = g.x; jp.y = g.y + 0.9f; jp.s = g.s + 2;
        g.pickups.add(jp);
        simFrames(g, scene, dl, ai, w, h, 90);
        render(dl, w, h, new File(out, "05_jetpack.png"));

        // stumble -> guard chase view
        Game g2 = new Game(prof, null);
        g2.start();
        simFrames(g2, scene, dl, ai, w, h, 30);
        render(dl, w, h, new File(out, "06_chase.png"));

        // jump over a barrier with coins
        Game g3 = new Game(prof, null);
        g3.start();
        simFrames(g3, scene, dl, ai, w, h, 60 * 8);
        g3.jump();
        simFrames(g3, scene, dl, ai, w, h, 12);
        render(dl, w, h, new File(out, "07_jump.png"));

        // roll
        g3.roll();
        simFrames(g3, scene, dl, null, w, h, 12);
        render(dl, w, h, new File(out, "08_roll.png"));

        // landscape
        simFrames(g3, scene, dl, ai, 960, 540, 200);
        render(dl, 960, 540, new File(out, "09_landscape.png"));

        // character line-up
        for (int c = 0; c < CharacterDef.ALL.length; c++) {
            Game gm = new Game(prof, null);
            scene.setPreviewCharacter(c);
            for (int i = 0; i < 20; i++) { gm.update(1 / 30f); scene.build(gm, dl, 400 / 600f, 1 / 30f); }
            render(dl, 400, 600, new File(out, "char_" + c + ".png"));
        }
        System.out.println("done");
    }

    /** Launcher icons: portrait of the default hero, rounded and framed. */
    static void icon(File out) throws Exception {
        Profile prof = new Profile(null);
        Game g = new Game(prof, null);
        Scene scene = new Scene();
        DrawList dl = new DrawList();
        for (int i = 0; i < 12; i++) { g.update(1 / 30f); scene.build(g, dl, 1f, 1 / 30f); }
        Mat4.lookAt(dl.view, 0.55f, 2.05f, -2.3f, 0.05f, 1.6f, 0, 0, 1, 0);
        Mat4.perspective(dl.proj, 42, 1, 0.3f, 420);
        Mat4.mul(dl.viewProj, dl.proj, dl.view);
        dl.camPos[0] = 0.55f; dl.camPos[1] = 2.05f; dl.camPos[2] = -2.3f;
        File tmp = new File(out, "icon_raw.png");
        render(dl, 512, 512, tmp);
        BufferedImage src = ImageIO.read(tmp);
        int[] sizes = {48, 72, 96, 192};
        String[] dirs = {"mdpi", "hdpi", "xhdpi", "xxxhdpi"};
        for (int k = 0; k < sizes.length; k++) {
            int n = sizes[k];
            BufferedImage im = new BufferedImage(n, n, BufferedImage.TYPE_INT_ARGB);
            java.awt.Graphics2D gr = im.createGraphics();
            gr.setRenderingHint(java.awt.RenderingHints.KEY_ANTIALIASING, java.awt.RenderingHints.VALUE_ANTIALIAS_ON);
            gr.setRenderingHint(java.awt.RenderingHints.KEY_INTERPOLATION, java.awt.RenderingHints.VALUE_INTERPOLATION_BICUBIC);
            float r = n * 0.22f, m = n * 0.04f;
            java.awt.geom.RoundRectangle2D rr = new java.awt.geom.RoundRectangle2D.Float(m, m, n - 2 * m, n - 2 * m, r, r);
            gr.setClip(rr);
            gr.drawImage(src, 0, 0, n, n, null);
            gr.setClip(null);
            gr.setStroke(new java.awt.BasicStroke(n * 0.045f));
            gr.setColor(new java.awt.Color(0xFFC928));
            gr.draw(rr);
            gr.dispose();
            File d = new File(out, "mipmap-" + dirs[k]);
            d.mkdirs();
            ImageIO.write(im, "png", new File(d, "ic_launcher.png"));
        }
        tmp.delete();
    }

    /** Animated GIF of an autopilot run (every 3rd frame at 20 fps). */
    static void gif(File file) throws Exception {
        Profile prof = new Profile(null);
        prof.boards = 3;
        Game g = new Game(prof, null);
        Scene scene = new Scene();
        DrawList dl = new DrawList();
        Autopilot ai = new Autopilot();
        int w = 300, h = 534;
        g.start();
        // skip the calm opening
        simFrames(g, scene, dl, ai, w, h, 60 * 9);
        javax.imageio.ImageWriter wr = ImageIO.getImageWritersByFormatName("gif").next();
        javax.imageio.stream.ImageOutputStream ios = ImageIO.createImageOutputStream(file);
        wr.setOutput(ios);
        wr.prepareWriteSequence(null);
        int frames = 150;
        for (int f = 0; f < frames; f++) {
            if (f == 50) g.hoverboard();
            if (f == 95) {
                Game.Pickup jp = new Game.Pickup();
                jp.type = Game.JETPACK; jp.x = g.x; jp.y = g.y + 0.9f; jp.s = g.s + 1;
                g.pickups.add(jp);
            }
            simFrames(g, scene, dl, ai, w, h, 3);
            BufferedImage im = renderImage(dl, w, h);
            javax.imageio.ImageWriteParam p = wr.getDefaultWriteParam();
            javax.imageio.metadata.IIOMetadata md = wr.getDefaultImageMetadata(new javax.imageio.ImageTypeSpecifier(im), p);
            String fmt = md.getNativeMetadataFormatName();
            javax.imageio.metadata.IIOMetadataNode rootN = (javax.imageio.metadata.IIOMetadataNode) md.getAsTree(fmt);
            javax.imageio.metadata.IIOMetadataNode gce = new javax.imageio.metadata.IIOMetadataNode("GraphicControlExtension");
            gce.setAttribute("disposalMethod", "none");
            gce.setAttribute("userInputFlag", "FALSE");
            gce.setAttribute("transparentColorFlag", "FALSE");
            gce.setAttribute("delayTime", "5");
            gce.setAttribute("transparentColorIndex", "0");
            rootN.appendChild(gce);
            if (f == 0) {
                javax.imageio.metadata.IIOMetadataNode aes = new javax.imageio.metadata.IIOMetadataNode("ApplicationExtensions");
                javax.imageio.metadata.IIOMetadataNode ae = new javax.imageio.metadata.IIOMetadataNode("ApplicationExtension");
                ae.setAttribute("applicationID", "NETSCAPE");
                ae.setAttribute("authenticationCode", "2.0");
                ae.setUserObject(new byte[]{1, 0, 0});
                aes.appendChild(ae);
                rootN.appendChild(aes);
            }
            md.setFromTree(fmt, rootN);
            wr.writeToSequence(new javax.imageio.IIOImage(im, null, md), p);
        }
        wr.endWriteSequence();
        ios.close();
        System.out.println("wrote " + file);
    }

    static void simFrames(Game g, Scene scene, DrawList dl, Autopilot ai, int w, int h, int frames) {
        for (int i = 0; i < frames; i++) {
            if (ai != null) ai.drive(g);
            g.update(1 / 60f);
            scene.build(g, dl, w / (float) h, 1 / 60f);
            if (g.state != Game.RUNNING && g.state != Game.DYING) break;
        }
    }

    static void simulate(int runs) {
        Profile prof = new Profile(null);
        final int[] deaths = new int[2];
        double total = 0;
        for (int r = 0; r < runs; r++) {
            final Game[] ref = new Game[1];
            Game g = new Game(prof, new Game.Listener() {
                public void onSound(int id) {}
                public void onMessage(String t) {}
                public void onStateChanged(int st) {}
            });
            ref[0] = g;
            prof.keys = 0; prof.boards = 0;
            g.start();
            Autopilot ai = new Autopilot();
            int f = 0;
            while (g.state == Game.RUNNING && f < 60 * 60 * 6) {
                ai.drive(g);
                g.update(1 / 60f);
                f++;
            }
            total += g.s;
            String cause = "alive";
            if (g.state == Game.DYING) {
                deaths[g.deathKind]++;
                cause = g.deathKind == 0 ? "crash" : "caught";
                String what = "";
                for (Game.Obstacle o : g.obstacles) {
                    if (Math.abs(o.x - g.x) < 1.5f && g.s + 1 >= o.s0 && g.s - 1 <= o.s0 + o.len)
                        what += " type=" + o.type + (o.moving ? "(moving)" : "") + " lane=" + o.lane;
                }
                cause += what;
            }
            System.out.printf("run %2d: dist %6.0f  score %7d  coins %4d  t=%5.1fs  %s%n", r, g.s, g.score(), g.coinsRun, f / 60f, cause);
        }
        System.out.printf("avg dist %.0f, crashes %d, caught %d%n", total / runs, deaths[0], deaths[1]);
    }

    /** Simple look-ahead bot used for previews and generator testing. */
    public static class Autopilot {
        float cooldown;

        public void drive(Game g) {
            if (g.state != Game.RUNNING) return;
            cooldown -= 1 / 60f;
            float look = g.speed * 1.4f + 8;
            float[] free = new float[3];
            for (int l = -1; l <= 1; l++) free[l + 1] = danger(g, l, look);
            int cur = g.lane;
            // lane choice
            int best = cur;
            for (int l = -1; l <= 1; l++) if (free[l + 1] > free[best + 1] + 3) best = l;
            if (best != cur && cooldown <= 0 && Math.abs(g.x - cur * Game.LANE_W) < 0.2f) {
                int step = best > cur ? 1 : -1;
                if (danger(g, cur + step, 6) > 5) {
                    if (step > 0) g.right(); else g.left();
                    cooldown = 0.15f;
                }
            }
            // jump / roll for barriers in current lane
            for (Game.Obstacle o : g.obstacles) {
                if (o.lane != g.lane) continue;
                float d = o.s0 - g.s;
                if (d < 0 || d > g.speed * 0.3f) continue;
                if (o.type == Game.LOW && g.grounded) g.jump();
                if (o.type == Game.HIGH && !g.rolling) g.roll();
            }
        }

        /** Distance until something that can't be jumped/rolled in this lane. */
        float danger(Game g, int lane, float look) {
            float best = look;
            for (Game.Obstacle o : g.obstacles) {
                if (o.lane != lane) continue;
                float d = o.s0 - g.s;
                if (o.moving) d = d * g.speed / (g.speed + 12);
                if (d + o.len < -0.5f || d > look) continue;
                boolean bad = o.type == Game.BLOCK || (o.type == Game.TRAIN && g.y < Game.TRAIN_H - 0.8f && !rampBefore(g, o));
                if (o.type == Game.TRAIN && o.moving) bad = true;
                if (bad) best = Math.min(best, Math.max(d, 0));
            }
            return best;
        }

        boolean rampBefore(Game g, Game.Obstacle t) {
            for (Game.Obstacle o : g.obstacles)
                if (o.type == Game.RAMP && o.lane == t.lane && Math.abs(o.s0 + o.len - t.s0) < 0.5f && g.s <= o.s0 + 0.5f) return true;
            return false;
        }
    }

    // ------------------------------------------------------------------ software rasteriser

    static void render(DrawList dl, int w, int h, File file) throws Exception {
        ImageIO.write(renderImage(dl, w, h), "png", file);
        System.out.println("wrote " + file);
    }

    static BufferedImage renderImage(DrawList dl, int w, int h) {
        int ss = 2;
        W = w * ss; H = h * ss;
        zbuf = new float[W * H];
        cr = new float[W * H]; cg = new float[W * H]; cb = new float[W * H];
        java.util.Arrays.fill(zbuf, Float.MAX_VALUE);
        for (int pass = 0; pass < 3; pass++) {
            for (int i = 0; i < dl.count; i++) {
                int f = dl.flags[i];
                int p = (f & DrawList.F_NODEPTH) != 0 ? 0 : (f & DrawList.F_BLEND) != 0 ? 2 : 1;
                if (p == pass) drawCmd(dl, i);
            }
        }
        BufferedImage img = new BufferedImage(w, h, BufferedImage.TYPE_INT_RGB);
        for (int y = 0; y < h; y++) for (int x = 0; x < w; x++) {
            float r = 0, g = 0, b = 0;
            for (int j = 0; j < ss; j++) for (int k = 0; k < ss; k++) {
                int idx = (y * ss + j) * W + x * ss + k;
                r += cr[idx]; g += cg[idx]; b += cb[idx];
            }
            int n = ss * ss;
            img.setRGB(x, y, (clamp8(r / n) << 16) | (clamp8(g / n) << 8) | clamp8(b / n));
        }
        return img;
    }

    static int clamp8(float v) { return Math.max(0, Math.min(255, (int) (v * 255 + 0.5f))); }

    static void drawCmd(DrawList dl, int i) {
        Mesh mesh = dl.mesh[i];
        float[] m = dl.model[i], vp = dl.viewProj;
        float[] d = mesh.data;
        int fl = dl.flags[i];
        boolean fog = (fl & DrawList.F_NOFOG) == 0, blend = (fl & DrawList.F_BLEND) != 0, depth = (fl & DrawList.F_NODEPTH) == 0;
        float tr = dl.tint[i * 4], tg = dl.tint[i * 4 + 1], tb = dl.tint[i * 4 + 2], ta = dl.tint[i * 4 + 3];
        float em = dl.emissive[i];
        boolean unlit = (fl & DrawList.F_UNLIT) != 0;
        float lx = dl.lightDir[0], ly = dl.lightDir[1], lz = dl.lightDir[2];
        float ll = (float) Math.sqrt(lx * lx + ly * ly + lz * lz);
        lx /= ll; ly /= ll; lz /= ll;
        float[][] tri = new float[3][8]; // clip x,y,z,w, r,g,b,a
        for (int v = 0; v < mesh.vertexCount; v += 3) {
            for (int k = 0; k < 3; k++) {
                int o = (v + k) * Mesh.STRIDE;
                float px = d[o], py = d[o + 1], pz = d[o + 2];
                float wx = m[0] * px + m[4] * py + m[8] * pz + m[12];
                float wy = m[1] * px + m[5] * py + m[9] * pz + m[13];
                float wz = m[2] * px + m[6] * py + m[10] * pz + m[14];
                float nx = m[0] * d[o + 3] + m[4] * d[o + 4] + m[8] * d[o + 5];
                float ny = m[1] * d[o + 3] + m[5] * d[o + 4] + m[9] * d[o + 5];
                float nz = m[2] * d[o + 3] + m[6] * d[o + 4] + m[10] * d[o + 5];
                float nl = (float) Math.sqrt(nx * nx + ny * ny + nz * nz);
                if (nl > 0) { nx /= nl; ny /= nl; nz /= nl; }
                float[] c = unlit ? new float[]{d[o + 6] * tr, d[o + 7] * tg, d[o + 8] * tb, d[o + 9] * ta} : shade(dl, wx, wy, wz, nx, ny, nz, lx, ly, lz,
                        d[o + 6] * tr, d[o + 7] * tg, d[o + 8] * tb, d[o + 9] * ta, em, fog);
                float[] t = tri[k];
                t[0] = vp[0] * wx + vp[4] * wy + vp[8] * wz + vp[12];
                t[1] = vp[1] * wx + vp[5] * wy + vp[9] * wz + vp[13];
                t[2] = vp[2] * wx + vp[6] * wy + vp[10] * wz + vp[14];
                t[3] = vp[3] * wx + vp[7] * wy + vp[11] * wz + vp[15];
                t[4] = c[0]; t[5] = c[1]; t[6] = c[2]; t[7] = c[3];
            }
            clipAndRaster(tri, blend, depth);
        }
    }

    /** Mirrors the vertex shader in GameRenderer. */
    static float[] shade(DrawList dl, float wx, float wy, float wz, float nx, float ny, float nz, float lx, float ly, float lz,
                         float r, float g, float b, float a, float em, boolean fog) {
        float diff = Math.max(nx * lx + ny * ly + nz * lz, 0);
        float amb = 0.5f + 0.18f * ny;
        float vx = dl.camPos[0] - wx, vy = dl.camPos[1] - wy, vz = dl.camPos[2] - wz;
        float dist = (float) Math.sqrt(vx * vx + vy * vy + vz * vz);
        vx /= dist; vy /= dist; vz /= dist;
        float hx = lx + vx, hy = ly + vy, hz = lz + vz;
        float hl = (float) Math.sqrt(hx * hx + hy * hy + hz * hz);
        float spec = (float) Math.pow(Math.max((nx * hx + ny * hy + nz * hz) / hl, 0), 24) * 0.22f;
        float lit = amb + diff * 0.7f;
        float cr = r * lit + spec + r * em, cg = g * lit + spec + g * em, cb = b * lit + spec + b * em;
        if (fog) {
            float f = Math.max(0, Math.min(1, (dist - dl.fogStart) / (dl.fogEnd - dl.fogStart)));
            cr += (dl.fogColor[0] - cr) * f; cg += (dl.fogColor[1] - cg) * f; cb += (dl.fogColor[2] - cb) * f;
        }
        return new float[]{cr, cg, cb, a};
    }

    static void clipAndRaster(float[][] tri, boolean blend, boolean depth) {
        // clip against near plane z > -w
        float[][] in = tri;
        float[][] outp = new float[4][];
        int n = 0;
        for (int i = 0; i < 3; i++) {
            float[] a = in[i], b = in[(i + 1) % 3];
            float da = a[2] + a[3], db = b[2] + b[3];
            if (da >= 0) outp[n++] = a;
            if ((da >= 0) != (db >= 0)) {
                float t = da / (da - db);
                float[] c = new float[8];
                for (int k = 0; k < 8; k++) c[k] = a[k] + (b[k] - a[k]) * t;
                outp[n++] = c;
            }
        }
        if (n < 3) return;
        for (int i = 1; i + 1 < n; i++) raster(outp[0], outp[i], outp[i + 1], blend, depth);
    }

    static void raster(float[] a, float[] b, float[] c, boolean blend, boolean depth) {
        float ax = (a[0] / a[3] * 0.5f + 0.5f) * W, ay = (0.5f - a[1] / a[3] * 0.5f) * H, az = a[2] / a[3];
        float bx = (b[0] / b[3] * 0.5f + 0.5f) * W, by = (0.5f - b[1] / b[3] * 0.5f) * H, bz = b[2] / b[3];
        float cx = (c[0] / c[3] * 0.5f + 0.5f) * W, cy = (0.5f - c[1] / c[3] * 0.5f) * H, cz = c[2] / c[3];
        float area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax);
        if (Math.abs(area) < 1e-6f) return;
        int x0 = Math.max(0, (int) Math.floor(Math.min(ax, Math.min(bx, cx))));
        int x1 = Math.min(W - 1, (int) Math.ceil(Math.max(ax, Math.max(bx, cx))));
        int y0 = Math.max(0, (int) Math.floor(Math.min(ay, Math.min(by, cy))));
        int y1 = Math.min(H - 1, (int) Math.ceil(Math.max(ay, Math.max(by, cy))));
        for (int y = y0; y <= y1; y++) {
            float py = y + 0.5f;
            for (int x = x0; x <= x1; x++) {
                float px = x + 0.5f;
                float w0 = ((bx - px) * (cy - py) - (by - py) * (cx - px)) / area;
                float w1 = ((cx - px) * (ay - py) - (cy - py) * (ax - px)) / area;
                float w2 = 1 - w0 - w1;
                if (w0 < 0 || w1 < 0 || w2 < 0) continue;
                float z = w0 * az + w1 * bz + w2 * cz;
                int idx = y * W + x;
                if (depth && z >= zbuf[idx]) continue;
                float r = w0 * a[4] + w1 * b[4] + w2 * c[4];
                float g = w0 * a[5] + w1 * b[5] + w2 * c[5];
                float bl = w0 * a[6] + w1 * b[6] + w2 * c[6];
                float al = w0 * a[7] + w1 * b[7] + w2 * c[7];
                if (blend) {
                    cr[idx] += (r - cr[idx]) * al; cg[idx] += (g - cg[idx]) * al; cb[idx] += (bl - cb[idx]) * al;
                } else {
                    cr[idx] = r; cg[idx] = g; cb[idx] = bl;
                    if (depth) zbuf[idx] = z;
                }
            }
        }
    }
}
