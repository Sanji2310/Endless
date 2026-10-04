package com.endlessrush.core;

import com.pongo.core.Mat4;
import com.pongo.core.PongoAssets;
import com.pongo.core.RenderFrame;
import com.pongo.core.Zones;

/**
 * The zone world drawn through the toon renderer from pongo.bin: the Sakura Line -> Crystal Cavern set piece
 * (cutting, hill, portal, lined tunnel, mouth: blender/assets/tunnel.py), the same pieces turned round on the way
 * out, and the cavern's 12 m segments (blender/assets/cave.py) laid out by Zones.caveKit.
 *
 * Scene leaves out its own city segments wherever this layer owns the world (Zones.cityWorldAt / cityTrackAt).
 * Each frame this layer also blends the zone palette into the toon frame (Zones.apply: light, fog, Hotaru Lamp) and
 * into the old world's draw list, adds the cave effects (lamp dust, drips, crystal glints) and the zone title card.
 *
 * Pieces are exported at the Blender origin and placed here in game space (x right, y up, z = -distance). Anything
 * else that belongs to a zone (vehicles, zone obstacles) can go through piece(...) the same way.
 * Pure Java: used by the Android renderer and by the desktop preview.
 */
public final class ZoneWorld {
    /** Pieces are drawn at LOD1 past this distance from the camera. */
    static final float LOD_DIST = 48f;
    /** Pongo's head height at HERO_SCALE (where the Hotaru Lamp sits). */
    static final float HEAD_Y = 1.55f * PongoScene.HERO_SCALE;
    /** blender city.GROUND in game y (the cutting, hill and portal stand on it). */
    static final float GROUND = -0.35f;

    private final PongoAssets a;
    private final int[] cutL, cutR, hill, trees, portal, lined0, lined1, cityTrack, trackChange, mouth, signal;
    private final int[] caveTrack, caveFork, caveFrame, cavePipe;
    private final int[][] shell = new int[3][], deco = new int[3][], props = new int[3][];
    private final float[] uvCard, uvMote, uvDrip, uvSplash, uvSparkle;
    private final int[] kit = new int[3], kitPrev = new int[3];
    private final float[] light = new float[3], tmp = new float[3];
    private float time;

    /** True when pongo.bin carries the zone pieces (older builds only have Pongo and the coin). */
    public static boolean available(PongoAssets a) {
        return a.lod("tunnel_portal", 0) >= 0 && a.lod("cave_shell_1", 0) >= 0 && a.lod("cave_track", 0) >= 0;
    }

    public ZoneWorld(PongoAssets assets) {
        a = assets;
        cutL = lods("cutting_l"); cutR = lods("cutting_r"); hill = lods("tunnel_hill"); trees = lods("tunnel_trees");
        portal = lods("tunnel_portal"); lined0 = lods("tunnel_lined_0"); lined1 = lods("tunnel_lined_1");
        cityTrack = lods("city_track"); trackChange = lods("track_change"); mouth = lods("tunnel_mouth");
        signal = lods("tunnel_signal");
        caveTrack = lods("cave_track"); caveFork = lods("cave_fork"); caveFrame = lods("cave_frame"); cavePipe = lods("cave_pipe");
        for (int i = 0; i < 3; i++) {
            shell[i] = lods("cave_shell_" + (i + 1));
            deco[i] = lods("cave_deco_" + (i + 1));
            props[i] = lods("cave_props_" + (i + 1));
        }
        uvCard = a.tiles.get("ui_zone_cavern");
        uvMote = a.tile("fx_mote");
        uvDrip = a.tile("fx_drip");
        uvSplash = a.tile("fx_splash");
        uvSparkle = a.tile("fx_sparkle");
    }

    private int[] lods(String group) {
        int l0 = a.lod(group, 0), l1 = a.lod(group, 1);
        return new int[]{l0, l1 >= 0 ? l1 : l0};
    }

    /** Hands the zone stretches of the world over from Scene to this layer. */
    public void attach(Scene scene) { scene.toonWorld = true; }

