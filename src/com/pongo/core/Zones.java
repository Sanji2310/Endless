package com.pongo.core;

/**
 * The zone cycle along a run (docs/PONGO_DESIGN.md §4) and the set-piece transitions between zones.
 *
 * Distances are metres along the run (Blender +Y in the asset scripts, game -Z). Each zone lasts ZONE_LEN (a whole
 * number of 12 m track segments, so every set-piece edge falls on a segment seam). The transition into a zone is laid
 * out so its "mouth" (where the new zone's kit starts) sits exactly on the zone boundary b. For Sakura Line -> Crystal
 * Cavern that layout is blender/assets/tunnel.py:
 *
 *   b - 72  approach   cutting with retaining walls, hill rises         (tunnel_hill, cutting_l/r)
 *   b - 24  portal     tunnel mouth: title card, sting, whoosh          (tunnel_portal)
 *   b - 24  lined A    concrete-lined tunnel, Sakura Line track         (tunnel_lined_0 + city_track)
 *   b - 12  lined B    track turns into mine track at b - 6             (tunnel_lined_1 + track_change)
 *   b - 4   board      Pongo boards the ore cart waiting on the centre track
 *   b       mouth      lining ends, the cavern opens out                (tunnel_mouth, cave_* segments)
 *
 * Leaving the cavern uses the same pieces turned round (exitAt): the cavern narrows into the lining at b - 24, she
 * leaves the cart at b - 20, the mine track turns back into Sakura Line track, and she runs out of the portal at b
 * into the cutting (b .. b + 48), where the next zone starts.
 *
 * Nothing can hurt Pongo from the portal to the mouth. The lighting crossfades from whatever the time of day set to
 * the zone's palette between portal - 6 m and the mouth, and the Hotaru Lamp switches on as the light fades.
 *
 * Usage, once per frame after the time-of-day system has filled the RenderFrame:
 *   events = zones.update(distance, dt);   // EV_* bits crossed this frame (sounds, card, vehicle hand-off)
 *   zones.apply(frame, headX, headY, headZ); // blend lighting/fog toward the zone palette, place the lamp
 */
public final class Zones {
    public static final int SAKURA = 0, CAVERN = 1, RIVER = 2, SKY = 3, ROOFTOPS = 4, COUNT = 5;
    public static final String[] NAME = {"Sakura Line", "Crystal Cavern", "Bamboo River", "Sky Glide", "Express Rooftops"};
    public static final String[] KANJI = {"桜線", "水晶洞窟", "竹の川", "空の道", "特急の屋根"};
    /** Title card tiles painted by tunnel.title_cards() (null: not painted yet). */
    public static final String[] CARD = {"ui_zone_sakura", "ui_zone_cavern", null, null, null};

    /** About 1,400 m per zone (design §4), rounded to 120 track segments of 12 m. */
    public static final float ZONE_LEN = 1440f, SEG = 12f;
    /** The zones that have a kit, in run order; the run cycles through these. Bamboo River, Sky Glide and Express
     *  Rooftops join the cycle (in that order, after the cavern) when their kits and transitions exist. */
    public static final int[] CYCLE = {SAKURA, CAVERN};
    // Sakura Line -> Crystal Cavern set piece (tunnel.py: APPROACH, LINED)
    public static final float APPROACH = 48f, LINED = 24f, TRACK_CHANGE = 6f, BOARD = 4f;
    public static final float BLEND_LEAD = 6f;
    public static final float CARD_IN = 0.35f, CARD_HOLD = 2.2f, CARD_OUT = 0.45f;

    // events (bit flags returned by update)
    public static final int EV_APPROACH = 1;   // the set piece comes into view: start the tunnel ambience crossfade
    public static final int EV_PORTAL = 2;     // entering the tunnel lining: whoosh, sting, title card, lamp on
    public static final int EV_BOARD = 4;      // into a vehicle zone: hand Pongo to the vehicle (ore cart in the cave)
    public static final int EV_MOUTH = 8;      // the new zone starts: its ambience loop and controls take over
    public static final int EV_ZONE_END = 16;  // the next transition's approach is about to begin
    public static final int EV_LEAVE = 32;     // out of a vehicle zone: Pongo leaves the vehicle and runs on foot

