package com.pongo.core;

/**
 * GLSL ES 1.00 sources shared by the Android renderer and the WebGL preview harness.
 * Every program is compiled from a small #define prefix + one of these bodies.
 *
 * The look follows the Blender toon group (blender/lib/erlib.py, PongoToon) the design renders use: a crisp light
 * band over a violet-tinted shadow band, a hard rim, toon specular bands and inverted-hull ink. On top of that the
 * game adds what a single still doesn't need: the sun shadow map in the shadow tint, a little sky bounce in the
 * shadows, sun haze in the fog, and the zone materials (toon water, glowing crystals, painted clouds and sky).
 * Everything is one pass per surface with no extra render targets, so it stays cheap on mid-range GLES2 phones.
 */
public final class Shaders {
    private Shaders() {}

    public static final int MAX_BONES = 32;

    /** Shading types. 0..7 are packed in aOut.w as type / 7 (older pongo.bin files only have these); 8 and up as
     *  -(type - 7) / 7, so files built before the extra types still decode the same. Mirrors tools/assetbuilder. */
    public static final int T_STD = 0, T_SKIN = 1, T_GLASS = 2, T_HAIR = 3, T_METAL = 4, T_FOLIAGE = 5, T_NIGHT = 6, T_UNLIT = 7,
            T_CRYSTAL = 8, T_CLOUD = 9;

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
            "uniform vec4 uWind;\n" +          // xyz sway direction and strength, w time
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
            // sway: a slow lean plus a flutter, and a gust that rolls down the track every few seconds so whole rows of
            // trees and reeds bend one after the other instead of all at once
            "  float gust = 0.6 + 0.8 * smoothstep(0.55, 1.0, sin(uWind.w * 0.9 - w.z * 0.08 + w.x * 0.03));\n" +
            "  w.xyz += uWind.xyz * sw * gust * (sin(uWind.w * 2.3 + w.x * 0.35 + w.z * 0.21) + 0.45 * sin(uWind.w * 5.3 + w.z * 0.9 + w.y));\n" +
            "  gPos = w.xyz;\n" +
            "  gNrm = (uModel * vec4(n, 0.0)).xyz;\n" +
            "  gOut = (uModel * vec4(o, 0.0)).xyz;\n" +
            "}\n" +
            "float shadingType() {\n" +
            "  float t = aOut.w * 7.0;\n" +
            "  return t > -0.5 ? t : 7.0 - t;\n" +
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
            "varying float vSway;\n" +
            "void main() {\n" +
            "  skinAndPlace();\n" +
            "  vW = gPos; vN = gNrm; vUV = aUV; vCol = aCol; vMat = aMat; vType = shadingType(); vSway = aPos.w;\n" +
            "  vec4 s = uShadowVP * vec4(gPos, 1.0);\n" +
            "  vSh = s.xyz / s.w * 0.5 + 0.5;\n" +
            "  gl_Position = uVP * vec4(gPos, 1.0);\n" +
            "}\n";

