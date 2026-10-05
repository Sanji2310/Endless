package com.endlessrush.core;

import com.pongo.core.Mat4;
import com.pongo.core.PongoAssets;
import com.pongo.core.RenderFrame;
import com.pongo.core.Zones;

/**
 * Everything the player sees on the Sakura Line, drawn through the toon renderer from pongo.bin: the line itself
 * (track, sides, wires, gantries, poles), dense roadside streets with houses, apartments, konbini and sakura trees,
 * the far town and the horizon hills; the trains, ramps and barriers; the power-ups and pickups; Pongo's gear
 * (Kaze Board, Hayate pack, Maneki cat); and Inspector Daigo and Kuro the shiba. Run effects (petals, dust, speed
 * lines, impact frames) belong to the effects layer. Assets come from blender/assets/sakura_line.py, trains.py and
 * powerups.py, exported at the Blender origin and placed here in game space (x right, y up, z = -distance).
 *
 * Where the Crystal Cavern and its tunnel own the world (ZoneWorld, Zones.cityWorldAt / cityTrackAt), the city is
 * left out; obstacles, pickups, gear and chasers are drawn everywhere. Also sets the Sakura Line palette (sky, light,
 * fog) and the sun shadow map. Pure Java: used by the Android renderer and by the desktop preview.
 */
public final class SakuraWorld {
    static final float SEG = 12f, PLOT = 10f, GROUND = -0.35f;
    /** Distance tiers (blender/lib/gamelod.py): LOD0 inside LOD1_DIST, LOD1 inside LOD2_DIST, LOD2 beyond. */
    static final float LOD1_DIST = 36f, LOD2_DIST = 90f, VIEW_BACK = 16f, VIEW_AHEAD = 200f;
    /** Pieces farther than this from the runner cannot reach the shadow box; past INK_DIST the ink lines are left
     *  out (they are thinner than a pixel there and the haze has taken the contrast anyway). */
    static final float SHADOW_DIST = 48f, INK_DIST = 130f, TRACK_LOD1 = 24f, GARDEN_LOD1 = 18f, VERGE_LOD1 = 20f;

    private final PongoAssets a;
    private final boolean zones;
    private final int[] track, sideR, sideL, wires, lotR, lotL, gantry, pole, crossing, crossArm;
    private final int[][] houses = new int[5][], streets = new int[4][], sakura = new int[3][], far = new int[3][];
    private final int[] apartment, konbini, hills, clouds, verge, greenbed, backyard;
    private final int[][] gardens = new int[3][];
    private final int[] comFront, comMid, comFrontB, comMidB, expFront, expMid, expFrontB, expMidB, ramp, works, barricade, highBar;
    private final int puMagnet, puRocket, puBoots, puX2, puGacha, puOmamori, board, rocketPack, halo;
    private final int dTorso, dHead, dUarm, dFarm, dThigh, dShin, kBody, kHead, kUleg, kLleg;
    private final float[] uvGlow, uvStar;
    private final float[] tmp = new float[3], ident = Mat4.identity(), lv = new float[16], lp = new float[16];
    private final float[] planes = new float[24];
    private float runX, runZ, camS, camY;
    private boolean lookBack;
    private float time;


    public static boolean available(PongoAssets a) {
        return a.lod("sl_side_r", 0) >= 0 && a.lod("commuter_front", 0) >= 0 && a.lod("pu_magnet", 0) >= 0
                && a.lod("daigo_torso", 0) >= 0;
    }