    /** Lighting for one zone; values replace the time-of-day ones by blend weight. null fields keep time of day. */
    public static final class Palette {
        public float[] light, shade, skinShade, rim, skyTop, skyHor, skyLow, fog, ink, lampCol, vignette;
        public float fogStart, fogEnd, fogMax = 1f, heightFog, shadowStrength = 1f, lampRadius, night = -1f;
    }

    public static final Palette[] PALETTE = new Palette[COUNT];

    static {
        Palette c = new Palette();
        // see blender/assets/cave.py: SHADOW 0x6E62AE, cave_tint() light 0xFFE8C8 / rim 0xA8ECFF, cave_world() sky.
        // The Sakura Line manner underground: high-key, a lavender shadow band, warm lantern light, violet distance.
        c.shade = rgb(0x6E62AE);
        c.skinShade = rgb(0xB8849C);
        c.light = rgb(0xFFE8C8);         // lantern-warm lit band
        c.rim = rgb(0xA8ECFF);           // crystal-cool rim
        c.skyTop = rgb(0x2B2452);
        c.skyHor = rgb(0x4A3F7A);
        c.skyLow = rgb(0x2B2452);
        c.fog = rgb(0x3E3570);
        c.fogStart = 20f;
        c.fogEnd = 110f;
        c.heightFog = 0.12f;           // low dust haze over the tracks
        c.ink = rgb(0x2A2040);
        c.lampCol = new float[]{1.25f, 1.0f, 0.68f};   // Hotaru Lamp: warm brass beam
        c.lampRadius = 16f;
        c.shadowStrength = 0f;         // the sun shadow map means nothing in here
        c.vignette = new float[]{0.16f, 0.12f, 0.3f, 0.3f};
        c.night = 0f;
        PALETTE[CAVERN] = c;
    }

    // ------------------------------------------------------------------ state

    public int zone = SAKURA, prevZone = SAKURA;
    /** The palette being blended in (-1: none) and its weight: 0 = time-of-day look, 1 = the zone palette. With only
     *  the cave palette defined, the blend runs up through the tunnel in and down through the transition out. */
    public int paletteZone = -1;
    public float blend;
    public boolean invulnerable, inTransition;
    /** Seconds since the title card started, or -1 when no card is showing. */
    public float cardTime = -1f;
    public int cardZone = -1;
    private float lastDist = -1f;

    /** Zone of a distance (the run repeats CYCLE). */
    public static int zoneAt(float d) {
        int k = (int) Math.floor(d / ZONE_LEN), n = CYCLE.length;
        return CYCLE[((k % n) + n) % n];
    }

    /** Distance of the next zone boundary at or after d. */
    public static float nextBoundary(float d) {
        return (float) (Math.floor(d / ZONE_LEN) + 1) * ZONE_LEN;
    }

    /** True when the transition at `boundary` leaves the cavern (the set piece turned round: lining before the
     *  boundary, portal on it, cutting after it). */
    public static boolean exitAt(float boundary) { return boundary > 0f && zoneAt(boundary - 1f) == CAVERN; }

    /** Where (in metres along the run) the transition at `boundary` puts its pieces. */
    public static float portalAt(float boundary) { return boundary - LINED; }
    public static float approachAt(float boundary) { return boundary - LINED - APPROACH; }
    public static float boardAt(float boundary) { return boundary - BOARD; }
    public static float leaveAt(float boundary) { return boundary - LINED + BOARD; }

    /** The stretch around the transition at `boundary` where the level generator starts no obstacle pattern (the
     *  lining, the mouth and a run-out either side, so nothing reaches into the set piece). */
    public static float safeFrom(float boundary) { return boundary - LINED - 60f; }
    public static float safeTo(float boundary) { return boundary + 30f; }