    /** Uniforms, shadow lookup and fog shared by the surface programs (toon and water). */
    private static final String FS_COMMON =
            "uniform sampler2D uAtlas;\n" +
            "uniform sampler2D uShadow;\n" +
            "uniform vec3 uCamPos;\n" +
            "uniform vec3 uSunDir;\n" +
            "uniform vec3 uSunCol;\n" +
            "uniform vec3 uLightCol;\n" +
            "uniform vec3 uShadeCol;\n" +
            "uniform vec3 uSkinShade;\n" +
            "uniform vec3 uRimCol;\n" +
            "uniform vec3 uSkyTop;\n" +
            "uniform vec3 uSkyHor;\n" +
            "uniform vec3 uFogCol;\n" +
            "uniform vec4 uFog;\n" +          // start, end, max, height-fog density
            "uniform vec4 uHaze;\n" +         // sun haze in the fog, sky bounce in the shadows, crystal pulse, aerial haze
            "uniform vec4 uShadowP;\n" +      // texel, bias, enabled, strength
            "uniform float uNight;\n" +
            "uniform float uTime;\n" +
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
            "varying float vSway;\n" +
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
            // distance fog with a height layer; looking toward the sun the haze warms up (the glow around a low sun)
            "vec3 applyFog(vec3 col) {\n" +
            "  vec3 d = vW - uCamPos;\n" +
            "  float dist = length(d);\n" +
            "  float fog = clamp((dist - uFog.x) / (uFog.y - uFog.x), 0.0, 1.0);\n" +
            "  fog = fog * fog * (3.0 - 2.0 * fog) * uFog.z;\n" +
            "  fog = max(fog, clamp(uFog.w * (1.0 - vW.y * 0.25), 0.0, 0.8) * clamp(dist * 0.02, 0.0, 1.0));\n" +
            // aerial perspective: a thin layer of sky-blue haze that starts close and thickens slowly, so the middle
            // distance already steps back in soft layers (the Genshin landscape look), more so near the ground
            "  float air = smoothstep(6.0, uFog.y * 0.9, dist) * uHaze.w * (1.0 - 0.4 * clamp(vW.y * 0.05, 0.0, 1.0));\n" +
            "  float sun = max(dot(d / max(dist, 0.001), uSunDir), 0.0);\n" +
            "  vec3 fc = uFogCol + uSunCol * (sun * sun * sun * sun * uHaze.x);\n" +
            "  col = mix(col, mix(uSkyHor, fc, 0.5), air);\n" +
            "  return mix(col, fc, fog);\n" +
            "}\n" +
            "vec3 lampLight(vec3 alb, vec3 N) {\n" +
            "  if (uLamp.w <= 0.0) return vec3(0.0);\n" +
            "  vec3 d = uLamp.xyz - vW;\n" +
            "  float dl = length(d) + 0.001;\n" +
            "  float att = clamp(1.0 - dl / uLamp.w, 0.0, 1.0);\n" +
            "  float nl = dot(N, d / dl);\n" +
            "  return alb * uLampCol * att * att * (0.35 + 0.65 * smoothstep(-0.05, 0.1, nl));\n" +
            "}\n";

    public static final String MAIN_FS = PREC_FRAG + FS_COMMON +
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
            // sky bounce: shadowed faces that look up take a little of the sky, so the ground shadows read lilac-blue
            // like the renders rather than flat grey
            "  shade = mix(shade, shade * (0.55 + 0.6 * uSkyTop), clamp(N.y, 0.0, 1.0) * uHaze.y);\n" +
            "  vec3 col = mix(alb * shade * (0.72 + 0.28 * ao), alb * uLightCol, lit);\n" +
            "  float fres = 1.0 - max(dot(N, V), 0.0);\n" +
            "  if (type == 5) {\n" +
            // foliage: light through the leaves from behind, and a root-to-tip gradient (the sway weight grows
            // toward the tips) so grass and canopies read darker inside and brighter at the ends
            "    col += alb * uLightCol * 0.3 * max(-ndl, 0.0);\n" +
            "    col *= 0.86 + 0.18 * clamp(vSway * 2.5, 0.0, 1.0);\n" +
            "  }\n" +
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
            "  if (type == 8) {\n" +
            // crystal: a mineral first, a light second. The body is cel-shaded like stone in a muted (partly
            // desaturated) version of its colour; a faint glow rises softly toward the face-on core, breathing very
            // slowly along the wall; facet edges catch a thin cool rim and the sun or lamp gives one small glint
            "    float facing = 1.0 - fres;\n" +
            "    float pulse = 0.9 + 0.1 * sin(uTime * uHaze.z + dot(vW, vec3(0.9, 1.3, 0.7)));\n" +
            "    vec3 mineral = mix(vec3(dot(alb, vec3(0.3, 0.55, 0.15))), alb, 0.55) * 0.92;\n" +
            "    col = mix(mineral * shade * (0.72 + 0.28 * ao), mineral * uLightCol, lit);\n" +
            "    col += mineral * (vMat.z * 0.6 * pulse) * smoothstep(0.15, 1.0, facing) * (0.6 + 0.4 * facing);\n" +
            "    col += uRimCol * smoothstep(0.62, 0.8, fres) * 0.25 * vMat.y;\n" +
            "    col += vec3(smoothstep(0.965, 0.98, nh) * 0.55 * vMat.x * (0.3 + 0.7 * lit));\n" +
            "    em = uEmis;\n" +
            "  } else if (type == 9) {\n" +
            // cloud: wide wrap light in three painted tones (sunlit cream, lilac middle, violet underside) and a warm
            // silver lining where the cloud stands against the sun
            "    float w = ndl * 0.5 + 0.5;\n" +
            "    vec3 under = alb * mix(shade, uSkyTop, 0.25);\n" +
            "    vec3 mid = alb * mix(shade, uLightCol, 0.6);\n" +
            "    col = mix(under, mix(mid, alb * uLightCol, smoothstep(0.62, 0.7, w)), smoothstep(0.34, 0.42, w));\n" +
            "    float back = max(dot(-V, uSunDir), 0.0);\n" +
            "    col += uSunCol * smoothstep(0.55, 0.7, fres) * (0.15 + 0.6 * back * back) * vMat.y;\n" +
            "  }\n" +
            "  col += alb * em * 2.2;\n" +
            "  col += lampLight(alb, N) * (1.0 - 0.6 * lit);\n" +
            "  if (type == 7) col = alb * (1.0 + vMat.z);\n" +
            "  col = applyFog(col);\n" +
            "#ifdef DECAL\n" +
            "  gl_FragColor = vec4(col, tx.a * uTint.a);\n" +
            "#else\n" +
            "  gl_FragColor = vec4(col, uTint.a);\n" +
            "#endif\n" +
            "}\n";