    /** @param zones true when ZoneWorld draws the tunnel and cavern (the city is then left out there) */
    public SakuraWorld(PongoAssets assets, boolean zones) {
        a = assets;
        this.zones = zones;
        track = lods("sl_track"); sideR = lods("sl_side_r"); sideL = lods("sl_side_l"); wires = lods("sl_wires");
        lotR = lods("sl_lot_r"); lotL = lods("sl_lot_l"); gantry = lods("sl_gantry"); pole = lods("sl_pole");
        crossing = lods("sl_crossing"); crossArm = lods("sl_crossing_arm");
        String[] hn = {"sl_house_a", "sl_house_b", "sl_house_c", "sl_house_d", "sl_house_e"};
        for (int i = 0; i < 5; i++) houses[i] = lods(hn[i]);
        for (int i = 0; i < 4; i++) streets[i] = lods("sl_street_" + i);
        for (int i = 0; i < 3; i++) { sakura[i] = lods("sl_sakura_" + (i + 1)); far[i] = lods("sl_far_" + i); }
        apartment = lods("sl_apartment"); konbini = lods("sl_konbini"); hills = lods("sl_hills");
        clouds = lods("sl_clouds"); verge = lods("sl_verge"); greenbed = lods("sl_greenbed");
        backyard = lods("sl_backyard");
        for (int i = 0; i < 3; i++) gardens[i] = lods("sl_garden_" + i);
        comFront = lods("commuter_front"); comMid = lods("commuter_mid");
        comFrontB = lods("commuter_front_b"); comMidB = lods("commuter_mid_b");
        expFront = lods("express_front"); expMid = lods("express_mid");
        expFrontB = lods("express_front_b"); expMidB = lods("express_mid_b");
        ramp = lods("ramp"); works = lods("works"); barricade = lods("ob_barricade"); highBar = lods("ob_gantry");
        puMagnet = a.lod("pu_magnet", 0); puRocket = a.lod("pu_rocket", 0); puBoots = a.lod("pu_boots", 0);
        puX2 = a.lod("pu_x2", 0); puGacha = a.lod("pu_gacha", 0); puOmamori = a.lod("pu_omamori", 0);
        board = a.lod("kaze_board", 0); rocketPack = a.lod("rocket_pack", 0); halo = a.lod("pickup_halo", 0);
        dTorso = a.lod("daigo_torso", 0); dHead = a.lod("daigo_head", 0); dUarm = a.lod("daigo_uarm", 0);
        dFarm = a.lod("daigo_farm", 0); dThigh = a.lod("daigo_thigh", 0); dShin = a.lod("daigo_shin", 0);
        kBody = a.lod("kuro_body", 0); kHead = a.lod("kuro_head", 0); kUleg = a.lod("kuro_uleg", 0); kLleg = a.lod("kuro_lleg", 0);
        uvGlow = a.tile("fx_glow"); uvStar = a.tile("fx_star");
    }

    private int[] lods(String group) {
        return new int[]{a.lod(group, 0), a.lod(group, 1), a.lod(group, 2)};
    }

    /**
     * Adds the world, obstacles, pickups, gear and chasers to f, and sets the shadow map.
     * Call after PongoScene.build (camera current) and ZoneWorld.build (zone palette applied).
     */
    public void build(Game g, RenderFrame f, float dt) {
        boolean paused = g.state == Game.PAUSED;
        if (!paused) time += dt;
        boolean menu = g.state == Game.MENU;
        float ps = g.s, from = ps - (menu ? 160 : VIEW_BACK), to = ps + VIEW_AHEAD;
        runX = g.x;
        runZ = -ps;
        camS = -f.camPos[2];
        camY = f.camPos[1];
        lookBack = menu;
        frustum(f.viewProj);

        city(f, from, to);
        obstacles(g, f, from, to);
        pickups(g, f, ps);
        gear(g, f, menu);
        if (!menu && g.guardGap < 12 && g.state != Game.GAME_OVER && g.state != Game.SAVE_ME)
            chasers(g, f, -ps + g.guardGap + 0.2f, g.x * 0.6f - 0.6f, g.state == Game.DYING && g.deathKind == 1);
        shadows(g, f);
    }

    // ------------------------------------------------------------------ sky, fog, shadows

    /**
     * The Sakura Line palette: the pale spring sky, sun and shade colours and haze of the renders. Set every frame
     * before ZoneWorld.build, whose zone palette (Zones.apply) blends from these values inside the cave.
     */
    public void palette(RenderFrame f) {
        set(f.skyTop, 0.42f, 0.71f, 0.97f);
        set(f.skyHor, 0.88f, 0.95f, 1.0f);
        set(f.skyLow, 0.8f, 0.86f, 0.95f);
        set(f.fogCol, 0.86f, 0.93f, 1.0f);
        set(f.lightCol, 1.0f, 0.97f, 0.93f);
        set(f.shadeCol, 0.66f, 0.62f, 0.88f);
        set(f.skinShade, 0.93f, 0.68f, 0.7f);
        set(f.rimCol, 1f, 0.95f, 0.85f);
        set(f.ink, 0.16f, 0.13f, 0.2f);
        f.vignette[0] = 0.1f; f.vignette[1] = 0.08f; f.vignette[2] = 0.2f; f.vignette[3] = 0.18f;
        f.fogStart = 70f;
        f.fogEnd = 260f;
        f.fogMax = 1f;
        f.heightFog = 0f;
        f.shadowStrength = 1f;
        f.night = 0f;
    }

    private void shadows(Game g, RenderFrame f) {
        // a sun shadow box that follows the runner, a little ahead of her so near obstacles cast onto the track
        float cx = g.x * 0.5f, cy = 0, cz = -g.s - 12f;
        float sx = f.sunDir[0], sy = f.sunDir[1], sz = f.sunDir[2];
        Mat4.lookAt(lv, cx + sx * 60, cy + sy * 60, cz + sz * 60, cx, cy, cz, 0, 1, 0);
        Mat4.ortho(lp, -26, 26, -30, 30, 1, 140);
        Mat4.mul(f.shadowVP, lp, lv);
        f.shadowOn = true;
        f.shadowSize = 2048;
    }