    /**
     * Adds the zone pieces in view to f, blends the zone palette into f and dl, and adds the effects and title card.
     * Call after PongoScene.build (the camera and time-of-day lighting in f are current) and before the world draws.
     */
    public void build(Game g, DrawList dl, RenderFrame f, float dt) {
        if (g.state != Game.PAUSED) time += dt;
        boolean menu = g.state == Game.MENU;
        float ps = g.s, from = ps - (menu ? 160 : 14), to = ps + 185;
        Zones z = g.zones;

        // set pieces whose stretch [approach, boundary + approach] overlaps the view
        float b = Zones.nextBoundary(from - Zones.APPROACH) ;
        for (; b - Zones.LINED - Zones.APPROACH < to; b += Zones.ZONE_LEN) {
            if (b + Zones.APPROACH < from) continue;
            if (Zones.exitAt(b)) setPiece(f, b, true);
            else if (Zones.zoneAt(b) == Zones.CAVERN) setPiece(f, b, false);
        }
        // cavern segments
        int k0 = (int) Math.floor(from / Zones.SEG), k1 = (int) Math.floor(to / Zones.SEG);
        for (int k = k0; k <= k1; k++) {
            float d = k * Zones.SEG;
            if (Zones.zoneAt(d) != Zones.CAVERN) continue;
            float caveStart = Zones.nextBoundary(d) - Zones.ZONE_LEN;
            int i = Math.round((d - caveStart) / Zones.SEG);
            if (d >= Zones.portalAt(caveStart + Zones.ZONE_LEN)) continue;      // the lining on the way out
            caveSegment(f, d, i);
        }

        // palette: the toon frame first, then the same light and fog onto the old world's draws
        z.apply(f, g.x, g.y + HEAD_Y, -ps);
        tintWorld(dl, f, z);
        if (z.paletteZone == Zones.CAVERN && z.blend > 0.02f && !menu) effects(g, f, z.blend);
        card(f, z);
    }

    // ------------------------------------------------------------------ pieces

    /** Draws mesh lods[] at game offset (x, y, -dist) in a frame (identity, or turned round for the way out). */
    private float[] piece(RenderFrame f, int[] lods, float[] frame, float x, float y, float dist) {
        if (lods[0] < 0) return null;
        float[] m = f.draw(lods[0]);
        Mat4.copy(m, frame);
        Mat4.translate(m, x, y, -dist);
        Mat4.transformPoint(m, 0, 0, 0, tmp);
        float dx = tmp[0] - f.camPos[0], dz = tmp[2] - f.camPos[2];
        if (dx * dx + dz * dz > LOD_DIST * LOD_DIST) f.mesh[f.count - 1] = lods[1];
        return m;
    }

    private final float[] frameM = new float[16];

    /** The tunnel set piece at boundary b: going in (portal at b - LINED, mouth on b), or turned round going out
     *  (mouth at b - LINED, portal on b, cutting after b). Local distances are measured from the portal. */
    private void setPiece(RenderFrame f, float b, boolean out) {
        float[] fr = frameM;
        Mat4.setIdentity(fr);
        if (out) {
            Mat4.translate(fr, 0, 0, -b);
            Mat4.rotY(fr, 180);
        } else {
            Mat4.translate(fr, 0, 0, -Zones.portalAt(b));
        }
        for (int i = 0; i < 4; i++) {
            float y0 = -Zones.APPROACH + i * Zones.SEG;
            piece(f, cutL, fr, 0, 0, y0);
            piece(f, cutR, fr, 0, 0, y0);
        }
        piece(f, hill, fr, 0, 0, 0);
        piece(f, trees, fr, 0, 0, 0);
        piece(f, portal, fr, 0, 0, 0);
        piece(f, signal, fr, -4.7f, GROUND + 0.1f, -4f);
        piece(f, lined0, fr, 0, 0, 0);
        piece(f, cityTrack, fr, 0, 0, 0);
        piece(f, lined1, fr, 0, 0, Zones.SEG);
        piece(f, trackChange, fr, 0, 0, Zones.SEG);
        piece(f, mouth, fr, 0, 0, Zones.LINED);
    }

    private final float[] ident = Mat4.identity();

