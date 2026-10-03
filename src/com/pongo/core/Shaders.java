package com.pongo.core;

/**
 * GLSL ES 1.00 sources shared by the Android renderer and the WebGL preview harness.
 * Every program is compiled from a small #define prefix + one of these bodies.
 */
public final class Shaders {
    private Shaders() {}

    public static final int MAX_BONES = 24;

    /** Shading types packed in aOut.w (x7). Mirrors tools/assetbuilder. */
    public static final int T_STD = 0, T_SKIN = 1, T_GLASS = 2, T_HAIR = 3, T_METAL = 4, T_FOLIAGE = 5, T_NIGHT = 6, T_UNLIT = 7;

    public static final String PREC_FRAG =
            "#ifdef GL_FRAGMENT_PRECISION_HIGH\nprecision highp float;\n#else\nprecision mediump float;\n#endif\n";

    // ------------------------------------------------------------------ shared vertex input + skinning

    private static final String VERT_COMMON =
            "attribute vec4 aPos;\n" +
            "attribute vec4 aNrm;\n" +
            "attribute vec4 aOut;\n" +
            "attribute vec2 aUV;\n" +
            "attribute vec4 aCol;\n" +
            "attribute vec4 aMat;\n" +
            "#ifdef SKIN\n" +
            "attribute vec4 aBone;\n" +
            "attribute vec4 aWeight;\n" +
            "uniform vec4 uBones[" + (MAX_BONES * 3) + "];\n" +
            "#endif\n" +
            "uniform mat4 uVP;\n" +
            "uniform mat4 uModel;\n" +
            "uniform vec3 uPosScale;\n" +
            "uniform vec3 uPosOffset;\n" +
            "uniform vec4 uWind;\n" +
            "vec3 gPos; vec3 gNrm; vec3 gOut;\n" +
            "void skinAndPlace() {\n" +
            "  vec3 p = aPos.xyz * uPosScale + uPosOffset;\n" +
            "  vec3 n = aNrm.xyz;\n" +
            "  vec3 o = aOut.xyz;\n" +
            "#ifdef SKIN\n" +
            "  int b0 = int(aBone.x + 0.5) * 3; int b1 = int(aBone.y + 0.5) * 3;\n" +
            "  int b2 = int(aBone.z + 0.5) * 3; int b3 = int(aBone.w + 0.5) * 3;\n" +
            "  vec4 r0 = uBones[b0] * aWeight.x + uBones[b1] * aWeight.y + uBones[b2] * aWeight.z + uBones[b3] * aWeight.w;\n" +
            "  vec4 r1 = uBones[b0 + 1] * aWeight.x + uBones[b1 + 1] * aWeight.y + uBones[b2 + 1] * aWeight.z + uBones[b3 + 1] * aWeight.w;\n" +
            "  vec4 r2 = uBones[b0 + 2] * aWeight.x + uBones[b1 + 2] * aWeight.y + uBones[b2 + 2] * aWeight.z + uBones[b3 + 2] * aWeight.w;\n" +
            "  vec4 hp = vec4(p, 1.0);\n" +
            "  p = vec3(dot(r0, hp), dot(r1, hp), dot(r2, hp));\n" +
            "  n = vec3(dot(r0.xyz, n), dot(r1.xyz, n), dot(r2.xyz, n));\n" +
            "  o = vec3(dot(r0.xyz, o), dot(r1.xyz, o), dot(r2.xyz, o));\n" +
            "#endif\n" +
            "  vec4 w = uModel * vec4(p, 1.0);\n" +
            "  float sw = aPos.w;\n" +
            "  w.xyz += uWind.xyz * sw * (sin(uWind.w * 2.3 + w.x * 0.35 + w.z * 0.21) + 0.45 * sin(uWind.w * 5.3 + w.z * 0.9 + w.y));\n" +
            "  gPos = w.xyz;\n" +
            "  gNrm = (uModel * vec4(n, 0.0)).xyz;\n" +
            "  gOut = (uModel * vec4(o, 0.0)).xyz;\n" +
            "}\n";