    // ------------------------------------------------------------------ the line and the town

    /**
     * Draws a piece at game offset (x, y, -dist), turned rotY degrees: the distance tier picks the mesh, pieces whose
     * bounds are outside the view (and too far to shadow anything in view) are left out, and far pieces skip the
     * shadow map and the ink. Returns the model matrix, or null when nothing was drawn.
     */
    private float[] piece(RenderFrame f, int[] lods, float x, float y, float dist, float rotY) {
        return piece(f, lods, x, y, dist, rotY, LOD1_DIST);
    }

    private float[] piece(RenderFrame f, int[] lods, float x, float y, float dist, float rotY, float lod1) {
        if (lods == null || lods[0] < 0) return null;
        float z = -dist;
        // bounds centre in game space (the Mat4.rotY turn of the local centre, then the offset): the tier and the
        // culling go by where the piece really is, not by its origin on the line
        float c = 1, s = 0;
        if (rotY != 0) {
            double r = Math.toRadians(rotY);
            c = (float) Math.cos(r);
            s = (float) Math.sin(r);
        }
        PongoAssets.Mesh m0 = a.meshes[lods[0]];
        float lx = m0.center[0], ly = m0.center[1], lz = m0.center[2];
        float wx = x + c * lx + s * lz, wy = y + ly, wz = z - s * lx + c * lz;
        float dx = wx - f.camPos[0], dz = wz - f.camPos[2];
        float d2 = dx * dx + dz * dz;
        int mesh = d2 < lod1 * lod1 ? lods[0] : d2 < LOD2_DIST * LOD2_DIST ? lods[1] : lods[2];
        PongoAssets.Mesh me = a.meshes[mesh];
        float rx = wx - runX, rz = wz - runZ;
        boolean nearRunner = rx * rx + rz * rz < (SHADOW_DIST + me.radius) * (SHADOW_DIST + me.radius);
        boolean seen = inView(wx, wy, wz, me.radius);
        if (!seen && !nearRunner) return null;
        int fl = 0;
        if (!nearRunner) fl |= RenderFrame.D_NO_SHADOW;
        if (d2 > INK_DIST * INK_DIST || overCamera(me, x, y, z, c, s)) fl |= RenderFrame.D_NO_OUTLINE;
        float[] m = f.draw(mesh, fl, 1, 1, 1, 1, 0);
        Mat4.translate(m, x, y, z);
        if (rotY != 0) Mat4.rotY(m, rotY);
        return m;
    }

    /** View frustum planes (a, b, c, d; normalised, pointing inward) from the view-projection matrix. */
    private void frustum(float[] m) {
        for (int p = 0; p < 6; p++) {
            int row = p >> 1;
            float sg = (p & 1) == 0 ? 1 : -1;
            float a = m[3] + sg * m[row], b = m[7] + sg * m[4 + row], cc = m[11] + sg * m[8 + row], d = m[15] + sg * m[12 + row];
            float l = (float) Math.sqrt(a * a + b * b + cc * cc);
            planes[p * 4] = a / l; planes[p * 4 + 1] = b / l; planes[p * 4 + 2] = cc / l; planes[p * 4 + 3] = d / l;
        }
    }

    private boolean inView(float x, float y, float z, float r) {
        for (int p = 0; p < 6; p++) {
            int o = p * 4;
            if (planes[o] * x + planes[o + 1] * y + planes[o + 2] * z + planes[o + 3] < -r) return false;
        }
        return true;
    }

    /**
     * True when the piece reaches over the camera: it spans the camera's depth and rises above it. The ink hull of
     * such a piece has vertices behind the camera, where its screen-space push turns into wedges across the view
     * (seen under the gantries), so it is drawn without ink while the camera passes.
     */
    private boolean overCamera(PongoAssets.Mesh me, float x, float y, float z, float c, float s) {
        if (y + me.bmax[1] < camY - 0.5f) return false;
        float camZ = -camS, z0 = Float.MAX_VALUE, z1 = -Float.MAX_VALUE;
        for (int k = 0; k < 4; k++) {
            float lx = (k & 1) == 0 ? me.bmin[0] : me.bmax[0], lz = (k & 2) == 0 ? me.bmin[2] : me.bmax[2];
            float wz = z - s * lx + c * lz;
            z0 = Math.min(z0, wz);
            z1 = Math.max(z1, wz);
        }
        return camZ > z0 - 0.5f && camZ < z1 + 0.5f;
    }

