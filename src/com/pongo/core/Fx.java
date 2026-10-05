package com.pongo.core;

/**
 * The effects system: pooled sprite particles and ribbon trails, written into a RenderFrame as particle quads.
 *
 * Sprites are the vfx_* tiles painted by blender/assets/tex_fx.py (and the cave ones from tex_cave.py) in the Sakura
 * Line look: cel puffs, petals and leaves, water, sparks, glows. Solid sprites carry their own colours and are drawn
 * alpha blended (back to front); light sprites are white and drawn additively, tinted by the particle colour.
 *
 * Particle modes:
 *   BILL    camera-facing, rotating
 *   TUMBLE  camera-facing, flipping about its long axis (petals, leaves, feathers, confetti flutter)
 *   VEL     stretched along its velocity on screen (sparks, spray, streaks)
 *   FLAT    lying on a horizontal plane (ripples, foam, wind rings, landing rings)
 *
 * Every effect in the game is a preset method below (coinPickup, landDust, splash, cartSparks...), so the game side
 * and the vehicle side trigger effects with one call at a world position. Ambient fields (petals, leaves, wisps,
 * fireflies) are kept alive by the caller spawning a few each frame (see com.endlessrush.core.FxLayer).
 *
 * Usage, once per frame after the camera in the RenderFrame is set:
 *   fx.update(dt);
 *   ... presets / trails ...
 *   fx.draw(frame);
 *
 * Pure Java: used by the Android renderer and by the desktop preview.
 */
public final class Fx {
    // ------------------------------------------------------------------ sprites

    public static final int PUFF = 0, PUFF2 = 1, PUFF3 = 2, PETAL = 3, LEAF_BAMBOO = 4, LEAF_MAPLE = 5, STAR = 6, GLOW = 7,
            RING = 8, BURST = 9, SPARK = 10, STREAK = 11, TRAIL = 12, DROPLET = 13, CROWN = 14, FOAM = 15, RIPPLE = 16,
            FLAME = 17, SWIRL = 18, WINDRING = 19, CHIP = 20, FEATHER = 21, CONFETTI = 22, SHARD = 23, WISP = 24,
            MOTE = 25, DRIP = 26, SPLASH = 27, SPARKLE = 28, ROCKDUST = 29, SPRITES = 30;
    public static final String[] SPRITE_NAMES = {"vfx_puff", "vfx_puff2", "vfx_puff3", "vfx_petal", "vfx_leaf_bamboo",
            "vfx_leaf_maple", "vfx_star", "vfx_glow", "vfx_ring", "vfx_burst", "vfx_spark", "vfx_streak", "vfx_trail", "vfx_droplet",
            "vfx_crown", "vfx_foam", "vfx_ripple", "vfx_flame", "vfx_swirl", "vfx_windring", "vfx_chip", "vfx_feather",
            "vfx_confetti", "vfx_shard", "vfx_wisp", "fx_mote", "fx_drip", "fx_splash", "fx_sparkle", "fx_rockdust"};

    public static final int BILL = 0, TUMBLE = 1, VEL = 2, FLAT = 3;

    // palette (linear-ish sRGB, matching the cel shade and ink of the kits)
    public static final float[] GOLD = {1f, 0.84f, 0.38f}, WARM_WHITE = {1f, 0.97f, 0.9f}, PINK = {1f, 0.72f, 0.84f},
            CYAN = {0.62f, 0.94f, 1f}, MINT = {0.6f, 1f, 0.8f}, VIOLET = {0.78f, 0.7f, 1f}, ORANGE = {1f, 0.6f, 0.3f},
            RED = {1f, 0.42f, 0.42f}, SKY = {0.72f, 0.88f, 1f};
    /** Dust colours by surface: ballast/concrete, cave rock, river sand, train roof. */
    public static final float[] DUST_CITY = {0.93f, 0.88f, 0.82f}, DUST_CAVE = {0.74f, 0.7f, 0.8f},
            DUST_SAND = {0.95f, 0.9f, 0.76f}, DUST_ROOF = {0.86f, 0.86f, 0.9f};

    /** Up to this many live particles; spawns past it recycle the oldest. */
    public static final int CAP = 1800;

    private final float[][] uv = new float[SPRITES][];
    private final float[] white;
    private final boolean[] has = new boolean[SPRITES];
    private final boolean[] lightSprite = new boolean[SPRITES];

    // particle state (structure of arrays)
    private final int[] spr = new int[CAP], mode = new int[CAP];
    private final boolean[] add = new boolean[CAP], shrink = new boolean[CAP];
    private final float[] x = new float[CAP], y = new float[CAP], z = new float[CAP];
    private final float[] vx = new float[CAP], vy = new float[CAP], vz = new float[CAP];
    private final float[] grav = new float[CAP], drag = new float[CAP], windK = new float[CAP];
    private final float[] age = new float[CAP], life = new float[CAP];
    private final float[] s0 = new float[CAP], s1 = new float[CAP], aspect = new float[CAP], stretch = new float[CAP];
    private final float[] rot = new float[CAP], spin = new float[CAP], flip = new float[CAP], flipRate = new float[CAP];
    private final float[] cr = new float[CAP], cg = new float[CAP], cb = new float[CAP], ca = new float[CAP];
    private final float[] fadeIn = new float[CAP], flutter = new float[CAP], phase = new float[CAP];
    private int live, cursor;

    /** World wind (m/s) that pushes particles with windK > 0. */
    public final float[] wind = new float[3];
    /** Multiplies the colour of solid (alpha-blended) sprites: the zone light, so white puffs dim in the cave. */
    public final float[] ambient = {1f, 1f, 1f};
    /** 0..1: lowers spawn counts on slow devices (LOW quality). */
    public float density = 1f;
    public float time;

    private long seed = 0x5DEECE66DL;

    public Fx(PongoAssets a) {
        white = inset(a.tile("_white"));
        for (int i = 0; i < SPRITES; i++) {
            float[] t = a.tiles.get(SPRITE_NAMES[i]);
            has[i] = t != null;
            uv[i] = t != null ? inset(t) : a.tile("_white");
        }
        for (int s : new int[]{STAR, GLOW, RING, BURST, SPARK, STREAK, TRAIL, RIPPLE, SWIRL, MOTE, SPARKLE, SPLASH})
            lightSprite[s] = true;
    }

    /** True when pongo.bin carries the fx sprites (older builds don't: then every preset is a no-op). */
    public static boolean available(PongoAssets a) { return a.tiles.get("vfx_puff") != null && a.tiles.get("vfx_star") != null; }

    public boolean hasSprite(int s) { return has[s]; }

    /** The atlas's plain white tile (flat-coloured quads). */
    public float[] whiteUv() { return white; }

    /** Pulls the uv rect in by half a texel-ish so neighbouring atlas tiles never bleed into a sprite's edge. */
    private static float[] inset(float[] t) {
        float du = (t[2] - t[0]) * 0.012f, dv = (t[3] - t[1]) * 0.012f;
        return new float[]{t[0] + du, t[1] + dv, t[2] - du, t[3] - dv};
    }

    // ------------------------------------------------------------------ random

    public float rnd() {
        seed = (seed * 0x5DEECE66DL + 0xBL) & ((1L << 48) - 1);
        return (int) (seed >>> 24) / (float) (1 << 24);
    }

    public float rnd(float a, float b) { return a + (b - a) * rnd(); }

    private int count(float n) {
        float c = n * density;
        int k = (int) c;
        return k + (rnd() < c - k ? 1 : 0);
    }

    // ------------------------------------------------------------------ spawning