    // ------------------------------------------------------------------ toon water

    /**
     * Water parts (material flag F_WATER): the material colour is the shallow tint, the shadow tint makes the deep
     * side. Three drifting sine waves give an analytic ripple normal (no normal map); the sky reflects in two hard
     * fresnel bands; flow streaks (dashed white lines in wobbly lanes) scroll along uWater.xy; the sun breaks into
     * hard glints. Received shadows darken it like any surface. Opaque, one pass.
     */
    public static final String WATER_FS = PREC_FRAG + FS_COMMON +
            "uniform vec4 uWater;\n" +         // xy flow in m/s (game x, z), z ripple scale (1/m), w streak amount
            "float hash1(float n) { return fract(sin(n * 12.9898) * 43758.5453); }\n" +
            "void main() {\n" +
            "  vec3 alb = texture2D(uAtlas, vUV).rgb * vCol.rgb * uTint.rgb;\n" +
            "  vec2 p = vW.xz * uWater.z;\n" +
            "  vec2 fl = uWater.xy * (uTime * uWater.z);\n" +
            "  vec2 q = p - fl;\n" +
            // ripple normal from the gradient of three sines
            "  float w1 = dot(q, vec2(0.8, 0.6)) * 2.1 + uTime * 1.3;\n" +
            "  float w2 = dot(q, vec2(-0.5, 0.86)) * 3.3 - uTime * 1.7;\n" +
            "  float w3 = dot(q, vec2(0.15, -0.99)) * 5.1 + uTime * 2.3;\n" +
            "  vec2 g = vec2(0.8, 0.6) * (2.1 * cos(w1)) + vec2(-0.5, 0.86) * (3.3 * 0.6 * cos(w2)) + vec2(0.15, -0.99) * (5.1 * 0.3 * cos(w3));\n" +
            "  vec3 N = normalize(normalize(vN) + vec3(-g.x, 0.0, -g.y) * 0.035);\n" +
            "  vec3 V = normalize(uCamPos - vW);\n" +
            "  float lit = shadowAmount();\n" +
            "  vec3 deep = alb * uShadeCol * 0.82;\n" +
            "  vec3 N0 = normalize(vN);\n" +
            "  float facing = max(dot(N, V), 0.0);\n" +
            // looking straight down it is deeper, at a glance it takes the sky (the deep tint follows the flat surface,
            // so ripples don't break it into blotches)
            "  vec3 col = mix(alb, deep, smoothstep(0.35, 0.9, max(dot(N0, V), 0.0)) * 0.55);\n" +
            "  col *= mix(uShadeCol * 0.9 + 0.1, uLightCol, lit);\n" +
            "  vec3 R = reflect(-V, N);\n" +
            "  vec3 sky = mix(uSkyHor, uSkyTop, clamp(R.y * 1.4, 0.0, 1.0));\n" +
            "  float fres = 1.0 - facing;\n" +
            "  col = mix(col, sky, smoothstep(0.45, 0.6, fres) * 0.25 + smoothstep(0.75, 0.9, fres) * 0.3);\n" +
            // light on the ripple crests: soft bright patches where the three waves line up
            "  float hgt = sin(w1) + 0.6 * sin(w2) + 0.3 * sin(w3);\n" +
            "  col += uLightCol * smoothstep(1.3, 1.6, hgt) * 0.16 * (0.4 + 0.6 * lit);\n" +
            // flow streaks: fine short dashes in wobbly lanes, few of them, fading out in the distance before they alias
            "  vec2 fd = length(uWater.xy) > 0.001 ? normalize(uWater.xy) : vec2(0.0, -1.0);\n" +
            "  vec2 ps = vec2(dot(p, vec2(-fd.y, fd.x)), dot(p, fd));\n" +
            "  float lane = ps.x * 6.0 + sin(ps.y * 0.9 + uTime * 0.5) * 0.8;\n" +
            "  float li = floor(lane);\n" +
            "  float along = ps.y * (1.2 + 0.8 * hash1(li)) - length(fl) * 1.4 + hash1(li + 7.0) * 9.0;\n" +
            "  float fa = fract(along);\n" +
            "  float dash = smoothstep(0.0, 0.05, fa) * (1.0 - smoothstep(0.12, 0.2, fa));\n" +
            "  float thin = 1.0 - smoothstep(0.04, 0.1, abs(fract(lane) - 0.5));\n" +
            "  float far = 1.0 - smoothstep(14.0, 30.0, length(vW - uCamPos));\n" +
            "  float streak = dash * thin * step(0.7, hash1(li + 3.0)) * uWater.w * far;\n" +
            "  col = mix(col, uLightCol * 0.97 + 0.03, streak * (0.25 + 0.3 * lit));\n" +
            // sun glints and the specular band
            "  float sg = max(dot(R, uSunDir), 0.0);\n" +
            "  col += uSunCol * (smoothstep(0.985, 0.99, sg) * 1.2 + smoothstep(0.93, 0.94, sg) * 0.18) * vMat.x * lit;\n" +
            "  col += alb * (vMat.z + uEmis) * 1.5;\n" +
            "  col += lampLight(alb, N);\n" +
            "  col = applyFog(col);\n" +
            "  gl_FragColor = vec4(col, uTint.a);\n" +
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
            // a vertex behind the camera (w <= 0) has no screen position: pushing it out flips the hull into
            // wedges that cover the screen (seen under the overhead wires), so it is not pushed
            "  float px = (c.w > 0.05 && c2.w > 0.05) ? uOutline * aNrm.w * clamp(9.0 / c.w, 0.3, 1.0) : 0.0;\n" +
            "  c.xy += dir * px * 2.0 / uScreen * c.w;\n" +
            "  vCol = aCol;\n" +
            "  vW = gPos;\n" +
            "  gl_Position = c;\n" +
            "}\n";