    // ------------------------------------------------------------------ main toon program

    public static final String MAIN_VS = VERT_COMMON +
            "uniform mat4 uShadowVP;\n" +
            "varying vec3 vW;\n" +
            "varying vec3 vN;\n" +
            "varying vec2 vUV;\n" +
            "varying vec4 vCol;\n" +
            "varying vec4 vMat;\n" +
            "varying float vType;\n" +
            "varying vec3 vSh;\n" +
            "void main() {\n" +
            "  skinAndPlace();\n" +
            "  vW = gPos; vN = gNrm; vUV = aUV; vCol = aCol; vMat = aMat; vType = aOut.w * 7.0;\n" +
            "  vec4 s = uShadowVP * vec4(gPos, 1.0);\n" +
            "  vSh = s.xyz / s.w * 0.5 + 0.5;\n" +
            "  gl_Position = uVP * vec4(gPos, 1.0);\n" +
            "}\n";

    public static final String MAIN_FS = PREC_FRAG +
            "uniform sampler2D uAtlas;\n" +
            "uniform sampler2D uShadow;\n" +
            "uniform vec3 uCamPos;\n" +
            "uniform vec3 uSunDir;\n" +
            "uniform vec3 uLightCol;\n" +
            "uniform vec3 uShadeCol;\n" +
            "uniform vec3 uSkinShade;\n" +
            "uniform vec3 uRimCol;\n" +
            "uniform vec3 uSkyTop;\n" +
            "uniform vec3 uSkyHor;\n" +
            "uniform vec3 uFogCol;\n" +
            "uniform vec4 uFog;\n" +          // start, end, max, height-fog density
            "uniform vec4 uShadowP;\n" +      // texel, bias, enabled, strength
            "uniform float uNight;\n" +
            "uniform vec4 uLamp;\n" +         // xyz position, w radius (0 = off)
            "uniform vec3 uLampCol;\n" +
            "uniform vec4 uTint;\n" +
            "uniform float uEmis;\n" +
            "varying vec3 vW;\n" +
            "varying vec3 vN;\n" +
            "varying vec2 vUV;\n" +
            "varying vec4 vCol;\n" +
            "varying vec4 vMat;\n" +
            "varying float vType;\n" +
            "varying vec3 vSh;\n" +
            "float unpackDepth(vec4 c) { return dot(c, vec4(1.0, 1.0 / 255.0, 1.0 / 65025.0, 1.0 / 16581375.0)); }\n" +
            "float shadowTap(vec2 uv, float z) { return step(z - uShadowP.y, unpackDepth(texture2D(uShadow, uv))); }\n" +
            "float shadowAmount() {\n" +
            "  if (uShadowP.z < 0.5) return 1.0;\n" +
            "  vec3 s = vSh;\n" +
            "  if (s.x <= 0.0 || s.x >= 1.0 || s.y <= 0.0 || s.y >= 1.0 || s.z >= 1.0) return 1.0;\n" +
            "  float t = uShadowP.x;\n" +
            "  vec2 g = s.xy / t - 0.5;\n" +
            "  vec2 f = fract(g);\n" +
            "  vec2 b = (floor(g) + 0.5) * t;\n" +
            "  float a0 = shadowTap(b, s.z);\n" +
            "  float a1 = shadowTap(b + vec2(t, 0.0), s.z);\n" +
            "  float a2 = shadowTap(b + vec2(0.0, t), s.z);\n" +
            "  float a3 = shadowTap(b + vec2(t, t), s.z);\n" +
            "  float r = mix(mix(a0, a1, f.x), mix(a2, a3, f.x), f.y);\n" +
            "  r = smoothstep(0.25, 0.75, r);\n" +
            "  vec2 e = min(s.xy, 1.0 - s.xy);\n" +
            "  float fade = clamp(min(e.x, e.y) * 14.0, 0.0, 1.0);\n" +
            "  return mix(1.0, r, fade * uShadowP.w);\n" +
            "}\n" +
            "void main() {\n" +
            "  vec4 tx = texture2D(uAtlas, vUV);\n" +
            "#ifdef CUTOUT\n" +
            "  if (tx.a < 0.5) discard;\n" +
            "#endif\n" +
            "  vec3 alb = tx.rgb * vCol.rgb * uTint.rgb;\n" +
            "  int type = int(vType + 0.5);\n" +
            "  vec3 N = normalize(vN);\n" +
            "  vec3 V = normalize(uCamPos - vW);\n" +
            "#ifdef DOUBLE\n" +
            "  if (dot(N, V) < 0.0) N = -N;\n" +
            "#endif\n" +
            "  float ndl = dot(N, uSunDir);\n" +
            "  float soft = 0.012 + vMat.w * 0.3;\n" +
            "  float lit = smoothstep(-soft, soft, ndl - 0.03) * shadowAmount();\n" +
            "  float ao = vCol.a;\n" +
            "  lit *= smoothstep(0.2, 0.62, ao);\n" +
            "  vec3 shade = (type == 1) ? uSkinShade : uShadeCol;\n" +
            "  vec3 col = mix(alb * shade * (0.72 + 0.28 * ao), alb * uLightCol, lit);\n" +
            "  float fres = 1.0 - max(dot(N, V), 0.0);\n" +
            "  if (type == 5) col += alb * uLightCol * 0.3 * max(-ndl, 0.0);\n" +
            "  col += uRimCol * smoothstep(0.6, 0.68, fres) * vMat.y * (0.3 + 0.7 * lit);\n" +
            "  vec3 H = normalize(uSunDir + V);\n" +
            "  float nh = max(dot(N, H), 0.0);\n" +
            "  float sp;\n" +
            "  if (type == 3) {\n" +
            "    float band = abs(dot(normalize(N - V * dot(N, V)), vec3(0.0, 1.0, 0.0)));\n" +
            "    sp = smoothstep(0.42, 0.5, pow(nh, 8.0)) * smoothstep(0.35, 0.6, band);\n" +
            "  } else {\n" +
            "    sp = smoothstep(0.5, 0.56, pow(nh, type == 4 ? 70.0 : 40.0));\n" +
            "  }\n" +
            "  col += vec3(sp * vMat.x * (0.25 + 0.75 * lit));\n" +
            "  if (type == 2) {\n" +
            "    vec3 R = reflect(-V, N);\n" +
            "    vec3 sky = mix(uSkyHor, uSkyTop, clamp(R.y * 1.5 + 0.2, 0.0, 1.0));\n" +
            "    col = mix(col, sky, 0.35 + 0.45 * fres);\n" +
            "    col += vec3(smoothstep(0.96, 0.975, nh)) * 0.9;\n" +
            "  }\n" +
            "  float em = vMat.z * (type == 6 ? uNight : 1.0) + uEmis;\n" +
            "  col += alb * em * 2.2;\n" +
            "  if (uLamp.w > 0.0) {\n" +
            "    vec3 d = uLamp.xyz - vW;\n" +
            "    float dl = length(d) + 0.001;\n" +
            "    float att = clamp(1.0 - dl / uLamp.w, 0.0, 1.0);\n" +
            "    float nl = dot(N, d / dl);\n" +
            "    col += alb * uLampCol * att * att * (0.35 + 0.65 * smoothstep(-0.05, 0.1, nl));\n" +
            "  }\n" +
            "  if (type == 7) col = alb * (1.0 + vMat.z);\n" +
            "  float dist = length(vW - uCamPos);\n" +
            "  float fog = clamp((dist - uFog.x) / (uFog.y - uFog.x), 0.0, 1.0);\n" +
            "  fog = fog * fog * (3.0 - 2.0 * fog) * uFog.z;\n" +
            "  fog = max(fog, clamp(uFog.w * (1.0 - vW.y * 0.25), 0.0, 0.8) * clamp(dist * 0.02, 0.0, 1.0));\n" +
            "  col = mix(col, uFogCol, fog);\n" +
            "#ifdef DECAL\n" +
            "  gl_FragColor = vec4(col, tx.a * uTint.a);\n" +
            "#else\n" +
            "  gl_FragColor = vec4(col, uTint.a);\n" +
            "#endif\n" +
            "}\n";