    // behind the start line (the menu looks back down the line) it is always the Sakura Line
    private boolean cityHere(float d) { return !zones || d < 0 || Zones.cityWorldAt(d); }
    private boolean trackHere(float d) { return !zones || d < 0 || Zones.cityTrackAt(d); }

    /** Level crossings every 30 segments (360 m), offset so the first is soon after the start. */
    static boolean crossingAt(int k) { return Math.floorMod(k, 30) == 9; }

    private void city(RenderFrame f, float from, float to) {
        // horizon: hills, the far peak and the clouds ride with the camera so they never come closer
        int sky = RenderFrame.D_NO_FOG | RenderFrame.D_NO_SHADOW | RenderFrame.D_NO_OUTLINE;
        if (hills[0] >= 0) {
            float[] m = f.draw(hills[0], sky, 1, 1, 1, 1, 0);
            Mat4.translate(m, 0, 0, f.camPos[2]);
            if (lookBack) Mat4.rotY(m, 180);
        }
        if (clouds[0] >= 0) {
            float[] m = f.draw(clouds[0], sky, 1, 1, 1, 1, 0);
            Mat4.translate(m, 0, 0, f.camPos[2]);
            // the menu camera looks back down the line: the sky turns round with it
            if (lookBack) Mat4.rotY(m, 180);
        }
        int k0 = (int) Math.floor(from / SEG), k1 = (int) Math.floor(to / SEG);
        for (int k = k0; k <= k1; k++) {
            float d = k * SEG;
            if (!trackHere(d)) continue;
            boolean cross = crossingAt(k);
            // the sleepers and ballast are the densest piece: full detail only right around her
            if (!cross) piece(f, track, 0, 0, d, 0, TRACK_LOD1);
            if (!cityHere(d)) continue;
            if (cross) {
                piece(f, crossing, 0, 0, d, 0);
                piece(f, track, 0, 0, d, 0, TRACK_LOD1);
                // the barrier arms stand raised over their housings, as in the kit, so nothing reaches over the lanes
                float[] arm = piece(f, crossArm, 6.35f, GROUND + 0.9f, d + SEG / 2 - 3f, 180);
                if (arm != null) Mat4.rotZ(arm, 72);
                arm = piece(f, crossArm, -6.35f, GROUND + 0.9f, d + SEG / 2 + 3f, 0);
                if (arm != null) Mat4.rotZ(arm, 72);
            } else {
                piece(f, sideR, 0, 0, d, 0);
                piece(f, sideL, 0, 0, d, 0);
                // grass and wildflowers along both fences (the left is the same strip turned round)
                piece(f, verge, 0, 0, d, 0, VERGE_LOD1);
                piece(f, verge, 0, 0, d + SEG, 180, VERGE_LOD1);
                // and a planted bed of azaleas, hydrangeas and grass along the line side of each lane
                piece(f, greenbed, 0, 0, d, 0, VERGE_LOD1);
                piece(f, greenbed, 0, 0, d + SEG, 180, VERGE_LOD1);
            }
            // Overhead wires and gantries that the camera is about to pass under: a 2 cm wire half a metre over
            // the lens is a black bar across the top of the screen, and a gantry a few metres ahead is a giant
            // truss over everything. Both fade out on the way in (no ink, see-through) and are gone overhead.
            float wa = fadeIn(lookBack ? camS - d - SEG : d - camS, 2f, 12f);
            if (camS >= d - 3f && camS <= d + SEG + 1) wa = 0;
            if (wa > 0.02f) fade(f, piece(f, wires, 0, 0, d, 0), wa);
            piece(f, lotR, 0, 0, d, 0);
            piece(f, lotL, 0, 0, d, 0);
            if (Math.floorMod(k, 2) == 0) {
                float ga = fadeIn(lookBack ? camS - d - 6f : d + 6f - camS, 3f, 11f);
                if (ga > 0.02f) fade(f, piece(f, gantry, 0, 0, d + 6f, 0), ga);
                // utility poles alternate sides every 24 m; on the left the pole is turned round so its cables
                // reach back to the previous one
                if (Math.floorMod(k, 4) == 0) piece(f, pole, 0, 0, d + 2f, 0);
                else piece(f, pole, 0, 0, d + 2f + 24f, 180);
            }
        }
        // plots of houses, apartments and konbini, the street clutter in front of them and sakura on the kerb
        int p0 = (int) Math.floor(from / PLOT) - 2, p1 = (int) Math.floor(to / PLOT);
        for (int side = -1; side <= 1; side += 2) {
            float rot = side > 0 ? -90 : 90;
            for (int pair = Math.floorDiv(p0, 2); pair <= Math.floorDiv(p1, 2); pair++) {
                float ys = pair * 2 * PLOT;
                if (!cityHere(ys) || !cityHere(ys + 2 * PLOT)) continue;
                if (crossNear(ys, 2 * PLOT)) continue;
                int h = hash(pair * 2 + (side > 0 ? 7 : 13));
                if (h % 5 == 0) {
                    boolean kon = (h >> 5) % 3 == 0;
                    piece(f, kon ? konbini : apartment, side * (kon ? 19.5f : 12.6f), GROUND, ys + PLOT, rot);
                    // trees and lawn behind the apartment block (the konbini lot runs out to the field)
                    if (!kon) gardenPiece(f, backyard, side, ys);
                } else {
                    piece(f, houses[(h >> 3) % 5], side * 13.6f, GROUND, ys + PLOT / 2, rot);
                    piece(f, houses[(h >> 9) % 5], side * 13.6f, GROUND, ys + PLOT * 1.5f, rot);
                    // hedges between the houses and the back gardens
                    gardenPiece(f, gardens[(h >> 13) % 3], side, ys);
                }
            }
            for (int p = p0; p <= p1; p++) {
                float ys = p * PLOT;
                if (!cityHere(ys) || crossNear(ys, PLOT)) continue;
                int h = hash(p * 31 + (side > 0 ? 3 : 5));
                // built for the right side; the left side is the same strip turned round
                if (side > 0) piece(f, streets[h % 4], 0, 0, ys, 0);
                else piece(f, streets[h % 4], 0, 0, ys + PLOT, 180);
                if ((h >> 4) % 3 == 0) piece(f, sakura[(h >> 6) % 3], side * 9.9f, GROUND, ys + 5f, (h >> 8) % 360);
            }
            int v0 = (int) Math.floor(from / 24f) - 1, v1 = (int) Math.floor(to / 24f);
            for (int v = v0; v <= v1; v++) {
                float ys = v * 24f;
                if (!cityHere(ys)) continue;
                int h = hash(v * 17 + (side > 0 ? 1 : 2));
                if (side > 0) piece(f, far[h % 3], 0, 0, ys, 0);
                else piece(f, far[h % 3], 0, 0, ys + 24f, 180);
            }
        }
    }