    /** If d falls in a set piece's safe stretch, the distance where it ends; otherwise d. */
    public static float skipSafe(float d) {
        float b = nextBoundary(d - 30f);
        return d >= safeFrom(b) && d < safeTo(b) ? safeTo(b) : d;
    }

    /** False where the Sakura Line world (buildings, lamps, trees, bridges) gives way to a set piece or the cavern. */
    public static boolean cityWorldAt(float d) {
        if (zoneAt(d) == CAVERN) return false;
        float b = nextBoundary(d), pb = b - ZONE_LEN;
        if (zoneAt(b) == CAVERN && d >= approachAt(b)) return false;          // cutting and hill into the tunnel
        return !(exitAt(pb) && d < pb + APPROACH);                             // cutting after the way out
    }

    /** False where the Sakura Line track gives way to the set piece's own track (the lined tunnel) or mine track. */
    public static boolean cityTrackAt(float d) {
        if (zoneAt(d) == CAVERN) return false;
        float b = nextBoundary(d);
        return !(zoneAt(b) == CAVERN && d >= portalAt(b));
    }

    /** Back to the start of a run (the first zone, nothing blended, no card). */
    public void reset() {
        zone = prevZone = CYCLE[0];
        paletteZone = -1;
        blend = 0f;
        invulnerable = inTransition = false;
        cardTime = -1f;
        cardZone = -1;
        lastDist = -1f;
    }

    /** Advances to distance d; returns the EV_* events crossed since the last call. */
    public int update(float d, float dt) {
        int ev = 0;
        float b = nextBoundary(d), pb = b - ZONE_LEN;
        int next = zoneAt(b), cur = zoneAt(d);
        if (lastDist >= 0f) {
            ev |= crossed(lastDist, d, approachAt(b)) ? EV_APPROACH : 0;
            ev |= crossed(lastDist, d, portalAt(b)) ? EV_PORTAL : 0;
            ev |= crossed(lastDist, d, boardAt(b)) && isVehicleZone(next) ? EV_BOARD : 0;
            ev |= crossed(lastDist, d, leaveAt(b)) && isVehicleZone(cur) && !isVehicleZone(next) ? EV_LEAVE : 0;
            ev |= crossed(lastDist, d, pb) ? EV_MOUTH : 0;
            ev |= crossed(lastDist, d, approachAt(b) - 60f) ? EV_ZONE_END : 0;
        }
        lastDist = d;
        if (cur != zone) { prevZone = zone; zone = cur; }
        // blend: ramps up over the tunnel into a palette zone, ramps down over the tunnel out of it
        float in = smooth(portalAt(b) - BLEND_LEAD, b, d);       // toward the next zone
        float wNext = PALETTE[next] != null ? 1f : 0f, wCur = PALETTE[cur] != null ? 1f : 0f;
        paletteZone = wCur > 0f ? cur : (wNext > 0f ? next : -1);
        blend = wCur + (wNext - wCur) * in;
        inTransition = d >= approachAt(b);
        invulnerable = d >= portalAt(b) - 1f && d < b + 1f;
        // the title card shows on the way into the tunnel, or coming out of the portal when leaving the cavern
        int cardFor = (ev & EV_PORTAL) != 0 && !exitAt(b) ? next : (ev & EV_MOUTH) != 0 && exitAt(pb) ? cur : -1;
        if (cardFor >= 0 && CARD[cardFor] != null) { cardTime = 0f; cardZone = cardFor; }
        else if (cardTime >= 0f) {
            cardTime += dt;
            if (cardTime > CARD_IN + CARD_HOLD + CARD_OUT) { cardTime = -1f; cardZone = -1; }
        }
        return ev;
    }

    /** Title card slide: 0 = off screen left, 1 = in place; alpha follows the same curve. */
    public float cardSlide() {
        if (cardTime < 0f) return 0f;
        if (cardTime < CARD_IN) return easeOut(cardTime / CARD_IN);
        if (cardTime < CARD_IN + CARD_HOLD) return 1f;
        return 1f - easeIn((cardTime - CARD_IN - CARD_HOLD) / CARD_OUT);
    }

