import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.*;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/**
 * Builds assets/pongo.bin from Blender exports (build/models/*.erm) and texture tiles (build/tex/*.png).
 *
 * Texture atlas: every tile gets a cell aligned to 32 px with a gutter that repeats (t_*) or clamps
 * (everything else) its content; mip levels are built per cell so tiles never bleed into each other.
 * Triangles whose tiling UVs cross integer lines are split so each piece samples inside one cell.
 *
 * Vertex format (28 bytes, 36 when skinned):
 *   0 aPos    short4 norm  xyz = position (dequantised by per-mesh scale/offset), w = wind sway
 *   8 aNrm    byte4  norm  xyz = normal, w = outline width
 *  12 aOut    byte4  norm  xyz = smoothed outline normal, w = shading type / 7
 *  16 aUV     ushort2 norm atlas uv
 *  20 aCol    ubyte4 norm  rgb albedo tint (sRGB), a = ambient occlusion
 *  24 aMat    ubyte4 norm  specular, rim, emissive, softness
 *  28 aBone   ubyte4       bone indices   (skinned only)
 *  32 aWeight ubyte4 norm  bone weights   (skinned only)
 */
public class AssetBuilder {
    // material flags (mirror blender/lib/erlib.py)
    static final int F_DOUBLE = 1, F_UNLIT = 2, F_WATER = 4, F_NOCAST = 8, F_HAIR = 16, F_ALPHA = 32, F_GLASS = 64,
            F_METAL = 128, F_FOLIAGE = 256, F_NIGHT = 512, F_DECAL = 1024;
    // shading types (mirror core/Shaders.java)
    static final int T_STD = 0, T_SKIN = 1, T_GLASS = 2, T_HAIR = 3, T_METAL = 4, T_FOLIAGE = 5, T_NIGHT = 6, T_UNLIT = 7;
    // part classes
    static final int C_OPAQUE = 0, C_DOUBLE = 1, C_CUTOUT = 2, C_WATER = 3, C_DECAL = 4;

    // the atlas starts small and doubles until every tile fits (up to ATLAS_MAX)
    static final int ATLAS_W = 256, ATLAS_H = 256, ATLAS_MAX = 4096;

    // ------------------------------------------------------------------ data

    static class Mat {
        String name, tex;
        float r, g, b, spec, rim, emis, soft, outline, skin, sway;
        int flags;

        int type() {
            if ((flags & F_UNLIT) != 0) return T_UNLIT;
            if (skin > 0.5f) return T_SKIN;
            if ((flags & F_GLASS) != 0) return T_GLASS;
            if ((flags & F_HAIR) != 0) return T_HAIR;
            if ((flags & F_METAL) != 0) return T_METAL;
            if ((flags & F_FOLIAGE) != 0) return T_FOLIAGE;
            if ((flags & F_NIGHT) != 0) return T_NIGHT;
            return T_STD;
        }

        int cls() {
            if ((flags & F_DECAL) != 0) return C_DECAL;
            if ((flags & F_WATER) != 0) return C_WATER;
            if ((flags & F_ALPHA) != 0) return C_CUTOUT;
            if ((flags & F_DOUBLE) != 0) return C_DOUBLE;
            return C_OPAQUE;
        }
    }

    static class Bone {
        String name;
        int parent, dyn;
        float[] rest = new float[16];
    }

    static class Clip {
        String name;
        float fps;
        int frames, loop;
        float[] data; // frames * bones * 7
    }

    static class Erm {
        String name;
        boolean skinned;
        List<Mat> mats = new ArrayList<>();
        int nTri;
        float[] P, N, UV, COL;
        int[] MI;
        byte[] BI;
        float[] BW;
        List<Bone> bones = new ArrayList<>();
        List<Clip> clips = new ArrayList<>();
        Map<String, float[]> extras = new LinkedHashMap<>();
    }

    static class Tile {
        String name;
        BufferedImage img;
        int w, h, cellW, cellH, gx, gy, x, y; // x,y = cell origin in atlas
        boolean repeat;
        float u0, v0, u1, v1; // interior rect in atlas uv
    }

    // ------------------------------------------------------------------ reading

    static class LE {
        final ByteBuffer b;
        LE(byte[] d) { b = ByteBuffer.wrap(d).order(ByteOrder.LITTLE_ENDIAN); }
        int i() { return b.getInt(); }
        float f() { return b.getFloat(); }
        String s() { int n = b.getInt(); byte[] x = new byte[n]; b.get(x); return new String(x, StandardCharsets.UTF_8); }
        float[] fa(int n) { float[] a = new float[n]; for (int k = 0; k < n; k++) a[k] = b.getFloat(); return a; }
        int[] ia(int n) { int[] a = new int[n]; for (int k = 0; k < n; k++) a[k] = b.getInt(); return a; }
        byte[] ba(int n) { byte[] a = new byte[n]; b.get(a); return a; }
    }