    /** A 20 m garden strip built for the right side at y 0..20; the left side is the strip turned round. */
    private void gardenPiece(RenderFrame f, int[] lods, int side, float ys) {
        if (side > 0) piece(f, lods, 0, 0, ys, 0, GARDEN_LOD1);
        else piece(f, lods, 0, 0, ys + 2 * PLOT, 180, GARDEN_LOD1);
    }

    /** True when [ys, ys + len) overlaps a level crossing's road (the plots and streets leave it open). */
    private static boolean crossNear(float ys, float len) {
        int k0 = (int) Math.floor((ys - 2f) / SEG), k1 = (int) Math.floor((ys + len + 2f) / SEG);
        for (int k = k0; k <= k1; k++) {
            if (!crossingAt(k)) continue;
            float r0 = k * SEG + SEG / 2 - 3.5f, r1 = k * SEG + SEG / 2 + 3.5f;
            if (ys < r1 && ys + len > r0) return true;
        }
        return false;
    }

    // ------------------------------------------------------------------ obstacles

    private void obstacles(Game g, RenderFrame f, float from, float to) {
        for (int i = 0; i < g.obstacles.size(); i++) {
            Game.Obstacle o = g.obstacles.get(i);
            if (o.s0 > to || o.s0 + o.len < from) continue;
            switch (o.type) {
                case Game.TRAIN: {
                    boolean b = (o.variant & 1) != 0;
                    int[] front = o.moving ? (b ? expFrontB : expFront) : (b ? comFrontB : comFront);
                    int[] mid = o.moving ? (b ? expMidB : expMid) : (b ? comMidB : comMid);
                    for (int c = 0; c < o.cars; c++) piece(f, c == 0 ? front : mid, o.x, 0, o.s0 + c * Game.CAR_LEN, 0);
                    if (o.moving) {
                        // headlight glare and a light pool running ahead of the oncoming express
                        float z = -o.s0 + 0.2f;
                        float fl = 0.85f + 0.15f * (float) Math.sin(time * 20 + o.s0);
                        for (int s = -1; s <= 1; s += 2)
                            f.quad(true, o.x + s * 0.62f, 1.28f, z, 0.55f * fl, 0.55f * fl, 0, uvGlow, 1f, 0.95f, 0.75f, 0.9f);
                        f.quadPts(true, o.x - 1.1f, 0.2f, z, o.x + 1.1f, 0.2f, z, o.x + 1.6f, 0.2f, z + 9f, o.x - 1.6f, 0.2f, z + 9f,
                                uvGlow, RenderFrame.packColor(1f, 0.95f, 0.7f, 0.35f), RenderFrame.packColor(1f, 0.95f, 0.7f, 0f));
                    }
                    break;
                }
                case Game.RAMP: piece(f, ramp, o.x, 0, o.s0, 0); break;
                case Game.LOW: piece(f, barricade, o.x, 0, o.s0, 0); break;
                case Game.HIGH: piece(f, highBar, o.x, 0, o.s0, 0); break;
                default: piece(f, works, o.x, 0, o.s0, 0); break;
            }
        }
    }