    /**
     * Spawns one particle and returns its slot (the setters below tweak it). size: half-size in metres at birth;
     * the particle grows to size * grow over its life. Light sprites are drawn additively.
     */
    public int spawn(int sprite, int md, float px, float py, float pz, float pvx, float pvy, float pvz,
                     float lifeS, float size, float grow, float r, float g, float b, float a) {
        int i;
        if (live < CAP) i = live++;
        else { i = cursor; cursor = (cursor + 1) % CAP; }
        spr[i] = sprite; mode[i] = md; add[i] = lightSprite[sprite]; shrink[i] = false;
        x[i] = px; y[i] = py; z[i] = pz; vx[i] = pvx; vy[i] = pvy; vz[i] = pvz;
        grav[i] = 0; drag[i] = 0; windK[i] = 0;
        age[i] = 0; life[i] = Math.max(0.02f, lifeS);
        s0[i] = size; s1[i] = size * grow; aspect[i] = 1; stretch[i] = 0;
        rot[i] = rnd() * 6.2832f; spin[i] = 0; flip[i] = rnd() * 6.2832f; flipRate[i] = 0;
        cr[i] = r; cg[i] = g; cb[i] = b; ca[i] = a;
        fadeIn[i] = 0.08f; flutter[i] = 0; phase[i] = rnd() * 6.2832f;
        return i;
    }

    public Fx phys(int i, float gravity, float dragK, float windKk) { grav[i] = gravity; drag[i] = dragK; windK[i] = windKk; return this; }

    public Fx spin(int i, float rotation, float spinRate) { rot[i] = rotation; spin[i] = spinRate; return this; }

    public Fx tumble(int i, float flipRateK, float flutterK) { flipRate[i] = flipRateK; flutter[i] = flutterK; return this; }

    public Fx shape(int i, float aspectK, float stretchK) { aspect[i] = aspectK; stretch[i] = stretchK; return this; }

    /** Cel puffs shrink away at the end of their life (instead of fading), like hand-drawn smoke. */
    public Fx pop(int i) { shrink[i] = true; return this; }

    public Fx fade(int i, float in) { fadeIn[i] = in; return this; }

    public Fx blend(int i, boolean additive) { add[i] = additive; return this; }

    public int live() { return live; }

    public void clear() { live = 0; cursor = 0; }

    // ------------------------------------------------------------------ simulation

    public void update(float dt) {
        time += dt;
        if (dt <= 0) return;
        for (int i = 0; i < live; ) {
            age[i] += dt;
            if (age[i] >= life[i]) { kill(i); continue; }
            float d = Math.max(0f, 1f - drag[i] * dt);
            vx[i] = (vx[i] + (wind[0] * windK[i]) * drag[i] * dt) * d;
            vz[i] = (vz[i] + (wind[2] * windK[i]) * drag[i] * dt) * d;
            vy[i] = (vy[i] - grav[i] * dt + (wind[1] * windK[i]) * drag[i] * dt) * d;
            float fl = flutter[i];
            if (fl != 0) {
                // leaves and petals swing side to side as they fall
                float sw = (float) Math.sin(time * 2.6f + phase[i]);
                x[i] += sw * fl * dt;
                y[i] += Math.abs(sw) * fl * 0.25f * dt;
            }
            x[i] += vx[i] * dt; y[i] += vy[i] * dt; z[i] += vz[i] * dt;
            rot[i] += spin[i] * dt;
            flip[i] += flipRate[i] * dt;
            i++;
        }
    }

    private void kill(int i) {
        int j = --live;
        if (i == j) return;
        spr[i] = spr[j]; mode[i] = mode[j]; add[i] = add[j]; shrink[i] = shrink[j];
        x[i] = x[j]; y[i] = y[j]; z[i] = z[j]; vx[i] = vx[j]; vy[i] = vy[j]; vz[i] = vz[j];
        grav[i] = grav[j]; drag[i] = drag[j]; windK[i] = windK[j]; age[i] = age[j]; life[i] = life[j];
        s0[i] = s0[j]; s1[i] = s1[j]; aspect[i] = aspect[j]; stretch[i] = stretch[j];
        rot[i] = rot[j]; spin[i] = spin[j]; flip[i] = flip[j]; flipRate[i] = flipRate[j];
        cr[i] = cr[j]; cg[i] = cg[j]; cb[i] = cb[j]; ca[i] = ca[j];
        fadeIn[i] = fadeIn[j]; flutter[i] = flutter[j]; phase[i] = phase[j];
        if (cursor >= live) cursor = 0;
    }

    // ------------------------------------------------------------------ drawing

    private int[] order = new int[CAP];
    private long[] keys = new long[CAP];
    private final float[] p = new float[12];

    /** Writes every live particle into f (alpha sprites sorted back to front). Call once per frame, last. */
    public void draw(RenderFrame f) {
        float fx = -f.view[2], fy = -f.view[6], fz = -f.view[10];
        int na = 0;
        for (int i = 0; i < live; i++) {
            if (add[i]) { emit(f, i); continue; }
            float dep = (x[i] - f.camPos[0]) * fx + (y[i] - f.camPos[1]) * fy + (z[i] - f.camPos[2]) * fz;
            if (dep < 0.05f) continue;
            // far first: invert the depth so ascending sort = far to near
            keys[na++] = ((long) (Float.floatToIntBits(1e4f - Math.min(dep, 9999f))) << 32) | i;
        }
        java.util.Arrays.sort(keys, 0, na);
        for (int k = 0; k < na; k++) emit(f, (int) (keys[k] & 0xffffffffL));
    }

    private void emit(RenderFrame f, int i) {
        float t = age[i] / life[i];
        float e = 1f - (1f - t) * (1f - t);                     // ease out
        float size = s0[i] + (s1[i] - s0[i]) * e;
        float a = ca[i];
        float fi = fadeIn[i];
        if (fi > 0 && t < fi) a *= t / fi;
        if (shrink[i]) { if (t > 0.55f) size *= 1f - (t - 0.55f) / 0.45f; }
        else if (t > 0.6f) a *= 1f - (t - 0.6f) / 0.4f;
        if (a <= 0.004f || size <= 0.001f) return;
        float r = cr[i], g = cg[i], b = cb[i];
        if (!add[i]) { r *= ambient[0]; g *= ambient[1]; b *= ambient[2]; }
        float hw = size, hh = size * aspect[i];
        int sp = spr[i];
        float[] u = uv[sp];
        switch (mode[i]) {
            case TUMBLE: {
                float c = (float) Math.cos(flip[i]);
                // the back of a petal reads a little darker as it turns over
                if (c < 0 && !add[i]) { r *= 0.86f; g *= 0.82f; b *= 0.9f; }
                f.quad(add[i], x[i], y[i], z[i], hw * Math.max(0.12f, Math.abs(c)), hh, rot[i], u, r, g, b, a);
                break;
            }
            case VEL: {
                velQuad(f, i, hw, hh, u, RenderFrame.packColor(r, g, b, a));
                break;
            }
            case FLAT: {
                float c = (float) Math.cos(rot[i]), s = (float) Math.sin(rot[i]);
                float ax = c * hw, az = s * hw, bx = -s * hh, bz = c * hh;
                int col = RenderFrame.packColor(r, g, b, a);
                f.quadPts(add[i], x[i] - ax - bx, y[i], z[i] - az - bz, x[i] + ax - bx, y[i], z[i] + az - bz,
                        x[i] + ax + bx, y[i], z[i] + az + bz, x[i] - ax + bx, y[i], z[i] - az + bz, u, col, col);
                break;
            }
            default:
                f.quad(add[i], x[i], y[i], z[i], hw, hh, rot[i], u, r, g, b, a);
        }
    }

    /** A quad stretched along the particle's velocity as seen from the camera (u runs along the velocity). */
    private void velQuad(RenderFrame f, int i, float hw, float hh, float[] u, int col) {
        float dx = vx[i], dy = vy[i], dz = vz[i];
        float sp = (float) Math.sqrt(dx * dx + dy * dy + dz * dz);
        if (sp < 1e-4f) { dx = 0; dy = 1; dz = 0; sp = 1; }
        dx /= sp; dy /= sp; dz /= sp;
        float tx = f.camPos[0] - x[i], ty = f.camPos[1] - y[i], tz = f.camPos[2] - z[i];
        // side = dir x toCam
        float sx = dy * tz - dz * ty, sy = dz * tx - dx * tz, sz = dx * ty - dy * tx;
        float sl = (float) Math.sqrt(sx * sx + sy * sy + sz * sz);
        if (sl < 1e-5f) return;
        sx /= sl; sy /= sl; sz /= sl;
        float len = hw * (1f + stretch[i] * sp);
        float ax = dx * len, ay = dy * len, az = dz * len;
        float bx = sx * hh, by = sy * hh, bz = sz * hh;
        f.quadPts(add[i], x[i] - ax - bx, y[i] - ay - by, z[i] - az - bz, x[i] + ax - bx, y[i] + ay - by, z[i] + az - bz,
                x[i] + ax + bx, y[i] + ay + by, z[i] + az + bz, x[i] - ax + bx, y[i] - ay + by, z[i] - az + bz, u, col, col);
    }

