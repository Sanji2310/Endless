'use strict';
// WebGL 1 executor for PONGO render frames. Mirrors src/com/pongo/app/GLRenderer.java pass by pass,
// using the exact GLSL ES 1.00 sources from src/com/pongo/core/Shaders.java (exported to shaders.json).

const ATTR = { aPos: 0, aNrm: 1, aOut: 2, aUV: 3, aCol: 4, aMat: 5, aBone: 6, aWeight: 7, aXY: 0, aP: 0, aT: 1, aC: 2 };
let gl, canvas, A, FR = [], P = {}, atlasTex, shadow = null, fsTri, quadIdx, partVBO;

// ------------------------------------------------------------------ binary helpers
class Rd {
  constructor(buf, off = 0) { this.b = buf; this.dv = new DataView(buf); this.o = off; }
  i() { const v = this.dv.getInt32(this.o, true); this.o += 4; return v; }
  f() { const v = this.dv.getFloat32(this.o, true); this.o += 4; return v; }
  s() { const n = this.i(); const t = new TextDecoder().decode(new Uint8Array(this.b, this.o, n)); this.o += n + ((4 - n % 4) % 4); return t; }
  fa(n) { const a = new Float32Array(n); for (let k = 0; k < n; k++) a[k] = this.f(); return a; }
  bytes(n) { const u = new Uint8Array(this.b, this.o, n); this.o += n; return u; }
}

function parseAssets(buf) {
  const r = new Rd(buf);
  const mg = String.fromCharCode(...new Uint8Array(buf, 0, 4)); r.o = 4;
  if (mg !== 'PGO1') throw new Error('bad pongo.bin');
  r.i();
  const a = { meshes: [], tiles: {}, lods: {}, skeletons: [], levels: [] };
  a.atlasW = r.i(); a.atlasH = r.i();
  const nl = r.i();
  for (let l = 0; l < nl; l++) { const w = r.i(), h = r.i(); a.levels.push({ w, h, data: r.bytes(w * h * 4) }); }
  const nt = r.i();
  for (let t = 0; t < nt; t++) { const n = r.s(); a.tiles[n] = [r.f(), r.f(), r.f(), r.f()]; }
  const nm = r.i();
  for (let m = 0; m < nm; m++) {
    const me = { name: r.s(), group: r.s(), lod: r.i(), flags: r.i(), skeleton: r.i() };
    me.bmin = r.fa(3); me.bmax = r.fa(3); me.scale = r.fa(3); me.offset = r.fa(3);
    me.skinned = (me.flags & 1) !== 0;
    const stride = me.skinned ? 36 : 28;
    const np = r.i(); me.parts = []; me.hasOutline = false; me.castsShadow = false;
    for (let p = 0; p < np; p++) {
      const part = { cls: r.i(), flags: r.i(), chunks: [] };
      const nc = r.i();
      for (let c = 0; c < nc; c++) {
        const nv = r.i(), ni = r.i();
        const v = r.bytes(nv * stride);
        const ib = r.bytes(((ni * 2 + 3) >> 2) << 2);
        part.chunks.push({ nv, ni, v, ib });
      }
      if (part.flags & 2) me.hasOutline = true;
      if (!(part.flags & 1)) me.castsShadow = true;
      me.parts.push(part);
    }
    a.meshes.push(me);
  }
  return a;
}