    // ------------------------------------------------------------------ pickups

    private void pickups(Game g, RenderFrame f, float ps) {
        for (int i = 0; i < g.pickups.size(); i++) {
            Game.Pickup p = g.pickups.get(i);
            if (p.taken || p.type == Game.COIN || p.s > ps + 170 || p.s < ps - 10) continue;
            float bob = (float) Math.sin(time * 3 + p.s) * 0.15f;
            float spin = (time * 120 + p.s * 7) % 360;
            int mesh;
            float sc = 1.25f;
            switch (p.type) {
                case Game.MAGNET: mesh = puMagnet; spin = (float) Math.sin(time * 2 + p.s) * 40; sc = 1.4f; break;
                case Game.JETPACK: mesh = puRocket; break;
                case Game.SNEAKERS: mesh = puBoots; sc = 1.4f; break;
                case Game.X2: mesh = puX2; spin = (float) Math.sin(time * 2) * 35; break;
                case Game.MYSTERY: mesh = puGacha; sc = 1.3f; break;
                default: mesh = puOmamori; sc = 1.5f; spin = (float) Math.sin(time * 2.4f + p.s) * 50; break;
            }
            if (mesh < 0) continue;
            float y = p.y + bob;
            float[] m = f.draw(mesh, 0, 1, 1, 1, 1, 0.12f);
            Mat4.translate(m, p.x, y, -p.s);
            Mat4.rotY(m, spin);
            Mat4.scale(m, sc, sc, sc);
            // a soft glow behind it and a faint turning ring on the ground under it, so power-ups read from far away
            f.quad(true, p.x, y, -p.s + 0.3f, 0.75f, 0.75f, 0, uvGlow, 1f, 0.92f, 0.7f, 0.55f);
            if (halo >= 0) {
                float[] h = f.draw(halo, RenderFrame.D_NO_SHADOW | RenderFrame.D_NO_OUTLINE | RenderFrame.D_BLEND, 1, 1, 1, 0.45f, 0.6f);
                Mat4.translate(h, p.x, (p.y > 2f ? p.y - 1f : 0f) + 0.12f, -p.s);       // just above the sleepers
                Mat4.rotY(h, -time * 60);
            }
            if (((int) (time * 4 + p.s)) % 3 == 0)
                f.quad(true, p.x + 0.4f * (float) Math.sin(time * 5 + p.s), y + 0.35f, -p.s, 0.14f, 0.14f, time, uvStar, 1f, 1f, 0.85f, 0.9f);
        }
    }

    // ------------------------------------------------------------------ Pongo's gear

    private void gear(Game g, RenderFrame f, boolean menu) {
        if (menu) return;
        float hs = PongoScene.HERO_SCALE, px = g.x, py = g.y, pz = -g.s;
        if (g.boardT > 0 && board >= 0) {
            float[] m = f.draw(board, 0, 1, 1, 1, 1, 0.05f);
            Mat4.translate(m, px, py + 0.32f + 0.04f * (float) Math.sin(time * 6), pz);
            Mat4.rotZ(m, (g.lane * Game.LANE_W - g.x) * -6f);
            Mat4.scale(m, 1.1f, 1.1f, 1.1f);
            // hover glow and a ribbon of wind behind the board
            for (int s = -1; s <= 1; s += 2)
                f.quad(true, px, py + 0.12f, pz + s * 0.42f, 0.32f, 0.12f, 0, uvGlow, 0.5f, 0.95f, 1f, 0.8f);
        }
        if (g.jetT > 0 && rocketPack >= 0) {
            float[] m = f.draw(rocketPack, 0, 1, 1, 1, 1, 0.05f);
            Mat4.translate(m, px, py + 1.02f * hs, pz + 0.2f * hs);
            Mat4.scale(m, hs, hs, hs);
            // the thruster plume is drawn by the effects layer (FxLayer), not here
        }
        if (g.magT > 0 && puMagnet >= 0) {
            // the Maneki cat rides along at her shoulder, waving
            float[] m = f.draw(puMagnet, 0, 1, 1, 1, 1, 0.1f);
            Mat4.translate(m, px + 0.75f, py + 1.6f + 0.1f * (float) Math.sin(time * 4), pz + 0.1f);
            Mat4.rotY(m, 180 + 20 * (float) Math.sin(time * 3));
            Mat4.scale(m, 0.55f, 0.55f, 0.55f);
        }
        if (g.x2T > 0) {
            for (int k = 0; k < 3; k++) {
                float an = time * 3 + k * 2.09f;
                f.quad(true, px + 0.7f * (float) Math.cos(an), py + 1.1f + 0.4f * (float) Math.sin(an * 1.3f), pz + 0.7f * (float) Math.sin(an),
                        0.16f, 0.16f, time * 2, uvStar, 1f, 0.85f, 0.3f, 1f);
            }
        }
        // the Tobi Boots' heel glow is the effects layer's too
        if (g.invulnT > 0 && ((int) (g.invulnT * 12)) % 2 == 0)
            f.quad(true, px, py + 0.9f * hs, pz, 0.9f, 1.2f, 0, uvGlow, 1f, 1f, 1f, 0.35f);
    }