    public static final String OUTLINE_FS = PREC_FRAG +
            "uniform vec3 uInk;\n" +
            "uniform vec3 uCamPos;\n" +
            "uniform vec3 uSunDir;\n" +
            "uniform vec3 uSunCol;\n" +
            "uniform vec3 uFogCol;\n" +
            "uniform vec4 uFog;\n" +
            "uniform vec4 uHaze;\n" +
            "uniform vec4 uTint;\n" +
            "varying vec4 vCol;\n" +
            "varying vec3 vW;\n" +
            "void main() {\n" +
            "  vec3 c = mix(uInk, vCol.rgb * uTint.rgb * 0.3, 0.35);\n" +
            "  vec3 d = vW - uCamPos;\n" +
            "  float dist = length(d);\n" +
            "  float fog = clamp((dist - uFog.x) / (uFog.y - uFog.x), 0.0, 1.0) * uFog.z;\n" +
            "  float sun = max(dot(d / max(dist, 0.001), uSunDir), 0.0);\n" +
            "  vec3 fc = uFogCol + uSunCol * (sun * sun * sun * sun * uHaze.x);\n" +
            "  gl_FragColor = vec4(mix(c, fc, fog), uTint.a);\n" +
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

    /**
     * The painted sky: gradient, sun disc and glare, and anime cumulus in two layers. Along the horizon a bank of
     * puffy clouds is drawn as a silhouette of scalloped bumps over the azimuth (lit cream on the sun side, lilac
     * underneath, crisp edges); above it scattered clouds come from two octaves of value noise projected on a cloud
     * plane. Below the horizon an optional sea of clouds (the Sky Glide zone). Moon and stars at night. It is drawn
     * after the opaque geometry with the depth test on, so only the pixels that show sky pay for it.
     */
    public static final String SKY_FS = PREC_FRAG +
            "uniform vec3 uSkyTop;\n" +
            "uniform vec3 uSkyHor;\n" +
            "uniform vec3 uSkyLow;\n" +
            "uniform vec3 uSunDir;\n" +
            "uniform vec3 uSunCol;\n" +
            "uniform vec3 uMoonDir;\n" +
            "uniform vec3 uCloudLit;\n" +
            "uniform vec3 uCloudShade;\n" +
            "uniform vec4 uCloud;\n" +       // coverage 0..1, scale, drift (1/s), sea of clouds below the horizon 0..1
            "uniform float uNight;\n" +
            "uniform float uTime;\n" +
            "varying vec3 vDir;\n" +
            "float hash(vec3 p) { return fract(sin(dot(p, vec3(12.9898, 78.233, 37.719))) * 43758.5453); }\n" +
            "float hash2(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }\n" +
            "float vnoise(vec2 p) {\n" +
            "  vec2 i = floor(p); vec2 f = fract(p);\n" +
            "  f = f * f * (3.0 - 2.0 * f);\n" +
            "  return mix(mix(hash2(i), hash2(i + vec2(1.0, 0.0)), f.x), mix(hash2(i + vec2(0.0, 1.0)), hash2(i + vec2(1.0, 1.0)), f.x), f.y);\n" +
            "}\n" +
            // one row of scalloped bumps: k bumps around the circle, random heights, some missing (gaps between clouds)
            "float bumps(float az, float k, float seed) {\n" +
            "  float x = az * k + seed;\n" +
            "  float i = floor(x); float s = fract(x) * 2.0 - 1.0;\n" +
            "  float r = hash2(vec2(i, seed));\n" +
            "  r = r < 0.18 ? 0.0 : 0.45 + 0.55 * r;\n" +
            "  return sqrt(max(1.0 - s * s, 0.0)) * r;\n" +
            "}\n" +
            // painted cloud colour: lit when the sunward sample is thinner, with a cream top edge
            "vec3 cloudCol(float lit, float edge) {\n" +
            "  vec3 c = mix(uCloudShade, uCloudLit, smoothstep(0.25, 0.75, lit));\n" +
            "  return mix(c, uCloudLit * 1.06, edge);\n" +
            "}\n" +
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
            "  if (uCloud.x > 0.001) {\n" +
            "    float az = atan(d.x, -d.z) * 0.15915 + uTime * uCloud.z * 0.02;\n" +
            "    float sunAz = atan(uSunDir.x, -uSunDir.z) * 0.15915 + uTime * uCloud.z * 0.02;\n" +
            "    float toSun = 0.5 + 0.5 * cos((az - sunAz) * 6.2832);\n" +
            // horizon bank: cumulus heads built from three rows of bumps (big, medium, small) riding on each other,
            // grouped by a slow envelope so they gather into separate cloud masses with clear sky between them
            "    float env = 0.35 + 0.65 * smoothstep(0.2, 0.6, vnoise(vec2(az * 6.0, 1.7)));\n" +
            "    float big = bumps(az, 14.0, 0.37);\n" +
            "    float top = env * (uCloud.x * (0.3 * big + 0.09 * bumps(az, 37.0, 4.3) * step(0.01, big)\n" +
            "              + 0.035 * bumps(az, 89.0, 9.1) * step(0.01, big)));\n" +
            "    if (h > -0.004 && h < top) {\n" +
            "      float y = clamp(h / max(top, 0.001), 0.0, 1.0);\n" +
            "      float lit = toSun * 0.3 + 0.7 * smoothstep(0.05, 0.6, y);\n" +
            "      vec3 cc = cloudCol(lit, smoothstep(0.75, 1.0, y) * (0.3 + 0.7 * toSun));\n" +
            "      cc = mix(cc, uSkyHor, (1.0 - smoothstep(0.0, 0.2, y)) * 0.25);\n" +
            "      c = mix(c, cc, smoothstep(top, top - 0.0025, h));\n" +
            "    }\n" +
            // big painterly clouds on a plane above: three octaves for billowy shapes, a soft gradient from the lit
            // side to the lilac belly instead of a hard band, and a bright rim where the cloud thins toward the sun
            "    if (h > 0.02) {\n" +
            "      vec2 uv = d.xz / (h + 0.15) * uCloud.y + vec2(uTime * uCloud.z * 0.3, uTime * uCloud.z);\n" +
            "      float n = vnoise(uv) * 0.55 + vnoise(uv * 2.2 + 5.1) * 0.3 + vnoise(uv * 5.3 + 1.7) * 0.15;\n" +
            "      vec2 sw = uSunDir.xz * 0.22;\n" +
            "      float ns = vnoise(uv + sw) * 0.55 + vnoise((uv + sw) * 2.2 + 5.1) * 0.3;\n" +
            "      float th = 0.78 - uCloud.x * 0.42;\n" +
            "      float a = smoothstep(th, th + 0.06, n) * smoothstep(0.02, 0.14, h);\n" +
            "      float body = smoothstep(th + 0.02, th + 0.22, n);\n" +
            "      float lit = clamp(0.55 + (n - ns) * 3.0 + toSun * 0.2 - body * 0.25, 0.0, 1.0);\n" +
            "      vec3 cc = mix(uCloudShade, uCloudLit, lit);\n" +
            "      cc += uSunCol * (1.0 - body) * (0.15 + 0.5 * toSun) * 0.6;\n" +
            "      c = mix(c, cc, a * 0.97);\n" +
            "    }\n" +
            "  }\n" +
            // sea of clouds below the horizon
            "  if (uCloud.w > 0.001 && h < 0.0) {\n" +
            "    vec2 uv = d.xz / (-h + 0.05) * uCloud.y * 0.6 + vec2(0.0, uTime * uCloud.z * 1.5);\n" +
            "    float n = vnoise(uv) * 0.6 + vnoise(uv * 2.1 + 3.7) * 0.4;\n" +
            "    float ns = vnoise(uv + uSunDir.xz * 0.2) * 0.6 + vnoise((uv + uSunDir.xz * 0.2) * 2.1 + 3.7) * 0.4;\n" +
            "    float a = smoothstep(0.42, 0.45, n + uCloud.w * 0.25) * smoothstep(0.0, 0.03, -h);\n" +
            "    vec3 cc = cloudCol(0.5 + (ns - n) * -4.0, 0.0);\n" +
            "    c = mix(c, cc, a);\n" +
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
            {"water", "", "MAIN_VS", "WATER_FS"},
            {"outline", "", "OUTLINE_VS", "OUTLINE_FS"},
            {"outline_skin", "#define SKIN\n", "OUTLINE_VS", "OUTLINE_FS"},
            {"shadow", "", "SHADOW_VS", "SHADOW_FS"},
            {"shadow_skin", "#define SKIN\n", "SHADOW_VS", "SHADOW_FS"},
            {"shadow_cutout", "#define CUTOUT\n", "SHADOW_VS", "SHADOW_FS"},
            {"sky", "", "SKY_VS", "SKY_FS"},
            {"part", "", "PART_VS", "PART_FS"},
            {"screen", "", "SCREEN_VS", "SCREEN_FS"},
    };

    /** Every source key, in the order the WebGL harness export lists them. */
    public static final String[] KEYS = {"MAIN_VS", "MAIN_FS", "WATER_FS", "OUTLINE_VS", "OUTLINE_FS", "SHADOW_VS", "SHADOW_FS",
            "SKY_VS", "SKY_FS", "PART_VS", "PART_FS", "SCREEN_VS", "SCREEN_FS"};

    public static String source(String key) {
        switch (key) {
            case "MAIN_VS": return MAIN_VS;
            case "MAIN_FS": return MAIN_FS;
            case "WATER_FS": return WATER_FS;
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
