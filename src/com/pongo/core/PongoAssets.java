package com.pongo.core;

import java.io.DataInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.HashMap;
import java.util.Map;

/** Parses assets/pongo.bin (see tools/assetbuilder/AssetBuilder.java). No GL calls here. */
public final class PongoAssets {
    public static final int CLS_OPAQUE = 0, CLS_DOUBLE = 1, CLS_CUTOUT = 2, CLS_WATER = 3;
    public static final int PART_NOCAST = 1, PART_OUTLINE = 2;

    public static final class Chunk {
        public final int nVerts, nIdx;
        public ByteBuffer verts, idx;
        public int vbo, ibo; // renderer-owned

        Chunk(int nv, int ni) { nVerts = nv; nIdx = ni; }
    }

    public static final class Part {
        public final int cls, flags;
        public final Chunk[] chunks;

        Part(int cls, int flags, Chunk[] chunks) { this.cls = cls; this.flags = flags; this.chunks = chunks; }
    }

    public static final class Mesh {
        public String name, group;
        public int lod, flags, skeleton;
        public final float[] bmin = new float[3], bmax = new float[3], scale = new float[3], offset = new float[3];
        public final float[] center = new float[3];
        public float radius;
        public Part[] parts;
        public boolean hasOutline, castsShadow;

        public boolean skinned() { return (flags & 1) != 0; }
        public int stride() { return skinned() ? 36 : 28; }
    }

    public static final class Clip {
        public String name;
        public float fps;
        public int frames;
        public boolean loop;
        public float[] data; // frames * bones * 7 (qx qy qz qw tx ty tz), parent-relative

        public float duration() { return frames / fps; }
    }

    public static final class Skeleton {
        public String name;
        public int bones;
        public String[] names;
        public int[] parent, dyn;
        public float[][] rest, invRest, restLocal;
        public Clip[] clips;
        public final Map<String, Integer> clipIndex = new HashMap<String, Integer>();

        public int bone(String n) {
            for (int i = 0; i < bones; i++) if (names[i].equals(n)) return i;
            return -1;
        }

        public Clip clip(String n) {
            Integer i = clipIndex.get(n);
            return i == null ? null : clips[i];
        }
    }

    public int atlasW, atlasH;
    public ByteBuffer[] atlasLevels;
    public int[] levelW, levelH;
    public final Map<String, float[]> tiles = new HashMap<String, float[]>();
    public Mesh[] meshes;
    public final Map<String, Integer> meshIndex = new HashMap<String, Integer>();
    /** group name -> mesh ids by lod (index 0 = lod0) */
    public final Map<String, int[]> lods = new HashMap<String, int[]>();
    public Skeleton[] skeletons;
    public final Map<String, float[]> extras = new HashMap<String, float[]>();

    public int mesh(String name) {
        Integer i = meshIndex.get(name);
        return i == null ? -1 : i;
    }

    /** Mesh id for a group at a given lod (falls back to the closest available). */
    public int lod(String group, int lod) {
        int[] l = lods.get(group);
        if (l == null) return -1;
        for (int k = Math.min(lod, l.length - 1); k >= 0; k--) if (l[k] >= 0) return l[k];
        for (int k = 0; k < l.length; k++) if (l[k] >= 0) return l[k];
        return -1;
    }

    public float[] tile(String name) {
        float[] t = tiles.get(name);
        return t != null ? t : tiles.get("_white");
    }

    // ------------------------------------------------------------------ parsing

    private static final class Reader {
        final DataInputStream in;
        final byte[] b4 = new byte[4];

        Reader(InputStream is) { in = new DataInputStream(is); }

        int i() throws IOException {
            in.readFully(b4);
            return (b4[0] & 255) | ((b4[1] & 255) << 8) | ((b4[2] & 255) << 16) | ((b4[3] & 255) << 24);
        }

        float f() throws IOException { return Float.intBitsToFloat(i()); }

        String s() throws IOException {
            int n = i();
            byte[] b = new byte[n];
            in.readFully(b);
            int pad = (4 - n % 4) % 4;
            if (pad > 0) in.readFully(new byte[pad]);
            return new String(b, "UTF-8");
        }

        float[] fa(int n) throws IOException {
            float[] a = new float[n];
            byte[] b = new byte[n * 4];
            in.readFully(b);
            ByteBuffer.wrap(b).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer().get(a);
            return a;
        }

        ByteBuffer blob(int n) throws IOException {
            ByteBuffer bb = ByteBuffer.allocateDirect(n).order(ByteOrder.nativeOrder());
            byte[] tmp = new byte[Math.min(n, 1 << 16)];
            int left = n;
            while (left > 0) {
                int k = Math.min(left, tmp.length);
                in.readFully(tmp, 0, k);
                bb.put(tmp, 0, k);
                left -= k;
            }
            bb.position(0);
            return bb;
        }
    }

