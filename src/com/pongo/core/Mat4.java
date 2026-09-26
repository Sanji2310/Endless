package com.pongo.core;

/** Column-major 4x4 matrix helpers (OpenGL layout). */
public final class Mat4 {
    private Mat4() {}

    private static final ThreadLocal<float[]> TMP = new ThreadLocal<float[]>() {
        @Override protected float[] initialValue() { return new float[16]; }
    };
    private static final ThreadLocal<float[]> TMP2 = new ThreadLocal<float[]>() {
        @Override protected float[] initialValue() { return new float[16]; }
    };

    public static float[] identity() {
        float[] m = new float[16];
        setIdentity(m);
        return m;
    }

    public static void setIdentity(float[] m) {
        for (int i = 0; i < 16; i++) m[i] = 0;
        m[0] = m[5] = m[10] = m[15] = 1;
    }

    public static void copy(float[] dst, float[] src) { System.arraycopy(src, 0, dst, 0, 16); }

    /** out = a * b (out may alias a or b). */
    public static void mul(float[] out, float[] a, float[] b) {
        float[] t = TMP.get();
        for (int c = 0; c < 4; c++) {
            float b0 = b[c * 4], b1 = b[c * 4 + 1], b2 = b[c * 4 + 2], b3 = b[c * 4 + 3];
            t[c * 4] = a[0] * b0 + a[4] * b1 + a[8] * b2 + a[12] * b3;
            t[c * 4 + 1] = a[1] * b0 + a[5] * b1 + a[9] * b2 + a[13] * b3;
            t[c * 4 + 2] = a[2] * b0 + a[6] * b1 + a[10] * b2 + a[14] * b3;
            t[c * 4 + 3] = a[3] * b0 + a[7] * b1 + a[11] * b2 + a[15] * b3;
        }
        System.arraycopy(t, 0, out, 0, 16);
    }

    public static void translate(float[] m, float x, float y, float z) {
        m[12] += m[0] * x + m[4] * y + m[8] * z;
        m[13] += m[1] * x + m[5] * y + m[9] * z;
        m[14] += m[2] * x + m[6] * y + m[10] * z;
        m[15] += m[3] * x + m[7] * y + m[11] * z;
    }

    public static void scale(float[] m, float x, float y, float z) {
        for (int i = 0; i < 4; i++) { m[i] *= x; m[4 + i] *= y; m[8 + i] *= z; }
    }

    public static void rotate(float[] m, float deg, float ax, float ay, float az) {
        float[] r = TMP2.get();
        float a = (float) Math.toRadians(deg);
        float c = (float) Math.cos(a), s = (float) Math.sin(a), t = 1 - c;
        setIdentity(r);
        r[0] = t * ax * ax + c;      r[4] = t * ax * ay - s * az; r[8] = t * ax * az + s * ay;
        r[1] = t * ax * ay + s * az; r[5] = t * ay * ay + c;      r[9] = t * ay * az - s * ax;
        r[2] = t * ax * az - s * ay; r[6] = t * ay * az + s * ax; r[10] = t * az * az + c;
        mul(m, m, r);
    }

    public static void rotX(float[] m, float deg) { rotate(m, deg, 1, 0, 0); }
    public static void rotY(float[] m, float deg) { rotate(m, deg, 0, 1, 0); }
    public static void rotZ(float[] m, float deg) { rotate(m, deg, 0, 0, 1); }

    public static void perspective(float[] m, float fovYDeg, float aspect, float near, float far) {
        float f = 1f / (float) Math.tan(Math.toRadians(fovYDeg) / 2);
        for (int i = 0; i < 16; i++) m[i] = 0;
        m[0] = f / aspect;
        m[5] = f;
        m[10] = (far + near) / (near - far);
        m[11] = -1;
        m[14] = 2 * far * near / (near - far);
    }

    public static void ortho(float[] m, float l, float r, float b, float t, float n, float f) {
        for (int i = 0; i < 16; i++) m[i] = 0;
        m[0] = 2 / (r - l);
        m[5] = 2 / (t - b);
        m[10] = -2 / (f - n);
        m[12] = -(r + l) / (r - l);
        m[13] = -(t + b) / (t - b);
        m[14] = -(f + n) / (f - n);
        m[15] = 1;
    }

