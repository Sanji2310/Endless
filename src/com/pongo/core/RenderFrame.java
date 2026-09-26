package com.pongo.core;

import java.io.DataOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;

/**
 * Everything the renderer needs for one frame: camera, lighting/time-of-day uniforms,
 * mesh draws (with bone palettes), particle quads and screen overlays.
 * Produced by Scene on the game thread, consumed by GLRenderer (Android) or the WebGL harness.
 */
public final class RenderFrame {
    public static final int D_NO_OUTLINE = 1, D_NO_SHADOW = 2, D_BLEND = 4, D_NO_FOG = 8, D_NO_CULL = 16;

    // camera
    public int screenW = 1, screenH = 1;
    public final float[] view = new float[16], proj = new float[16], viewProj = new float[16], invViewProj = new float[16];
    public final float[] camPos = new float[3];

    // lighting / time of day
    public final float[] sunDir = {0.4f, 0.8f, 0.45f};
    public final float[] lightCol = {1f, 0.97f, 0.92f};
    public final float[] shadeCol = {0.62f, 0.6f, 0.86f};
    public final float[] skinShade = {0.93f, 0.68f, 0.7f};
    public final float[] rimCol = {1f, 0.95f, 0.85f};
    public final float[] skyTop = {0.3f, 0.62f, 0.95f};
    public final float[] skyHor = {0.82f, 0.92f, 1f};
    public final float[] skyLow = {0.7f, 0.8f, 0.9f};
    public final float[] sunCol = {1f, 0.95f, 0.8f};
    public final float[] moonDir = {-0.3f, 0.6f, -0.7f};
    public final float[] fogCol = {0.8f, 0.9f, 1f};
    public final float[] ink = {0.16f, 0.13f, 0.2f};
    public float fogStart = 60, fogEnd = 190, fogMax = 1, heightFog = 0;
    public float night, time;
    public final float[] wind = {0.08f, 0f, 0.05f, 0f};
    public final float[] lamp = new float[4];
    public final float[] lampCol = {1f, 0.8f, 0.5f};
    public float outlinePx = 2.2f;

    // shadow
    public boolean shadowOn;
    public int shadowSize = 2048;
    public final float[] shadowVP = new float[16];
    public float shadowBias = 0.0015f, shadowStrength = 1f;

    // draws
    public int count;
    public int[] mesh = new int[512];
    public int[] flags = new int[512];
    public float[][] model = new float[512][];
    public float[] tint = new float[512 * 4];
    public float[] emis = new float[512];
    public int[] boneStart = new int[512], boneRows = new int[512];
    public float[] bones = new float[4 * 3 * Shaders.MAX_BONES * 16];
    public int boneUsed;

    // particles: 4 vertices per quad, 6 ints per vertex (float bits of x y z u v, packed RGBA colour)
    public int[] alphaQuads = new int[6 * 4 * 1024];
    public int alphaCount;
    public int[] addQuads = new int[6 * 4 * 1024];
    public int addCount;

    // overlays
    public final float[] speed = new float[4];
    public final float[] flash = new float[4];
    public final float[] vignette = {0.1f, 0.08f, 0.2f, 0.25f};

    public void clear() {
        count = 0;
        boneUsed = 0;
        alphaCount = 0;
        addCount = 0;
    }

    private void grow() {
        int n = mesh.length * 2;
        mesh = java.util.Arrays.copyOf(mesh, n);
        flags = java.util.Arrays.copyOf(flags, n);
        model = java.util.Arrays.copyOf(model, n);
        tint = java.util.Arrays.copyOf(tint, n * 4);
        emis = java.util.Arrays.copyOf(emis, n);
        boneStart = java.util.Arrays.copyOf(boneStart, n);
        boneRows = java.util.Arrays.copyOf(boneRows, n);
    }

    /** Adds a draw and returns its model matrix (identity) to fill in. */
    public float[] draw(int meshId, int fl, float r, float g, float b, float a, float e) {
        if (count == mesh.length) grow();
        int i = count++;
        mesh[i] = meshId;
        flags[i] = fl;
        if (model[i] == null) model[i] = new float[16];
        Mat4.setIdentity(model[i]);
        tint[i * 4] = r; tint[i * 4 + 1] = g; tint[i * 4 + 2] = b; tint[i * 4 + 3] = a;
        emis[i] = e;
        boneStart[i] = 0;
        boneRows[i] = 0;
        return model[i];
    }

    public float[] draw(int meshId) { return draw(meshId, 0, 1, 1, 1, 1, 0); }

    /** Attach a bone palette (3 vec4 rows per bone) to the most recent draw. */
    public void bonesForLast(float[] rows, int nBones) {
        int n = nBones * 12;
        if (boneUsed + n > bones.length) bones = java.util.Arrays.copyOf(bones, Math.max(bones.length * 2, boneUsed + n));
        System.arraycopy(rows, 0, bones, boneUsed, n);
        boneStart[count - 1] = boneUsed;
        boneRows[count - 1] = nBones * 3;
        boneUsed += n;
    }

    // ------------------------------------------------------------------ particles

    /** RGBA as little-endian bytes r,g,b,a. */
    public static int packColor(float r, float g, float b, float a) {
        int ir = clamp8(r), ig = clamp8(g), ib = clamp8(b), ia = clamp8(a);
        return (ia << 24) | (ib << 16) | (ig << 8) | ir;
    }

    private static int clamp8(float v) { return Math.max(0, Math.min(255, (int) (v * 255 + 0.5f))); }