    static Erm readErm(Path p) throws IOException {
        LE r = new LE(Files.readAllBytes(p));
        byte[] mg = r.ba(4);
        if (!new String(mg, StandardCharsets.US_ASCII).equals("ERM1")) throw new IOException("bad magic " + p);
        r.i();
        Erm e = new Erm();
        e.name = r.s();
        e.skinned = r.i() == 1;
        int nm = r.i();
        for (int k = 0; k < nm; k++) {
            Mat m = new Mat();
            m.name = r.s();
            m.tex = r.s();
            m.r = r.f(); m.g = r.f(); m.b = r.f();
            m.spec = r.f(); m.rim = r.f(); m.emis = r.f(); m.soft = r.f(); m.outline = r.f(); m.skin = r.f(); m.sway = r.f();
            r.f(); r.f(); r.f(); // per-material shadow colour (design renders only)
            m.flags = r.i();
            e.mats.add(m);
        }
        int nt = r.i();
        e.nTri = nt;
        e.P = r.fa(nt * 9);
        e.N = r.fa(nt * 9);
        e.UV = r.fa(nt * 6);
        e.COL = r.fa(nt * 12);
        e.MI = r.ia(nt);
        if (e.skinned) {
            e.BI = r.ba(nt * 12);
            e.BW = r.fa(nt * 12);
            int nb = r.i();
            for (int k = 0; k < nb; k++) {
                Bone b = new Bone();
                b.name = r.s();
                b.parent = r.i();
                b.rest = r.fa(16);
                b.dyn = r.i();
                e.bones.add(b);
            }
            int nc = r.i();
            for (int k = 0; k < nc; k++) {
                Clip c = new Clip();
                c.name = r.s();
                c.fps = r.f();
                c.frames = r.i();
                c.loop = r.i();
                c.data = r.fa(c.frames * nb * 7);
                e.clips.add(c);
            }
        }
        if (r.b.remaining() >= 4) {
            int nx = r.i();
            for (int k = 0; k < nx; k++) {
                String key = r.s();
                int n = r.i();
                e.extras.put(key, r.fa(n));
            }
        }
        return e;
    }

    // ------------------------------------------------------------------ atlas

    static List<Tile> tiles = new ArrayList<>();
    static Map<String, Tile> tileMap = new HashMap<>();
    static int atlasW = ATLAS_W, atlasH = ATLAS_H;

    static Tile loadTile(Path dir, String name) throws IOException {
        if (tileMap.containsKey(name)) return tileMap.get(name);
        Tile t = new Tile();
        t.name = name;
        if (name.equals("_white")) {
            t.img = new BufferedImage(32, 32, BufferedImage.TYPE_INT_ARGB);
            for (int y = 0; y < 32; y++) for (int x = 0; x < 32; x++) t.img.setRGB(x, y, 0xFFFFFFFF);
        } else {
            Path p = dir.resolve(name + ".png");
            if (!Files.exists(p)) {
                System.err.println("WARNING: missing texture " + p + " (using white)");
                return loadTile(dir, "_white");
            }
            t.img = ImageIO.read(p.toFile());
        }
        t.w = t.img.getWidth();
        t.h = t.img.getHeight();
        t.repeat = name.startsWith("t_");
        int g = Math.max(8, Math.min(t.w, t.h) / 16);
        t.cellW = roundUp(t.w + 2 * g, 32);
        t.cellH = roundUp(t.h + 2 * g, 32);
        t.gx = (t.cellW - t.w) / 2;
        t.gy = (t.cellH - t.h) / 2;
        tiles.add(t);
        tileMap.put(name, t);
        return t;
    }

    static int roundUp(int v, int m) { return (v + m - 1) / m * m; }

    /** Shelf packing, tallest first. */
    static void pack() {
        List<Tile> sorted = new ArrayList<>(tiles);
        sorted.sort((a, b) -> b.cellH != a.cellH ? b.cellH - a.cellH : b.cellW - a.cellW);
        while (true) {
            int x = 0, y = 0, shelf = 0;
            boolean ok = true;
            for (Tile t : sorted) {
                if (x + t.cellW > atlasW) { x = 0; y += shelf; shelf = 0; }
                if (y + t.cellH > atlasH) { ok = false; break; }
                t.x = x; t.y = y;
                x += t.cellW;
                shelf = Math.max(shelf, t.cellH);
            }
            if (ok) break;
            if (atlasW >= ATLAS_MAX && atlasH >= ATLAS_MAX) throw new IllegalStateException("tiles do not fit a " + ATLAS_MAX + " atlas");
            if (atlasW <= atlasH) atlasW *= 2; else atlasH *= 2;
            System.out.println("atlas grows to " + atlasW + "x" + atlasH);
        }
        for (Tile t : tiles) {
            t.u0 = (t.x + t.gx) / (float) atlasW;
            t.v0 = (t.y + t.gy) / (float) atlasH;
            t.u1 = (t.x + t.gx + t.w) / (float) atlasW;
            t.v1 = (t.y + t.gy + t.h) / (float) atlasH;
        }
    }

