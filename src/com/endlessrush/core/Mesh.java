package com.endlessrush.core;

/** Interleaved triangle list: x,y,z, nx,ny,nz, r,g,b,a per vertex. */
public final class Mesh {
    public static final int STRIDE = 10;
    public final float[] data;
    public final int vertexCount;
    /** Renderer-owned handle (GL buffer id). */
    public int handle = 0;

    public Mesh(float[] data, int vertexCount) {
        this.data = data;
        this.vertexCount = vertexCount;
    }
}