    public static void lookAt(float[] m, float ex, float ey, float ez, float cx, float cy, float cz,
                              float ux, float uy, float uz) {
        float fx = cx - ex, fy = cy - ey, fz = cz - ez;
        float fl = (float) Math.sqrt(fx * fx + fy * fy + fz * fz);
        fx /= fl; fy /= fl; fz /= fl;
        float sx = fy * uz - fz * uy, sy = fz * ux - fx * uz, sz = fx * uy - fy * ux;
        float sl = (float) Math.sqrt(sx * sx + sy * sy + sz * sz);
        sx /= sl; sy /= sl; sz /= sl;
        float vx = sy * fz - sz * fy, vy = sz * fx - sx * fz, vz = sx * fy - sy * fx;
        m[0] = sx; m[4] = sy; m[8] = sz;
        m[1] = vx; m[5] = vy; m[9] = vz;
        m[2] = -fx; m[6] = -fy; m[10] = -fz;
        m[3] = 0; m[7] = 0; m[11] = 0;
        m[12] = -(sx * ex + sy * ey + sz * ez);
        m[13] = -(vx * ex + vy * ey + vz * ez);
        m[14] = (fx * ex + fy * ey + fz * ez);
        m[15] = 1;
    }

    /** Inverse of a rigid/affine matrix (upper 3x3 may include scale). */
    public static void invertAffine(float[] out, float[] m) {
        float a00 = m[0], a01 = m[4], a02 = m[8];
        float a10 = m[1], a11 = m[5], a12 = m[9];
        float a20 = m[2], a21 = m[6], a22 = m[10];
        float det = a00 * (a11 * a22 - a12 * a21) - a01 * (a10 * a22 - a12 * a20) + a02 * (a10 * a21 - a11 * a20);
        float id = Math.abs(det) < 1e-20f ? 0 : 1f / det;
        float b00 = (a11 * a22 - a12 * a21) * id, b01 = (a02 * a21 - a01 * a22) * id, b02 = (a01 * a12 - a02 * a11) * id;
        float b10 = (a12 * a20 - a10 * a22) * id, b11 = (a00 * a22 - a02 * a20) * id, b12 = (a02 * a10 - a00 * a12) * id;
        float b20 = (a10 * a21 - a11 * a20) * id, b21 = (a01 * a20 - a00 * a21) * id, b22 = (a00 * a11 - a01 * a10) * id;
        float tx = m[12], ty = m[13], tz = m[14];
        out[0] = b00; out[4] = b01; out[8] = b02;
        out[1] = b10; out[5] = b11; out[9] = b12;
        out[2] = b20; out[6] = b21; out[10] = b22;
        out[12] = -(b00 * tx + b01 * ty + b02 * tz);
        out[13] = -(b10 * tx + b11 * ty + b12 * tz);
        out[14] = -(b20 * tx + b21 * ty + b22 * tz);
        out[3] = 0; out[7] = 0; out[11] = 0; out[15] = 1;
    }