    /** Cavern segment i (from the mouth) at distance d: shell, deco, props, air pipe, mine track (or the Y parting,
     *  two segments long), and the timber frames at +1 m and +7 m. */
    private void caveSegment(RenderFrame f, float d, int i) {
        Zones.caveKit(i, kit);
        int sd = kit[0] - 1;
        piece(f, shell[sd], ident, 0, 0, d);
        piece(f, deco[sd], ident, 0, 0, d);
        piece(f, props[kit[1] - 1], ident, 0, 0, d);
        piece(f, cavePipe, ident, 0, 0, d);
        boolean forkHere = kit[2] == 1 && caveFork[0] >= 0;
        boolean forkPrev = false;
        if (i > 0) {
            Zones.caveKit(i - 1, kitPrev);
            forkPrev = kitPrev[2] == 1 && caveFork[0] >= 0;
        }
        if (forkHere) piece(f, caveFork, ident, 0, 0, d);
        else if (!forkPrev) piece(f, caveTrack, ident, 0, 0, d);
        piece(f, caveFrame, ident, 0, 0, d + 1f);
        piece(f, caveFrame, ident, 0, 0, d + 7f);
    }

    // ------------------------------------------------------------------ palette on the old world

    /** The old world (obstacles, pickups, blob shadows, sky) has no zone palette of its own: its draws take the
     *  zone's light as a tint and the toon frame's fog, so they sit in the same darkness as the cave. */
    private void tintWorld(DrawList dl, RenderFrame f, Zones z) {
        if (z.paletteZone < 0 || z.blend <= 0f) return;
        float t = z.blend;
        float[] p = Zones.PALETTE[z.paletteZone].light;
        // the old shader has no lamp, so the cave light is lifted a little for it
        for (int c = 0; c < 3; c++) light[c] = 1f + (Math.min(1f, p[c] * 1.35f) - 1f) * t;
        for (int i = 0; i < dl.count; i++) {
            boolean sky = (dl.flags[i] & DrawList.F_NODEPTH) != 0;
            for (int c = 0; c < 3; c++) {
                // the sky dome, sun and clouds sink into the cave dark
                float k = sky ? 1f + (f.fogCol[c] * 0.9f - 1f) * t : light[c];
                dl.tint[i * 4 + c] *= k;
            }
        }
        System.arraycopy(f.fogCol, 0, dl.fogColor, 0, 3);
        dl.fogStart = f.fogStart;
        dl.fogEnd = f.fogEnd;
    }

    // ------------------------------------------------------------------ effects

    private static float hash(int n) {
        n = (n << 13) ^ n;
        return ((n * (n * n * 15731 + 789221) + 1376312589) & 0x7fffffff) / (float) 0x7fffffff;
    }

