package com.pongo.app;

import android.opengl.GLES20;

import com.pongo.core.PongoAssets;
import com.pongo.core.RenderFrame;
import com.pongo.core.Shaders;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.FloatBuffer;
import java.nio.IntBuffer;
import java.nio.ShortBuffer;

/**
 * OpenGL ES 2.0 executor for RenderFrames: shadow map, cel-shaded meshes, toon water, painted sky, inverted-hull ink
 * outlines, decals, blended draws, particles and screen overlays. Pass for pass the same as the WebGL
 * preview harness (tools/web/render.js), with the GLSL sources from com.pongo.core.Shaders.
 *
 * It can also draw on top of another renderer's frame (no clear, no sky) sharing its depth buffer;
 * call {@link #render} and then restore your own GL state.
 */
public final class GLRenderer {
    private static final String[] ATTRS = {"aPos", "aNrm", "aOut", "aUV", "aCol", "aMat", "aBone", "aWeight"};
    private static final int MAX_QUADS = 16384;

    private static final class Prog {
        final String name;
        final boolean skin;
        int id, stamp = -1;
        int uVP, uModel, uPosScale, uPosOffset, uWind, uShadowVP, uCamPos, uSunDir, uLightCol, uShadeCol, uSkinShade,
                uRimCol, uSkyTop, uSkyHor, uSkyLow, uSunCol, uMoonDir, uFogCol, uFog, uShadowP, uNight, uTime, uLamp,
                uLampCol, uTint, uEmis, uInk, uScreen, uOutline, uAtlas, uShadow, uBones, uInvVP, uAdd, uSpeed, uFlash,
                uVignette, uHaze, uCloud, uCloudLit, uCloudShade, uWater;

        Prog(String name, boolean skin) { this.name = name; this.skin = skin; }
    }

    private final PongoAssets a;
    private final Prog[] progs = new Prog[Shaders.PROGRAMS.length];
    private Prog main, mainSkin, mainDouble, mainCutout, mainDecal, mainDecalSkin, water, outline, outlineSkin,
            shadowP, shadowSkin, shadowCutout, sky, part, screen;
    private int atlasTex, fsTri, quadIdx, partVbo;
    private int shadowTex, shadowFbo, shadowRb, shadowSize;
    private int stamp;
    private Prog cur;
    private FloatBuffer boneBuf;
    private IntBuffer partBuf;
    private final float[] v4 = new float[4];

    public GLRenderer(PongoAssets assets) { a = assets; }

