package com.endlessrush.core;

/**
 * The frame's camera, sun and fog as Scene computes them; the toon layers copy them into their RenderFrame.
 * The command arrays stay empty since every mesh goes through the toon renderer; ZoneWorld still walks them.
 */
public final class DrawList {
    public static final int F_NOFOG = 1, F_BLEND = 2, F_NODEPTH = 4, F_UNLIT = 8;

    public int count;
    public int[] flags = new int[0];
    public float[] tint = new float[0];

    public final float[] view = new float[16], proj = new float[16], viewProj = new float[16];
    public final float[] camPos = new float[3];
    /** The Sakura Line haze (SakuraWorld sets the rest of the palette). */
    public final float[] fogColor = {0.86f, 0.93f, 1.0f};
    public float fogStart = 70, fogEnd = 260;
    public final float[] lightDir = {0.45f, 0.8f, 0.4f};

    public void clear() { count = 0; }
}
