package android.opengl;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.Buffer;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.FloatBuffer;
import java.nio.IntBuffer;
import java.nio.ShortBuffer;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Desktop stand-in for android.opengl.GLES20 used by the preview build: every call is recorded into a
 * little-endian command stream that tools/web/gles.js replays on WebGL 1 (same API, same enums), so the
 * real Android renderers (GameRenderer + com.pongo.app.GLRenderer) can be run and screenshotted headless.
 *
 * Calls that return GL state are answered locally: object names are allocated here, attribute locations
 * are assigned at link time (and recorded as glBindAttribLocation), compile/link/framebuffer status
 * report success and real errors surface when the stream is replayed.
 */
public final class GLES20 {
    private GLES20() {}

    public static final int GL_DEPTH_BUFFER_BIT = 0x100, GL_COLOR_BUFFER_BIT = 0x4000, GL_TRIANGLES = 4, GL_ONE = 1,
            GL_FRONT = 0x404, GL_BACK = 0x405, GL_CULL_FACE = 0xB44, GL_DEPTH_TEST = 0xB71, GL_BLEND = 0xBE2,
            GL_POLYGON_OFFSET_FILL = 0x8037, GL_LEQUAL = 0x203, GL_SRC_ALPHA = 0x302, GL_ONE_MINUS_SRC_ALPHA = 0x303,
            GL_BYTE = 0x1400, GL_UNSIGNED_BYTE = 0x1401, GL_SHORT = 0x1402, GL_UNSIGNED_SHORT = 0x1403, GL_FLOAT = 0x1406,
            GL_RGBA = 0x1908, GL_TEXTURE_2D = 0xDE1, GL_TEXTURE_MAG_FILTER = 0x2800, GL_TEXTURE_MIN_FILTER = 0x2801,
            GL_TEXTURE_WRAP_S = 0x2802, GL_TEXTURE_WRAP_T = 0x2803, GL_NEAREST = 0x2600, GL_LINEAR = 0x2601,
            GL_LINEAR_MIPMAP_LINEAR = 0x2703, GL_CLAMP_TO_EDGE = 0x812F, GL_TEXTURE0 = 0x84C0, GL_TEXTURE1 = 0x84C1,
            GL_ARRAY_BUFFER = 0x8892, GL_ELEMENT_ARRAY_BUFFER = 0x8893, GL_STREAM_DRAW = 0x88E0, GL_STATIC_DRAW = 0x88E4,
            GL_DYNAMIC_DRAW = 0x88E8, GL_FRAGMENT_SHADER = 0x8B30, GL_VERTEX_SHADER = 0x8B31, GL_COMPILE_STATUS = 0x8B81,
            GL_LINK_STATUS = 0x8B82, GL_UNPACK_ALIGNMENT = 0xCF5, GL_FRAMEBUFFER = 0x8D40, GL_RENDERBUFFER = 0x8D41,
            GL_FRAMEBUFFER_BINDING = 0x8CA6, GL_COLOR_ATTACHMENT0 = 0x8CE0, GL_DEPTH_ATTACHMENT = 0x8D00,
            GL_DEPTH_COMPONENT16 = 0x81A5, GL_FRAMEBUFFER_COMPLETE = 0x8CD5;

    // opcodes (mirrored in tools/web/gles.js)
    static final int OP_ENABLE = 1, OP_DISABLE = 2, OP_CLEAR_COLOR = 3, OP_CLEAR = 4, OP_VIEWPORT = 5, OP_DEPTH_MASK = 6,
            OP_DEPTH_FUNC = 7, OP_BLEND_FUNC = 8, OP_CULL_FACE = 9, OP_POLYGON_OFFSET = 10, OP_USE_PROGRAM = 11,
            OP_CREATE_SHADER = 12, OP_SHADER_SOURCE = 13, OP_COMPILE_SHADER = 14, OP_CREATE_PROGRAM = 15,
            OP_ATTACH_SHADER = 16, OP_BIND_ATTRIB = 17, OP_LINK_PROGRAM = 18, OP_GET_UNIFORM = 19, OP_UNIFORM_1F = 20,
            OP_UNIFORM_2F = 21, OP_UNIFORM_3F = 22, OP_UNIFORM_4F = 23, OP_UNIFORM_1I = 24, OP_UNIFORM_3FV = 25,
            OP_UNIFORM_4FV = 26, OP_UNIFORM_MAT4 = 27, OP_ENABLE_ATTRIB = 28, OP_DISABLE_ATTRIB = 29, OP_ATTRIB_POINTER = 30,
            OP_GEN_BUFFER = 31, OP_BIND_BUFFER = 32, OP_BUFFER_DATA = 33, OP_DRAW_ARRAYS = 34, OP_DRAW_ELEMENTS = 35,
            OP_GEN_TEXTURE = 36, OP_BIND_TEXTURE = 37, OP_ACTIVE_TEXTURE = 38, OP_PIXEL_STORE = 39, OP_TEX_IMAGE = 40,
            OP_TEX_PARAM = 41, OP_GEN_FRAMEBUFFER = 42, OP_BIND_FRAMEBUFFER = 43, OP_GEN_RENDERBUFFER = 44,
            OP_BIND_RENDERBUFFER = 45, OP_RENDERBUFFER_STORAGE = 46, OP_FRAMEBUFFER_TEXTURE = 47,
            OP_FRAMEBUFFER_RENDERBUFFER = 48, OP_PRESENT = 99;