function parseFrames(buf) {
  const r = new Rd(buf);
  const mg = String.fromCharCode(...new Uint8Array(buf, 0, 4)); r.o = 4;
  if (mg !== 'PGF1') throw new Error('bad frames.bin');
  const n = r.i();
  const out = [];
  for (let k = 0; k < n; k++) {
    const len = r.i();
    const start = r.o;
    const F = {};
    F.W = r.i(); F.H = r.i();
    F.vp = r.fa(16); F.ivp = r.fa(16); F.view = r.fa(16);
    F.cam = r.fa(3);
    for (const key of ['sunDir', 'lightCol', 'shadeCol', 'skinShade', 'rimCol', 'skyTop', 'skyHor', 'skyLow', 'sunCol', 'moonDir', 'fogCol', 'ink']) F[key] = r.fa(3);
    F.fog = [r.f(), r.f(), r.f(), r.f()];
    F.night = r.f(); F.time = r.f();
    F.wind = r.fa(4); F.lamp = r.fa(4); F.lampCol = r.fa(3);
    F.outline = r.f();
    F.shadowOn = r.i() === 1; F.shadowSize = r.i(); F.shadowVP = r.fa(16); F.shadowBias = r.f(); F.shadowStrength = r.f();
    const nd = r.i(); F.draws = [];
    for (let d = 0; d < nd; d++) {
      const D = { mesh: r.i(), flags: r.i(), model: r.fa(16), tint: r.fa(4), emis: r.f() };
      const rows = r.i(); D.bones = rows ? r.fa(rows * 4) : null;
      F.draws.push(D);
    }
    const na = r.i(); F.alphaN = na; F.alpha = r.bytes(na * 96);
    const nad = r.i(); F.addN = nad; F.add = r.bytes(nad * 96);
    F.speed = r.fa(4); F.flash = r.fa(4); F.vignette = r.fa(4);
    r.o = start + len;
    out.push(F);
  }
  return out;
}

// ------------------------------------------------------------------ GL setup
function compile(type, src) {
  const s = gl.createShader(type);
  gl.shaderSource(s, src);
  gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error('shader compile failed: ' + gl.getShaderInfoLog(s) + '\n' + src);
  return s;
}

function buildPrograms(sj) {
  for (const [name, defs, vs, fs] of sj.programs) {
    const p = gl.createProgram();
    gl.attachShader(p, compile(gl.VERTEX_SHADER, defs + sj.sources[vs]));
    gl.attachShader(p, compile(gl.FRAGMENT_SHADER, defs + sj.sources[fs]));
    for (const [a, i] of Object.entries(ATTR)) gl.bindAttribLocation(p, i, a);
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error('link failed ' + name + ': ' + gl.getProgramInfoLog(p));
    const u = {};
    const nu = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
    for (let k = 0; k < nu; k++) { const inf = gl.getActiveUniform(p, k); const nm = inf.name.replace('[0]', ''); u[nm] = gl.getUniformLocation(p, nm); }
    P[name] = { p, u, skin: defs.includes('SKIN') };
  }
}

function uploadAssets() {
  atlasTex = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, atlasTex);
  gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
  A.levels.forEach((lv, l) => gl.texImage2D(gl.TEXTURE_2D, l, gl.RGBA, lv.w, lv.h, 0, gl.RGBA, gl.UNSIGNED_BYTE, lv.data));
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  const an = gl.getExtension('EXT_texture_filter_anisotropic');
  if (an) gl.texParameterf(gl.TEXTURE_2D, an.TEXTURE_MAX_ANISOTROPY_EXT, 4);
  for (const me of A.meshes) for (const part of me.parts) for (const c of part.chunks) {
    c.vbo = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, c.vbo); gl.bufferData(gl.ARRAY_BUFFER, c.v, gl.STATIC_DRAW);
    c.ibo = gl.createBuffer(); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, c.ibo); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, c.ib, gl.STATIC_DRAW);
  }
  fsTri = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, fsTri); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  const idx = new Uint16Array(16384 * 6);
  for (let q = 0; q < 16384; q++) { const b = q * 4; idx.set([b, b + 1, b + 2, b, b + 2, b + 3], q * 6); }
  quadIdx = gl.createBuffer(); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, quadIdx); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, idx, gl.STATIC_DRAW);
  partVBO = gl.createBuffer();
}

function ensureShadow(size) {
  if (shadow && shadow.size === size) return;
  const t = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, t);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, size, size, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  const rb = gl.createRenderbuffer();
  gl.bindRenderbuffer(gl.RENDERBUFFER, rb);
  gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT16, size, size);
  const fb = gl.createFramebuffer();
  gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, t, 0);
  gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, rb);
  if (gl.checkFramebufferStatus(gl.FRAMEBUFFER) !== gl.FRAMEBUFFER_COMPLETE) throw new Error('shadow fbo incomplete');
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  shadow = { size, t, fb };
}