    /** (Re)creates every GL object; call from onSurfaceCreated (the old context and its objects are gone). */
    public void onSurfaceCreated() {
        cur = null;
        shadowSize = 0;
        for (int i = 0; i < Shaders.PROGRAMS.length; i++) {
            String[] p = Shaders.PROGRAMS[i];
            Prog pr = new Prog(p[0], p[1].contains("SKIN"));
            pr.id = link(p[1] + Shaders.source(p[2]), p[1] + Shaders.source(p[3]));
            locate(pr);
            progs[i] = pr;
        }
        main = prog("main"); mainSkin = prog("main_skin"); mainDouble = prog("main_double"); mainCutout = prog("main_cutout");
        mainDecal = prog("main_decal"); mainDecalSkin = prog("main_decal_skin"); water = prog("water"); outline = prog("outline");
        outlineSkin = prog("outline_skin"); shadowP = prog("shadow"); shadowSkin = prog("shadow_skin");
        shadowCutout = prog("shadow_cutout"); sky = prog("sky"); part = prog("part"); screen = prog("screen");

        int[] id = new int[1];
        GLES20.glGenTextures(1, id, 0);
        atlasTex = id[0];
        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, atlasTex);
        GLES20.glPixelStorei(GLES20.GL_UNPACK_ALIGNMENT, 1);
        for (int l = 0; l < a.atlasLevels.length; l++) {
            ByteBuffer lv = a.atlasLevels[l];
            if (lv == null) throw new IllegalStateException("pongo.bin was loaded without its atlas");
            lv.position(0);
            GLES20.glTexImage2D(GLES20.GL_TEXTURE_2D, l, GLES20.GL_RGBA, a.levelW[l], a.levelH[l], 0, GLES20.GL_RGBA,
                    GLES20.GL_UNSIGNED_BYTE, lv);
        }
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_MIN_FILTER, GLES20.GL_LINEAR_MIPMAP_LINEAR);
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_MAG_FILTER, GLES20.GL_LINEAR);
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_WRAP_S, GLES20.GL_CLAMP_TO_EDGE);
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_WRAP_T, GLES20.GL_CLAMP_TO_EDGE);

        for (PongoAssets.Mesh me : a.meshes) {
            int stride = me.stride();
            for (PongoAssets.Part p : me.parts) {
                for (PongoAssets.Chunk c : p.chunks) {
                    c.vbo = buffer(GLES20.GL_ARRAY_BUFFER, c.verts, c.nVerts * stride);
                    c.ibo = buffer(GLES20.GL_ELEMENT_ARRAY_BUFFER, c.idx, c.nIdx * 2);
                }
            }
        }
        FloatBuffer tri = ByteBuffer.allocateDirect(6 * 4).order(ByteOrder.nativeOrder()).asFloatBuffer();
        tri.put(new float[]{-1, -1, 3, -1, -1, 3}).position(0);
        fsTri = buffer(GLES20.GL_ARRAY_BUFFER, tri, 6 * 4);
        ShortBuffer qi = ByteBuffer.allocateDirect(MAX_QUADS * 12).order(ByteOrder.nativeOrder()).asShortBuffer();
        for (int q = 0; q < MAX_QUADS; q++) {
            short b = (short) (q * 4);
            qi.put(b).put((short) (b + 1)).put((short) (b + 2)).put(b).put((short) (b + 2)).put((short) (b + 3));
        }
        qi.position(0);
        quadIdx = buffer(GLES20.GL_ELEMENT_ARRAY_BUFFER, qi, MAX_QUADS * 12);
        GLES20.glGenBuffers(1, id, 0);
        partVbo = id[0];
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, 0);
        GLES20.glBindBuffer(GLES20.GL_ELEMENT_ARRAY_BUFFER, 0);
    }

    /**
     * Draws one frame into the current framebuffer.
     * @param overlay true to draw on top of what is already there: no clear and no sky; the depth buffer is kept
     */
    public void render(RenderFrame f, boolean overlay) {
        stamp++;
        cur = null;
        GLES20.glActiveTexture(GLES20.GL_TEXTURE1);
        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, 0);
        GLES20.glActiveTexture(GLES20.GL_TEXTURE0);
        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, atlasTex);
        GLES20.glDisable(GLES20.GL_BLEND);

        // ---- shadow pass
        if (f.shadowOn) {
            int[] prevFbo = new int[1];
            GLES20.glGetIntegerv(GLES20.GL_FRAMEBUFFER_BINDING, prevFbo, 0);
            ensureShadow(f.shadowSize);
            GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, shadowFbo);
            GLES20.glViewport(0, 0, shadowSize, shadowSize);
            GLES20.glClearColor(1, 1, 1, 1);
            GLES20.glDepthMask(true);
            GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT | GLES20.GL_DEPTH_BUFFER_BIT);
            GLES20.glEnable(GLES20.GL_DEPTH_TEST);
            GLES20.glDepthFunc(GLES20.GL_LEQUAL);
            GLES20.glDisable(GLES20.GL_CULL_FACE);
            GLES20.glEnable(GLES20.GL_POLYGON_OFFSET_FILL);
            GLES20.glPolygonOffset(1.5f, 3.0f);
            for (int d = 0; d < f.count; d++) {
                if ((f.flags[d] & RenderFrame.D_NO_SHADOW) != 0) continue;
                PongoAssets.Mesh me = a.meshes[f.mesh[d]];
                if (!me.castsShadow) continue;
                if (me.skinned()) {
                    drawMesh(begin(shadowSkin, f, f.shadowVP), me, f, d, F_SHADOW_ANY);
                } else {
                    drawMesh(begin(shadowP, f, f.shadowVP), me, f, d, F_SHADOW_SOLID);
                    drawMesh(begin(shadowCutout, f, f.shadowVP), me, f, d, F_SHADOW_CUT);
                }
            }
            GLES20.glDisable(GLES20.GL_POLYGON_OFFSET_FILL);
            GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, prevFbo[0]);
            stamp++; // globals carry the shadow VP until re-set for the main pass
        }
        GLES20.glActiveTexture(GLES20.GL_TEXTURE1);
        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, shadowTex != 0 ? shadowTex : atlasTex);
        GLES20.glActiveTexture(GLES20.GL_TEXTURE0);

        GLES20.glViewport(0, 0, f.screenW, f.screenH);
        if (!overlay) {
            GLES20.glClearColor(f.fogCol[0], f.fogCol[1], f.fogCol[2], 1);
            GLES20.glDepthMask(true);
            GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT | GLES20.GL_DEPTH_BUFFER_BIT);
        }
        GLES20.glEnable(GLES20.GL_DEPTH_TEST);
        GLES20.glDepthFunc(GLES20.GL_LEQUAL);
        GLES20.glDepthMask(true);
        GLES20.glEnable(GLES20.GL_CULL_FACE);
        GLES20.glCullFace(GLES20.GL_BACK);

        // ---- opaque, double-sided, cutout and water parts (decals come after the outlines)
        for (int cls = 0; cls <= 3; cls++) {
            for (int d = 0; d < f.count; d++) {
                if ((f.flags[d] & RenderFrame.D_BLEND) != 0) continue;
                PongoAssets.Mesh me = a.meshes[f.mesh[d]];
                if (!hasClass(me, cls)) continue;
                Prog pr = me.skinned() ? mainSkin : cls == 1 ? mainDouble : cls == 2 ? mainCutout : cls == 3 ? water : main;
                if (cls == 1 || cls == 2 || (f.flags[d] & RenderFrame.D_NO_CULL) != 0) GLES20.glDisable(GLES20.GL_CULL_FACE);
                else GLES20.glEnable(GLES20.GL_CULL_FACE);
                drawMesh(begin(pr, f, f.viewProj), me, f, d, cls);
            }
        }
        // ---- painted sky, after the opaque surfaces so only the pixels that still show sky are shaded
        if (!overlay || f.skyOverlay) sky(f);
        // ---- ink outlines (inverted hull)
        GLES20.glEnable(GLES20.GL_CULL_FACE);
        GLES20.glCullFace(GLES20.GL_FRONT);
        for (int d = 0; d < f.count; d++) {
            if ((f.flags[d] & RenderFrame.D_NO_OUTLINE) != 0) continue;
            PongoAssets.Mesh me = a.meshes[f.mesh[d]];
            if (!me.hasOutline) continue;
            drawMesh(begin(me.skinned() ? outlineSkin : outline, f, f.viewProj), me, f, d, F_OUTLINE);
        }
        GLES20.glCullFace(GLES20.GL_BACK);
        // ---- decals (eyes, mouths, prints): alpha blended over the surfaces they sit on
        GLES20.glEnable(GLES20.GL_BLEND);
        GLES20.glBlendFunc(GLES20.GL_SRC_ALPHA, GLES20.GL_ONE_MINUS_SRC_ALPHA);
        GLES20.glDepthMask(false);
        GLES20.glEnable(GLES20.GL_POLYGON_OFFSET_FILL);
        GLES20.glPolygonOffset(-1.0f, -2.0f);
        GLES20.glDisable(GLES20.GL_CULL_FACE);
        for (int d = 0; d < f.count; d++) {
            PongoAssets.Mesh me = a.meshes[f.mesh[d]];
            if (!hasClass(me, 4)) continue;
            drawMesh(begin(me.skinned() ? mainDecalSkin : mainDecal, f, f.viewProj), me, f, d, 4);
        }
        GLES20.glDisable(GLES20.GL_POLYGON_OFFSET_FILL);
        // ---- blended draws
        for (int d = 0; d < f.count; d++) {
            if ((f.flags[d] & RenderFrame.D_BLEND) == 0) continue;
            PongoAssets.Mesh me = a.meshes[f.mesh[d]];
            drawMesh(begin(me.skinned() ? mainSkin : mainDouble, f, f.viewProj), me, f, d, F_ALL);
        }
        // ---- particles
        particles(f, f.alphaQuads, f.alphaCount, false);
        particles(f, f.addQuads, f.addCount, true);
        // ---- screen overlay (speed lines, impact flash, vignette)
        if (f.speed[0] > 0 || f.flash[3] > 0 || f.vignette[3] > 0) {
            GLES20.glDisable(GLES20.GL_DEPTH_TEST);
            GLES20.glBlendFunc(GLES20.GL_SRC_ALPHA, GLES20.GL_ONE_MINUS_SRC_ALPHA);
            use(screen);
            attribs(1);
            GLES20.glUniform4f(screen.uSpeed, f.speed[0], f.speed[1], f.screenW / (float) f.screenH, f.speed[3]);
            u4(screen.uFlash, f.flash);
            u4(screen.uVignette, f.vignette);
            fullScreen();
            GLES20.glEnable(GLES20.GL_DEPTH_TEST);
        }
        GLES20.glDisable(GLES20.GL_BLEND);
        GLES20.glDepthMask(true);
        GLES20.glCullFace(GLES20.GL_BACK);
        GLES20.glDisable(GLES20.GL_CULL_FACE);
        attribs(0);
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, 0);
        GLES20.glBindBuffer(GLES20.GL_ELEMENT_ARRAY_BUFFER, 0);
        GLES20.glUseProgram(0);
        cur = null;
    }

    /** Full-screen sky at the far plane: depth-tested against what is drawn, never writing depth. */
    private void sky(RenderFrame f) {
        GLES20.glDisable(GLES20.GL_CULL_FACE);
        GLES20.glDepthMask(false);
        GLES20.glDepthFunc(GLES20.GL_LEQUAL);
        use(sky);
        attribs(1);
        GLES20.glUniformMatrix4fv(sky.uInvVP, 1, false, f.invViewProj, 0);
        u3(sky.uSkyTop, f.skyTop); u3(sky.uSkyHor, f.skyHor); u3(sky.uSkyLow, f.skyLow); u3(sky.uSunDir, f.sunDir);
        u3(sky.uSunCol, f.sunCol); u3(sky.uMoonDir, f.moonDir);
        u3(sky.uCloudLit, f.cloudLit); u3(sky.uCloudShade, f.cloudShade); u4(sky.uCloud, f.cloud);
        GLES20.glUniform1f(sky.uNight, f.night);
        GLES20.glUniform1f(sky.uTime, f.time);
        fullScreen();
        GLES20.glDepthMask(true);
    }

    // part filters for drawMesh besides a class index 0..4
    private static final int F_ALL = -1, F_OUTLINE = -2, F_SHADOW_ANY = -3, F_SHADOW_SOLID = -4, F_SHADOW_CUT = -5;

    private static boolean accept(PongoAssets.Part p, int filter) {
        switch (filter) {
            case F_ALL: return true;
            case F_OUTLINE: return (p.flags & PongoAssets.PART_OUTLINE) != 0 && p.cls != PongoAssets.CLS_DOUBLE && p.cls != PongoAssets.CLS_CUTOUT;
            case F_SHADOW_ANY: return (p.flags & PongoAssets.PART_NOCAST) == 0;
            case F_SHADOW_SOLID: return (p.flags & PongoAssets.PART_NOCAST) == 0 && p.cls != PongoAssets.CLS_CUTOUT;
            case F_SHADOW_CUT: return (p.flags & PongoAssets.PART_NOCAST) == 0 && p.cls == PongoAssets.CLS_CUTOUT;
            default: return p.cls == filter;
        }
    }

    private static boolean hasClass(PongoAssets.Mesh me, int cls) {
        for (PongoAssets.Part p : me.parts) if (p.cls == cls) return true;
        return false;
    }

    private void drawMesh(Prog pr, PongoAssets.Mesh me, RenderFrame f, int d, int filter) {
        boolean any = false;
        for (PongoAssets.Part p : me.parts) if (accept(p, filter)) { any = true; break; }
        if (!any) return;
        GLES20.glUniformMatrix4fv(pr.uModel, 1, false, f.model[d], 0);
        GLES20.glUniform3f(pr.uPosScale, me.scale[0], me.scale[1], me.scale[2]);
        GLES20.glUniform3f(pr.uPosOffset, me.offset[0], me.offset[1], me.offset[2]);
        if (pr.uTint >= 0) GLES20.glUniform4f(pr.uTint, f.tint[d * 4], f.tint[d * 4 + 1], f.tint[d * 4 + 2], f.tint[d * 4 + 3]);
        if (pr.uEmis >= 0) GLES20.glUniform1f(pr.uEmis, f.emis[d]);
        if (pr.skin && f.boneRows[d] > 0 && pr.uBones >= 0) {
            int n = f.boneRows[d] * 4;
            if (boneBuf == null || boneBuf.capacity() < n)
                boneBuf = ByteBuffer.allocateDirect(Math.max(n, Shaders.MAX_BONES * 12) * 4).order(ByteOrder.nativeOrder()).asFloatBuffer();
            boneBuf.clear();
            boneBuf.put(f.bones, f.boneStart[d], n).position(0);
            GLES20.glUniform4fv(pr.uBones, f.boneRows[d], boneBuf);
        }
        int stride = me.stride();
        for (PongoAssets.Part p : me.parts) {
            if (!accept(p, filter)) continue;
            for (PongoAssets.Chunk c : p.chunks) {
                GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, c.vbo);
                GLES20.glBindBuffer(GLES20.GL_ELEMENT_ARRAY_BUFFER, c.ibo);
                GLES20.glVertexAttribPointer(0, 4, GLES20.GL_SHORT, true, stride, 0);
                GLES20.glVertexAttribPointer(1, 4, GLES20.GL_BYTE, true, stride, 8);
                GLES20.glVertexAttribPointer(2, 4, GLES20.GL_BYTE, true, stride, 12);
                GLES20.glVertexAttribPointer(3, 2, GLES20.GL_UNSIGNED_SHORT, true, stride, 16);
                GLES20.glVertexAttribPointer(4, 4, GLES20.GL_UNSIGNED_BYTE, true, stride, 20);
                GLES20.glVertexAttribPointer(5, 4, GLES20.GL_UNSIGNED_BYTE, true, stride, 24);
                if (pr.skin) {
                    GLES20.glVertexAttribPointer(6, 4, GLES20.GL_UNSIGNED_BYTE, false, stride, 28);
                    GLES20.glVertexAttribPointer(7, 4, GLES20.GL_UNSIGNED_BYTE, true, stride, 32);
                }
                GLES20.glDrawElements(GLES20.GL_TRIANGLES, c.nIdx, GLES20.GL_UNSIGNED_SHORT, 0);
            }
        }
    }

    private void particles(RenderFrame f, int[] quads, int n, boolean additive) {
        if (n == 0) return;
        n = Math.min(n, MAX_QUADS);
        GLES20.glDisable(GLES20.GL_CULL_FACE);
        GLES20.glEnable(GLES20.GL_BLEND);
        GLES20.glDepthMask(false);
        use(part);
        attribs(3);
        GLES20.glUniformMatrix4fv(part.uVP, 1, false, f.viewProj, 0);
        u3(part.uCamPos, f.camPos);
        GLES20.glUniform4f(part.uFog, f.fogStart, f.fogEnd, f.fogMax, f.heightFog);
        u3(part.uFogCol, f.fogCol);
        GLES20.glUniform1f(part.uAdd, additive ? 1 : 0);
        GLES20.glUniform1i(part.uAtlas, 0);
        int ints = n * 24;
        if (partBuf == null || partBuf.capacity() < ints)
            partBuf = ByteBuffer.allocateDirect(Math.max(ints, 24 * 1024) * 4).order(ByteOrder.LITTLE_ENDIAN).asIntBuffer();
        partBuf.clear();
        partBuf.put(quads, 0, ints).position(0);
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, partVbo);
        GLES20.glBufferData(GLES20.GL_ARRAY_BUFFER, ints * 4, partBuf, GLES20.GL_STREAM_DRAW);
        GLES20.glVertexAttribPointer(0, 3, GLES20.GL_FLOAT, false, 24, 0);
        GLES20.glVertexAttribPointer(1, 2, GLES20.GL_FLOAT, false, 24, 12);
        GLES20.glVertexAttribPointer(2, 4, GLES20.GL_UNSIGNED_BYTE, true, 24, 20);
        GLES20.glBindBuffer(GLES20.GL_ELEMENT_ARRAY_BUFFER, quadIdx);
        if (additive) GLES20.glBlendFunc(GLES20.GL_ONE, GLES20.GL_ONE);
        else GLES20.glBlendFunc(GLES20.GL_SRC_ALPHA, GLES20.GL_ONE_MINUS_SRC_ALPHA);
        GLES20.glDrawElements(GLES20.GL_TRIANGLES, n * 6, GLES20.GL_UNSIGNED_SHORT, 0);
    }

    // ------------------------------------------------------------------ state helpers

    private Prog prog(String name) {
        for (Prog p : progs) if (p.name.equals(name)) return p;
        throw new IllegalArgumentException(name);
    }

    private void use(Prog p) {
        if (cur != p) {
            GLES20.glUseProgram(p.id);
            cur = p;
        }
    }

    /** Binds a mesh program and (once per pass) uploads the frame-wide uniforms. */
    private Prog begin(Prog pr, RenderFrame f, float[] vp) {
        use(pr);
        attribs(pr.skin ? 8 : 6);
        if (pr.stamp == stamp) return pr;
        pr.stamp = stamp;
        GLES20.glUniformMatrix4fv(pr.uVP, 1, false, vp, 0);
        u4(pr.uWind, f.wind);
        if (pr.uShadowVP >= 0) GLES20.glUniformMatrix4fv(pr.uShadowVP, 1, false, f.shadowVP, 0);
        u3(pr.uCamPos, f.camPos); u3(pr.uSunDir, f.sunDir); u3(pr.uLightCol, f.lightCol); u3(pr.uShadeCol, f.shadeCol);
        u3(pr.uSkinShade, f.skinShade); u3(pr.uRimCol, f.rimCol); u3(pr.uSkyTop, f.skyTop); u3(pr.uSkyHor, f.skyHor);
        u3(pr.uFogCol, f.fogCol); u3(pr.uSunCol, f.sunCol); u4(pr.uHaze, f.haze); u4(pr.uWater, f.water);
        if (pr.uTime >= 0) GLES20.glUniform1f(pr.uTime, f.time);
        if (pr.uFog >= 0) GLES20.glUniform4f(pr.uFog, f.fogStart, f.fogEnd, f.fogMax, f.heightFog);
        if (pr.uNight >= 0) GLES20.glUniform1f(pr.uNight, f.night);
        u4(pr.uLamp, f.lamp); u3(pr.uLampCol, f.lampCol); u3(pr.uInk, f.ink);
        if (pr.uScreen >= 0) GLES20.glUniform2f(pr.uScreen, f.screenW, f.screenH);
        if (pr.uOutline >= 0) GLES20.glUniform1f(pr.uOutline, f.outlinePx);
        if (pr.uShadowP >= 0)
            GLES20.glUniform4f(pr.uShadowP, 1f / Math.max(1, f.shadowSize), f.shadowBias, f.shadowOn ? 1 : 0, f.shadowStrength);
        if (pr.uAtlas >= 0) GLES20.glUniform1i(pr.uAtlas, 0);
        if (pr.uShadow >= 0) GLES20.glUniform1i(pr.uShadow, 1);
        return pr;
    }

    private static void attribs(int n) {
        for (int i = 0; i < 8; i++) {
            if (i < n) GLES20.glEnableVertexAttribArray(i);
            else GLES20.glDisableVertexAttribArray(i);
        }
    }

    private void fullScreen() {
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, fsTri);
        GLES20.glVertexAttribPointer(0, 2, GLES20.GL_FLOAT, false, 8, 0);
        GLES20.glDrawArrays(GLES20.GL_TRIANGLES, 0, 3);
    }

    private static void u3(int loc, float[] v) { if (loc >= 0) GLES20.glUniform3f(loc, v[0], v[1], v[2]); }

    private static void u4(int loc, float[] v) { if (loc >= 0) GLES20.glUniform4f(loc, v[0], v[1], v[2], v[3]); }

    private void ensureShadow(int size) {
        if (shadowSize == size && shadowFbo != 0) return;
        int[] id = new int[1];
        GLES20.glGenTextures(1, id, 0);
        shadowTex = id[0];
        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, shadowTex);
        GLES20.glTexImage2D(GLES20.GL_TEXTURE_2D, 0, GLES20.GL_RGBA, size, size, 0, GLES20.GL_RGBA, GLES20.GL_UNSIGNED_BYTE, null);
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_MIN_FILTER, GLES20.GL_NEAREST);
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_MAG_FILTER, GLES20.GL_NEAREST);
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_WRAP_S, GLES20.GL_CLAMP_TO_EDGE);
        GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_WRAP_T, GLES20.GL_CLAMP_TO_EDGE);
        GLES20.glGenRenderbuffers(1, id, 0);
        shadowRb = id[0];
        GLES20.glBindRenderbuffer(GLES20.GL_RENDERBUFFER, shadowRb);
        GLES20.glRenderbufferStorage(GLES20.GL_RENDERBUFFER, GLES20.GL_DEPTH_COMPONENT16, size, size);
        GLES20.glGenFramebuffers(1, id, 0);
        shadowFbo = id[0];
        GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, shadowFbo);
        GLES20.glFramebufferTexture2D(GLES20.GL_FRAMEBUFFER, GLES20.GL_COLOR_ATTACHMENT0, GLES20.GL_TEXTURE_2D, shadowTex, 0);
        GLES20.glFramebufferRenderbuffer(GLES20.GL_FRAMEBUFFER, GLES20.GL_DEPTH_ATTACHMENT, GLES20.GL_RENDERBUFFER, shadowRb);
        if (GLES20.glCheckFramebufferStatus(GLES20.GL_FRAMEBUFFER) != GLES20.GL_FRAMEBUFFER_COMPLETE)
            throw new RuntimeException("shadow framebuffer incomplete");
        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, atlasTex);
        shadowSize = size;
    }

    private static int buffer(int target, java.nio.Buffer data, int bytes) {
        int[] id = new int[1];
        GLES20.glGenBuffers(1, id, 0);
        GLES20.glBindBuffer(target, id[0]);
        data.position(0);
        GLES20.glBufferData(target, bytes, data, GLES20.GL_STATIC_DRAW);
        return id[0];
    }

    private static void locate(Prog p) {
        int id = p.id;
        p.uVP = GLES20.glGetUniformLocation(id, "uVP");
        p.uModel = GLES20.glGetUniformLocation(id, "uModel");
        p.uPosScale = GLES20.glGetUniformLocation(id, "uPosScale");
        p.uPosOffset = GLES20.glGetUniformLocation(id, "uPosOffset");
        p.uWind = GLES20.glGetUniformLocation(id, "uWind");
        p.uShadowVP = GLES20.glGetUniformLocation(id, "uShadowVP");
        p.uCamPos = GLES20.glGetUniformLocation(id, "uCamPos");
        p.uSunDir = GLES20.glGetUniformLocation(id, "uSunDir");
        p.uLightCol = GLES20.glGetUniformLocation(id, "uLightCol");
        p.uShadeCol = GLES20.glGetUniformLocation(id, "uShadeCol");
        p.uSkinShade = GLES20.glGetUniformLocation(id, "uSkinShade");
        p.uRimCol = GLES20.glGetUniformLocation(id, "uRimCol");
        p.uSkyTop = GLES20.glGetUniformLocation(id, "uSkyTop");
        p.uSkyHor = GLES20.glGetUniformLocation(id, "uSkyHor");
        p.uSkyLow = GLES20.glGetUniformLocation(id, "uSkyLow");
        p.uSunCol = GLES20.glGetUniformLocation(id, "uSunCol");
        p.uMoonDir = GLES20.glGetUniformLocation(id, "uMoonDir");
        p.uFogCol = GLES20.glGetUniformLocation(id, "uFogCol");
        p.uFog = GLES20.glGetUniformLocation(id, "uFog");
        p.uShadowP = GLES20.glGetUniformLocation(id, "uShadowP");
        p.uNight = GLES20.glGetUniformLocation(id, "uNight");
        p.uTime = GLES20.glGetUniformLocation(id, "uTime");
        p.uLamp = GLES20.glGetUniformLocation(id, "uLamp");
        p.uLampCol = GLES20.glGetUniformLocation(id, "uLampCol");
        p.uTint = GLES20.glGetUniformLocation(id, "uTint");
        p.uEmis = GLES20.glGetUniformLocation(id, "uEmis");
        p.uInk = GLES20.glGetUniformLocation(id, "uInk");
        p.uScreen = GLES20.glGetUniformLocation(id, "uScreen");
        p.uOutline = GLES20.glGetUniformLocation(id, "uOutline");
        p.uAtlas = GLES20.glGetUniformLocation(id, "uAtlas");
        p.uShadow = GLES20.glGetUniformLocation(id, "uShadow");
        p.uBones = GLES20.glGetUniformLocation(id, "uBones");
        p.uInvVP = GLES20.glGetUniformLocation(id, "uInvVP");
        p.uAdd = GLES20.glGetUniformLocation(id, "uAdd");
        p.uSpeed = GLES20.glGetUniformLocation(id, "uSpeed");
        p.uFlash = GLES20.glGetUniformLocation(id, "uFlash");
        p.uVignette = GLES20.glGetUniformLocation(id, "uVignette");
        p.uHaze = GLES20.glGetUniformLocation(id, "uHaze");
        p.uCloud = GLES20.glGetUniformLocation(id, "uCloud");
        p.uCloudLit = GLES20.glGetUniformLocation(id, "uCloudLit");
        p.uCloudShade = GLES20.glGetUniformLocation(id, "uCloudShade");
        p.uWater = GLES20.glGetUniformLocation(id, "uWater");
    }

    private static int compile(int type, String src) {
        int s = GLES20.glCreateShader(type);
        GLES20.glShaderSource(s, src);
        GLES20.glCompileShader(s);
        int[] ok = new int[1];
        GLES20.glGetShaderiv(s, GLES20.GL_COMPILE_STATUS, ok, 0);
        if (ok[0] == 0) throw new RuntimeException("pongo shader: " + GLES20.glGetShaderInfoLog(s));
        return s;
    }

    private static int link(String vs, String fs) {
        int p = GLES20.glCreateProgram();
        GLES20.glAttachShader(p, compile(GLES20.GL_VERTEX_SHADER, vs));
        GLES20.glAttachShader(p, compile(GLES20.GL_FRAGMENT_SHADER, fs));
        // fixed attribute slots shared by every program (mesh: 0..7, sky/screen: aXY = 0, particles: aP aT aC = 0..2)
        for (int i = 0; i < ATTRS.length; i++) GLES20.glBindAttribLocation(p, i, ATTRS[i]);
        GLES20.glBindAttribLocation(p, 0, "aXY");
        GLES20.glBindAttribLocation(p, 0, "aP");
        GLES20.glBindAttribLocation(p, 1, "aT");
        GLES20.glBindAttribLocation(p, 2, "aC");
        GLES20.glLinkProgram(p);
        int[] ok = new int[1];
        GLES20.glGetProgramiv(p, GLES20.GL_LINK_STATUS, ok, 0);
        if (ok[0] == 0) throw new RuntimeException("pongo link: " + GLES20.glGetProgramInfoLog(p));
        return p;
    }
}