    // ------------------------------------------------------------------ ink outline (inverted hull)

    public static final String OUTLINE_VS = VERT_COMMON +
            "uniform vec2 uScreen;\n" +
            "uniform float uOutline;\n" +
            "varying vec4 vCol;\n" +
            "varying vec3 vW;\n" +
            "void main() {\n" +
            "  skinAndPlace();\n" +
            "  vec4 c = uVP * vec4(gPos, 1.0);\n" +
            "  vec4 c2 = uVP * vec4(gPos + normalize(gOut) * 0.05, 1.0);\n" +
            "  vec2 d = (c2.xy / c2.w - c.xy / c.w) * uScreen;\n" +
            "  float l = length(d);\n" +
            "  vec2 dir = l > 1e-5 ? d / l : vec2(0.0);\n" +
            "  float px = uOutline * aNrm.w * clamp(9.0 / max(c.w, 0.1), 0.3, 1.0);\n" +
            "  c.xy += dir * px * 2.0 / uScreen * c.w;\n" +
            "  vCol = aCol;\n" +
            "  vW = gPos;\n" +
            "  gl_Position = c;\n" +
            "}\n";

    public static final String OUTLINE_FS = PREC_FRAG +
            "uniform vec3 uInk;\n" +
            "uniform vec3 uCamPos;\n" +
            "uniform vec3 uFogCol;\n" +
            "uniform vec4 uFog;\n" +
            "uniform vec4 uTint;\n" +
            "varying vec4 vCol;\n" +
            "varying vec3 vW;\n" +
            "void main() {\n" +
            "  vec3 c = mix(uInk, vCol.rgb * uTint.rgb * 0.3, 0.35);\n" +
            "  float dist = length(vW - uCamPos);\n" +
            "  float fog = clamp((dist - uFog.x) / (uFog.y - uFog.x), 0.0, 1.0) * uFog.z;\n" +
            "  gl_FragColor = vec4(mix(c, uFogCol, fog), uTint.a);\n" +
            "}\n";