    /** Returns atlas mip levels as RGBA byte arrays. */
    static List<byte[]> buildAtlasLevels() {
        List<byte[]> levels = new ArrayList<>();
        // per tile interior pixels per level (float RGBA premultiplied-free)
        Map<Tile, float[]> cur = new HashMap<>();
        for (Tile t : tiles) {
            float[] px = new float[t.w * t.h * 4];
            for (int y = 0; y < t.h; y++) for (int x = 0; x < t.w; x++) {
                int c = t.img.getRGB(x, y);
                int i = (y * t.w + x) * 4;
                px[i] = (c >> 16) & 255; px[i + 1] = (c >> 8) & 255; px[i + 2] = c & 255; px[i + 3] = (c >>> 24) & 255;
            }
            cur.put(t, px);
        }
        int lw = atlasW, lh = atlasH, L = 0;
        int[] tw = new int[tiles.size()], th = new int[tiles.size()];
        for (int k = 0; k < tiles.size(); k++) { tw[k] = tiles.get(k).w; th[k] = tiles.get(k).h; }
        byte[] prev = null;
        while (true) {
            byte[] out = new byte[lw * lh * 4];
            if (L <= 5) {
                for (int k = 0; k < tiles.size(); k++) {
                    Tile t = tiles.get(k);
                    int s = 1 << L;
                    int cx = t.x / s, cy = t.y / s, cw = t.cellW / s, ch = t.cellH / s, gx = t.gx / s, gy = t.gy / s;
                    int w = tw[k], h = th[k];
                    float[] px = cur.get(t);
                    if (w < 2 || h < 2 || gx < 1 || gy < 1) {
                        float[] avg = average(px);
                        for (int y = 0; y < ch; y++) for (int x = 0; x < cw; x++) put(out, lw, cx + x, cy + y, avg, 0);
                    } else {
                        for (int y = 0; y < ch; y++) {
                            int sy = y - gy;
                            sy = t.repeat ? Math.floorMod(sy, h) : Math.max(0, Math.min(h - 1, sy));
                            for (int x = 0; x < cw; x++) {
                                int sx = x - gx;
                                sx = t.repeat ? Math.floorMod(sx, w) : Math.max(0, Math.min(w - 1, sx));
                                put(out, lw, cx + x, cy + y, px, (sy * w + sx) * 4);
                            }
                        }
                    }
                    // next level of this tile's interior
                    if (w >= 2 && h >= 2) {
                        int nw = w / 2, nh = h / 2;
                        float[] np = new float[nw * nh * 4];
                        for (int y = 0; y < nh; y++) for (int x = 0; x < nw; x++) for (int c = 0; c < 4; c++) {
                            np[(y * nw + x) * 4 + c] = (px[((2 * y) * w + 2 * x) * 4 + c] + px[((2 * y) * w + 2 * x + 1) * 4 + c]
                                    + px[((2 * y + 1) * w + 2 * x) * 4 + c] + px[((2 * y + 1) * w + 2 * x + 1) * 4 + c]) * 0.25f;
                        }
                        cur.put(t, np);
                        tw[k] = nw; th[k] = nh;
                    }
                }
            } else {
                // plain box filter of the previous level
                int pw = lw * 2, ph = lh * 2;
                for (int y = 0; y < lh; y++) for (int x = 0; x < lw; x++) for (int c = 0; c < 4; c++) {
                    int sx = Math.min(2 * x, pw - 1), sy = Math.min(2 * y, ph - 1);
                    int sx1 = Math.min(sx + 1, pw - 1), sy1 = Math.min(sy + 1, ph - 1);
                    int v = (prev[(sy * pw + sx) * 4 + c] & 255) + (prev[(sy * pw + sx1) * 4 + c] & 255)
                            + (prev[(sy1 * pw + sx) * 4 + c] & 255) + (prev[(sy1 * pw + sx1) * 4 + c] & 255);
                    out[(y * lw + x) * 4 + c] = (byte) ((v + 2) / 4);
                }
            }
            levels.add(out);
            prev = out;
            if (lw == 1 && lh == 1) break;
            lw = Math.max(1, lw / 2);
            lh = Math.max(1, lh / 2);
            L++;
        }
        return levels;
    }

    static float[] average(float[] px) {
        float[] a = new float[4];
        int n = px.length / 4;
        for (int i = 0; i < n; i++) for (int c = 0; c < 4; c++) a[c] += px[i * 4 + c];
        for (int c = 0; c < 4; c++) a[c] /= Math.max(1, n);
        return a;
    }