    public static PongoAssets load(InputStream is, boolean keepAtlas) throws IOException {
        Reader r = new Reader(is);
        byte[] magic = new byte[4];
        r.in.readFully(magic);
        if (magic[0] != 'P' || magic[1] != 'G' || magic[2] != 'O' || magic[3] != '1') throw new IOException("not a pongo.bin");
        r.i();
        PongoAssets a = new PongoAssets();
        a.atlasW = r.i();
        a.atlasH = r.i();
        int nl = r.i();
        a.atlasLevels = new ByteBuffer[nl];
        a.levelW = new int[nl];
        a.levelH = new int[nl];
        for (int l = 0; l < nl; l++) {
            a.levelW[l] = r.i();
            a.levelH[l] = r.i();
            int n = a.levelW[l] * a.levelH[l] * 4;
            if (keepAtlas) a.atlasLevels[l] = r.blob(n);
            else r.in.skipBytes(n);
        }
        int nt = r.i();
        for (int t = 0; t < nt; t++) {
            String name = r.s();
            a.tiles.put(name, new float[]{r.f(), r.f(), r.f(), r.f()});
        }
        int nm = r.i();
        a.meshes = new Mesh[nm];
        for (int m = 0; m < nm; m++) {
            Mesh me = new Mesh();
            me.name = r.s();
            me.group = r.s();
            me.lod = r.i();
            me.flags = r.i();
            me.skeleton = r.i();
            for (int k = 0; k < 3; k++) me.bmin[k] = r.f();
            for (int k = 0; k < 3; k++) me.bmax[k] = r.f();
            for (int k = 0; k < 3; k++) me.scale[k] = r.f();
            for (int k = 0; k < 3; k++) me.offset[k] = r.f();
            float rr = 0;
            for (int k = 0; k < 3; k++) {
                me.center[k] = (me.bmin[k] + me.bmax[k]) * 0.5f;
                float h = (me.bmax[k] - me.bmin[k]) * 0.5f;
                rr += h * h;
            }
            me.radius = (float) Math.sqrt(rr);
            int np = r.i();
            me.parts = new Part[np];
            int stride = (me.flags & 1) != 0 ? 36 : 28;
            for (int p = 0; p < np; p++) {
                int cls = r.i(), pf = r.i(), nc = r.i();
                Chunk[] ch = new Chunk[nc];
                for (int c = 0; c < nc; c++) {
                    int nv = r.i(), ni = r.i();
                    Chunk ck = new Chunk(nv, ni);
                    ck.verts = r.blob(nv * stride);
                    ck.idx = r.blob(((ni * 2 + 3) / 4) * 4);
                    ch[c] = ck;
                }
                me.parts[p] = new Part(cls, pf, ch);
                if ((pf & PART_OUTLINE) != 0) me.hasOutline = true;
                if ((pf & PART_NOCAST) == 0) me.castsShadow = true;
            }
            a.meshes[m] = me;
            a.meshIndex.put(me.name, m);
            int[] l = a.lods.get(me.group);
            if (l == null || l.length <= me.lod) {
                int[] n2 = new int[Math.max(me.lod + 1, l == null ? 0 : l.length)];
                java.util.Arrays.fill(n2, -1);
                if (l != null) System.arraycopy(l, 0, n2, 0, l.length);
                l = n2;
                a.lods.put(me.group, l);
            }
            l[me.lod] = m;
        }
        int ns = r.i();
        a.skeletons = new Skeleton[ns];
        for (int s = 0; s < ns; s++) {
            Skeleton sk = new Skeleton();
            sk.name = r.s();
            sk.bones = r.i();
            sk.names = new String[sk.bones];
            sk.parent = new int[sk.bones];
            sk.dyn = new int[sk.bones];
            sk.rest = new float[sk.bones][];
            sk.invRest = new float[sk.bones][];
            sk.restLocal = new float[sk.bones][];
            for (int b = 0; b < sk.bones; b++) {
                sk.names[b] = r.s();
                sk.parent[b] = r.i();
                sk.dyn[b] = r.i();
                sk.rest[b] = r.fa(16);
                sk.invRest[b] = new float[16];
                Mat4.invertAffine(sk.invRest[b], sk.rest[b]);
            }
            for (int b = 0; b < sk.bones; b++) {
                sk.restLocal[b] = new float[16];
                if (sk.parent[b] >= 0) Mat4.mul(sk.restLocal[b], sk.invRest[sk.parent[b]], sk.rest[b]);
                else Mat4.copy(sk.restLocal[b], sk.rest[b]);
            }
            int nc = r.i();
            sk.clips = new Clip[nc];
            for (int c = 0; c < nc; c++) {
                Clip cl = new Clip();
                cl.name = r.s();
                cl.fps = r.f();
                cl.frames = r.i();
                cl.loop = r.i() == 1;
                cl.data = r.fa(cl.frames * sk.bones * 7);
                sk.clips[c] = cl;
                sk.clipIndex.put(cl.name, c);
            }
            a.skeletons[s] = sk;
        }
        int nx = r.i();
        for (int x = 0; x < nx; x++) {
            String k = r.s();
            int n = r.i();
            a.extras.put(k, r.fa(n));
        }
        return a;
    }
}