    /** Dust motes drifting in the lamp's pool, water drips falling from the vault onto the track with a splash ring,
     *  and crystals glinting on the walls. Faded in with the palette blend. */
    private void effects(Game g, RenderFrame f, float w) {
        float ps = g.s;
        // motes: a loose cloud ahead of her, inside the lamp radius, drifting and twinkling
        for (int n = 0; n < 26; n++) {
            float hx = hash(n * 3 + 1), hy = hash(n * 3 + 2), hz = hash(n * 3 + 3);
            float cyc = (time * (0.05f + 0.05f * hx) + hz) % 1f;
            float px = g.x + (hx - 0.5f) * 5f + (float) Math.sin(time * 0.7f + n) * 0.3f;
            float py = 0.6f + hy * 2.8f + (float) Math.sin(time * 0.9f + n * 1.7f) * 0.25f;
            float pz = -(ps + 1.5f + cyc * 14f);
            float a = w * 0.55f * (float) Math.sin(cyc * Math.PI) * (0.6f + 0.4f * (float) Math.sin(time * 3f + n));
            if (a <= 0.01f) continue;
            f.quad(true, px, py, pz, 0.035f, 0.035f, 0, uvMote, 1f, 0.86f, 0.6f, a);
        }
        // drips: fixed spots per segment, falling every couple of seconds
        int k0 = (int) Math.floor(ps / Zones.SEG), k1 = (int) Math.floor((ps + 60f) / Zones.SEG);
        for (int k = k0; k <= k1; k++) {
            for (int j = 0; j < 2; j++) {
                int id = k * 7 + j;
                float dx = (hash(id) - 0.5f) * 8f, ds = k * Zones.SEG + hash(id + 99) * Zones.SEG;
                float top = 4.2f + hash(id + 7) * 1.4f, period = 1.6f + hash(id + 3) * 1.8f;
                float t = (time + hash(id + 5) * period) % period;
                float fall = (float) Math.sqrt(2f * top / 9.8f);
                if (t < fall) {
                    float y = top - 4.9f * t * t;
                    f.quad(false, dx, y, -ds, 0.05f, 0.09f, 0, uvDrip, 0.75f, 0.9f, 1f, 0.85f * w);
                } else if (t < fall + 0.35f) {
                    float s = (t - fall) / 0.35f;
                    float r = 0.1f + s * 0.35f;
                    // splash ring lying on the ground
                    f.quadPts(false, dx - r, 0.03f, -ds + r, dx + r, 0.03f, -ds + r, dx + r, 0.03f, -ds - r, dx - r, 0.03f, -ds - r,
                            uvSplash, RenderFrame.packColor(0.8f, 0.92f, 1f, (1f - s) * 0.8f * w),
                            RenderFrame.packColor(0.8f, 0.92f, 1f, (1f - s) * 0.8f * w));
                }
            }
        }
        // glints: crystal points on the walls catching the lamp
        k1 = (int) Math.floor((ps + 90f) / Zones.SEG);
        for (int k = k0; k <= k1; k++) {
            for (int j = 0; j < 3; j++) {
                int id = k * 13 + j + 500;
                float side = hash(id) < 0.5f ? -1f : 1f;
                float gx = side * (4.6f + hash(id + 1) * 1.2f), gy = 0.8f + hash(id + 2) * 3.4f;
                float gs = k * Zones.SEG + hash(id + 3) * Zones.SEG;
                float ph = (time * (0.6f + hash(id + 4)) + hash(id + 5) * 6f) % 3f;
                if (ph > 0.6f) continue;
                float a = (float) Math.sin(ph / 0.6f * Math.PI) * w;
                int c = (int) (hash(id + 6) * 3);
                float r = c == 0 ? 0.5f : c == 1 ? 0.71f : 1f, gg = c == 0 ? 0.94f : c == 1 ? 0.61f : 0.6f, bb = c == 2 ? 0.84f : 1f;
                f.quad(true, gx, gy, -gs, 0.16f, 0.16f, time * 0.8f, uvSparkle, r, gg, bb, a);
            }
        }
    }

    // ------------------------------------------------------------------ title card

    /** The zone title card (tunnel.title_cards) sliding in at the top left, drawn as a quad just in front of the
     *  camera: Zones.cardSlide() eases it in and out. */
    private void card(RenderFrame f, Zones z) {
        float slide = z.cardSlide();
        if (slide <= 0f || z.cardZone < 0) return;
        String name = Zones.CARD[z.cardZone];
        float[] uv = name != null ? a.tiles.get(name) : null;
        if (uv == null) return;
        float W = f.screenW, H = f.screenH;
        float cw = (W < H ? 0.66f : 0.375f) * W, ch = cw * 200f / 640f;
        float margin = 0.04f * W;
        float x0 = -cw + (margin + cw) * slide, y0 = 0.1f * H;
        float tx = 1f / f.proj[0], ty = 1f / f.proj[5], dn = 0.5f;
        float[] v = f.view;
        float rx = v[0], ry = v[4], rz = v[8], ux = v[1], uy = v[5], uz = v[9], fx = -v[2], fy = -v[6], fz = -v[10];
        float cx = f.camPos[0] + fx * dn, cy = f.camPos[1] + fy * dn, cz = f.camPos[2] + fz * dn;
        float[] xs = {x0, x0 + cw, x0 + cw, x0}, ys = {y0 + ch, y0 + ch, y0, y0};
        float[] p = new float[12];
        for (int i = 0; i < 4; i++) {
            float nx = (2f * xs[i] / W - 1f) * tx * dn, ny = (1f - 2f * ys[i] / H) * ty * dn;
            p[i * 3] = cx + rx * nx + ux * ny;
            p[i * 3 + 1] = cy + ry * nx + uy * ny;
            p[i * 3 + 2] = cz + rz * nx + uz * ny;
        }
        int col = RenderFrame.packColor(1, 1, 1, slide);
        f.quadPts(false, p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9], p[10], p[11], uv, col, col);
    }
}
