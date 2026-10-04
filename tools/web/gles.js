'use strict';
// Replays a GLES 2.0 command stream recorded by tools/preview/stubs/android/opengl/GLES20.java on WebGL 1,
// so the Android renderers run unchanged in headless Chromium. Opcodes mirror that file.
const OP = {
  ENABLE: 1, DISABLE: 2, CLEAR_COLOR: 3, CLEAR: 4, VIEWPORT: 5, DEPTH_MASK: 6, DEPTH_FUNC: 7, BLEND_FUNC: 8,
  CULL_FACE: 9, POLYGON_OFFSET: 10, USE_PROGRAM: 11, CREATE_SHADER: 12, SHADER_SOURCE: 13, COMPILE_SHADER: 14,
  CREATE_PROGRAM: 15, ATTACH_SHADER: 16, BIND_ATTRIB: 17, LINK_PROGRAM: 18, GET_UNIFORM: 19, UNIFORM_1F: 20,
  UNIFORM_2F: 21, UNIFORM_3F: 22, UNIFORM_4F: 23, UNIFORM_1I: 24, UNIFORM_3FV: 25, UNIFORM_4FV: 26, UNIFORM_MAT4: 27,
  ENABLE_ATTRIB: 28, DISABLE_ATTRIB: 29, ATTRIB_POINTER: 30, GEN_BUFFER: 31, BIND_BUFFER: 32, BUFFER_DATA: 33,
  DRAW_ARRAYS: 34, DRAW_ELEMENTS: 35, GEN_TEXTURE: 36, BIND_TEXTURE: 37, ACTIVE_TEXTURE: 38, PIXEL_STORE: 39,
  TEX_IMAGE: 40, TEX_PARAM: 41, GEN_FRAMEBUFFER: 42, BIND_FRAMEBUFFER: 43, GEN_RENDERBUFFER: 44,
  BIND_RENDERBUFFER: 45, RENDERBUFFER_STORAGE: 46, FRAMEBUFFER_TEXTURE: 47, FRAMEBUFFER_RENDERBUFFER: 48, PRESENT: 99,
};

let gl, canvas, buf, dv, pos = 0;
const obj = new Map();      // recorded name -> WebGL object (uniform locations included)
const srcOf = new Map();
const frames = [];

const i32 = () => { const v = dv.getInt32(pos, true); pos += 4; return v; };
const f32 = () => { const v = dv.getFloat32(pos, true); pos += 4; return v; };
const fArr = n => { const a = new Float32Array(n); for (let k = 0; k < n; k++) a[k] = f32(); return a; };
const blob = () => { const n = i32(); const u = new Uint8Array(buf, pos, n); pos += n + ((4 - n % 4) % 4); return u; };
const str = () => new TextDecoder().decode(blob());
const o = id => (id === 0 ? null : obj.get(id));

