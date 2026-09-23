package com.endlessrush.core;

import java.util.ArrayList;

/** Builds flat-shaded, vertex-coloured low-poly meshes out of primitives. */
public final class MeshBuilder {
    private float[] buf = new float[8192];
    private int n;
    private float[] m = Mat4.identity();
    private final ArrayList<float[]> stack = new ArrayList<float[]>();
    private float cr = 1, cg = 1, cb = 1, ca = 1;
    private final float[] p0 = new float[3], p1 = new float[3], p2 = new float[3];

    public MeshBuilder color(int rgb) {
        cr = ((rgb >> 16) & 255) / 255f;
        cg = ((rgb >> 8) & 255) / 255f;
        cb = (rgb & 255) / 255f;
        ca = 1;
        return this;
    }

    public MeshBuilder alpha(float a) { ca = a; return this; }

    public MeshBuilder push() { stack.add(m.clone()); return this; }
    public MeshBuilder pop() { m = stack.remove(stack.size() - 1); return this; }
    public MeshBuilder translate(float x, float y, float z) { Mat4.translate(m, x, y, z); return this; }
    public MeshBuilder rotX(float d) { Mat4.rotX(m, d); return this; }
    public MeshBuilder rotY(float d) { Mat4.rotY(m, d); return this; }
    public MeshBuilder rotZ(float d) { Mat4.rotZ(m, d); return this; }
    public MeshBuilder scale(float x, float y, float z) { Mat4.scale(m, x, y, z); return this; }

    private void xf(float x, float y, float z, float[] o) {
        o[0] = m[0] * x + m[4] * y + m[8] * z + m[12];
        o[1] = m[1] * x + m[5] * y + m[9] * z + m[13];
        o[2] = m[2] * x + m[6] * y + m[10] * z + m[14];
    }

    private void emit(float[] p, float nx, float ny, float nz) {
        if (n + 10 > buf.length) {
            float[] nb = new float[buf.length * 2];
            System.arraycopy(buf, 0, nb, 0, n);
            buf = nb;
        }
        buf[n++] = p[0]; buf[n++] = p[1]; buf[n++] = p[2];
        buf[n++] = nx; buf[n++] = ny; buf[n++] = nz;
        buf[n++] = cr; buf[n++] = cg; buf[n++] = cb; buf[n++] = ca;
    }

    /** Triangle in local space, counter-clockwise when seen from the front. */
    public MeshBuilder tri(float ax, float ay, float az, float bx, float by, float bz, float cx, float cy, float cz) {
        xf(ax, ay, az, p0); xf(bx, by, bz, p1); xf(cx, cy, cz, p2);
        float ux = p1[0] - p0[0], uy = p1[1] - p0[1], uz = p1[2] - p0[2];
        float vx = p2[0] - p0[0], vy = p2[1] - p0[1], vz = p2[2] - p0[2];
        float nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
        float l = (float) Math.sqrt(nx * nx + ny * ny + nz * nz);
        if (l < 1e-9f) return this;
        nx /= l; ny /= l; nz /= l;
        emit(p0, nx, ny, nz); emit(p1, nx, ny, nz); emit(p2, nx, ny, nz);
        return this;
    }

    public MeshBuilder quad(float[] a, float[] b, float[] c, float[] d) {
        tri(a[0], a[1], a[2], b[0], b[1], b[2], c[0], c[1], c[2]);
        tri(a[0], a[1], a[2], c[0], c[1], c[2], d[0], d[1], d[2]);
        return this;
    }

    private static float[] v(float x, float y, float z) { return new float[]{x, y, z}; }

    /** Axis-aligned box centred at (cx,cy,cz) with full sizes sx,sy,sz. */
    public MeshBuilder box(float cx, float cy, float cz, float sx, float sy, float sz) {
        return taperBox(cx, cy, cz, sx, sy, sz, 1f, 1f);
    }