    private static ByteBuffer out = ByteBuffer.allocate(1 << 20).order(ByteOrder.LITTLE_ENDIAN);
    /** When false, clears and draw calls are left out of the stream (state and uploads are still recorded). */
    public static boolean drawing = true;
    private static int nextName = 1, boundFbo;
    private static final Map<Integer, String> shaderSrc = new HashMap<Integer, String>();
    private static final Map<Integer, Integer> shaderType = new HashMap<Integer, Integer>();
    private static final Map<Integer, List<Integer>> programShaders = new HashMap<Integer, List<Integer>>();
    private static final Map<Integer, Map<String, Integer>> attribs = new HashMap<Integer, Map<String, Integer>>();
    private static final Pattern ATTRIB = Pattern.compile("attribute\\s+\\w+\\s+(\\w+)\\s*;");

    // ------------------------------------------------------------------ stream

    private static void room(int n) {
        if (out.remaining() >= n) return;
        ByteBuffer b = ByteBuffer.allocate(Math.max(out.capacity() * 2, out.position() + n + 1024)).order(ByteOrder.LITTLE_ENDIAN);
        out.flip();
        b.put(out);
        out = b;
    }

    private static void op(int code, int... args) {
        room(8 + args.length * 4);
        out.putInt(code);
        for (int a : args) out.putInt(a);
    }

    private static void f(float... v) {
        room(v.length * 4);
        for (float x : v) out.putFloat(x);
    }

    private static void str(String s) {
        byte[] b = s.getBytes(java.nio.charset.StandardCharsets.UTF_8);
        room(4 + b.length + 4);
        out.putInt(b.length);
        out.put(b);
        while ((out.position() & 3) != 0) out.put((byte) 0);
    }

    private static void bytes(Buffer data, int n) {
        room(4 + n + 4);
        out.putInt(n);
        ByteBuffer src = asBytes(data, n);
        out.put(src);
        while ((out.position() & 3) != 0) out.put((byte) 0);
    }

    /** Copies the first n bytes from the buffer's position 0 as little-endian bytes. */
    private static ByteBuffer asBytes(Buffer data, int n) {
        ByteBuffer b = ByteBuffer.allocate(n).order(ByteOrder.LITTLE_ENDIAN);
        if (data instanceof ByteBuffer) {
            ByteBuffer d = ((ByteBuffer) data).duplicate();
            d.position(0);
            d.limit(Math.min(d.capacity(), n));
            b.put(d);
        } else if (data instanceof FloatBuffer) {
            FloatBuffer d = ((FloatBuffer) data).duplicate();
            d.position(0);
            while (b.remaining() >= 4 && d.hasRemaining()) b.putFloat(d.get());
        } else if (data instanceof ShortBuffer) {
            ShortBuffer d = ((ShortBuffer) data).duplicate();
            d.position(0);
            while (b.remaining() >= 2 && d.hasRemaining()) b.putShort(d.get());
        } else if (data instanceof IntBuffer) {
            IntBuffer d = ((IntBuffer) data).duplicate();
            d.position(0);
            while (b.remaining() >= 4 && d.hasRemaining()) b.putInt(d.get());
        } else {
            throw new IllegalArgumentException("unsupported buffer " + data);
        }
        b.flip();
        return b;
    }

    /** Marks the end of a frame; the replayer saves the canvas under this name. */
    public static void present(String name) {
        op(OP_PRESENT);
        str(name);
    }

    /** Writes the recorded stream and starts a new one. */
    public static void save(OutputStream os) throws IOException {
        os.write(out.array(), 0, out.position());
        out.clear();
    }

    // ------------------------------------------------------------------ state

    public static void glEnable(int cap) { op(OP_ENABLE, cap); }

    public static void glDisable(int cap) { op(OP_DISABLE, cap); }

