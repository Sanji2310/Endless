package com.pongo.core;

/**
 * Time of day for the toon renderer (docs/PONGO_DESIGN.md section 5): five phases that follow each other as the run
 * goes on, each a full set of frame lighting (sun, cel light and shadow tints, rim, sky, clouds, fog, ink, night).
 * Hiru (day) is the light of the Sakura Line design renders: blender/assets/studio.py's sun and sky with the
 * PongoToon defaults (light tint, the 0xB3ACDC lilac shadow, 0x2A2233 ink).
 *
 * A zone palette (Zones.apply) is blended on top of this, so the cavern keeps its own look whatever the hour.
 * Pure Java, no allocation per frame.
 */
public final class Lighting {
    private Lighting() {}

    public static final int ASA = 0, HIRU = 1, YUYAKE = 2, TASOGARE = 3, YORU = 4, PHASES = 5;
    public static final String[] NAME = {"Asa", "Hiru", "Yuyake", "Tasogare", "Yoru"};
    /** Metres of running per phase. */
    public static final float PHASE_LEN = 1100f;
    /** The run starts in the day, like the renders, and goes day -> sunset -> dusk -> night -> dawn -> day. */
    public static final int START = HIRU;
    /** Share of each phase spent blending into the next one (the rest holds the phase's own look). */
    public static final float BLEND = 0.22f;
    /** Aerial perspective strength by day (Shaders applyFog: the blue haze layering the middle distance). */
    public static final float AIR = 0.32f;

    /** One phase. Colours are sRGB like the material colours; the renderer shades in that space. */
    public static final class Key {
        public final float[] sunDir = new float[3], light, shade, skinShade, rim, skyTop, skyHor, skyLow, sunCol, fog, ink,
                cloudLit, cloudShade;
        public float night, haze, bounce, fogStart, fogEnd, heightFog, cover;

        Key(float sx, float sy, float sz, int light, int shade, int skin, int rim, int top, int hor, int low, int sun,
            int fog, int ink, int cloudLit, int cloudShade) {
            float l = (float) Math.sqrt(sx * sx + sy * sy + sz * sz);
            sunDir[0] = sx / l; sunDir[1] = sy / l; sunDir[2] = sz / l;
            this.light = rgb(light); this.shade = rgb(shade); this.skinShade = rgb(skin); this.rim = rgb(rim);
            skyTop = rgb(top); skyHor = rgb(hor); skyLow = rgb(low); sunCol = rgb(sun); this.fog = rgb(fog);
            this.ink = rgb(ink); this.cloudLit = rgb(cloudLit); this.cloudShade = rgb(cloudShade);
        }

        Key set(float night, float haze, float bounce, float fogStart, float fogEnd, float heightFog, float cover) {
            this.night = night; this.haze = haze; this.bounce = bounce; this.fogStart = fogStart; this.fogEnd = fogEnd;
            this.heightFog = heightFog; this.cover = cover;
            return this;
        }
    }

    /** Sun directions are in game space (x right, y up, the run heads to -z; +z is behind the runner). */
    public static final Key[] KEYS = new Key[PHASES];

    static {
        // Asa: low pink-gold sun ahead and to the right, lilac shadows, morning mist along the ground
        KEYS[ASA] = new Key(0.55f, 0.24f, -0.8f, 0xFFDCD8, 0xA890C4, 0xE6AEB8, 0xFFD4B8, 0x8CB2E8, 0xFFD8D2, 0xE8CCDA,
                0xFFC2A0, 0xF2DCE6, 0x30243A, 0xFFEEEA, 0xC4A6CC).set(0.05f, 0.5f, 0.3f, 30f, 160f, 0.16f, 0.35f);
        // Hiru: the renders. High sun behind and to the right, crisp lilac shadows, cyan sky, big white clouds
        KEYS[HIRU] = new Key(0.45f, 0.8f, 0.4f, 0xFFFBF5, 0xB3ACDC, 0xEDBFC4, 0xFFF3E0, 0x7EC8F8, 0xE8F6FF, 0xD0E4F4,
                0xFFF2D8, 0xDCEEFB, 0x2A2233, 0xFFFFFF, 0xC9C4EA).set(0f, 0.18f, 0.35f, 60f, 200f, 0f, 0.55f);
        // Yuyake: orange sun low ahead on the left, long shadows, crimson clouds, warm glow in the haze
        KEYS[YUYAKE] = new Key(-0.45f, 0.2f, -0.87f, 0xFFC896, 0x9070AC, 0xCC8E9E, 0xFFB070, 0x5A7AC8, 0xFFB47E, 0xF0A890,
                0xFF9C54, 0xF4BA94, 0x3A1E30, 0xFFD2A4, 0xB0729C).set(0f, 0.65f, 0.3f, 50f, 175f, 0.04f, 0.6f);
        // Tasogare: the sun just gone, purple-blue sky, soft violet light, lamps and windows coming on
        KEYS[TASOGARE] = new Key(-0.8f, 0.14f, -0.35f, 0xBCAAE6, 0x52488A, 0x8C6C96, 0xC8A2FF, 0x2C306E, 0xB48CC8, 0x6A5A9A,
                0xEA92B2, 0x8070AA, 0x1E1630, 0xE2AAD2, 0x5E5292).set(0.55f, 0.45f, 0.35f, 40f, 165f, 0.06f, 0.5f);
        // Yoru: indigo, moonlight from behind on the right (the "sun" is the moon), glowing windows, stars
        KEYS[YORU] = new Key(0.4f, 0.7f, 0.5f, 0x92A2E2, 0x36386E, 0x605482, 0x9CB8FF, 0x0C1030, 0x2A3466, 0x141A3C,
                0x6474B4, 0x1E2650, 0x0A0A1A, 0x5C6CAA, 0x22264E).set(1f, 0.2f, 0.25f, 35f, 150f, 0.05f, 0.35f);
    }