    /** Box whose top face is scaled by (tx,tz) relative to the bottom. */
    public MeshBuilder taperBox(float cx, float cy, float cz, float sx, float sy, float sz, float tx, float tz) {
        float x0 = cx - sx / 2, x1 = cx + sx / 2, y0 = cy - sy / 2, y1 = cy + sy / 2, z0 = cz - sz / 2, z1 = cz + sz / 2;
        float X0 = cx - sx * tx / 2, X1 = cx + sx * tx / 2, Z0 = cz - sz * tz / 2, Z1 = cz + sz * tz / 2;
        float[] a = v(x0, y0, z1), b = v(x1, y0, z1), c = v(x1, y0, z0), d = v(x0, y0, z0);
        float[] e = v(X0, y1, Z1), f = v(X1, y1, Z1), g = v(X1, y1, Z0), h = v(X0, y1, Z0);
        quad(a, b, f, e); // front (+z)
        quad(c, d, h, g); // back (-z)
        quad(b, c, g, f); // right (+x)
        quad(d, a, e, h); // left (-x)
        quad(e, f, g, h); // top
        quad(d, c, b, a); // bottom
        return this;
    }

    /** Cylinder along Y centred at (cx,cy,cz). */
    public MeshBuilder cylinder(float cx, float cy, float cz, float r, float h, int seg) {
        return frustum(cx, cy, cz, r, r, h, seg, true, true);
    }

    public MeshBuilder frustum(float cx, float cy, float cz, float r0, float r1, float h, int seg, boolean capB, boolean capT) {
        float y0 = cy - h / 2, y1 = cy + h / 2;
        for (int i = 0; i < seg; i++) {
            double a0 = Math.PI * 2 * i / seg, a1 = Math.PI * 2 * (i + 1) / seg;
            float s0 = (float) Math.sin(a0), c0 = (float) Math.cos(a0), s1 = (float) Math.sin(a1), c1 = (float) Math.cos(a1);
            float[] b0 = v(cx + s0 * r0, y0, cz + c0 * r0), b1 = v(cx + s1 * r0, y0, cz + c1 * r0);
            float[] t0 = v(cx + s0 * r1, y1, cz + c0 * r1), t1 = v(cx + s1 * r1, y1, cz + c1 * r1);
            if (r1 < 1e-4f) tri(b0[0], b0[1], b0[2], b1[0], b1[1], b1[2], cx, y1, cz);
            else quad(b0, b1, t1, t0);
            if (capT && r1 > 1e-4f) tri(cx, y1, cz, t0[0], t0[1], t0[2], t1[0], t1[1], t1[2]);
            if (capB && r0 > 1e-4f) tri(cx, y0, cz, b1[0], b1[1], b1[2], b0[0], b0[1], b0[2]);
        }
        return this;
    }

    /** Cylinder whose axis runs along X (wheels, coins facing sideways). */
    public MeshBuilder cylinderX(float cx, float cy, float cz, float r, float len, int seg) {
        push().translate(cx, cy, cz).rotZ(90).cylinder(0, 0, 0, r, len, seg).pop();
        return this;
    }

    /** Cylinder whose axis runs along Z. */
    public MeshBuilder cylinderZ(float cx, float cy, float cz, float r, float len, int seg) {
        push().translate(cx, cy, cz).rotX(90).cylinder(0, 0, 0, r, len, seg).pop();
        return this;
    }

    public MeshBuilder sphere(float cx, float cy, float cz, float rx, float ry, float rz, int lat, int lon) {
        for (int i = 0; i < lat; i++) {
            double t0 = Math.PI * i / lat, t1 = Math.PI * (i + 1) / lat;
            for (int j = 0; j < lon; j++) {
                double f0 = Math.PI * 2 * j / lon, f1 = Math.PI * 2 * (j + 1) / lon;
                float[] a = sp(cx, cy, cz, rx, ry, rz, t0, f0), b = sp(cx, cy, cz, rx, ry, rz, t1, f0);
                float[] c = sp(cx, cy, cz, rx, ry, rz, t1, f1), d = sp(cx, cy, cz, rx, ry, rz, t0, f1);
                if (i == 0) tri(a[0], a[1], a[2], b[0], b[1], b[2], c[0], c[1], c[2]);
                else if (i == lat - 1) tri(a[0], a[1], a[2], b[0], b[1], b[2], d[0], d[1], d[2]);
                else quad(a, b, c, d);
            }
        }
        return this;
    }