    // ------------------------------------------------------------------ shadow depth (packed RGBA)

    public static final String SHADOW_VS = VERT_COMMON +
            "varying vec2 vUV;\n" +
            "void main() {\n" +
            "  skinAndPlace();\n" +
            "  vUV = aUV;\n" +
            "  gl_Position = uVP * vec4(gPos, 1.0);\n" +
            "}\n";

    public static final String SHADOW_FS = PREC_FRAG +
            "uniform sampler2D uAtlas;\n" +
            "varying vec2 vUV;\n" +
            "vec4 packDepth(float d) {\n" +
            "  vec4 e = fract(vec4(1.0, 255.0, 65025.0, 16581375.0) * d);\n" +
            "  return e - e.yzww * vec4(1.0 / 255.0, 1.0 / 255.0, 1.0 / 255.0, 0.0);\n" +
            "}\n" +
            "void main() {\n" +
            "#ifdef CUTOUT\n" +
            "  if (texture2D(uAtlas, vUV).a < 0.5) discard;\n" +
            "#endif\n" +
            "  gl_FragColor = packDepth(gl_FragCoord.z);\n" +
            "}\n";

    // ------------------------------------------------------------------ painted sky (full-screen)

    public static final String SKY_VS =
            "attribute vec2 aXY;\n" +
            "uniform mat4 uInvVP;\n" +
            "varying vec3 vDir;\n" +
            "void main() {\n" +
            "  vec4 a = uInvVP * vec4(aXY, -1.0, 1.0);\n" +
            "  vec4 b = uInvVP * vec4(aXY, 1.0, 1.0);\n" +
            "  vDir = b.xyz / b.w - a.xyz / a.w;\n" +
            "  gl_Position = vec4(aXY, 0.9999, 1.0);\n" +
            "}\n";

