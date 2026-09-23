package com.endlessrush.core;

/** Flat list of draw commands produced each frame. */
public final class DrawList {
    public static final int F_NOFOG = 1, F_BLEND = 2, F_NODEPTH = 4, F_UNLIT = 8;

    public int count;
    public Mesh[] mesh = new Mesh[256];
    public float[][] model = new float[256][];
    public float[] tint = new float[256 * 4];
    public float[] emissive = new float[256];
    public int[] flags = new int[256];

    public final float[] view = new float[16], proj = new float[16], viewProj = new float[16];
    public final float[] camPos = new float[3];
    public final float[] fogColor = {0.73f, 0.87f, 0.98f};
    public float fogStart = 55, fogEnd = 175;
    public final float[] lightDir = {0.45f, 0.8f, 0.4f};

    public void clear() { count = 0; }

    private void grow() {
        int n = mesh.length * 2;
        Mesh[] m2 = new Mesh[n]; System.arraycopy(mesh, 0, m2, 0, count); mesh = m2;
        float[][] mo = new float[n][]; System.arraycopy(model, 0, mo, 0, count); model = mo;
        float[] t = new float[n * 4]; System.arraycopy(tint, 0, t, 0, count * 4); tint = t;
        float[] e = new float[n]; System.arraycopy(emissive, 0, e, 0, count); emissive = e;
        int[] f = new int[n]; System.arraycopy(flags, 0, f, 0, count); flags = f;
    }

    /** Adds a command; returns its model matrix to fill in (initialised to identity). */
    public float[] add(Mesh m, float r, float g, float b, float a, float emis, int fl) {
        if (count == mesh.length) grow();
        int i = count++;
        mesh[i] = m;
        if (model[i] == null) model[i] = new float[16];
        Mat4.setIdentity(model[i]);
        tint[i * 4] = r; tint[i * 4 + 1] = g; tint[i * 4 + 2] = b; tint[i * 4 + 3] = a;
        emissive[i] = emis;
        flags[i] = fl;
        return model[i];
    }

    public float[] add(Mesh m) { return add(m, 1, 1, 1, 1, 0, 0); }
}