    // ------------------------------------------------------------------ Inspector Daigo and Kuro

    /** Draws a part under parent * T(x, y, z) * rotY(yaw) * rotX(pitch) * rotZ(roll) and returns its matrix. */
    private float[] part(RenderFrame f, int mesh, float[] parent, float x, float y, float z, float yaw, float pitch,
                         float roll) {
        if (mesh < 0) return null;
        float[] m = f.draw(mesh);
        Mat4.copy(m, parent);
        Mat4.translate(m, x, y, z);
        if (yaw != 0) Mat4.rotY(m, yaw);
        if (pitch != 0) Mat4.rotX(m, pitch);
        if (roll != 0) Mat4.rotZ(m, roll);
        return m;
    }

    // The chase run, the same numbers as blender/assets/sakura_line.py (daigo_pose, kuro_pose): angles in degrees, +
    // swings a limb forward, knee and elbow flex measured from straight; the hips are lifted so the lower foot is down.
    private static final float HIP_X = 0.15f, SH_X = 0.37f, SH_Z = 0.6f, NECK = 0.74f, UARM = 0.28f, THIGH = 0.46f;
    private static final float K_ULEG = 0.17f, K_HIP_Z = -0.06f;
    /** Knee flex through the stride (phase in degrees, flex): heel kick, knee drive, reach, stance, push off. */
    private static final float[] KNEE = {0, 116, 45, 102, 90, 80, 125, 36, 155, 15, 205, 15, 250, 20, 270, 26, 300, 62,
            330, 102, 360, 116};
    private static final float[] SOLE = {0.22f, -0.47f, -0.08f, -0.49f, 0.07f, -0.49f}, PAW = {0.06f, -0.175f, -0.02f, -0.18f};
    /** Kuro's legs: x, y (forward) on the body, gallop phase offset. */
    private static final float[] K_LEGS = {-0.1f, 0.25f, 0f, 0.1f, 0.25f, 0.35f, -0.1f, -0.25f, 2.5f, 0.1f, -0.25f, 2.85f};
    private final float[] legA = new float[4], armA = new float[4], kLeg = new float[8];

    static float keyed(float deg, float[] k) {
        float d = deg % 360f;
        if (d < 0) d += 360f;
        for (int i = 2; i < k.length; i += 2)
            if (d <= k[i]) {
                float t = (d - k[i - 2]) / (k[i] - k[i - 2]);
                return k[i - 1] + (k[i + 1] - k[i - 1]) * (0.5f - 0.5f * (float) Math.cos(Math.PI * t));
            }
        return k[k.length - 1];
    }

    /** Height of the upper pivot above the lowest of pts (y forward, z down the lower segment) of a two-segment limb. */
    static float drop(float upper, float theta, float flex, float[] pts) {
        double t = Math.toRadians(theta), ph = Math.toRadians(theta - flex), lo = 9;
        for (int i = 0; i < pts.length; i += 2) lo = Math.min(lo, pts[i] * Math.sin(ph) + pts[i + 1] * Math.cos(ph));
        return (float) (upper * Math.cos(t) - lo);
    }

    private final float[] root = new float[16], torso = new float[16], droot = new float[16];