    /** One-frame sprite not owned by the pool (auras, glows that follow something). */
    public void now(RenderFrame f, int sprite, float px, float py, float pz, float hw, float hh, float rotation,
                    float r, float g, float b, float a) {
        if (!has[sprite] || a <= 0.004f) return;
        boolean ad = lightSprite[sprite];
        if (!ad) { r *= ambient[0]; g *= ambient[1]; b *= ambient[2]; }
        f.quad(ad, px, py, pz, hw, hh, rotation, uv[sprite], r, g, b, a);
    }

    /** One-frame sprite forced to alpha blending (light sprites that must read over pale daylight ground). */
    public void nowAlpha(RenderFrame f, int sprite, float px, float py, float pz, float hw, float hh,
                         float r, float g, float b, float a) {
        if (!has[sprite] || a <= 0.004f) return;
        f.quad(false, px, py, pz, hw, hh, 0, uv[sprite], r, g, b, a);
    }

    /** One-frame sprite lying flat at height py. */
    public void nowFlat(RenderFrame f, int sprite, float px, float py, float pz, float hw, float hh, float rotation,
                        float r, float g, float b, float a) {
        if (!has[sprite] || a <= 0.004f) return;
        boolean ad = lightSprite[sprite];
        if (!ad) { r *= ambient[0]; g *= ambient[1]; b *= ambient[2]; }
        float c = (float) Math.cos(rotation), s = (float) Math.sin(rotation);
        float ax = c * hw, az = s * hw, bx = -s * hh, bz = c * hh;
        int col = RenderFrame.packColor(r, g, b, a);
        f.quadPts(ad, px - ax - bx, py, pz - az - bz, px + ax - bx, py, pz + az - bz,
                px + ax + bx, py, pz + az + bz, px - ax + bx, py, pz - az + bz, uv[sprite], col, col);
    }

    // ------------------------------------------------------------------ ribbon trails

    /**
     * A ribbon behind something moving (board hover pods, rocket thrusters, glider wingtips, boat wake, magnet coin
     * streams). push() its position every frame, then draw it; old points fade out after `life` seconds.
     */
    public static final class Trail {
        final int n;
        final float[] px, py, pz, pt;
        int head, size;
        public float width, life;
        public float r = 1, g = 1, b = 1, a = 1;
        public boolean additive = true, flat;
        public int sprite = TRAIL;

        public Trail(int points, float width, float life) {
            n = points;
            px = new float[n]; py = new float[n]; pz = new float[n]; pt = new float[n];
            this.width = width;
            this.life = life;
        }

        public Trail color(float[] c, float alpha) { r = c[0]; g = c[1]; b = c[2]; a = alpha; return this; }

        public void reset() { size = 0; }

        /** Adds a point at time t (Fx.time). Points closer than 4 cm to the last one just move it. */
        public void push(float x, float y, float z, float t) {
            if (size > 0) {
                int l = (head - 1 + n) % n;
                float dx = x - px[l], dy = y - py[l], dz = z - pz[l];
                if (dx * dx + dy * dy + dz * dz < 0.0016f && size > 1) { px[l] = x; py[l] = y; pz[l] = z; pt[l] = t; return; }
            }
            px[head] = x; py[head] = y; pz[head] = z; pt[head] = t;
            head = (head + 1) % n;
            if (size < n) size++;
        }
    }

    /** Draws a trail as a camera-facing strip (or a flat one on the ground/water when trail.flat), tapering and
     *  fading toward its old end. */
    public void draw(RenderFrame f, Trail tr) {
        if (tr.size < 2 || !has[tr.sprite]) return;
        float[] u = uv[tr.sprite];
        float um = (u[0] + u[2]) * 0.5f;
        float[] uvSeg = {um, u[1], um, u[3]};
        float pxp = 0, pyp = 0, pzp = 0, sxp = 0, syp = 0, szp = 0, ap = 0;
        boolean first = true;
        for (int k = 0; k < tr.size; k++) {
            int i = (tr.head - tr.size + k + tr.n * 2) % tr.n;
            float ageT = (time - tr.pt[i]) / tr.life;
            if (ageT >= 1f) continue;
            float k1 = (k + 1f) / tr.size;
            float w = tr.width * (0.25f + 0.75f * k1) * (1f - ageT * 0.6f);
            float alpha = tr.a * (1f - ageT) * k1;
            // side vector
            int j = (i + 1) % tr.n;
            boolean last = k == tr.size - 1;
            int i0 = last ? (i - 1 + tr.n) % tr.n : i, i1 = last ? i : j;
            float dx = tr.px[i1] - tr.px[i0], dy = tr.py[i1] - tr.py[i0], dz = tr.pz[i1] - tr.pz[i0];
            float sx, sy, sz;
            if (tr.flat) { sx = -dz; sy = 0; sz = dx; }
            else {
                float tx = f.camPos[0] - tr.px[i], ty = f.camPos[1] - tr.py[i], tz = f.camPos[2] - tr.pz[i];
                sx = dy * tz - dz * ty; sy = dz * tx - dx * tz; sz = dx * ty - dy * tx;
            }
            float sl = (float) Math.sqrt(sx * sx + sy * sy + sz * sz);
            if (sl < 1e-6f) continue;
            sx = sx / sl * w; sy = sy / sl * w; sz = sz / sl * w;
            float cx = tr.px[i], cy = tr.py[i], cz = tr.pz[i];
            if (!first) {
                float rr = tr.r, gg = tr.g, bb = tr.b;
                if (!tr.additive) { rr *= ambient[0]; gg *= ambient[1]; bb *= ambient[2]; }
                f.quadPts(tr.additive, pxp - sxp, pyp - syp, pzp - szp, pxp + sxp, pyp + syp, pzp + szp,
                        cx + sx, cy + sy, cz + sz, cx - sx, cy - sy, cz - sz, uvSeg,
                        RenderFrame.packColor(rr, gg, bb, ap), RenderFrame.packColor(rr, gg, bb, alpha));
            }
            first = false;
            pxp = cx; pyp = cy; pzp = cz; sxp = sx; syp = sy; szp = sz; ap = alpha;
        }
    }

    // ================================================================== presets: running and pickups

    /** Landing: a ring of cel dust puffs rolling out from her feet, bigger the harder she lands (0..1). */
    public void landDust(float px, float py, float pz, float hard, float[] dust) {
        int n = count(5 + hard * 7);
        for (int k = 0; k < n; k++) {
            float ang = k / (float) n * 6.2832f + rnd(-0.3f, 0.3f);
            float sp = rnd(1.6f, 3.2f) * (0.6f + hard);
            int i = spawn(PUFF + (k % 3), BILL, px + (float) Math.cos(ang) * 0.25f, py + 0.12f, pz + (float) Math.sin(ang) * 0.25f,
                    (float) Math.cos(ang) * sp, rnd(0.3f, 0.9f), (float) Math.sin(ang) * sp,
                    rnd(0.45f, 0.75f), rnd(0.28f, 0.4f) * (0.8f + hard * 0.5f), 1.9f, dust[0], dust[1], dust[2], 0.95f);
            phys(i, -0.6f, 4.5f, 0).pop(i).spin(i, rnd() * 6.28f, rnd(-1.5f, 1.5f));
        }
        if (hard > 0.5f) {
            int i = spawn(RING, FLAT, px, py + 0.04f, pz, 0, 0, 0, 0.32f, 0.45f, 4.2f, dust[0], dust[1], dust[2], 0.55f);
            fade(i, 0);
        }
    }