    static void put(byte[] out, int w, int x, int y, float[] src, int si) {
        int o = (y * w + x) * 4;
        for (int c = 0; c < 4; c++) out[o + c] = (byte) Math.max(0, Math.min(255, Math.round(src[si + c])));
    }

    // ------------------------------------------------------------------ geometry

    /** A corner with all attributes, before packing. */
    static class V {
        float px, py, pz, nx, ny, nz, ox, oy, oz, u, v, r, g, b, ao;
        float spec, rim, emis, soft, outline, sway;
        int type;
        int[] bi = new int[4];
        float[] bw = new float[4];
    }

    static class Part {
        int cls, flags; // flags: 1 = nocast, 2 = outline
        List<V> tris = new ArrayList<>();
    }

    static class Chunk {
        byte[] v, i;
        int nIdx;
        Chunk(byte[] v, List<Integer> ib) { this.v = v; this.i = idxBytes(ib); this.nIdx = ib.size(); }
    }

    static class OutMesh {
        String name, group;
        int lod, flags, skeleton = -1;
        float[] bmin = new float[3], bmax = new float[3], scale = new float[3], offset = new float[3];
        List<int[]> partHdr = new ArrayList<>();
        List<List<Chunk>> partChunks = new ArrayList<>();
        int verts, tris;
    }

