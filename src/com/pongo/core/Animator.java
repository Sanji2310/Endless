package com.pongo.core;

/**
 * Skeletal animation player: samples baked clips (parent-relative rotation + translation per bone),
 * cross-fades between clips, runs forward kinematics and produces the GPU skinning palette
 * (3 vec4 rows per bone). Bones flagged dynamic (scarf tails, twin-tails...) get a spring
 * simulation on top so they trail behind the motion and flutter in the wind.
 */
public final class Animator {
    public final PongoAssets.Skeleton sk;
    public final int n;
    public final float[][] local, world;
    public final float[] palette;
    public float speed = 1f;

    private PongoAssets.Clip cur, prev;
    private float tCur, tPrev, fade = 1f, fadeDur = 0.0001f;

    private final float[] qa = new float[4], qb = new float[4], ta = new float[3], tb = new float[3];

    // dynamic chain state: tip direction per dynamic bone (world space) and its velocity
    private final float[][] dynDir, dynVel;
    private boolean dynInit;
    public final float[] wind = {0f, 0f, 0f};
    public final float[] velocity = {0f, 0f, 0f};
    private final float[] tmp = new float[16], tmp2 = new float[16];

    public Animator(PongoAssets.Skeleton sk) {
        this.sk = sk;
        n = sk.bones;
        local = new float[n][16];
        world = new float[n][16];
        palette = new float[n * 12];
        dynDir = new float[n][3];
        dynVel = new float[n][3];
        for (int b = 0; b < n; b++) {
            Mat4.copy(local[b], sk.restLocal[b]);
            Mat4.copy(world[b], sk.rest[b]);
        }
    }

    public PongoAssets.Clip clip() { return cur; }

    public float time() { return tCur; }

    public boolean playing(String name) { return cur != null && cur.name.equals(name); }

    /** Start a clip with a cross-fade. Re-playing the current looping clip keeps its phase. */
    public void play(String name, float fadeTime) {
        PongoAssets.Clip c = sk.clip(name);
        if (c == null) return;
        if (c == cur && (c.loop || tCur < c.duration())) return;
        if (cur != null && fadeTime > 0) {
            prev = cur;
            tPrev = tCur;
            fade = 0f;
            fadeDur = fadeTime;
        } else {
            prev = null;
            fade = 1f;
        }
        cur = c;
        tCur = 0f;
    }

    /** Restart the clip from the beginning even if it is already playing. */
    public void restart(String name, float fadeTime) {
        PongoAssets.Clip c = sk.clip(name);
        if (c == null) return;
        if (cur != null && fadeTime > 0) {
            prev = cur;
            tPrev = tCur;
            fade = 0f;
            fadeDur = fadeTime;
        }
        cur = c;
        tCur = 0f;
    }

    public void setPhase(float t01) { if (cur != null) tCur = t01 * cur.duration(); }

    public boolean finished() { return cur != null && !cur.loop && tCur >= cur.duration(); }

    public void update(float dt) {
        tCur += dt * speed;
        tPrev += dt * speed;
        if (fade < 1f) fade = Math.min(1f, fade + dt / fadeDur);
        evaluate(dt);
    }

    private void sample(PongoAssets.Clip c, float t, int b, float[] q, float[] tr) {
        int frames = c.frames;
        float f = t * c.fps;
        int i0, i1;
        float a;
        if (c.loop) {
            f = f % frames;
            if (f < 0) f += frames;
            i0 = (int) f;
            i1 = (i0 + 1) % frames;
            a = f - i0;
        } else {
            if (f >= frames - 1) { i0 = i1 = frames - 1; a = 0; }
            else if (f <= 0) { i0 = 0; i1 = Math.min(1, frames - 1); a = 0; }
            else { i0 = (int) f; i1 = i0 + 1; a = f - i0; }
        }
        int o0 = (i0 * n + b) * 7, o1 = (i1 * n + b) * 7;
        float[] d = c.data;
        slerp(d[o0], d[o0 + 1], d[o0 + 2], d[o0 + 3], d[o1], d[o1 + 1], d[o1 + 2], d[o1 + 3], a, q);
        tr[0] = d[o0 + 4] + (d[o1 + 4] - d[o0 + 4]) * a;
        tr[1] = d[o0 + 5] + (d[o1 + 5] - d[o0 + 5]) * a;
        tr[2] = d[o0 + 6] + (d[o1 + 6] - d[o0 + 6]) * a;
    }

    static void slerp(float ax, float ay, float az, float aw, float bx, float by, float bz, float bw, float t, float[] out) {
        float dot = ax * bx + ay * by + az * bz + aw * bw;
        if (dot < 0) { bx = -bx; by = -by; bz = -bz; bw = -bw; dot = -dot; }
        float s0, s1;
        if (dot > 0.9995f) {
            s0 = 1 - t;
            s1 = t;
        } else {
            float th = (float) Math.acos(dot);
            float st = (float) Math.sin(th);
            s0 = (float) Math.sin((1 - t) * th) / st;
            s1 = (float) Math.sin(t * th) / st;
        }
        float x = ax * s0 + bx * s1, y = ay * s0 + by * s1, z = az * s0 + bz * s1, w = aw * s0 + bw * s1;
        float l = (float) Math.sqrt(x * x + y * y + z * z + w * w);
        if (l < 1e-8f) l = 1;
        out[0] = x / l; out[1] = y / l; out[2] = z / l; out[3] = w / l;
    }