    /** Take-off: a small puff pushed back and down from her feet. */
    public void jumpPuff(float px, float py, float pz, float runSpeed, float[] dust) {
        int n = count(4);
        for (int k = 0; k < n; k++) {
            int i = spawn(PUFF + (k % 3), BILL, px + rnd(-0.25f, 0.25f), py + 0.1f, pz + rnd(0f, 0.3f),
                    rnd(-1.2f, 1.2f), rnd(0.2f, 0.8f), -runSpeed * 0.35f + rnd(0.5f, 1.5f),
                    rnd(0.35f, 0.5f), rnd(0.22f, 0.3f), 1.7f, dust[0], dust[1], dust[2], 0.9f);
            phys(i, 0, 5f, 0).pop(i);
        }
    }

    /** Lane change: a kick of dust on the outer foot and two wind streaks on the side she moves away from. */
    public void dodgeKick(float px, float py, float pz, float dir, float runSpeed, float[] dust) {
        for (int k = 0; k < count(3); k++) {
            int i = spawn(PUFF + k % 3, BILL, px - dir * 0.2f, py + 0.08f, pz + rnd(0, 0.3f), -dir * rnd(1.5f, 3f), rnd(0.3f, 0.9f),
                    -runSpeed * 0.4f, rnd(0.3f, 0.45f), rnd(0.2f, 0.27f), 1.8f, dust[0], dust[1], dust[2], 0.85f);
            phys(i, 0, 5f, 0).pop(i);
        }
        for (int k = 0; k < 2; k++) {
            int i = spawn(STREAK, VEL, px - dir * (0.5f + k * 0.2f), py + 0.7f + k * 0.5f, pz + 0.4f, -dir * 6f, 0, 0,
                    0.22f, 0.7f, 1.3f, 1, 1, 1, 0.55f);
            shape(i, 0.08f, 0);
        }
    }

    /** Rolling / sliding: a low dust trail; call every frame while she slides. */
    public void slideDust(float px, float py, float pz, float runSpeed, float dt, float[] dust) {
        for (int k = 0; k < count(dt * 26); k++) {
            int i = spawn(PUFF + k % 3, BILL, px + rnd(-0.3f, 0.3f), py + 0.1f, pz + rnd(0.1f, 0.5f),
                    rnd(-0.8f, 0.8f), rnd(0.2f, 0.7f), -runSpeed * 0.15f, rnd(0.35f, 0.55f), rnd(0.2f, 0.28f), 1.8f,
                    dust[0], dust[1], dust[2], 0.85f);
            phys(i, 0, 4f, 0).pop(i);
        }
    }

    /** Fast running: occasional footfall puffs. Call every frame while running. */
    public void runDust(float px, float py, float pz, float runSpeed, float dt, float[] dust) {
        float rate = Math.max(0f, (runSpeed - 20f) * 0.6f);
        for (int k = 0; k < count(dt * rate); k++) {
            int i = spawn(PUFF + k % 3, BILL, px + rnd(-0.2f, 0.2f), py + 0.06f, pz + 0.3f, rnd(-0.6f, 0.6f), rnd(0.2f, 0.5f),
                    -runSpeed * 0.1f, rnd(0.25f, 0.4f), rnd(0.14f, 0.2f), 1.8f, dust[0], dust[1], dust[2], 0.7f);
            phys(i, 0, 4f, 0).pop(i);
        }
    }

    /** Coin collected: a gold starburst, a ring, a pop of kira stars and a soft flash. */
    public void coinPickup(float px, float py, float pz, float vzRun) {
        int i = spawn(BURST, BILL, px, py, pz, 0, 0, vzRun, 0.24f, 0.4f, 2.1f, GOLD[0], GOLD[1], GOLD[2], 0.95f);
        fade(i, 0);
        i = spawn(GLOW, BILL, px, py, pz, 0, 0, vzRun, 0.22f, 0.6f, 1.4f, 1f, 0.9f, 0.55f, 0.8f);
        fade(i, 0);
        int n = count(4);
        for (int k = 0; k < n; k++) {
            float ang = k / (float) n * 6.2832f + rnd(-0.4f, 0.4f);
            i = spawn(STAR, BILL, px, py, pz, (float) Math.cos(ang) * rnd(1.5f, 2.6f), (float) Math.sin(ang) * rnd(1.5f, 2.6f) + 1f,
                    vzRun, rnd(0.3f, 0.45f), rnd(0.14f, 0.2f), 0.4f, 1f, 0.95f, 0.7f, 1f);
            phys(i, 3f, 2f, 0).spin(i, 0, rnd(-4f, 4f));
        }
    }

    /** A coin glinting as it spins (call now and then per visible coin). */
    public void coinGlint(float px, float py, float pz) {
        int i = spawn(STAR, BILL, px + rnd(-0.12f, 0.12f), py + rnd(-0.1f, 0.2f), pz, 0, 0, 0, 0.35f, 0.16f, 1.2f, 1f, 0.95f, 0.75f, 0.95f);
        fade(i, 0.35f);
        spin(i, rnd() * 0.5f, 1.5f);
    }

    /** A magnet-pulled coin's streak: gold sparkles left along its flight (call per pulled coin each frame). */
    public void magnetStream(float px, float py, float pz, float dt) {
        for (int k = 0; k < count(dt * 30); k++) {
            int i = spawn(SPARKLE, BILL, px + rnd(-0.1f, 0.1f), py + rnd(-0.1f, 0.1f), pz, 0, rnd(0.2f, 0.6f), 0,
                    rnd(0.25f, 0.4f), rnd(0.07f, 0.11f), 0.3f, GOLD[0], GOLD[1], GOLD[2], 0.9f);
            fade(i, 0);
        }
    }

    /** Power-up collected: burst + ring + rising stars in the power-up's colour, with confetti for the Gacha. */
    public void powerPickup(float px, float py, float pz, float vzRun, float[] c, boolean confetti) {
        int i = spawn(BURST, BILL, px, py, pz, 0, 0, vzRun, 0.3f, 0.4f, 2.6f, c[0], c[1], c[2], 1f);
        fade(i, 0);
        i = spawn(RING, BILL, px, py, pz, 0, 0, vzRun, 0.35f, 0.3f, 4.5f, 1f, 1f, 1f, 0.9f);
        fade(i, 0);
        i = spawn(GLOW, BILL, px, py, pz, 0, 0, vzRun, 0.3f, 0.5f, 1.5f, c[0], c[1], c[2], 0.8f);
        fade(i, 0);
        for (int k = 0; k < count(10); k++) {
            float ang = rnd() * 6.2832f;
            i = spawn(STAR, BILL, px, py, pz, (float) Math.cos(ang) * rnd(1.5f, 3.5f), rnd(1.5f, 4.5f), vzRun + (float) Math.sin(ang) * rnd(1f, 2f),
                    rnd(0.4f, 0.7f), rnd(0.1f, 0.18f), 0.5f, c[0] * 0.5f + 0.5f, c[1] * 0.5f + 0.5f, c[2] * 0.5f + 0.5f, 1f);
            phys(i, 4f, 1.5f, 0).spin(i, 0, rnd(-5f, 5f));
        }
        if (confetti) {
            float[][] cols = {PINK, CYAN, GOLD, MINT, VIOLET, ORANGE};
            for (int k = 0; k < count(22); k++) {
                float ang = rnd() * 6.2832f;
                float[] cc = cols[k % cols.length];
                i = spawn(CONFETTI, TUMBLE, px, py + 0.2f, pz, (float) Math.cos(ang) * rnd(1.5f, 4f), rnd(3f, 6.5f),
                        vzRun + (float) Math.sin(ang) * rnd(1f, 3f), rnd(1.0f, 1.6f), rnd(0.07f, 0.1f), 1f, cc[0], cc[1], cc[2], 1f);
                phys(i, 7f, 1.6f, 0).tumble(i, rnd(6f, 14f), 0.4f).spin(i, rnd() * 6.28f, rnd(-3f, 3f));
            }
        }
    }

    /** Stumble (clipping a train side or a barrier): sparks off the hit side, a puff, two stars. */
    public void stumble(float px, float py, float pz, float side, float runSpeed) {
        sparks(px + side * 0.4f, py + 0.8f, pz, side, 0, 0, 10, runSpeed);
        for (int k = 0; k < count(3); k++) {
            int i = spawn(PUFF + k % 3, BILL, px + side * 0.3f, py + 0.5f, pz, side * rnd(0.5f, 1.5f), rnd(0.5f, 1.2f), -runSpeed * 0.3f,
                    0.45f, 0.18f, 1.8f, DUST_CITY[0], DUST_CITY[1], DUST_CITY[2], 0.9f);
            phys(i, 0, 4f, 0).pop(i);
        }
    }