    public MeshBuilder sphere(float cx, float cy, float cz, float r, int lat, int lon) {
        return sphere(cx, cy, cz, r, r, r, lat, lon);
    }

    private static float[] sp(float cx, float cy, float cz, float rx, float ry, float rz, double t, double f) {
        return v(cx + rx * (float) (Math.sin(t) * Math.sin(f)), cy + ry * (float) Math.cos(t), cz + rz * (float) (Math.sin(t) * Math.cos(f)));
    }

    /** Flat disc facing +Y. */
    public MeshBuilder disc(float cx, float cy, float cz, float r, int seg) {
        for (int i = 0; i < seg; i++) {
            double a0 = Math.PI * 2 * i / seg, a1 = Math.PI * 2 * (i + 1) / seg;
            tri(cx, cy, cz, cx + r * (float) Math.sin(a0), cy, cz + r * (float) Math.cos(a0),
                    cx + r * (float) Math.sin(a1), cy, cz + r * (float) Math.cos(a1));
        }
        return this;
    }

    /** Torus around Y axis. */
    public MeshBuilder torus(float cx, float cy, float cz, float R, float r, int seg, int sides) {
        for (int i = 0; i < seg; i++) {
            double a0 = Math.PI * 2 * i / seg, a1 = Math.PI * 2 * (i + 1) / seg;
            for (int j = 0; j < sides; j++) {
                double b0 = Math.PI * 2 * j / sides, b1 = Math.PI * 2 * (j + 1) / sides;
                float[] p = tp(cx, cy, cz, R, r, a0, b0), q = tp(cx, cy, cz, R, r, a1, b0);
                float[] s = tp(cx, cy, cz, R, r, a1, b1), t = tp(cx, cy, cz, R, r, a0, b1);
                quad(p, t, s, q);
            }
        }
        return this;
    }

    private static float[] tp(float cx, float cy, float cz, float R, float r, double a, double b) {
        float d = R + r * (float) Math.cos(b);
        return v(cx + d * (float) Math.sin(a), cy + r * (float) Math.sin(b), cz + d * (float) Math.cos(a));
    }

    private static final String[] FONT_CHARS = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "X", "?", "!"};
    private static final String[] FONT = {
            "111101101101111", "010110010010111", "111001111100111", "111001111001111", "101101111001001",
            "111100111001111", "111100111101111", "111001001001001", "111101111101111", "111101111001111",
            "101101010101101", "111001011000010", "010010010000010"};

    /** Voxel text in the XY plane, facing +Z, centred at origin. */
    public MeshBuilder text(String s, float cell, float depth) {
        float w = s.length() * 4 * cell - cell;
        for (int k = 0; k < s.length(); k++) {
            String ch = String.valueOf(s.charAt(k));
            int idx = -1;
            for (int i = 0; i < FONT_CHARS.length; i++) if (FONT_CHARS[i].equals(ch)) idx = i;
            if (idx < 0) continue;
            String bits = FONT[idx];
            for (int r = 0; r < 5; r++) for (int c = 0; c < 3; c++) {
                if (bits.charAt(r * 3 + c) == '1') {
                    box(-w / 2 + (k * 4 + c + 0.5f) * cell, (2 - r) * cell, 0, cell * 1.02f, cell * 1.02f, depth);
                }
            }
        }
        return this;
    }

    public Mesh build() {
        float[] d = new float[n];
        System.arraycopy(buf, 0, d, 0, n);
        Mesh mesh = new Mesh(d, n / Mesh.STRIDE);
        n = 0;
        Mat4.setIdentity(m);
        stack.clear();
        return mesh;
    }
}