    public static void glClearColor(float r, float g, float b, float a) { op(OP_CLEAR_COLOR); f(r, g, b, a); }

    public static void glClear(int mask) { if (drawing) op(OP_CLEAR, mask); }

    public static void glViewport(int x, int y, int w, int h) { op(OP_VIEWPORT, x, y, w, h); }

    public static void glDepthMask(boolean flag) { op(OP_DEPTH_MASK, flag ? 1 : 0); }

    public static void glDepthFunc(int func) { op(OP_DEPTH_FUNC, func); }

    public static void glBlendFunc(int s, int d) { op(OP_BLEND_FUNC, s, d); }

    public static void glCullFace(int mode) { op(OP_CULL_FACE, mode); }

    public static void glPolygonOffset(float factor, float units) { op(OP_POLYGON_OFFSET); f(factor, units); }

    public static void glPixelStorei(int pname, int v) { op(OP_PIXEL_STORE, pname, v); }

    public static void glGetIntegerv(int pname, int[] params, int offset) {
        if (pname == GL_FRAMEBUFFER_BINDING) params[offset] = boundFbo;
        else throw new UnsupportedOperationException("glGetIntegerv " + pname);
    }

    // ------------------------------------------------------------------ shaders

    public static int glCreateShader(int type) {
        int id = nextName++;
        shaderType.put(id, type);
        op(OP_CREATE_SHADER, id, type);
        return id;
    }

    public static void glShaderSource(int shader, String src) {
        shaderSrc.put(shader, src);
        op(OP_SHADER_SOURCE, shader);
        str(src);
    }

    public static void glCompileShader(int shader) { op(OP_COMPILE_SHADER, shader); }

    public static void glGetShaderiv(int shader, int pname, int[] params, int offset) { params[offset] = 1; }

    public static String glGetShaderInfoLog(int shader) { return ""; }

    public static int glCreateProgram() {
        int id = nextName++;
        programShaders.put(id, new ArrayList<Integer>());
        attribs.put(id, new HashMap<String, Integer>());
        op(OP_CREATE_PROGRAM, id);
        return id;
    }

    public static void glAttachShader(int program, int shader) {
        programShaders.get(program).add(shader);
        op(OP_ATTACH_SHADER, program, shader);
    }

    public static void glBindAttribLocation(int program, int index, String name) {
        attribs.get(program).put(name, index);
        op(OP_BIND_ATTRIB, program, index);
        str(name);
    }

    public static void glLinkProgram(int program) {
        // give every attribute the vertex shader declares a fixed slot, like a driver would
        Map<String, Integer> a = attribs.get(program);
        for (int sh : programShaders.get(program)) {
            if (shaderType.get(sh) != GL_VERTEX_SHADER) continue;
            Matcher m = ATTRIB.matcher(shaderSrc.get(sh));
            while (m.find()) {
                String name = m.group(1);
                if (a.containsKey(name)) continue;
                int slot = 0;
                while (a.containsValue(slot)) slot++;
                glBindAttribLocation(program, slot, name);
            }
        }
        op(OP_LINK_PROGRAM, program);
    }

    public static void glGetProgramiv(int program, int pname, int[] params, int offset) { params[offset] = 1; }

    public static String glGetProgramInfoLog(int program) { return ""; }

    public static void glUseProgram(int program) { op(OP_USE_PROGRAM, program); }

    public static int glGetAttribLocation(int program, String name) {
        Integer i = attribs.get(program).get(name);
        return i == null ? -1 : i;
    }

    public static int glGetUniformLocation(int program, String name) {
        int id = nextName++;
        op(OP_GET_UNIFORM, id, program);
        str(name);
        return id;
    }

    // ------------------------------------------------------------------ uniforms

    public static void glUniform1f(int loc, float x) { if (loc >= 0) { op(OP_UNIFORM_1F, loc); f(x); } }

    public static void glUniform2f(int loc, float x, float y) { if (loc >= 0) { op(OP_UNIFORM_2F, loc); f(x, y); } }

    public static void glUniform3f(int loc, float x, float y, float z) { if (loc >= 0) { op(OP_UNIFORM_3F, loc); f(x, y, z); } }

    public static void glUniform4f(int loc, float x, float y, float z, float w) { if (loc >= 0) { op(OP_UNIFORM_4F, loc); f(x, y, z, w); } }

    public static void glUniform1i(int loc, int x) { if (loc >= 0) op(OP_UNIFORM_1I, loc, x); }

    public static void glUniform3fv(int loc, int count, float[] v, int offset) {
        if (loc < 0) return;
        op(OP_UNIFORM_3FV, loc, count * 3);
        for (int i = 0; i < count * 3; i++) f(v[offset + i]);
    }