    /** Sparks flying off in direction (dx, dy, dz) with spread: graze, stumble, cart wheels, pantographs. */
    public void sparks(float px, float py, float pz, float dx, float dy, float dz, int n, float runSpeed) {
        for (int k = 0; k < count(n); k++) {
            float sp = rnd(3f, 8f);
            int i = spawn(SPARK, VEL, px, py, pz, dx * sp + rnd(-2.5f, 2.5f), dy * sp + rnd(0.5f, 4f), dz * sp + rnd(-2.5f, 2.5f) - runSpeed * 0.4f,
                    rnd(0.18f, 0.38f), 0.05f, 0.6f, 1f, rnd(0.7f, 0.9f), 0.45f, 1f);
            phys(i, 14f, 1.5f, 0).shape(i, 0.35f, 0.045f);
            fade(i, 0);
        }
    }

    /** Crash: the impact burst, a fan of rock chips and puffs, and orbiting dizzy stars over her head. The screen
     *  impact flash and radial lines are FxLayer's (RenderFrame.flash / speed). */
    public void crash(float px, float py, float pz, float[] dust) {
        int i = spawn(BURST, BILL, px, py + 1f, pz + 0.5f, 0, 0, 0, 0.32f, 0.7f, 3.4f, 1f, 1f, 0.92f, 1f);
        fade(i, 0);
        i = spawn(RING, BILL, px, py + 1f, pz + 0.5f, 0, 0, 0, 0.4f, 0.6f, 5f, 1f, 0.95f, 0.85f, 0.9f);
        fade(i, 0);
        for (int k = 0; k < count(10); k++) {
            float ang = rnd() * 6.2832f;
            i = spawn(CHIP, TUMBLE, px, py + rnd(0.5f, 1.5f), pz + 0.4f, (float) Math.cos(ang) * rnd(2f, 5f), rnd(2f, 6f), rnd(1.5f, 4f),
                    rnd(0.7f, 1.1f), rnd(0.09f, 0.15f), 1f, dust[0], dust[1], dust[2], 1f);
            phys(i, 16f, 0.8f, 0).tumble(i, rnd(8f, 16f), 0).spin(i, 0, rnd(-6f, 6f));
        }
        for (int k = 0; k < count(9); k++) {
            float ang = rnd() * 6.2832f;
            i = spawn(PUFF + k % 3, BILL, px + (float) Math.cos(ang) * 0.4f, py + rnd(0.3f, 1.6f), pz + 0.4f,
                    (float) Math.cos(ang) * rnd(1f, 2.5f), rnd(0.5f, 2f), rnd(1f, 2.5f), rnd(0.6f, 0.9f), rnd(0.32f, 0.48f), 1.8f,
                    dust[0], dust[1], dust[2], 0.95f);
            phys(i, -0.5f, 3f, 0).pop(i);
        }
        sparks(px, py + 1f, pz + 0.4f, 0, 0.5f, 0.8f, 14, 0);
    }

    /** Dizzy stars circling over her head after a crash (call each frame while she lies there). */
    public void dizzy(RenderFrame f, float px, float py, float pz, float t) {
        for (int k = 0; k < 3; k++) {
            float ang = t * 4f + k * 2.094f;
            now(f, STAR, px + (float) Math.cos(ang) * 0.45f, py + (float) Math.sin(t * 6f + k) * 0.06f,
                    pz + (float) Math.sin(ang) * 0.3f, 0.13f, 0.13f, t * 3f, 1f, 0.92f, 0.5f, 1f);
        }
    }

    /** Omamori revive: a red-gold burst and a ring of petals blown outward. */
    public void revive(float px, float py, float pz) {
        powerPickup(px, py + 1f, pz, 0, RED, false);
        for (int k = 0; k < count(24); k++) {
            float ang = k / 24f * 6.2832f;
            int i = spawn(PETAL, TUMBLE, px, py + 1f, pz, (float) Math.cos(ang) * 5f, rnd(0.5f, 2.5f), (float) Math.sin(ang) * 5f,
                    rnd(1.2f, 1.8f), rnd(0.07f, 0.1f), 1f, 1, 1, 1, 1f);
            phys(i, 1.5f, 1.8f, 0.5f).tumble(i, rnd(4f, 9f), 0.6f);
        }
    }

    // ================================================================== presets: power-ups (held)

    /** Hayate Rocket: wind-swirl flames, smoke puffs and sparks from two nozzles at (tx +- 0.16, ty, tz). She flies
     *  face down with the pack on her back, so the thrust leaves the nozzles backward and a little down. Call each
     *  frame; vzRun is her velocity along z. */
    public void rocketThrust(RenderFrame f, float tx, float ty, float tz, float vzRun, float dt) {
        // thrust direction: backward (+z) and slightly down
        float dx = 0, dy = -0.38f, dz = 0.92f;
        for (int s = -1; s <= 1; s += 2) {
            float nx = tx + s * 0.16f;
            float fl = 0.85f + 0.25f * (float) Math.sin(time * 47f + s * 1.7f);
            beam(f, FLAME, nx, ty, tz, dx, dy, dz, 0.62f * fl, 0.17f, 1, 1, 1, 1f, false);
            nowAlpha(f, GLOW, nx + dx * 0.12f, ty + dy * 0.12f, tz + dz * 0.12f, 0.22f, 0.22f, 1f, 0.75f, 0.45f, 0.45f);
            for (int k = 0; k < count(dt * 18); k++) {
                float back = rnd(0.55f, 0.75f);
                int i = spawn(PUFF + k % 3, BILL, nx + dx * back, ty + dy * back, tz + dz * back,
                        rnd(-0.5f, 0.5f), rnd(-1.6f, -0.6f), vzRun * 0.45f + rnd(1f, 2.5f), rnd(0.35f, 0.55f), rnd(0.12f, 0.17f), 2.4f,
                        1f, 0.96f, 0.92f, 0.95f);
                phys(i, 0, 2f, 0).pop(i);
            }
            if (rnd() < dt * 20) {
                int i = spawn(SPARK, VEL, nx + dz * 0f, ty + dy * 0.5f, tz + dz * 0.5f, rnd(-1.5f, 1.5f), rnd(-3f, -1f), vzRun * 0.5f + rnd(3f, 6f),
                        0.25f, 0.04f, 0.5f, 1f, 0.75f, 0.4f, 1f);
                phys(i, 6f, 1f, 0).shape(i, 0.4f, 0.04f);
            }
        }
    }

    /** A one-frame sprite laid along direction (dx, dy, dz) from its root at (px, py, pz), facing the camera across
     *  its width: the sprite's top edge (v0) sits at the root, its bottom edge at the far end. len and halfW in m. */
    public void beam(RenderFrame f, int sprite, float px, float py, float pz, float dx, float dy, float dz,
                     float len, float halfW, float r, float g, float b, float a, boolean additive) {
        if (!has[sprite] || a <= 0.004f) return;
        float tx = f.camPos[0] - px, ty = f.camPos[1] - py, tz = f.camPos[2] - pz;
        float sx = dy * tz - dz * ty, sy = dz * tx - dx * tz, sz = dx * ty - dy * tx;
        float sl = (float) Math.sqrt(sx * sx + sy * sy + sz * sz);
        if (sl < 1e-5f) return;
        sx = sx / sl * halfW; sy = sy / sl * halfW; sz = sz / sl * halfW;
        float ex = px + dx * len, ey = py + dy * len, ez = pz + dz * len;
        if (!additive) { r *= ambient[0]; g *= ambient[1]; b *= ambient[2]; }
        int col = RenderFrame.packColor(r, g, b, a);
        // quadPts: p0/p1 take uv v1 (bottom), p2/p3 take v0 (top) -> p2/p3 at the root
        f.quadPts(additive, ex - sx, ey - sy, ez - sz, ex + sx, ey + sy, ez + sz, px + sx, py + sy, pz + sz, px - sx, py - sy, pz - sz,
                uv[sprite], col, col);
    }