// ------------------------------------------------------------------ drawing
let cur = null;
function use(name) { const pr = P[name]; if (cur !== pr) { gl.useProgram(pr.p); cur = pr; } return pr; }
function u3(pr, n, v) { if (pr.u[n]) gl.uniform3f(pr.u[n], v[0], v[1], v[2]); }
function u4(pr, n, v) { if (pr.u[n]) gl.uniform4f(pr.u[n], v[0], v[1], v[2], v[3]); }
function u1(pr, n, v) { if (pr.u[n]) gl.uniform1f(pr.u[n], v); }
function um(pr, n, m) { if (pr.u[n]) gl.uniformMatrix4fv(pr.u[n], false, m); }

function meshAttribs(skinned, prog) {
  const st = skinned ? 36 : 28;
  gl.vertexAttribPointer(0, 4, gl.SHORT, true, st, 0);
  gl.vertexAttribPointer(1, 4, gl.BYTE, true, st, 8);
  gl.vertexAttribPointer(2, 4, gl.BYTE, true, st, 12);
  gl.vertexAttribPointer(3, 2, gl.UNSIGNED_SHORT, true, st, 16);
  gl.vertexAttribPointer(4, 4, gl.UNSIGNED_BYTE, true, st, 20);
  gl.vertexAttribPointer(5, 4, gl.UNSIGNED_BYTE, true, st, 24);
  if (prog.skin) {
    gl.vertexAttribPointer(6, 4, gl.UNSIGNED_BYTE, false, st, 28);
    gl.vertexAttribPointer(7, 4, gl.UNSIGNED_BYTE, true, st, 32);
  }
}

function enableAttribs(n) { for (let i = 0; i < 8; i++) { if (i < n) gl.enableVertexAttribArray(i); else gl.disableVertexAttribArray(i); } }

function setGlobals(pr, F, vp) {
  um(pr, 'uVP', vp);
  u4(pr, 'uWind', F.wind);
  um(pr, 'uShadowVP', F.shadowVP);
  u3(pr, 'uCamPos', F.cam); u3(pr, 'uSunDir', F.sunDir); u3(pr, 'uLightCol', F.lightCol); u3(pr, 'uShadeCol', F.shadeCol);
  u3(pr, 'uSkinShade', F.skinShade); u3(pr, 'uRimCol', F.rimCol); u3(pr, 'uSkyTop', F.skyTop); u3(pr, 'uSkyHor', F.skyHor);
  u3(pr, 'uFogCol', F.fogCol); u4(pr, 'uFog', F.fog); u1(pr, 'uNight', F.night); u4(pr, 'uLamp', F.lamp); u3(pr, 'uLampCol', F.lampCol);
  u3(pr, 'uInk', F.ink);
  if (pr.u.uScreen) gl.uniform2f(pr.u.uScreen, F.W, F.H);
  u1(pr, 'uOutline', F.outline);
  u4(pr, 'uShadowP', [1 / F.shadowSize, F.shadowBias, F.shadowOn ? 1 : 0, F.shadowStrength]);
  if (pr.u.uAtlas) gl.uniform1i(pr.u.uAtlas, 0);
  if (pr.u.uShadow) gl.uniform1i(pr.u.uShadow, 1);
}

function drawMesh(pr, me, D, partFilter) {
  um(pr, 'uModel', D.model);
  u3(pr, 'uPosScale', me.scale); u3(pr, 'uPosOffset', me.offset);
  u4(pr, 'uTint', D.tint); u1(pr, 'uEmis', D.emis);
  if (pr.skin && D.bones && pr.u.uBones) gl.uniform4fv(pr.u.uBones, D.bones);
  for (const part of me.parts) {
    if (!partFilter(part)) continue;
    for (const c of part.chunks) {
      gl.bindBuffer(gl.ARRAY_BUFFER, c.vbo);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, c.ibo);
      meshAttribs(me.skinned, pr);
      gl.drawElements(gl.TRIANGLES, c.ni, gl.UNSIGNED_SHORT, 0);
    }
  }
}