    public static boolean isVehicleZone(int z) { return z == CAVERN || z == RIVER || z == SKY; }

    /** Blends the frame (already lit for the time of day) toward the active zone palette and places the Hotaru Lamp
     *  at Pongo's head (game space) when the cave palette is in effect. */
    public void apply(RenderFrame f, float headX, float headY, float headZ) {
        Palette p = paletteZone >= 0 ? PALETTE[paletteZone] : null;
        float t = blend;
        if (p == null || t <= 0f) { f.lamp[3] = 0f; return; }
        mix(f.lightCol, p.light, t);
        mix(f.shadeCol, p.shade, t);
        mix(f.skinShade, p.skinShade, t);
        mix(f.rimCol, p.rim, t);
        mix(f.skyTop, p.skyTop, t);
        mix(f.skyHor, p.skyHor, t);
        mix(f.skyLow, p.skyLow, t);
        mix(f.fogCol, p.fog, t);
        mix(f.ink, p.ink, t);
        mix(f.vignette, p.vignette, t);
        f.fogStart += (p.fogStart - f.fogStart) * t;
        f.fogEnd += (p.fogEnd - f.fogEnd) * t;
        f.fogMax += (p.fogMax - f.fogMax) * t;
        f.heightFog += (p.heightFog - f.heightFog) * t;
        f.shadowStrength += (p.shadowStrength - f.shadowStrength) * t;
        if (p.night >= 0f) f.night += (p.night - f.night) * t;
        // the lamp's pool grows in as the daylight fades (a little lead so it is on before the dark)
        float lampT = Math.min(1f, t * 1.4f);
        if (p.lampRadius > 0f && lampT > 0f) {
            f.lamp[0] = headX;
            f.lamp[1] = headY + 0.15f;
            f.lamp[2] = headZ - 0.6f;      // a little ahead of her (game forward = -Z)
            f.lamp[3] = p.lampRadius * lampT;
            mix(f.lampCol, p.lampCol, 1f);
        } else f.lamp[3] = 0f;
    }

    // ------------------------------------------------------------------ cave layout

    /** Kit pieces for cave segment i (12 m each from the mouth): out[0] shell/deco seed (1..3), out[1] props seed (1..3),
     *  out[2] 1 if a Y parting (cave_fork, 2 segments long) starts here. Frames go at +1 m and +7 m in every segment.
     *  The first segment after the mouth always uses seed 1 (tunnel_mouth closes against its seam). */
    public static void caveKit(int i, int[] out) {
        int h = i * 0x9E3779B1;
        h ^= h >>> 15;
        out[0] = i == 0 ? 1 : 1 + ((h & 0x7fffffff) % 3);
        out[1] = 1 + (((h >>> 7) & 0x7fffffff) % 3);
        out[2] = (i >= 4 && i % 9 == 4) ? 1 : 0;
    }

    // ------------------------------------------------------------------ helpers

    static boolean crossed(float a, float b, float x) { return a < x && b >= x; }

    static float smooth(float a, float b, float x) {
        float t = Math.max(0f, Math.min(1f, (x - a) / (b - a)));
        return t * t * (3f - 2f * t);
    }

    static float easeOut(float t) { t = Math.max(0f, Math.min(1f, t)); return 1f - (1f - t) * (1f - t) * (1f - t); }

    static float easeIn(float t) { t = Math.max(0f, Math.min(1f, t)); return t * t * t; }

    static void mix(float[] dst, float[] src, float t) {
        if (src == null) return;
        for (int i = 0; i < Math.min(dst.length, src.length); i++) dst[i] += (src[i] - dst[i]) * t;
    }

    static float[] rgb(int h) {
        return new float[]{((h >> 16) & 255) / 255f, ((h >> 8) & 255) / 255f, (h & 255) / 255f};
    }
}