    /** Maneki Magnet: a gold pull swirl turning on the ground around her and a soft glow. Call each frame. */
    public void magnetAura(RenderFrame f, float px, float py, float pz, float strength) {
        float a = 0.5f * strength;
        nowFlat(f, SWIRL, px, py + 0.05f, pz, 1.25f, 1.25f, -time * 3.2f, GOLD[0], GOLD[1], GOLD[2], a);
        nowFlat(f, RING, px, py + 0.06f, pz, 1.6f + 0.2f * (float) Math.sin(time * 5f), 1.6f + 0.2f * (float) Math.sin(time * 5f), 0,
                GOLD[0], GOLD[1], GOLD[2], a * 0.6f);
    }

    /** Tobi Boots: a flat wind ring bursting out under her feet at take-off, and feathers of wind at the heels. */
    public void bootsJump(float px, float py, float pz, float vzRun) {
        int i = spawn(WINDRING, FLAT, px, py + 0.1f, pz, 0, 0.6f, vzRun * 0.2f, 0.45f, 0.35f, 3.4f, 1, 1, 1, 0.95f);
        fade(i, 0);
        i = spawn(WINDRING, FLAT, px, py + 0.35f, pz, 0, 1.2f, vzRun * 0.2f, 0.4f, 0.25f, 2.6f, 1, 1, 1, 0.8f);
        fade(i, 0);
        spin(i, 1f, 6f);
        for (int k = 0; k < count(6); k++) {
            float ang = rnd() * 6.2832f;
            i = spawn(STREAK, VEL, px + (float) Math.cos(ang) * 0.3f, py + 0.2f, pz + (float) Math.sin(ang) * 0.3f,
                    (float) Math.cos(ang) * 2f, rnd(-5f, -3f), (float) Math.sin(ang) * 2f, 0.25f, 0.3f, 1.2f, 1, 1, 1, 0.6f);
            shape(i, 0.07f, 0);
        }
    }

    /** Tobi Boots worn: little green-white sparkles shed from the heels. Call each frame. */
    public void bootsTrail(float px, float py, float pz, float dt) {
        for (int k = 0; k < count(dt * 18); k++) {
            int i = spawn(SPARKLE, BILL, px + rnd(-0.15f, 0.15f), py + rnd(0.05f, 0.25f), pz + 0.2f, 0, rnd(0.2f, 0.6f), 0,
                    rnd(0.3f, 0.5f), rnd(0.05f, 0.08f), 0.4f, MINT[0], MINT[1], MINT[2], 0.9f);
            fade(i, 0);
        }
    }

    /** Fever Star (x2): a golden aura, orbiting stars and sparkles rising off her. Call each frame. */
    public void feverAura(RenderFrame f, float px, float py, float pz, float dt, float strength) {
        float pulse = 0.85f + 0.15f * (float) Math.sin(time * 9f);
        now(f, GLOW, px, py + 0.95f, pz, 1.05f * pulse, 1.25f * pulse, 0, 1f, 0.78f, 0.35f, 0.45f * strength);
        for (int k = 0; k < 4; k++) {
            float ang = time * 3.2f + k * 1.5708f;
            float h = py + 0.5f + 0.35f * k + 0.15f * (float) Math.sin(time * 2f + k);
            now(f, STAR, px + (float) Math.cos(ang) * 0.6f, h, pz + (float) Math.sin(ang) * 0.45f, 0.12f, 0.12f, time * 2f,
                    1f, 0.9f, 0.5f, strength);
        }
        for (int k = 0; k < count(dt * 16 * strength); k++) {
            int i = spawn(SPARKLE, BILL, px + rnd(-0.45f, 0.45f), py + rnd(0.2f, 1.6f), pz + rnd(-0.2f, 0.3f), 0, rnd(0.8f, 1.6f), 0,
                    rnd(0.4f, 0.6f), rnd(0.06f, 0.1f), 0.3f, GOLD[0], GOLD[1], GOLD[2], 1f);
            fade(i, 0);
        }
    }

    /** Kaze Board: glows under the two hover pods (their ribbons are Trails the caller owns). */
    public void boardHover(RenderFrame f, float px, float py, float pz) {
        for (int s = -1; s <= 1; s += 2) {
            float fl = 0.85f + 0.15f * (float) Math.sin(time * 30f + s);
            now(f, GLOW, px, py - 0.02f, pz + s * 0.45f, 0.45f * fl, 0.32f * fl, 0, CYAN[0], CYAN[1], CYAN[2], 0.8f);
            nowAlpha(f, GLOW, px, py - 0.05f, pz + s * 0.45f, 0.3f * fl, 0.22f * fl, 0.35f, 0.85f, 1f, 0.55f);
        }
        nowFlat(f, RIPPLE, px, py - 0.35f, pz, 0.6f + 0.1f * (float) Math.sin(time * 12f), 0.9f, 0, CYAN[0], CYAN[1], CYAN[2], 0.35f);
    }

    /** Kaze Board breaks (absorbing a crash): shards of the board and a cyan burst. */
    public void boardBreak(float px, float py, float pz) {
        int i = spawn(BURST, BILL, px, py + 0.6f, pz, 0, 0, 0, 0.3f, 0.5f, 3f, CYAN[0], CYAN[1], CYAN[2], 1f);
        fade(i, 0);
        for (int k = 0; k < count(14); k++) {
            float ang = rnd() * 6.2832f;
            i = spawn(SHARD, TUMBLE, px, py + 0.3f, pz, (float) Math.cos(ang) * rnd(2f, 4.5f), rnd(2f, 5f), (float) Math.sin(ang) * rnd(1f, 3f),
                    rnd(0.6f, 1f), rnd(0.07f, 0.12f), 1f, 0.8f, 0.95f, 1f, 1f);
            phys(i, 14f, 0.8f, 0).tumble(i, rnd(8f, 14f), 0).spin(i, rnd() * 6.28f, rnd(-5f, 5f));
        }
    }

    // ================================================================== presets: zones and vehicles

    /** Falling ambient: one petal/leaf/feather drifting down and tumbling, pushed by the wind. */
    public void drifter(int sprite, float px, float py, float pz, float size, float[] c) {
        int i = spawn(sprite, TUMBLE, px, py, pz, rnd(-0.4f, 0.4f), rnd(-1.1f, -0.6f), rnd(-0.4f, 0.4f),
                rnd(4f, 6.5f), size * rnd(0.8f, 1.2f), 1f, c[0], c[1], c[2], 1f);
        phys(i, 0, 0.6f, 1f).tumble(i, rnd(2.5f, 5f), rnd(0.4f, 0.9f)).spin(i, rnd() * 6.28f, rnd(-1.2f, 1.2f));
        fade(i, 0.12f);
    }

    /** Pollen / light motes hanging in sunlit air (the Genshin-style ambient fill): soft, dim, slowly drifting
     *  and twinkling, never bright points. */
    public void pollen(float px, float py, float pz, float[] c) {
        int i = spawn(MOTE, BILL, px, py, pz, rnd(-0.25f, 0.25f), rnd(-0.08f, 0.12f), rnd(-0.25f, 0.25f), rnd(3f, 5f),
                rnd(0.035f, 0.07f), 1.1f, c[0], c[1], c[2], rnd(0.25f, 0.45f));
        phys(i, 0, 0.4f, 0.6f).tumble(i, 0, 0.25f);
        fade(i, 0.3f);
    }

    /** A dandelion seed floating across the way. */
    public void seed(float px, float py, float pz) {
        int i = spawn(STAR, TUMBLE, px, py, pz, rnd(-0.3f, 0.3f), rnd(-0.15f, 0.05f), rnd(-0.3f, 0.3f), rnd(4f, 6f),
                rnd(0.06f, 0.09f), 1f, 1f, 1f, 0.95f, 0.5f);
        phys(i, 0, 0.5f, 1f).tumble(i, rnd(0.6f, 1.2f), 0.5f).spin(i, rnd() * 6.28f, rnd(-0.6f, 0.6f));
        fade(i, 0.2f);
    }