    static OutMesh buildMesh(Erm e, Path texDir) throws IOException {
        // smoothed outline normals: average by position
        Map<Long, float[]> avg = new HashMap<>();
        int nc = e.nTri * 3;
        for (int k = 0; k < nc; k++) {
            long key = posKey(e.P[k * 3], e.P[k * 3 + 1], e.P[k * 3 + 2]);
            float[] a = avg.computeIfAbsent(key, kk -> new float[3]);
            a[0] += e.N[k * 3]; a[1] += e.N[k * 3 + 1]; a[2] += e.N[k * 3 + 2];
        }
        Map<Integer, Part> parts = new TreeMap<>();
        for (int t = 0; t < e.nTri; t++) {
            Mat m = e.mats.get(Math.max(0, Math.min(e.mats.size() - 1, e.MI[t])));
            int cls = m.cls();
            int pf = ((m.flags & F_NOCAST) != 0 ? 1 : 0);
            int key = cls * 4 + pf;
            Part part = parts.computeIfAbsent(key, kk -> { Part p = new Part(); p.cls = cls; p.flags = pf; return p; });
            if (m.outline > 0) part.flags |= 2;
            V[] c = new V[3];
            for (int j = 0; j < 3; j++) {
                int k = t * 3 + j;
                V v = new V();
                v.px = e.P[k * 3]; v.py = e.P[k * 3 + 1]; v.pz = e.P[k * 3 + 2];
                v.nx = e.N[k * 3]; v.ny = e.N[k * 3 + 1]; v.nz = e.N[k * 3 + 2];
                float[] a = avg.get(posKey(v.px, v.py, v.pz));
                float al = (float) Math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2]);
                if (al < 1e-6f) { v.ox = v.nx; v.oy = v.ny; v.oz = v.nz; } else { v.ox = a[0] / al; v.oy = a[1] / al; v.oz = a[2] / al; }
                v.u = e.UV[k * 2]; v.v = e.UV[k * 2 + 1];
                v.r = m.r * e.COL[k * 4]; v.g = m.g * e.COL[k * 4 + 1]; v.b = m.b * e.COL[k * 4 + 2]; v.ao = e.COL[k * 4 + 3];
                v.spec = m.spec; v.rim = m.rim; v.emis = m.emis; v.soft = m.soft; v.outline = m.outline; v.sway = m.sway;
                v.type = m.type();
                if (e.skinned) {
                    for (int q = 0; q < 4; q++) { v.bi[q] = e.BI[k * 4 + q] & 255; v.bw[q] = e.BW[k * 4 + q]; }
                }
                c[j] = v;
            }
            Tile tile = loadTile(texDir, m.tex == null || m.tex.isEmpty() ? "_white" : m.tex);
            if (tile.repeat) splitTiled(c, tile, part.tris);
            else {
                for (V v : c) mapClamp(v, tile);
                part.tris.add(c[0]); part.tris.add(c[1]); part.tris.add(c[2]);
            }
        }
        OutMesh om = new OutMesh();
        om.name = e.name;
        int at = e.name.indexOf('@');
        om.group = at >= 0 ? e.name.substring(0, at) : e.name;
        om.lod = at >= 0 ? Integer.parseInt(e.name.substring(at + 1)) : 0;
        om.flags = e.skinned ? 1 : 0;
        float[] mn = {1e30f, 1e30f, 1e30f}, mx = {-1e30f, -1e30f, -1e30f};
        for (Part p : parts.values()) for (V v : p.tris) {
            mn[0] = Math.min(mn[0], v.px); mn[1] = Math.min(mn[1], v.py); mn[2] = Math.min(mn[2], v.pz);
            mx[0] = Math.max(mx[0], v.px); mx[1] = Math.max(mx[1], v.py); mx[2] = Math.max(mx[2], v.pz);
        }
        for (int i = 0; i < 3; i++) {
            if (mn[i] > mx[i]) { mn[i] = 0; mx[i] = 0; }
            om.bmin[i] = mn[i]; om.bmax[i] = mx[i];
            om.offset[i] = (mn[i] + mx[i]) * 0.5f;
            om.scale[i] = Math.max((mx[i] - mn[i]) * 0.5f, 1e-4f);
        }
        int stride = e.skinned ? 36 : 28;
        for (Part p : parts.values()) {
            om.partHdr.add(new int[]{p.cls, p.flags});
            List<Chunk> chunks = new ArrayList<>();
            Map<ByteKey, Integer> index = new HashMap<>();
            ByteArrayOutputStream vb = new ByteArrayOutputStream();
            List<Integer> ib = new ArrayList<>();
            int nv = 0;
            for (int t = 0; t < p.tris.size(); t += 3) {
                if (nv > 65535 - 3) {
                    chunks.add(new Chunk(vb.toByteArray(), ib));
                    om.verts += nv;
                    vb.reset(); ib.clear(); index.clear(); nv = 0;
                }
                for (int j = 0; j < 3; j++) {
                    byte[] packed = pack(p.tris.get(t + j), om, e.skinned, stride);
                    ByteKey bk = new ByteKey(packed);
                    Integer id = index.get(bk);
                    if (id == null) {
                        id = nv++;
                        index.put(bk, id);
                        vb.write(packed, 0, packed.length);
                    }
                    ib.add(id);
                }
                om.tris++;
            }
            if (!ib.isEmpty()) {
                chunks.add(new Chunk(vb.toByteArray(), ib));
                om.verts += nv;
            }
            om.partChunks.add(chunks);
        }
        return om;
    }

    static long posKey(float x, float y, float z) {
        long a = Math.round(x * 20000.0), b = Math.round(y * 20000.0), c = Math.round(z * 20000.0);
        return (a * 73856093L) ^ (b * 19349663L) ^ (c * 83492791L);
    }

    static void mapClamp(V v, Tile t) {
        float u = Math.max(0, Math.min(1, v.u)), w = Math.max(0, Math.min(1, v.v));
        v.u = t.u0 + u * (t.u1 - t.u0);
        v.v = t.v0 + (1 - w) * (t.v1 - t.v0);
    }

    /** Clip a triangle against unit UV cells; each piece is mapped into the tile's atlas cell. */
    static void splitTiled(V[] c, Tile t, List<V> out) {
        float umin = Math.min(c[0].u, Math.min(c[1].u, c[2].u)), umax = Math.max(c[0].u, Math.max(c[1].u, c[2].u));
        float vmin = Math.min(c[0].v, Math.min(c[1].v, c[2].v)), vmax = Math.max(c[0].v, Math.max(c[1].v, c[2].v));
        int i0 = (int) Math.floor(umin + 1e-5f), i1 = (int) Math.ceil(umax - 1e-5f) - 1;
        int j0 = (int) Math.floor(vmin + 1e-5f), j1 = (int) Math.ceil(vmax - 1e-5f) - 1;
        if (i1 < i0) i1 = i0;
        if (j1 < j0) j1 = j0;
        if ((long) (i1 - i0 + 1) * (j1 - j0 + 1) > 2500) {
            // absurd UV span: squash into a single cell
            for (V v : c) { V m = copy(v); m.u = 0.5f; m.v = 0.5f; mapTile(m, t, 0, 0); out.add(m); }
            return;
        }
        for (int i = i0; i <= i1; i++) {
            for (int j = j0; j <= j1; j++) {
                // polygon in barycentric coordinates
                List<float[]> poly = new ArrayList<>();
                poly.add(new float[]{1, 0, 0}); poly.add(new float[]{0, 1, 0}); poly.add(new float[]{0, 0, 1});
                poly = clip(poly, c, 0, i, true);
                poly = clip(poly, c, 0, i + 1, false);
                poly = clip(poly, c, 1, j, true);
                poly = clip(poly, c, 1, j + 1, false);
                if (poly.size() < 3) continue;
                V[] pv = new V[poly.size()];
                for (int k = 0; k < poly.size(); k++) {
                    pv[k] = interp(c, poly.get(k));
                    mapTile(pv[k], t, i, j);
                }
                for (int k = 1; k + 1 < pv.length; k++) {
                    if (area(pv[0], pv[k], pv[k + 1]) < 1e-14f) continue;
                    out.add(pv[0]); out.add(pv[k]); out.add(pv[k + 1]);
                }
            }
        }
    }

    static float area(V a, V b, V c) {
        float ux = b.px - a.px, uy = b.py - a.py, uz = b.pz - a.pz, vx = c.px - a.px, vy = c.py - a.py, vz = c.pz - a.pz;
        float x = uy * vz - uz * vy, y = uz * vx - ux * vz, z = ux * vy - uy * vx;
        return x * x + y * y + z * z;
    }

    static float uvAt(V[] c, float[] b, int axis) {
        return axis == 0 ? b[0] * c[0].u + b[1] * c[1].u + b[2] * c[2].u : b[0] * c[0].v + b[1] * c[1].v + b[2] * c[2].v;
    }

    static List<float[]> clip(List<float[]> poly, V[] c, int axis, float edge, boolean keepAbove) {
        List<float[]> out = new ArrayList<>();
        int n = poly.size();
        for (int k = 0; k < n; k++) {
            float[] a = poly.get(k), b = poly.get((k + 1) % n);
            float da = uvAt(c, a, axis) - edge, db = uvAt(c, b, axis) - edge;
            if (!keepAbove) { da = -da; db = -db; }
            boolean ina = da >= -1e-6f, inb = db >= -1e-6f;
            if (ina) out.add(a);
            if (ina != inb) {
                float s = da / (da - db);
                out.add(new float[]{a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s, a[2] + (b[2] - a[2]) * s});
            }
        }
        return out;
    }

    static V copy(V s) {
        V v = new V();
        v.px = s.px; v.py = s.py; v.pz = s.pz; v.nx = s.nx; v.ny = s.ny; v.nz = s.nz; v.ox = s.ox; v.oy = s.oy; v.oz = s.oz;
        v.u = s.u; v.v = s.v; v.r = s.r; v.g = s.g; v.b = s.b; v.ao = s.ao; v.spec = s.spec; v.rim = s.rim; v.emis = s.emis;
        v.soft = s.soft; v.outline = s.outline; v.sway = s.sway; v.type = s.type;
        v.bi = s.bi.clone(); v.bw = s.bw.clone();
        return v;
    }

    static V interp(V[] c, float[] b) {
        V v = copy(c[0]);
        v.px = b[0] * c[0].px + b[1] * c[1].px + b[2] * c[2].px;
        v.py = b[0] * c[0].py + b[1] * c[1].py + b[2] * c[2].py;
        v.pz = b[0] * c[0].pz + b[1] * c[1].pz + b[2] * c[2].pz;
        v.nx = b[0] * c[0].nx + b[1] * c[1].nx + b[2] * c[2].nx;
        v.ny = b[0] * c[0].ny + b[1] * c[1].ny + b[2] * c[2].ny;
        v.nz = b[0] * c[0].nz + b[1] * c[1].nz + b[2] * c[2].nz;
        v.ox = b[0] * c[0].ox + b[1] * c[1].ox + b[2] * c[2].ox;
        v.oy = b[0] * c[0].oy + b[1] * c[1].oy + b[2] * c[2].oy;
        v.oz = b[0] * c[0].oz + b[1] * c[1].oz + b[2] * c[2].oz;
        v.u = b[0] * c[0].u + b[1] * c[1].u + b[2] * c[2].u;
        v.v = b[0] * c[0].v + b[1] * c[1].v + b[2] * c[2].v;
        v.r = b[0] * c[0].r + b[1] * c[1].r + b[2] * c[2].r;
        v.g = b[0] * c[0].g + b[1] * c[1].g + b[2] * c[2].g;
        v.b = b[0] * c[0].b + b[1] * c[1].b + b[2] * c[2].b;
        v.ao = b[0] * c[0].ao + b[1] * c[1].ao + b[2] * c[2].ao;
        v.sway = b[0] * c[0].sway + b[1] * c[1].sway + b[2] * c[2].sway;
        // blend skin weights by bone
        Map<Integer, Float> w = new HashMap<>();
        for (int k = 0; k < 3; k++) for (int q = 0; q < 4; q++) {
            if (c[k].bw[q] <= 0) continue;
            w.merge(c[k].bi[q], c[k].bw[q] * b[k], Float::sum);
        }
        List<Map.Entry<Integer, Float>> es = new ArrayList<>(w.entrySet());
        es.sort((x, y) -> Float.compare(y.getValue(), x.getValue()));
        float sum = 0;
        for (int q = 0; q < 4 && q < es.size(); q++) sum += es.get(q).getValue();
        for (int q = 0; q < 4; q++) {
            if (q < es.size() && sum > 0) { v.bi[q] = es.get(q).getKey(); v.bw[q] = es.get(q).getValue() / sum; }
            else { v.bi[q] = 0; v.bw[q] = 0; }
        }
        return v;
    }

    static void mapTile(V v, Tile t, int ci, int cj) {
        float u = Math.max(0, Math.min(1, v.u - ci)), w = Math.max(0, Math.min(1, v.v - cj));
        v.u = t.u0 + u * (t.u1 - t.u0);
        v.v = t.v0 + (1 - w) * (t.v1 - t.v0);
    }

    static byte[] pack(V v, OutMesh om, boolean skinned, int stride) {
        ByteBuffer b = ByteBuffer.allocate(stride).order(ByteOrder.LITTLE_ENDIAN);
        b.putShort(qs((v.px - om.offset[0]) / om.scale[0]));
        b.putShort(qs((v.py - om.offset[1]) / om.scale[1]));
        b.putShort(qs((v.pz - om.offset[2]) / om.scale[2]));
        b.putShort(qs(v.sway));
        float nl = (float) Math.sqrt(v.nx * v.nx + v.ny * v.ny + v.nz * v.nz);
        if (nl < 1e-8f) nl = 1;
        b.put(qb(v.nx / nl)); b.put(qb(v.ny / nl)); b.put(qb(v.nz / nl)); b.put(qb(Math.min(1f, v.outline)));
        float ol = (float) Math.sqrt(v.ox * v.ox + v.oy * v.oy + v.oz * v.oz);
        if (ol < 1e-8f) ol = 1;
        b.put(qb(v.ox / ol)); b.put(qb(v.oy / ol)); b.put(qb(v.oz / ol)); b.put(qb(v.type / 7f));
        b.putShort(qus(v.u)); b.putShort(qus(v.v));
        b.put(qub(v.r)); b.put(qub(v.g)); b.put(qub(v.b)); b.put(qub(v.ao));
        b.put(qub(v.spec)); b.put(qub(v.rim)); b.put(qub(v.emis)); b.put(qub(v.soft));
        if (skinned) {
            for (int q = 0; q < 4; q++) b.put((byte) v.bi[q]);
            // weights to bytes, keep the sum at 255
            int[] w = new int[4];
            int s = 0;
            for (int q = 0; q < 4; q++) { w[q] = Math.round(Math.max(0, v.bw[q]) * 255); s += w[q]; }
            w[0] += 255 - s;
            for (int q = 0; q < 4; q++) b.put((byte) Math.max(0, Math.min(255, w[q])));
        }
        return b.array();
    }

    static short qs(float f) { return (short) Math.round(Math.max(-1f, Math.min(1f, f)) * 32767f); }
    static byte qb(float f) { return (byte) Math.round(Math.max(-1f, Math.min(1f, f)) * 127f); }
    static byte qub(float f) { return (byte) Math.round(Math.max(0f, Math.min(1f, f)) * 255f); }
    static short qus(float f) { return (short) Math.round(Math.max(0f, Math.min(1f, f)) * 65535f); }

    static byte[] idxBytes(List<Integer> ib) {
        int n = ib.size();
        ByteBuffer b = ByteBuffer.allocate(((n * 2 + 3) / 4) * 4).order(ByteOrder.LITTLE_ENDIAN);
        for (int i : ib) b.putShort((short) i);
        return b.array();
    }

    static final class ByteKey {
        final byte[] d;
        final int h;
        ByteKey(byte[] d) { this.d = d; this.h = Arrays.hashCode(d); }
        @Override public int hashCode() { return h; }
        @Override public boolean equals(Object o) { return o instanceof ByteKey && Arrays.equals(d, ((ByteKey) o).d); }
    }

    // ------------------------------------------------------------------ writing

    static class W {
        final DataOutputStream o;
        final ByteBuffer tmp = ByteBuffer.allocate(8).order(ByteOrder.LITTLE_ENDIAN);
        W(OutputStream os) { o = new DataOutputStream(new BufferedOutputStream(os, 1 << 20)); }
        void i(int v) throws IOException { tmp.clear(); tmp.putInt(v); o.write(tmp.array(), 0, 4); }
        void f(float v) throws IOException { tmp.clear(); tmp.putFloat(v); o.write(tmp.array(), 0, 4); }
        void s(String v) throws IOException { byte[] b = v.getBytes(StandardCharsets.UTF_8); i(b.length); o.write(b); int pad = (4 - b.length % 4) % 4; for (int k = 0; k < pad; k++) o.write(0); }
        void b(byte[] v) throws IOException { o.write(v); }
    }

    public static void main(String[] args) throws Exception {
        Path modelsDir = Paths.get(args.length > 0 ? args[0] : "build/models");
        Path texDir = Paths.get(args.length > 1 ? args[1] : "build/tex");
        Path out = Paths.get(args.length > 2 ? args[2] : "assets/pongo.bin");
        loadTile(texDir, "_white");
        List<Path> files = new ArrayList<>();
        try (DirectoryStream<Path> ds = Files.newDirectoryStream(modelsDir, "*.erm")) { for (Path p : ds) files.add(p); }
        Collections.sort(files);
        // extra tiles requested explicitly (sprites/UI used by code, not by meshes)
        Path extraList = texDir.resolve("_extra.txt");
        if (Files.exists(extraList)) for (String line : Files.readAllLines(extraList)) if (!line.trim().isEmpty()) loadTile(texDir, line.trim());
        List<Erm> erms = new ArrayList<>();
        for (Path p : files) erms.add(readErm(p));
        // tiles are loaded lazily while building meshes; do a pre-pass so packing happens first
        for (Erm e : erms) for (Mat m : e.mats) loadTile(texDir, m.tex == null || m.tex.isEmpty() ? "_white" : m.tex);
        pack();
        List<OutMesh> meshes = new ArrayList<>();
        List<Erm> skels = new ArrayList<>();
        long totalV = 0, totalT = 0;
        for (Erm e : erms) {
            OutMesh om = buildMesh(e, texDir);
            if (e.skinned) { om.skeleton = skels.size(); skels.add(e); }
            meshes.add(om);
            totalV += om.verts; totalT += om.tris;
            System.out.printf("  %-28s lod%d tris %7d verts %7d parts %d%s%n", om.group, om.lod, om.tris, om.verts, om.partHdr.size(), e.skinned ? " skinned bones=" + e.bones.size() + " clips=" + e.clips.size() : "");
        }
        List<byte[]> levels = buildAtlasLevels();
        Files.createDirectories(out.getParent());
        try (OutputStream os = Files.newOutputStream(out)) {
            W w = new W(os);
            w.b("PGO1".getBytes(StandardCharsets.US_ASCII));
            w.i(1);
            // atlas
            w.i(atlasW); w.i(atlasH); w.i(levels.size());
            int lw = atlasW, lh = atlasH;
            for (byte[] lv : levels) { w.i(lw); w.i(lh); w.b(lv); lw = Math.max(1, lw / 2); lh = Math.max(1, lh / 2); }
            // tiles (for sprites / UI lookups by name)
            w.i(tiles.size());
            for (Tile t : tiles) { w.s(t.name); w.f(t.u0); w.f(t.v0); w.f(t.u1); w.f(t.v1); }
            // meshes
            w.i(meshes.size());
            for (OutMesh m : meshes) {
                w.s(m.name); w.s(m.group); w.i(m.lod); w.i(m.flags); w.i(m.skeleton);
                for (int i = 0; i < 3; i++) w.f(m.bmin[i]);
                for (int i = 0; i < 3; i++) w.f(m.bmax[i]);
                for (int i = 0; i < 3; i++) w.f(m.scale[i]);
                for (int i = 0; i < 3; i++) w.f(m.offset[i]);
                w.i(m.partHdr.size());
                for (int p = 0; p < m.partHdr.size(); p++) {
                    w.i(m.partHdr.get(p)[0]); w.i(m.partHdr.get(p)[1]);
                    List<Chunk> ch = m.partChunks.get(p);
                    w.i(ch.size());
                    int stride = (m.flags & 1) != 0 ? 36 : 28;
                    for (Chunk c : ch) {
                        w.i(c.v.length / stride);
                        w.i(c.nIdx); // index data is padded to 4 bytes
                        w.b(c.v);
                        w.b(c.i);
                    }
                }
            }
            // skeletons
            w.i(skels.size());
            for (Erm e : skels) {
                w.s(e.name);
                w.i(e.bones.size());
                for (Bone b : e.bones) {
                    w.s(b.name); w.i(b.parent); w.i(b.dyn);
                    for (float f : b.rest) w.f(f);
                }
                w.i(e.clips.size());
                for (Clip c : e.clips) {
                    w.s(c.name); w.f(c.fps); w.i(c.frames); w.i(c.loop);
                    for (float f : c.data) w.f(f);
                }
            }
            // extras (named float arrays, e.g. attachment points)
            int nx = 0;
            for (Erm e : erms) nx += e.extras.size();
            w.i(nx);
            for (Erm e : erms) for (Map.Entry<String, float[]> x : e.extras.entrySet()) {
                w.s(e.name + "." + x.getKey());
                w.i(x.getValue().length);
                for (float f : x.getValue()) w.f(f);
            }
            w.o.flush();
        }
        System.out.printf("atlas %dx%d, %d tiles; %d meshes, %d tris, %d verts -> %s (%.1f MB)%n", atlasW, atlasH, tiles.size(),
                meshes.size(), totalT, totalV, out, Files.size(out) / 1048576.0);
    }
}