    public static final String SKY_FS = PREC_FRAG +
            "uniform vec3 uSkyTop;\n" +
            "uniform vec3 uSkyHor;\n" +
            "uniform vec3 uSkyLow;\n" +
            "uniform vec3 uSunDir;\n" +
            "uniform vec3 uSunCol;\n" +
            "uniform vec3 uMoonDir;\n" +
            "uniform float uNight;\n" +
            "uniform float uTime;\n" +
            "varying vec3 vDir;\n" +
            "float hash(vec3 p) { return fract(sin(dot(p, vec3(12.9898, 78.233, 37.719))) * 43758.5453); }\n" +
            "void main() {\n" +
            "  vec3 d = normalize(vDir);\n" +
            "  float h = d.y;\n" +
            "  vec3 c = h > 0.0 ? mix(uSkyHor, uSkyTop, pow(clamp(h * 1.4, 0.0, 1.0), 0.65)) : mix(uSkyHor, uSkyLow, clamp(-h * 5.0, 0.0, 1.0));\n" +
            "  float s = max(dot(d, uSunDir), 0.0);\n" +
            "  c += uSunCol * (pow(s, 12.0) * 0.35 + pow(s, 90.0) * 0.6);\n" +
            "  c = mix(c, vec3(1.0, 0.98, 0.9) * uSunCol * 1.4, smoothstep(0.9988, 0.9993, s));\n" +
            "  if (uNight > 0.01) {\n" +
            "    float m = dot(d, uMoonDir);\n" +
            "    c += vec3(0.25, 0.3, 0.45) * pow(max(m, 0.0), 40.0) * uNight;\n" +
            "    c = mix(c, vec3(0.97, 0.96, 0.86), smoothstep(0.9994, 0.99965, m) * uNight);\n" +
            "    vec3 q = floor(d * 180.0);\n" +
            "    float st = step(0.9965, hash(q)) * smoothstep(0.02, 0.25, h);\n" +
            "    st *= 0.6 + 0.4 * sin(uTime * 3.0 + hash(q + 3.0) * 40.0);\n" +
            "    c += vec3(st) * uNight;\n" +
            "  }\n" +
            "  gl_FragColor = vec4(c, 1.0);\n" +
            "}\n";

    // ------------------------------------------------------------------ particles, glows and ribbon trails

    public static final String PART_VS =
            "attribute vec3 aP;\n" +
            "attribute vec2 aT;\n" +
            "attribute vec4 aC;\n" +
            "uniform mat4 uVP;\n" +
            "uniform vec3 uCamPos;\n" +
            "uniform vec4 uFog;\n" +
            "varying vec2 vT;\n" +
            "varying vec4 vC;\n" +
            "varying float vFog;\n" +
            "void main() {\n" +
            "  vT = aT; vC = aC;\n" +
            "  float dist = length(aP - uCamPos);\n" +
            "  vFog = clamp((dist - uFog.x) / (uFog.y - uFog.x), 0.0, 1.0) * uFog.z;\n" +
            "  gl_Position = uVP * vec4(aP, 1.0);\n" +
            "}\n";

    public static final String PART_FS = PREC_FRAG +
            "uniform sampler2D uAtlas;\n" +
            "uniform vec3 uFogCol;\n" +
            "uniform float uAdd;\n" +
            "varying vec2 vT;\n" +
            "varying vec4 vC;\n" +
            "varying float vFog;\n" +
            "void main() {\n" +
            "  vec4 t = texture2D(uAtlas, vT) * vC;\n" +
            "  if (uAdd > 0.5) { gl_FragColor = vec4(t.rgb * t.a * (1.0 - vFog), 1.0); }\n" +
            "  else { gl_FragColor = vec4(mix(t.rgb, uFogCol, vFog), t.a); }\n" +
            "}\n";

    // ------------------------------------------------------------------ screen overlays: speed lines, flash, vignette

    public static final String SCREEN_VS =
            "attribute vec2 aXY;\n" +
            "varying vec2 vXY;\n" +
            "void main() { vXY = aXY; gl_Position = vec4(aXY, 0.0, 1.0); }\n";