    /** A firefly: a small warm-green glow that wanders and pulses. */
    public void firefly(float px, float py, float pz) {
        int i = spawn(GLOW, BILL, px, py, pz, rnd(-0.4f, 0.4f), rnd(-0.15f, 0.25f), rnd(-0.4f, 0.4f), rnd(2.5f, 4f), rnd(0.06f, 0.09f), 1f,
                0.85f, 1f, 0.5f, 1f);
        phys(i, 0, 0.3f, 0.3f).tumble(i, 0, 0.5f);
        fade(i, 0.3f);
    }

    /** A cloud wisp streaming past the glider, or low mist over the river. */
    public void wisp(float px, float py, float pz, float size, float alpha, float vzRel) {
        int i = spawn(WISP, BILL, px, py, pz, rnd(-0.3f, 0.3f), 0, vzRel, rnd(2.5f, 4f), size, 1.25f, 1, 1, 1, alpha);
        spin(i, rnd(-0.08f, 0.08f), 0).shape(i, 0.5f, 0).fade(i, 0.3f);
    }

    /** A wind streak rushing past (speed, glider, rooftops): a long thin additive line moving toward the camera. */
    public void windStreak(float px, float py, float pz, float vzRel, float alpha) {
        int i = spawn(STREAK, VEL, px, py, pz, 0, 0, vzRel, rnd(0.3f, 0.5f), rnd(0.6f, 1.2f), 1.1f, 1, 1, 1, alpha);
        shape(i, 0.035f, 0).fade(i, 0.25f);
    }

    /** Splash where something meets water: a crown, droplets thrown up and out, a ripple ring and foam.
     *  size ~ 0.5 (paddle) .. 2 (a croc's snap, a stone drop). wy = water height. */
    public void splash(float px, float wy, float pz, float size, float vzRel) {
        int i = spawn(CROWN, BILL, px, wy + 0.25f * size, pz, 0, 0, vzRel, 0.42f, 0.3f * size, 1.6f, 1, 1, 1, 1f);
        pop(i).fade(i, 0).shape(i, 0.9f, 0);
        for (int k = 0; k < count(8 * size); k++) {
            float ang = rnd() * 6.2832f, sp = rnd(1.2f, 3f) * (0.6f + 0.4f * size);
            i = spawn(DROPLET, VEL, px, wy + 0.1f, pz, (float) Math.cos(ang) * sp, rnd(2.5f, 5f) * (0.7f + 0.3f * size),
                    (float) Math.sin(ang) * sp + vzRel, rnd(0.45f, 0.75f), rnd(0.045f, 0.075f) * (0.8f + 0.2f * size), 0.8f, 1, 1, 1, 1f);
            phys(i, 11f, 0.4f, 0).shape(i, 1.6f, 0.03f).fade(i, 0);
        }
        ripple(px, wy, pz, 0.6f * size, vzRel);
        i = spawn(FOAM, FLAT, px, wy + 0.02f, pz, 0, 0, vzRel, rnd(0.8f, 1.2f), 0.35f * size, 2.2f, 1, 1, 1, 0.85f);
        fade(i, 0);
    }

    /** A ripple ring spreading on the water. */
    public void ripple(float px, float wy, float pz, float size, float vzRel) {
        int i = spawn(RIPPLE, FLAT, px, wy + 0.015f, pz, 0, 0, vzRel, rnd(0.8f, 1.1f), 0.2f * size, 5f, 0.9f, 0.97f, 1f, 0.65f);
        fade(i, 0);
    }

    /** Bamboo canoe: bow spray and a foam wake. Call each frame while it moves; speed in m/s along the river,
     *  steer -1..1 (the outer side throws more spray). */
    public void boatSpray(float px, float wy, float pz, float speed, float steer, float dt) {
        float k = Math.min(1.5f, speed / 18f);
        for (int s = -1; s <= 1; s += 2) {
            float side = 1f + 0.8f * Math.max(0f, s * steer);
            for (int n = 0; n < count(dt * 22 * k * side); n++) {
                int i = spawn(DROPLET, VEL, px + s * 0.3f, wy + 0.12f, pz - 1.1f, s * rnd(1.2f, 2.6f) * side, rnd(1.5f, 3.2f), rnd(0.5f, 2.5f),
                        rnd(0.35f, 0.55f), rnd(0.035f, 0.055f), 0.8f, 1, 1, 1, 0.95f);
                phys(i, 10f, 0.5f, 0).shape(i, 1.6f, 0.03f).fade(i, 0);
            }
            for (int n = 0; n < count(dt * 12 * k); n++) {
                int i = spawn(FOAM, FLAT, px + s * rnd(0.35f, 0.6f), wy + 0.02f, pz + rnd(-0.4f, 0.8f), s * rnd(0.3f, 0.9f), 0, rnd(0.5f, 1.5f),
                        rnd(0.9f, 1.4f), rnd(0.14f, 0.22f), 2.4f, 1, 1, 1, 0.8f);
                spin(i, rnd() * 6.28f, rnd(-0.5f, 0.5f)).fade(i, 0.05f);
            }
        }
    }

    /** A paddle stroke entering the water: a small splash and droplets flicked back off the blade. */
    public void paddleSplash(float px, float wy, float pz, float vzRel) {
        splash(px, wy, pz, 0.45f, vzRel);
        for (int k = 0; k < count(5); k++) {
            int i = spawn(DROPLET, VEL, px, wy + 0.3f, pz, rnd(-0.6f, 0.6f), rnd(1.5f, 3f), rnd(1.5f, 3f) + vzRel,
                    0.5f, 0.04f, 0.8f, 1, 1, 1, 0.95f);
            phys(i, 10f, 0.4f, 0).shape(i, 1.6f, 0.03f).fade(i, 0);
        }
    }

    /** Ore cart: sparks from the wheels on a track switch or braking, and grit dust. intensity 0..1. */
    public void cartSparks(float px, float py, float pz, float intensity, float speed) {
        for (int s = -1; s <= 1; s += 2) sparks(px + s * 0.5f, py + 0.08f, pz + rnd(-0.4f, 0.4f), s * 0.5f, 0.6f, 0.8f, (int) (6 * intensity) + 1, speed);
        for (int k = 0; k < count(3 * intensity); k++) {
            int i = spawn(ROCKDUST, BILL, px + rnd(-0.5f, 0.5f), py + 0.1f, pz + 0.5f, rnd(-0.8f, 0.8f), rnd(0.3f, 0.8f), -speed * 0.2f,
                    rnd(0.5f, 0.8f), rnd(0.15f, 0.22f), 1.8f, DUST_CAVE[0], DUST_CAVE[1], DUST_CAVE[2], 0.8f);
            phys(i, 0, 3f, 0).pop(i);
        }
    }

    /** Rockfall / dust trickling from the cave vault: chips and a curtain of rock dust falling from height top. */
    public void rockfall(float px, float top, float pz, float size) {
        for (int k = 0; k < count(6 * size); k++) {
            int i = spawn(CHIP, TUMBLE, px + rnd(-0.6f, 0.6f) * size, top - rnd(0, 0.5f), pz + rnd(-0.6f, 0.6f) * size, rnd(-0.5f, 0.5f), rnd(-2f, 0f), 0,
                    rnd(0.8f, 1.2f), rnd(0.05f, 0.1f) * size, 1f, DUST_CAVE[0], DUST_CAVE[1], DUST_CAVE[2], 1f);
            phys(i, 12f, 0.2f, 0).tumble(i, rnd(6f, 12f), 0);
        }
        for (int k = 0; k < count(8 * size); k++) {
            int i = spawn(PUFF + k % 3, BILL, px + rnd(-0.5f, 0.5f) * size, top - rnd(0.2f, 2.5f), pz + rnd(-0.5f, 0.5f), rnd(-0.3f, 0.3f), rnd(-1.5f, -0.5f), 0,
                    rnd(0.8f, 1.3f), rnd(0.2f, 0.35f) * size, 1.8f, DUST_CAVE[0], DUST_CAVE[1], DUST_CAVE[2], 0.85f);
            phys(i, 0, 1.2f, 0).pop(i);
        }
    }