    /** General 4x4 inverse. Returns false if singular. */
    public static boolean invert(float[] out, float[] m) {
        float[] inv = TMP2.get();
        inv[0] = m[5] * m[10] * m[15] - m[5] * m[11] * m[14] - m[9] * m[6] * m[15] + m[9] * m[7] * m[14] + m[13] * m[6] * m[11] - m[13] * m[7] * m[10];
        inv[4] = -m[4] * m[10] * m[15] + m[4] * m[11] * m[14] + m[8] * m[6] * m[15] - m[8] * m[7] * m[14] - m[12] * m[6] * m[11] + m[12] * m[7] * m[10];
        inv[8] = m[4] * m[9] * m[15] - m[4] * m[11] * m[13] - m[8] * m[5] * m[15] + m[8] * m[7] * m[13] + m[12] * m[5] * m[11] - m[12] * m[7] * m[9];
        inv[12] = -m[4] * m[9] * m[14] + m[4] * m[10] * m[13] + m[8] * m[5] * m[14] - m[8] * m[6] * m[13] - m[12] * m[5] * m[10] + m[12] * m[6] * m[9];
        inv[1] = -m[1] * m[10] * m[15] + m[1] * m[11] * m[14] + m[9] * m[2] * m[15] - m[9] * m[3] * m[14] - m[13] * m[2] * m[11] + m[13] * m[3] * m[10];
        inv[5] = m[0] * m[10] * m[15] - m[0] * m[11] * m[14] - m[8] * m[2] * m[15] + m[8] * m[3] * m[14] + m[12] * m[2] * m[11] - m[12] * m[3] * m[10];
        inv[9] = -m[0] * m[9] * m[15] + m[0] * m[11] * m[13] + m[8] * m[1] * m[15] - m[8] * m[3] * m[13] - m[12] * m[1] * m[11] + m[12] * m[3] * m[9];
        inv[13] = m[0] * m[9] * m[14] - m[0] * m[10] * m[13] - m[8] * m[1] * m[14] + m[8] * m[2] * m[13] + m[12] * m[1] * m[10] - m[12] * m[2] * m[9];
        inv[2] = m[1] * m[6] * m[15] - m[1] * m[7] * m[14] - m[5] * m[2] * m[15] + m[5] * m[3] * m[14] + m[13] * m[2] * m[7] - m[13] * m[3] * m[6];
        inv[6] = -m[0] * m[6] * m[15] + m[0] * m[7] * m[14] + m[4] * m[2] * m[15] - m[4] * m[3] * m[14] - m[12] * m[2] * m[7] + m[12] * m[3] * m[6];
        inv[10] = m[0] * m[5] * m[15] - m[0] * m[7] * m[13] - m[4] * m[1] * m[15] + m[4] * m[3] * m[13] + m[12] * m[1] * m[7] - m[12] * m[3] * m[5];
        inv[14] = -m[0] * m[5] * m[14] + m[0] * m[6] * m[13] + m[4] * m[1] * m[14] - m[4] * m[2] * m[13] - m[12] * m[1] * m[6] + m[12] * m[2] * m[5];
        inv[3] = -m[1] * m[6] * m[11] + m[1] * m[7] * m[10] + m[5] * m[2] * m[11] - m[5] * m[3] * m[10] - m[9] * m[2] * m[7] + m[9] * m[3] * m[6];
        inv[7] = m[0] * m[6] * m[11] - m[0] * m[7] * m[10] - m[4] * m[2] * m[11] + m[4] * m[3] * m[10] + m[8] * m[2] * m[7] - m[8] * m[3] * m[6];
        inv[11] = -m[0] * m[5] * m[11] + m[0] * m[7] * m[9] + m[4] * m[1] * m[11] - m[4] * m[3] * m[9] - m[8] * m[1] * m[7] + m[8] * m[3] * m[5];
        inv[15] = m[0] * m[5] * m[10] - m[0] * m[6] * m[9] - m[4] * m[1] * m[10] + m[4] * m[2] * m[9] + m[8] * m[1] * m[6] - m[8] * m[2] * m[5];
        float det = m[0] * inv[0] + m[1] * inv[4] + m[2] * inv[8] + m[3] * inv[12];
        if (Math.abs(det) < 1e-30f) return false;
        det = 1f / det;
        for (int i = 0; i < 16; i++) out[i] = inv[i] * det;
        return true;
    }

    /** Matrix from rotation quaternion + translation. */
    public static void fromQT(float[] m, float qx, float qy, float qz, float qw, float tx, float ty, float tz) {
        float xx = qx * qx, yy = qy * qy, zz = qz * qz, xy = qx * qy, xz = qx * qz, yz = qy * qz, wx = qw * qx, wy = qw * qy, wz = qw * qz;
        m[0] = 1 - 2 * (yy + zz); m[4] = 2 * (xy - wz);     m[8] = 2 * (xz + wy);      m[12] = tx;
        m[1] = 2 * (xy + wz);     m[5] = 1 - 2 * (xx + zz); m[9] = 2 * (yz - wx);      m[13] = ty;
        m[2] = 2 * (xz - wy);     m[6] = 2 * (yz + wx);     m[10] = 1 - 2 * (xx + yy); m[14] = tz;
        m[3] = 0; m[7] = 0; m[11] = 0; m[15] = 1;
    }

    public static void transformPoint(float[] m, float x, float y, float z, float[] out) {
        out[0] = m[0] * x + m[4] * y + m[8] * z + m[12];
        out[1] = m[1] * x + m[5] * y + m[9] * z + m[13];
        out[2] = m[2] * x + m[6] * y + m[10] * z + m[14];
    }
}