    /** Phase position for a run distance: an integer part (the phase) and a fraction (how far into it). */
    public static float phaseAt(float distance) {
        float p = START + Math.max(0f, distance) / PHASE_LEN;
        return p % PHASES;
    }

    /** Which phase is showing at a distance (for title cards and stings). */
    public static int phaseIndex(float distance) { return (int) phaseAt(distance) % PHASES; }

    /**
     * Fills the frame's lighting for a phase position (see phaseAt). Each phase holds its look and blends into the
     * next over the last BLEND of its length.
     */
    public static void apply(RenderFrame f, float phase) {
        int i = ((int) Math.floor(phase) % PHASES + PHASES) % PHASES;
        float frac = phase - (float) Math.floor(phase);
        float t = frac < 1f - BLEND ? 0f : (frac - (1f - BLEND)) / BLEND;
        t = t * t * (3f - 2f * t);
        apply(f, KEYS[i], KEYS[(i + 1) % PHASES], t);
    }

    /** Fills the frame with a blend of two keys (t = 0: a, 1: b). */
    public static void apply(RenderFrame f, Key a, Key b, float t) {
        for (int c = 0; c < 3; c++) {
            f.sunDir[c] = a.sunDir[c] + (b.sunDir[c] - a.sunDir[c]) * t;
        }
        float l = (float) Math.sqrt(f.sunDir[0] * f.sunDir[0] + f.sunDir[1] * f.sunDir[1] + f.sunDir[2] * f.sunDir[2]);
        for (int c = 0; c < 3; c++) f.sunDir[c] /= Math.max(l, 1e-4f);
        mix(f.lightCol, a.light, b.light, t);
        mix(f.shadeCol, a.shade, b.shade, t);
        mix(f.skinShade, a.skinShade, b.skinShade, t);
        mix(f.rimCol, a.rim, b.rim, t);
        mix(f.skyTop, a.skyTop, b.skyTop, t);
        mix(f.skyHor, a.skyHor, b.skyHor, t);
        mix(f.skyLow, a.skyLow, b.skyLow, t);
        mix(f.sunCol, a.sunCol, b.sunCol, t);
        mix(f.fogCol, a.fog, b.fog, t);
        mix(f.ink, a.ink, b.ink, t);
        mix(f.cloudLit, a.cloudLit, b.cloudLit, t);
        mix(f.cloudShade, a.cloudShade, b.cloudShade, t);
        f.night = lerp(a.night, b.night, t);
        f.haze[0] = lerp(a.haze, b.haze, t);
        f.haze[1] = lerp(a.bounce, b.bounce, t);
        f.fogStart = lerp(a.fogStart, b.fogStart, t);
        f.fogEnd = lerp(a.fogEnd, b.fogEnd, t);
        f.fogMax = 1f;
        f.heightFog = lerp(a.heightFog, b.heightFog, t);
        f.cloud[0] = lerp(a.cover, b.cover, t);
        // aerial haze: thinner at night, when the distance goes dark rather than pale
        f.haze[3] = AIR * (1f - 0.5f * f.night);
        // the moon rides opposite the sun by day; at night the light itself is moonlight
        float n = f.night;
        f.moonDir[0] = lerp(-0.3f, f.sunDir[0], n);
        f.moonDir[1] = lerp(0.6f, f.sunDir[1], n);
        f.moonDir[2] = lerp(-0.7f, f.sunDir[2], n);
    }

    private final static float[] lv = new float[16], lp = new float[16];

    /**
     * Points the sun shadow map at a box of the given radius around (cx, cy, cz), snapped to whole shadow texels so
     * the edges don't crawl as the camera moves. Turns shadows on at the given map size.
     */
    public static void fitShadow(RenderFrame f, float cx, float cy, float cz, float radius, int size) {
        float[] s = f.sunDir;
        float back = radius * 3f;
        // a light view anchored at the world origin (not at the centre), so snapping is to a fixed texel grid
        Mat4.lookAt(lv, 0, 0, 0, -s[0], -s[1], -s[2], Math.abs(s[1]) > 0.99f ? 1 : 0, Math.abs(s[1]) > 0.99f ? 0 : 1, 0);
        float texel = 2f * radius / size;
        float lx = lv[0] * cx + lv[4] * cy + lv[8] * cz + lv[12];
        float ly = lv[1] * cx + lv[5] * cy + lv[9] * cz + lv[13];
        float depth = -(lv[2] * cx + lv[6] * cy + lv[10] * cz + lv[14]);
        lx = (float) Math.floor(lx / texel) * texel;
        ly = (float) Math.floor(ly / texel) * texel;
        Mat4.ortho(lp, lx - radius, lx + radius, ly - radius, ly + radius, depth - back, depth + radius * 2f);
        Mat4.mul(f.shadowVP, lp, lv);
        f.shadowOn = true;
        f.shadowSize = size;
    }

    static float[] rgb(int hex) {
        return new float[]{((hex >> 16) & 255) / 255f, ((hex >> 8) & 255) / 255f, (hex & 255) / 255f};
    }

    private static float lerp(float a, float b, float t) { return a + (b - a) * t; }

    private static void mix(float[] out, float[] a, float[] b, float t) {
        for (int c = 0; c < 3; c++) out[c] = a[c] + (b[c] - a[c]) * t;
    }
}