    /** Inspector Daigo sprinting at Pongo with Kuro galloping alongside, rigid parts on a jointed run cycle (the parts
     *  face Blender +Y = game -Z, which is forward). */
    private void chasers(Game g, RenderFrame f, float gz, float gx, boolean grabbing) {
        float p = g.animPhase * 11, hip = 0;
        for (int side = 0; side < 2; side++) {
            float q = p + side * (float) Math.PI;
            if (grabbing) {
                legA[side * 2] = 22; legA[side * 2 + 1] = 34;
                armA[side * 2] = 84; armA[side * 2 + 1] = 12;
            } else {
                legA[side * 2] = 18 + 48 * (float) Math.sin(q);
                legA[side * 2 + 1] = keyed((float) Math.toDegrees(q), KNEE);
                float s = -(float) Math.sin(q);
                armA[side * 2] = 10 + 56 * s;
                armA[side * 2 + 1] = 92 + 22 * s;
            }
            hip = Math.max(hip, drop(THIGH, legA[side * 2], legA[side * 2 + 1], SOLE));
        }
        float c2 = (float) Math.cos(2 * p);
        float lean = grabbing ? 8 : 27 + 3 * c2, twist = grabbing ? 0 : -10 * (float) Math.sin(p);
        float head = grabbing ? 10 : 20 + 3 * c2;
        f.quad(false, gx, 0.04f, gz, 0.6f, 0.6f, 0, uvGlow, 0.3f, 0.25f, 0.45f, 0.35f);
        Mat4.setIdentity(root);
        Mat4.translate(root, gx, hip, gz);
        for (int side = 0; side < 2; side++) {
            float sx = side == 0 ? -1 : 1;
            float[] th = part(f, dThigh, root, sx * HIP_X, 0, 0, 0, legA[side * 2], 0);
            if (th != null) part(f, dShin, th, 0, -THIGH, 0, 0, -legA[side * 2 + 1], 0);
        }
        Mat4.copy(torso, root);
        Mat4.rotY(torso, twist);
        Mat4.rotX(torso, -lean);
        part(f, dTorso, torso, 0, 0, 0, 0, 0, 0);
        part(f, dHead, torso, 0, NECK, -0.02f, 0, head, 0);
        for (int side = 0; side < 2; side++) {
            float sx = side == 0 ? -1 : 1;
            float[] ua = part(f, dUarm, torso, sx * SH_X, SH_Z, 0, 0, armA[side * 2], sx * 8);
            if (ua != null) part(f, dFarm, ua, 0, -UARM, 0, 0, armA[side * 2 + 1], 0);
        }
        // Kuro gallops alongside, a little ahead
        float dx = gx + 1.0f, dz = gz - 0.6f, kq = g.animPhase * 16;
        float pitch = 7 * (float) Math.sin(kq + 0.6f), pr = (float) Math.toRadians(pitch), ky = 0;
        for (int l = 0; l < 4; l++) {
            float off = K_LEGS[l * 3 + 2], u = 38 * (float) Math.sin(kq + off);
            float k = 8 + 72 * (float) Math.pow(Math.max(0, Math.cos(kq + off + 0.4f)), 2);
            kLeg[l * 2] = u; kLeg[l * 2 + 1] = k;
            float pz = K_LEGS[l * 3 + 1] * (float) Math.sin(pr) + K_HIP_Z * (float) Math.cos(pr);
            ky = Math.max(ky, drop(K_ULEG, u, k, PAW) - pz);
        }
        f.quad(false, dx, 0.04f, dz, 0.35f, 0.45f, 0, uvGlow, 0.3f, 0.25f, 0.45f, 0.3f);
        Mat4.setIdentity(droot);
        Mat4.translate(droot, dx, ky, dz);
        Mat4.rotX(droot, pitch);
        part(f, kBody, droot, 0, 0, 0, 0, 0, 0);
        part(f, kHead, droot, 0, 0.14f, -0.36f, 0, -pitch * 0.6f, 0);
        for (int l = 0; l < 4; l++) {
            float[] up = part(f, kUleg, droot, K_LEGS[l * 3], K_HIP_Z, -K_LEGS[l * 3 + 1], 0, kLeg[l * 2], 0);
            if (up != null) part(f, kLleg, up, 0, -K_ULEG, 0, 0, -kLeg[l * 2 + 1], 0);
        }
    }

    // ------------------------------------------------------------------ helpers

    /** 0 at or before `from` metres ahead of the camera, rising to 1 at `to`. */
    private static float fadeIn(float ahead, float from, float to) {
        return Math.max(0f, Math.min(1f, (ahead - from) / (to - from)));
    }

    /** Makes the draw just added (m non-null) see-through at alpha a < 1, without ink. */
    private static void fade(RenderFrame f, float[] m, float a) {
        if (m == null || a >= 1f) return;
        int i = f.count - 1;
        f.flags[i] |= RenderFrame.D_NO_OUTLINE | RenderFrame.D_BLEND;
        f.tint[i * 4 + 3] = a;
    }

    private static void set(float[] v, float r, float g, float b) { v[0] = r; v[1] = g; v[2] = b; }

    static int hash(int k) {
        int h = k * 0x45d9f3b;
        h = ((h >>> 16) ^ h) * 0x45d9f3b;
        h = (h >>> 16) ^ h;
        return h & 0x7fffffff;
    }
}