function mainProgFor(cls, skinned) {
  if (skinned) return 'main_skin';
  if (cls === 1) return 'main_double';
  if (cls === 2) return 'main_cutout';
  return 'main';
}

function renderFrame(i) {
  const F = FR[i];
  if (canvas.width !== F.W || canvas.height !== F.H) { canvas.width = F.W; canvas.height = F.H; }
  gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, atlasTex);
  cur = null;
  // ---- shadow pass
  if (F.shadowOn) {
    ensureShadow(F.shadowSize);
    gl.bindFramebuffer(gl.FRAMEBUFFER, shadow.fb);
    gl.viewport(0, 0, shadow.size, shadow.size);
    gl.clearColor(1, 1, 1, 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.DEPTH_TEST); gl.depthFunc(gl.LEQUAL); gl.depthMask(true);
    gl.disable(gl.CULL_FACE); gl.disable(gl.BLEND);
    gl.enable(gl.POLYGON_OFFSET_FILL); gl.polygonOffset(1.5, 3.0);
    for (const D of F.draws) {
      if (D.flags & 2) continue;
      const me = A.meshes[D.mesh];
      if (!me.castsShadow) continue;
      for (const cut of [false, true]) {
        const name = me.skinned ? 'shadow_skin' : (cut ? 'shadow_cutout' : 'shadow');
        if (me.skinned && cut) continue;
        const pr = use(name);
        enableAttribs(pr.skin ? 8 : 6);
        setGlobals(pr, F, F.shadowVP);
        drawMesh(pr, me, D, p => !(p.flags & 1) && (me.skinned || (p.cls === 2) === cut));
      }
    }
    gl.disable(gl.POLYGON_OFFSET_FILL);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  }
  gl.activeTexture(gl.TEXTURE1);
  gl.bindTexture(gl.TEXTURE_2D, shadow ? shadow.t : atlasTex);
  gl.activeTexture(gl.TEXTURE0);
  // ---- main
  gl.viewport(0, 0, F.W, F.H);
  gl.clearColor(F.fogCol[0], F.fogCol[1], F.fogCol[2], 1);
  gl.depthMask(true);
  gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
  // sky
  {
    gl.disable(gl.DEPTH_TEST); gl.depthMask(false); gl.disable(gl.CULL_FACE); gl.disable(gl.BLEND);
    const pr = use('sky');
    enableAttribs(1);
    um(pr, 'uInvVP', F.ivp);
    u3(pr, 'uSkyTop', F.skyTop); u3(pr, 'uSkyHor', F.skyHor); u3(pr, 'uSkyLow', F.skyLow); u3(pr, 'uSunDir', F.sunDir);
    u3(pr, 'uSunCol', F.sunCol); u3(pr, 'uMoonDir', F.moonDir); u1(pr, 'uNight', F.night); u1(pr, 'uTime', F.time);
    gl.bindBuffer(gl.ARRAY_BUFFER, fsTri);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 8, 0);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }
  gl.enable(gl.DEPTH_TEST); gl.depthFunc(gl.LEQUAL); gl.depthMask(true);
  gl.enable(gl.CULL_FACE); gl.cullFace(gl.BACK);
  // opaque, double-sided and cutout parts
  for (const cls of [0, 1, 2, 3]) {
    for (const D of F.draws) {
      if (D.flags & 4) continue;
      const me = A.meshes[D.mesh];
      if (!me.parts.some(p => p.cls === cls)) continue;
      const pr = use(mainProgFor(cls, me.skinned));
      if (cls === 1 || cls === 2 || (D.flags & 16)) gl.disable(gl.CULL_FACE); else gl.enable(gl.CULL_FACE);
      enableAttribs(pr.skin ? 8 : 6);
      setGlobals(pr, F, F.vp);
      drawMesh(pr, me, D, p => p.cls === cls);
    }
  }
  // ink outlines (inverted hull)
  gl.enable(gl.CULL_FACE); gl.cullFace(gl.FRONT);
  for (const D of F.draws) {
    if (D.flags & 1) continue;
    const me = A.meshes[D.mesh];
    if (!me.hasOutline) continue;
    const pr = use(me.skinned ? 'outline_skin' : 'outline');
    enableAttribs(pr.skin ? 8 : 6);
    setGlobals(pr, F, F.vp);
    drawMesh(pr, me, D, p => (p.flags & 2) && p.cls !== 1 && p.cls !== 2);
  }
  gl.cullFace(gl.BACK);
  // blended draws
  gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA); gl.depthMask(false);
  for (const D of F.draws) {
    if (!(D.flags & 4)) continue;
    const me = A.meshes[D.mesh];
    const pr = use(me.skinned ? 'main_skin' : 'main_double');
    enableAttribs(pr.skin ? 8 : 6);
    setGlobals(pr, F, F.vp);
    drawMesh(pr, me, D, p => true);
  }
  // particles
  gl.disable(gl.CULL_FACE);
  const drawParts = (bytes, n, additive) => {
    if (!n) return;
    const pr = use('part');
    enableAttribs(3);
    um(pr, 'uVP', F.vp); u3(pr, 'uCamPos', F.cam); u4(pr, 'uFog', F.fog); u3(pr, 'uFogCol', F.fogCol); u1(pr, 'uAdd', additive ? 1 : 0);
    if (pr.u.uAtlas) gl.uniform1i(pr.u.uAtlas, 0);
    gl.bindBuffer(gl.ARRAY_BUFFER, partVBO);
    gl.bufferData(gl.ARRAY_BUFFER, bytes, gl.DYNAMIC_DRAW);
    gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 24, 0);
    gl.vertexAttribPointer(1, 2, gl.FLOAT, false, 24, 12);
    gl.vertexAttribPointer(2, 4, gl.UNSIGNED_BYTE, true, 24, 20);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, quadIdx);
    if (additive) gl.blendFunc(gl.ONE, gl.ONE); else gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    gl.drawElements(gl.TRIANGLES, Math.min(n, 16384) * 6, gl.UNSIGNED_SHORT, 0);
  };
  drawParts(F.alpha, F.alphaN, false);
  drawParts(F.add, F.addN, true);
  // screen overlay
  gl.disable(gl.DEPTH_TEST);
  gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
  {
    const pr = use('screen');
    enableAttribs(1);
    u4(pr, 'uSpeed', [F.speed[0], F.speed[1], F.W / F.H, F.speed[3]]);
    u4(pr, 'uFlash', F.flash); u4(pr, 'uVignette', F.vignette);
    gl.bindBuffer(gl.ARRAY_BUFFER, fsTri);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 8, 0);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }
  gl.disable(gl.BLEND); gl.depthMask(true);
  gl.finish();
  return true;
}

async function main() {
  canvas = document.getElementById('c');
  gl = canvas.getContext('webgl', { antialias: true, preserveDrawingBuffer: true, alpha: false });
  if (!gl) throw new Error('no webgl');
  const q = new URLSearchParams(location.search);
  const [ab, fb, sj] = await Promise.all([
    fetch(q.get('assets') || 'pongo.bin').then(r => r.arrayBuffer()),
    fetch(q.get('frames') || 'frames.bin').then(r => r.arrayBuffer()),
    fetch('shaders.json').then(r => r.json())]);
  A = parseAssets(ab);
  FR = parseFrames(fb);
  buildPrograms(sj);
  uploadAssets();
  window.frameCount = FR.length;
  window.renderFrame = renderFrame;
  window.ready = true;
}
main().catch(e => { window.error = String(e && e.stack || e); console.error(e); });