function step() {
  const op = i32();
  switch (op) {
    case OP.ENABLE: gl.enable(i32()); break;
    case OP.DISABLE: gl.disable(i32()); break;
    case OP.CLEAR_COLOR: gl.clearColor(f32(), f32(), f32(), f32()); break;
    case OP.CLEAR: gl.clear(i32()); break;
    case OP.VIEWPORT: { const x = i32(), y = i32(), w = i32(), h = i32(); gl.viewport(x, y, w, h); break; }
    case OP.DEPTH_MASK: gl.depthMask(i32() !== 0); break;
    case OP.DEPTH_FUNC: gl.depthFunc(i32()); break;
    case OP.BLEND_FUNC: gl.blendFunc(i32(), i32()); break;
    case OP.CULL_FACE: gl.cullFace(i32()); break;
    case OP.POLYGON_OFFSET: gl.polygonOffset(f32(), f32()); break;
    case OP.USE_PROGRAM: gl.useProgram(o(i32())); break;
    case OP.CREATE_SHADER: { const id = i32(); obj.set(id, gl.createShader(i32())); break; }
    case OP.SHADER_SOURCE: { const s = obj.get(i32()); const t = str(); srcOf.set(s, t); gl.shaderSource(s, t); break; }
    case OP.COMPILE_SHADER: {
      const s = obj.get(i32()); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error('compile: ' + gl.getShaderInfoLog(s) + '\n' + srcOf.get(s));
      break;
    }
    case OP.CREATE_PROGRAM: obj.set(i32(), gl.createProgram()); break;
    case OP.ATTACH_SHADER: { const p = obj.get(i32()); gl.attachShader(p, obj.get(i32())); break; }
    case OP.BIND_ATTRIB: { const p = obj.get(i32()); const i = i32(); gl.bindAttribLocation(p, i, str()); break; }
    case OP.LINK_PROGRAM: {
      const p = obj.get(i32()); gl.linkProgram(p);
      if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error('link: ' + gl.getProgramInfoLog(p));
      break;
    }
    case OP.GET_UNIFORM: { const id = i32(); const p = obj.get(i32()); obj.set(id, gl.getUniformLocation(p, str())); break; }
    case OP.UNIFORM_1F: gl.uniform1f(o(i32()), f32()); break;
    case OP.UNIFORM_2F: gl.uniform2f(o(i32()), f32(), f32()); break;
    case OP.UNIFORM_3F: gl.uniform3f(o(i32()), f32(), f32(), f32()); break;
    case OP.UNIFORM_4F: gl.uniform4f(o(i32()), f32(), f32(), f32(), f32()); break;
    case OP.UNIFORM_1I: gl.uniform1i(o(i32()), i32()); break;
    case OP.UNIFORM_3FV: { const l = o(i32()); gl.uniform3fv(l, fArr(i32())); break; }
    case OP.UNIFORM_4FV: { const l = o(i32()); gl.uniform4fv(l, fArr(i32())); break; }
    case OP.UNIFORM_MAT4: { const l = o(i32()); gl.uniformMatrix4fv(l, false, fArr(i32())); break; }
    case OP.ENABLE_ATTRIB: gl.enableVertexAttribArray(i32()); break;
    case OP.DISABLE_ATTRIB: gl.disableVertexAttribArray(i32()); break;
    case OP.ATTRIB_POINTER: {
      const i = i32(), size = i32(), type = i32(), norm = i32() !== 0, stride = i32(), off = i32();
      gl.vertexAttribPointer(i, size, type, norm, stride, off); break;
    }
    case OP.GEN_BUFFER: obj.set(i32(), gl.createBuffer()); break;
    case OP.BIND_BUFFER: { const t = i32(); gl.bindBuffer(t, o(i32())); break; }
    case OP.BUFFER_DATA: { const t = i32(), usage = i32(); gl.bufferData(t, blob(), usage); break; }
    case OP.DRAW_ARRAYS: gl.drawArrays(i32(), i32(), i32()); break;
    case OP.DRAW_ELEMENTS: gl.drawElements(i32(), i32(), i32(), i32()); break;
    case OP.GEN_TEXTURE: obj.set(i32(), gl.createTexture()); break;
    case OP.BIND_TEXTURE: { const t = i32(); gl.bindTexture(t, o(i32())); break; }
    case OP.ACTIVE_TEXTURE: gl.activeTexture(i32()); break;
    case OP.PIXEL_STORE: gl.pixelStorei(i32(), i32()); break;
    case OP.TEX_IMAGE: {
      const target = i32(), level = i32(), ifmt = i32(), w = i32(), h = i32(), fmt = i32(), type = i32(), has = i32();
      gl.texImage2D(target, level, ifmt, w, h, 0, fmt, type, has ? blob() : null); break;
    }
    case OP.TEX_PARAM: gl.texParameteri(i32(), i32(), i32()); break;
    case OP.GEN_FRAMEBUFFER: obj.set(i32(), gl.createFramebuffer()); break;
    case OP.BIND_FRAMEBUFFER: { const t = i32(); gl.bindFramebuffer(t, o(i32())); break; }
    case OP.GEN_RENDERBUFFER: obj.set(i32(), gl.createRenderbuffer()); break;
    case OP.BIND_RENDERBUFFER: { const t = i32(); gl.bindRenderbuffer(t, o(i32())); break; }
    case OP.RENDERBUFFER_STORAGE: gl.renderbufferStorage(i32(), i32(), i32(), i32()); break;
    case OP.FRAMEBUFFER_TEXTURE: { const t = i32(), a = i32(), tt = i32(), tex = o(i32()); gl.framebufferTexture2D(t, a, tt, tex, i32()); break; }
    case OP.FRAMEBUFFER_RENDERBUFFER: { const t = i32(), a = i32(), rt = i32(); gl.framebufferRenderbuffer(t, a, rt, o(i32())); break; }
    case OP.PRESENT: { const name = str(); gl.finish(); frames.push([name, canvas.toDataURL('image/png')]); break; }
    default: throw new Error('bad opcode ' + op + ' at ' + (pos - 4));
  }
  // getError is a full GPU round trip: checking every call made long recordings take many minutes, so it is
  // checked every few thousand calls and on every presented frame
  if (op === OP.PRESENT || ++sinceCheck >= 4096) {
    sinceCheck = 0;
    const e = gl.getError();
    if (e) throw new Error('GL error 0x' + e.toString(16) + ' near opcode ' + op + ' at ' + pos);
  }
}
let sinceCheck = 0;

async function main() {
  const q = new URLSearchParams(location.search);
  canvas = document.getElementById('c');
  canvas.width = +(q.get('w') || 540); canvas.height = +(q.get('h') || 960);
  gl = canvas.getContext('webgl', { antialias: true, depth: true, preserveDrawingBuffer: true, alpha: false });
  if (!gl) throw new Error('no webgl');
  buf = await fetch(q.get('stream') || 'gles.bin').then(r => r.arrayBuffer());
  dv = new DataView(buf);
  while (pos < buf.byteLength) step();
  window.frames = frames;
  window.ready = true;
}
main().catch(e => { window.error = String(e && e.stack || e); console.error(e); });