    private void evaluate(float dt) {
        float w = fade >= 1f ? 1f : fade * fade * (3 - 2 * fade);
        for (int b = 0; b < n; b++) {
            if (cur == null) {
                Mat4.copy(local[b], sk.restLocal[b]);
            } else {
                sample(cur, tCur, b, qa, ta);
                if (prev != null && w < 1f) {
                    sample(prev, tPrev, b, qb, tb);
                    slerp(qb[0], qb[1], qb[2], qb[3], qa[0], qa[1], qa[2], qa[3], w, qa);
                    ta[0] = tb[0] + (ta[0] - tb[0]) * w;
                    ta[1] = tb[1] + (ta[1] - tb[1]) * w;
                    ta[2] = tb[2] + (ta[2] - tb[2]) * w;
                }
                Mat4.fromQT(local[b], qa[0], qa[1], qa[2], qa[3], ta[0], ta[1], ta[2]);
            }
            int p = sk.parent[b];
            if (p >= 0) Mat4.mul(world[b], world[p], local[b]);
            else Mat4.copy(world[b], local[b]);
        }
        if (dt > 0) simulateDynamics(dt);
        for (int b = 0; b < n; b++) {
            Mat4.mul(tmp, world[b], sk.invRest[b]);
            int o = b * 12;
            palette[o] = tmp[0]; palette[o + 1] = tmp[4]; palette[o + 2] = tmp[8]; palette[o + 3] = tmp[12];
            palette[o + 4] = tmp[1]; palette[o + 5] = tmp[5]; palette[o + 6] = tmp[9]; palette[o + 7] = tmp[13];
            palette[o + 8] = tmp[2]; palette[o + 9] = tmp[6]; palette[o + 10] = tmp[10]; palette[o + 11] = tmp[14];
        }
    }

    /**
     * Spring chains: each dynamic bone keeps a lagging world direction that is pulled toward
     * the animated direction, gravity and the wind/drag, then the bone is re-aimed along it.
     */
    private void simulateDynamics(float dt) {
        dt = Math.min(dt, 1f / 30f);
        for (int b = 0; b < n; b++) {
            if (sk.dyn[b] == 0) continue;
            float[] m = world[b];
            // animated bone direction (local +Y of the bone in model space)
            float ax = m[4], ay = m[5], az = m[6];
            float al = (float) Math.sqrt(ax * ax + ay * ay + az * az);
            if (al < 1e-6f) continue;
            ax /= al; ay /= al; az /= al;
            float[] d = dynDir[b], v = dynVel[b];
            if (!dynInit) { d[0] = ax; d[1] = ay; d[2] = az; v[0] = v[1] = v[2] = 0; }
            // target: animated direction blended with gravity and wind/drag (opposite to motion)
            float tx = ax * 0.55f + (wind[0] - velocity[0] * 0.07f);
            float ty = ay * 0.55f - 0.45f + (wind[1] - velocity[1] * 0.07f);
            float tz = az * 0.55f + (wind[2] - velocity[2] * 0.07f);
            float tl = (float) Math.sqrt(tx * tx + ty * ty + tz * tz);
            if (tl > 1e-6f) { tx /= tl; ty /= tl; tz /= tl; }
            float k = 60f, damp = 7f;
            v[0] += ((tx - d[0]) * k - v[0] * damp) * dt;
            v[1] += ((ty - d[1]) * k - v[1] * damp) * dt;
            v[2] += ((tz - d[2]) * k - v[2] * damp) * dt;
            d[0] += v[0] * dt; d[1] += v[1] * dt; d[2] += v[2] * dt;
            float dl = (float) Math.sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]);
            if (dl < 1e-6f) continue;
            d[0] /= dl; d[1] /= dl; d[2] /= dl;
            // rotate the bone so its +Y axis points along d (minimal rotation from the animated axis)
            float cx = ay * d[2] - az * d[1], cy = az * d[0] - ax * d[2], cz = ax * d[1] - ay * d[0];
            float cosA = ax * d[0] + ay * d[1] + az * d[2];
            float sinA = (float) Math.sqrt(cx * cx + cy * cy + cz * cz);
            if (sinA < 1e-5f) continue;
            float ang = (float) Math.toDegrees(Math.atan2(sinA, cosA));
            // rotation about axis c through the bone head, applied in model space
            Mat4.setIdentity(tmp2);
            Mat4.translate(tmp2, m[12], m[13], m[14]);
            Mat4.rotate(tmp2, ang, cx / sinA, cy / sinA, cz / sinA);
            Mat4.translate(tmp2, -m[12], -m[13], -m[14]);
            Mat4.mul(m, tmp2, m);
            // children of this bone follow
            for (int c = b + 1; c < n; c++) {
                int p = sk.parent[c];
                if (p >= 0) Mat4.mul(world[c], world[p], local[c]);
            }
        }
        dynInit = true;
    }

    /** Model-space transform of a bone (for attachments like the rocket pack or glider). */
    public float[] bone(String name) {
        int b = sk.bone(name);
        return b >= 0 ? world[b] : null;
    }
}