    public static final String SCREEN_FS = PREC_FRAG +
            "uniform vec4 uSpeed;\n" +     // x intensity, y time, z aspect, w seed
            "uniform vec4 uFlash;\n" +     // rgb colour, a strength
            "uniform vec4 uVignette;\n" +  // rgb colour, a strength
            "varying vec2 vXY;\n" +
            "float hash(float n) { return fract(sin(n) * 43758.5453); }\n" +
            "void main() {\n" +
            "  vec2 p = vec2(vXY.x * uSpeed.z, vXY.y);\n" +
            "  float r = length(p);\n" +
            "  float a = atan(p.y, p.x);\n" +
            "  float k = floor(a * 38.0);\n" +
            "  float rnd = hash(k + floor(uSpeed.y * 14.0) * 7.13 + uSpeed.w);\n" +
            "  float line = step(0.55, rnd) * smoothstep(0.55 + rnd * 0.35, 1.25, r);\n" +
            "  float w = abs(fract(a * 38.0) - 0.5);\n" +
            "  line *= smoothstep(0.5, 0.2, w);\n" +
            "  float sl = line * uSpeed.x;\n" +
            "  float vig = smoothstep(0.7, 1.55, r) * uVignette.a;\n" +
            "  vec3 col = mix(vec3(1.0), uVignette.rgb, vig / max(vig + sl, 0.001));\n" +
            "  float alpha = clamp(sl * 0.8 + vig, 0.0, 1.0);\n" +
            "  col = mix(col, uFlash.rgb, uFlash.a);\n" +
            "  alpha = max(alpha, uFlash.a);\n" +
            "  gl_FragColor = vec4(col, alpha);\n" +
            "}\n";

    /** Program variants used by the renderers. */
    public static final String[][] PROGRAMS = {
            // name, defines, vs, fs
            {"main", "", "MAIN_VS", "MAIN_FS"},
            {"main_skin", "#define SKIN\n", "MAIN_VS", "MAIN_FS"},
            {"main_double", "#define DOUBLE\n", "MAIN_VS", "MAIN_FS"},
            {"main_cutout", "#define CUTOUT\n#define DOUBLE\n", "MAIN_VS", "MAIN_FS"},
            {"main_decal", "#define DECAL\n#define DOUBLE\n", "MAIN_VS", "MAIN_FS"},
            {"main_decal_skin", "#define DECAL\n#define SKIN\n", "MAIN_VS", "MAIN_FS"},
            {"outline", "", "OUTLINE_VS", "OUTLINE_FS"},
            {"outline_skin", "#define SKIN\n", "OUTLINE_VS", "OUTLINE_FS"},
            {"shadow", "", "SHADOW_VS", "SHADOW_FS"},
            {"shadow_skin", "#define SKIN\n", "SHADOW_VS", "SHADOW_FS"},
            {"shadow_cutout", "#define CUTOUT\n", "SHADOW_VS", "SHADOW_FS"},
            {"sky", "", "SKY_VS", "SKY_FS"},
            {"part", "", "PART_VS", "PART_FS"},
            {"screen", "", "SCREEN_VS", "SCREEN_FS"},
    };

    public static String source(String key) {
        switch (key) {
            case "MAIN_VS": return MAIN_VS;
            case "MAIN_FS": return MAIN_FS;
            case "OUTLINE_VS": return OUTLINE_VS;
            case "OUTLINE_FS": return OUTLINE_FS;
            case "SHADOW_VS": return SHADOW_VS;
            case "SHADOW_FS": return SHADOW_FS;
            case "SKY_VS": return SKY_VS;
            case "SKY_FS": return SKY_FS;
            case "PART_VS": return PART_VS;
            case "PART_FS": return PART_FS;
            case "SCREEN_VS": return SCREEN_VS;
            case "SCREEN_FS": return SCREEN_FS;
            default: throw new IllegalArgumentException(key);
        }
    }
}