    /** Crows scattering (the flock on the wires, a sky-zone crow dodged): black feathers spinning down. */
    public void feathers(float px, float py, float pz, int n) {
        for (int k = 0; k < count(n); k++) {
            int i = spawn(FEATHER, TUMBLE, px + rnd(-0.4f, 0.4f), py + rnd(-0.2f, 0.3f), pz + rnd(-0.4f, 0.4f), rnd(-1.5f, 1.5f), rnd(0f, 1.5f),
                    rnd(-1.5f, 1.5f), rnd(2f, 3f), rnd(0.08f, 0.12f), 1f, 1, 1, 1, 1f);
            phys(i, 1.2f, 1.6f, 0.6f).tumble(i, rnd(3f, 6f), rnd(0.5f, 1f)).spin(i, rnd() * 6.28f, rnd(-2f, 2f));
        }
    }

    /** Sky gust: an eddy swirl and streaks blowing sideways across the way (dir -1 / +1). */
    public void gust(float px, float py, float pz, float dir, float size) {
        int i = spawn(SWIRL, BILL, px, py, pz, dir * 3f, 0, 0, 0.9f, 0.5f * size, 2f, 1, 1, 1, 0.55f);
        spin(i, 0, dir * -5f).fade(i, 0.2f);
        for (int k = 0; k < count(8 * size); k++) {
            i = spawn(STREAK, VEL, px - dir * rnd(0.5f, 3f), py + rnd(-1.2f, 1.2f) * size, pz + rnd(-1.5f, 1.5f), dir * rnd(7f, 11f), rnd(-0.5f, 0.5f), 0,
                    rnd(0.4f, 0.7f), rnd(0.6f, 1.1f), 1f, 1, 1, 1, 0.6f);
            shape(i, 0.04f, 0).fade(i, 0.2f);
        }
    }

    /** Thermal: soft rising rings and sparkles in a column (lift for the glider). Call each frame near it. */
    public void thermal(float px, float py, float pz, float dt) {
        if (rnd() < dt * 2.5f) {
            int i = spawn(WINDRING, FLAT, px, py - 1.5f, pz, 0, 2.5f, 0, 1.6f, 0.6f, 2.4f, 1f, 0.96f, 0.85f, 0.7f);
            spin(i, rnd() * 6.28f, 1.5f).fade(i, 0.2f);
        }
        for (int k = 0; k < count(dt * 10); k++) {
            int i = spawn(SPARKLE, BILL, px + rnd(-1f, 1f), py - 1.5f, pz + rnd(-1f, 1f), 0, rnd(2f, 3.5f), 0, rnd(1f, 1.5f), 0.07f, 0.5f,
                    1f, 0.95f, 0.75f, 0.9f);
            fade(i, 0.2f);
        }
    }

    /** The glider bursting through a cloud: the cloud wall parts in big cel puffs thrown out radially, a soft ring
     *  of white opens around her, and wisps stream past on every side. */
    public void cloudBurst(float px, float py, float pz, float vzRel) {
        int i = spawn(RING, BILL, px, py, pz - 1.5f, 0, 0, vzRel * 0.5f, 0.45f, 0.8f, 4.5f, 1f, 1f, 1f, 0.7f);
        fade(i, 0);
        for (int k = 0; k < count(26); k++) {
            float ang = rnd() * 6.2832f, r = rnd(0.6f, 2f);
            float c = (float) Math.cos(ang), s = (float) Math.sin(ang);
            i = spawn(PUFF + k % 3, BILL, px + c * r, py + s * r * 0.8f, pz - rnd(0.5f, 4f),
                    c * rnd(3f, 6f), s * rnd(2.5f, 5f), vzRel * 0.4f, rnd(0.6f, 1.0f), rnd(0.6f, 1.1f), 1.7f, 1, 1, 1, 0.95f);
            phys(i, 0, 1.6f, 0).pop(i).spin(i, rnd() * 6.28f, rnd(-1f, 1f));
        }
        for (int k = 0; k < count(10); k++) {
            float ang = rnd() * 6.2832f, r = rnd(1.5f, 3.5f);
            i = spawn(WISP, BILL, px + (float) Math.cos(ang) * r, py + (float) Math.sin(ang) * r * 0.7f, pz - rnd(2f, 10f),
                    (float) Math.cos(ang) * 1.5f, (float) Math.sin(ang), vzRel + 10f, rnd(0.6f, 0.9f), rnd(1.2f, 2f), 1.3f, 1, 1, 1, 0.8f);
            shape(i, 0.45f, 0).fade(i, 0.1f).spin(i, ang + 1.5708f, 0);
        }
        for (int k = 0; k < count(12); k++)
            windStreak(px + rnd(-2.5f, 2.5f), py + rnd(-2f, 2f), pz - rnd(1f, 8f), vzRel - 16f, 0.7f);
    }

    /** Pantograph / catenary sparks on the Express Rooftops: a blue-white crackle at height py. */
    public void pantoSparks(float px, float py, float pz, float speed) {
        int i = spawn(STAR, BILL, px, py, pz, 0, 0, 0, 0.12f, 0.25f, 1.4f, 0.75f, 0.85f, 1f, 1f);
        fade(i, 0);
        for (int k = 0; k < count(6); k++) {
            int j = spawn(SPARK, VEL, px, py, pz, rnd(-2f, 2f), rnd(-1f, 2.5f), rnd(1f, 4f) + speed * 0.1f, rnd(0.15f, 0.3f), 0.04f, 0.6f,
                    0.8f, 0.9f, 1f, 1f);
            phys(j, 12f, 1f, 0).shape(j, 0.35f, 0.04f).fade(j, 0);
        }
    }

    /** A koi leaping out of the river: an arc of droplets and splashes where it leaves and re-enters. */
    public void koiLeap(float px, float wy, float pz, float vzRel) {
        splash(px, wy, pz, 0.8f, vzRel);
        for (int k = 0; k < count(10); k++) {
            int i = spawn(DROPLET, VEL, px + rnd(-0.1f, 0.1f), wy + 0.3f, pz, rnd(0.6f, 1.6f), rnd(4f, 6f), vzRel + rnd(-0.3f, 0.3f),
                    rnd(0.7f, 1f), 0.045f, 0.8f, 1, 1, 1, 1f);
            phys(i, 10f, 0.2f, 0).shape(i, 1.6f, 0.03f).fade(i, 0);
        }
    }

    /** Crystal chime: a cave crystal struck (cart graze, bat swarm passing) sheds shards and violet sparkles. */
    public void crystalChime(float px, float py, float pz, float[] c) {
        int i;
        for (int k = 0; k < count(4); k++) {
            float ang = rnd() * 6.2832f;
            i = spawn(SPARKLE, BILL, px, py, pz, (float) Math.cos(ang) * rnd(1f, 2.5f), rnd(0.5f, 2.5f), (float) Math.sin(ang) * rnd(1f, 2.5f),
                    rnd(0.4f, 0.7f), rnd(0.06f, 0.09f), 0.4f, c[0], c[1], c[2], 0.55f);
            phys(i, 3f, 2f, 0);
        }
        for (int k = 0; k < count(4); k++) {
            i = spawn(SHARD, TUMBLE, px, py, pz, rnd(-2f, 2f), rnd(1f, 3f), rnd(-2f, 2f), rnd(0.6f, 0.9f), rnd(0.05f, 0.08f), 1f,
                    c[0] * 0.4f + 0.6f, c[1] * 0.4f + 0.6f, c[2] * 0.4f + 0.6f, 1f);
            phys(i, 12f, 0.5f, 0).tumble(i, rnd(8f, 12f), 0);
        }
    }

    /** Steam puffing from a train or a vent: one cel puff rising and growing. */
    public void steam(float px, float py, float pz, float vy0, float size) {
        int i = spawn(PUFF + (int) (rnd() * 3), BILL, px, py, pz, rnd(-0.3f, 0.3f), vy0, 0, rnd(0.9f, 1.3f), size, 2.2f, 1, 1, 1, 0.9f);
        phys(i, 0, 1f, 0.8f).pop(i).spin(i, rnd() * 6.28f, rnd(-0.6f, 0.6f));
    }
}