    public static void glUniform4fv(int loc, int count, float[] v, int offset) {
        if (loc < 0) return;
        op(OP_UNIFORM_4FV, loc, count * 4);
        for (int i = 0; i < count * 4; i++) f(v[offset + i]);
    }

    public static void glUniform4fv(int loc, int count, FloatBuffer v) {
        if (loc < 0) return;
        op(OP_UNIFORM_4FV, loc, count * 4);
        FloatBuffer d = v.duplicate();
        for (int i = 0; i < count * 4; i++) f(d.get());
    }

    public static void glUniformMatrix4fv(int loc, int count, boolean transpose, float[] v, int offset) {
        if (loc < 0) return;
        op(OP_UNIFORM_MAT4, loc, count * 16);
        for (int i = 0; i < count * 16; i++) f(v[offset + i]);
    }

    // ------------------------------------------------------------------ vertex data and draws

    public static void glEnableVertexAttribArray(int i) { op(OP_ENABLE_ATTRIB, i); }

    public static void glDisableVertexAttribArray(int i) { op(OP_DISABLE_ATTRIB, i); }

    public static void glVertexAttribPointer(int i, int size, int type, boolean norm, int stride, int offset) {
        op(OP_ATTRIB_POINTER, i, size, type, norm ? 1 : 0, stride, offset);
    }

    public static void glGenBuffers(int n, int[] ids, int offset) {
        for (int k = 0; k < n; k++) {
            ids[offset + k] = nextName++;
            op(OP_GEN_BUFFER, ids[offset + k]);
        }
    }

    public static void glBindBuffer(int target, int buf) { op(OP_BIND_BUFFER, target, buf); }

    public static void glBufferData(int target, int size, Buffer data, int usage) {
        op(OP_BUFFER_DATA, target, usage);
        bytes(data, size);
    }

    public static void glDrawArrays(int mode, int first, int count) { if (drawing) op(OP_DRAW_ARRAYS, mode, first, count); }

    public static void glDrawElements(int mode, int count, int type, int offset) { if (drawing) op(OP_DRAW_ELEMENTS, mode, count, type, offset); }

    // ------------------------------------------------------------------ textures and framebuffers

    public static void glGenTextures(int n, int[] ids, int offset) {
        for (int k = 0; k < n; k++) {
            ids[offset + k] = nextName++;
            op(OP_GEN_TEXTURE, ids[offset + k]);
        }
    }

    public static void glBindTexture(int target, int tex) { op(OP_BIND_TEXTURE, target, tex); }

    public static void glActiveTexture(int unit) { op(OP_ACTIVE_TEXTURE, unit); }

    public static void glTexParameteri(int target, int pname, int v) { op(OP_TEX_PARAM, target, pname, v); }

    public static void glTexImage2D(int target, int level, int ifmt, int w, int h, int border, int fmt, int type, Buffer data) {
        op(OP_TEX_IMAGE, target, level, ifmt, w, h, fmt, type, data == null ? 0 : 1);
        if (data != null) bytes(data, w * h * 4);
    }

    public static void glGenFramebuffers(int n, int[] ids, int offset) {
        for (int k = 0; k < n; k++) {
            ids[offset + k] = nextName++;
            op(OP_GEN_FRAMEBUFFER, ids[offset + k]);
        }
    }

    public static void glBindFramebuffer(int target, int fb) {
        boundFbo = fb;
        op(OP_BIND_FRAMEBUFFER, target, fb);
    }

    public static void glGenRenderbuffers(int n, int[] ids, int offset) {
        for (int k = 0; k < n; k++) {
            ids[offset + k] = nextName++;
            op(OP_GEN_RENDERBUFFER, ids[offset + k]);
        }
    }

    public static void glBindRenderbuffer(int target, int rb) { op(OP_BIND_RENDERBUFFER, target, rb); }

    public static void glRenderbufferStorage(int target, int fmt, int w, int h) { op(OP_RENDERBUFFER_STORAGE, target, fmt, w, h); }

    public static void glFramebufferTexture2D(int target, int att, int textarget, int tex, int level) {
        op(OP_FRAMEBUFFER_TEXTURE, target, att, textarget, tex, level);
    }

    public static void glFramebufferRenderbuffer(int target, int att, int rbtarget, int rb) {
        op(OP_FRAMEBUFFER_RENDERBUFFER, target, att, rbtarget, rb);
    }

    public static int glCheckFramebufferStatus(int target) { return GL_FRAMEBUFFER_COMPLETE; }
}