    /** Camera-facing quad: centre, half-size, rotation (rad), uv rect, colour. */
    public void quad(boolean additive, float x, float y, float z, float hw, float hh, float rot,
                     float[] uv, float r, float g, float b, float a) {
        // camera basis from the view matrix
        float rx = view[0], ry = view[4], rz = view[8];
        float ux = view[1], uy = view[5], uz = view[9];
        float c = (float) Math.cos(rot), s = (float) Math.sin(rot);
        float ax = (rx * c + ux * s) * hw, ay = (ry * c + uy * s) * hw, az = (rz * c + uz * s) * hw;
        float bx = (-rx * s + ux * c) * hh, by = (-ry * s + uy * c) * hh, bz = (-rz * s + uz * c) * hh;
        quadPts(additive, x - ax - bx, y - ay - by, z - az - bz, x + ax - bx, y + ay - by, z + az - bz,
                x + ax + bx, y + ay + by, z + az + bz, x - ax + bx, y - ay + by, z - az + bz, uv, packColor(r, g, b, a), packColor(r, g, b, a));
    }

    /** Arbitrary quad p0..p3 (counter-clockwise); c0 for p0/p1, c1 for p2/p3 (used by ribbons). */
    public void quadPts(boolean additive, float x0, float y0, float z0, float x1, float y1, float z1,
                        float x2, float y2, float z2, float x3, float y3, float z3, float[] uv, int c0, int c1) {
        int[] q;
        int n;
        if (additive) {
            if ((addCount + 1) * 24 > addQuads.length) addQuads = java.util.Arrays.copyOf(addQuads, addQuads.length * 2);
            q = addQuads; n = addCount++ * 24;
        } else {
            if ((alphaCount + 1) * 24 > alphaQuads.length) alphaQuads = java.util.Arrays.copyOf(alphaQuads, alphaQuads.length * 2);
            q = alphaQuads; n = alphaCount++ * 24;
        }
        int u0 = Float.floatToRawIntBits(uv[0]), v0 = Float.floatToRawIntBits(uv[1]);
        int u1 = Float.floatToRawIntBits(uv[2]), v1 = Float.floatToRawIntBits(uv[3]);
        q[n] = fb(x0); q[n + 1] = fb(y0); q[n + 2] = fb(z0); q[n + 3] = u0; q[n + 4] = v1; q[n + 5] = c0;
        q[n + 6] = fb(x1); q[n + 7] = fb(y1); q[n + 8] = fb(z1); q[n + 9] = u1; q[n + 10] = v1; q[n + 11] = c0;
        q[n + 12] = fb(x2); q[n + 13] = fb(y2); q[n + 14] = fb(z2); q[n + 15] = u1; q[n + 16] = v0; q[n + 17] = c1;
        q[n + 18] = fb(x3); q[n + 19] = fb(y3); q[n + 20] = fb(z3); q[n + 21] = u0; q[n + 22] = v0; q[n + 23] = c1;
    }

    // ------------------------------------------------------------------ serialisation (preview harness)

    public void write(DataOutputStream o) throws IOException {
        ByteBuffer b = ByteBuffer.allocate(64 * 1024 + count * 128 + boneUsed * 4 + (alphaCount + addCount) * 96)
                .order(ByteOrder.LITTLE_ENDIAN);
        b.putInt(screenW).putInt(screenH);
        putM(b, viewProj); putM(b, invViewProj); putM(b, view);
        putV(b, camPos);
        putV(b, sunDir); putV(b, lightCol); putV(b, shadeCol); putV(b, skinShade); putV(b, rimCol);
        putV(b, skyTop); putV(b, skyHor); putV(b, skyLow); putV(b, sunCol); putV(b, moonDir); putV(b, fogCol); putV(b, ink);
        b.putFloat(fogStart).putFloat(fogEnd).putFloat(fogMax).putFloat(heightFog).putFloat(night).putFloat(time);
        for (int i = 0; i < 4; i++) b.putFloat(wind[i]);
        for (int i = 0; i < 4; i++) b.putFloat(lamp[i]);
        putV(b, lampCol);
        b.putFloat(outlinePx);
        b.putInt(shadowOn ? 1 : 0).putInt(shadowSize);
        putM(b, shadowVP);
        b.putFloat(shadowBias).putFloat(shadowStrength);
        b.putInt(count);
        for (int i = 0; i < count; i++) {
            b.putInt(mesh[i]).putInt(flags[i]);
            putM(b, model[i]);
            for (int k = 0; k < 4; k++) b.putFloat(tint[i * 4 + k]);
            b.putFloat(emis[i]);
            b.putInt(boneRows[i]);
            for (int k = 0; k < boneRows[i] * 4; k++) b.putFloat(bones[boneStart[i] + k]);
        }
        b.putInt(alphaCount);
        for (int k = 0; k < alphaCount * 24; k++) b.putInt(alphaQuads[k]);
        b.putInt(addCount);
        for (int k = 0; k < addCount * 24; k++) b.putInt(addQuads[k]);
        for (int k = 0; k < 4; k++) b.putFloat(speed[k]);
        for (int k = 0; k < 4; k++) b.putFloat(flash[k]);
        for (int k = 0; k < 4; k++) b.putFloat(vignette[k]);
        o.writeInt(Integer.reverseBytes(b.position()));
        o.write(b.array(), 0, b.position());
    }

    private static int fb(float f) { return Float.floatToRawIntBits(f); }

    private static void putM(ByteBuffer b, float[] m) { for (int i = 0; i < 16; i++) b.putFloat(m[i]); }

    private static void putV(ByteBuffer b, float[] v) { b.putFloat(v[0]).putFloat(v[1]).putFloat(v[2]); }
}
