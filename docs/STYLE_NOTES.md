# Style Notes: Ghibli / anime look for the toon runner

Art-direction notes for a cel-shaded mobile runner on a custom GLES2 toon shader: one light band,
a tinted shadow colour, rim light, inverted-hull outlines, vertex colours or a texture atlas, and
simple bloom as the only post effect. **Source caveat:** these notes come only from YouTube
transcripts. Nobody watched the videos, so the colours are described in words and no hex values
were sampled from the screen. Where the tutorials work in Blender (Eevee or Cycles), the notes
translate the idea into a bake or a vertex-data step.

---

## 1. How to Create Ghibli Trees in 3D (Lightning Boy Studio, `DEgzuMmJtu8`)
**Carries over**
- Build the canopy from **clumps of spheres inside a sculpted blob**. Two passes: about 20 large spheres, then about 200 small ones scattered in the *volume* (not on the surface) of a lumpy emitter. Decimate the source sphere hard (ratio 0.1) before instancing.
- **The key trick is normal transfer.** Duplicate the lumpy emitter as a "custom normals" proxy, decimate it and smooth it, then copy its normals onto the sphere clump (face custom normals). The clump then shades as one soft mass but keeps a broken silhouette. Bake this into the exported mesh normals, because our shader reads only vertex normals.
- **Flatten trees along one axis** (scale X down) to get the Ghibli look. Scale a tree up on the lit side to get one big lit plane.
- Ramp: use **3 close steps on the dark end**, with black almost hidden and dark areas "not actually that dark". Pick colours with an eyedropper from a film still: bright green, a slightly darker green and a deep shade.
- Put **pure white only at the far right of the ramp** so that only a strong rim/back light (strength 5) reaches it. This matches our rim-light term.
- Use several palettes per tree type: yellow-green, green and dark blue for one; darker pines for another. The tutorial switches palettes with a per-object value (object colour plus a "less than" threshold). For us that is a per-instance palette index or a vertex-colour row in the atlas.
- Local light pockets: point lights brighten big top regions, and *negative* point lights paint shadow. Bake both into vertex colour (AO/tint).

**Does not carry over:** particle instancing, live AO for black crevices (bake it instead),
negative lights at runtime, and the 4-step ramp (we have one band, so fold AO into vertex colour).

## 2. Lightning Boy Shader Beginner Guide: Shading & Modeling Tips (Lightning Boy Studio, `gCAMvBCfiew`)
**Carries over**
- **Base colour is the shadow colour. The key light adds the colour you actually picture.** Author the shadow colour first and make it darker *and hue-shifted*.
- Gradient tints: a subtle yellow sphere-gradient at the top and a **dark purple gradient toward the feet/bottom**, so shadows "start warm and end purple". Use a large, soft gradient sphere. This is cheap for us: tint vertex colours by height, or add a world-Y lerp in the shader.
- One global HSV/curve control across all materials, with named overrides. We can mirror this with a global uniform for saturation and shadow tint.
- Modelling: low-poly quads, **few points**, and add every edge loop for a reason. Push vertices "in quite an extreme way" so that a fold or scarf catches a band. Rotate the model and check the silhouette lines from every angle.
- **Flat faces pop on and off.** A sharp toon band needs curvature. Bevel edges or use a smooth cage with creased edges so a cube or sword gets highlight edges instead of whole-face flips.
- Outlines are an inverted hull, so **move geometry away from neighbours** (scarf off the chest) to stop clipping. Keep outlines **very thin near the eyes**. Tint the outline per material instead of using pure black, with one outline colour per material slot.
- Rim light should be guided by the key light (stronger where already lit) or driven by a separate direction for shoulder rims.
- Glow: push the value above 1 (around 10) and let bloom bleed it. With our simple bloom, we reserve over-bright for emissive pickups and eyes.
- Textured assets: put the texture on the *lit* colour and derive the shadow by an adjustment (darken, desaturate, tint) instead of a second texture.

**Does not carry over:** screen-space AO, halftone/hatch/painterly layer styles (possible later
as a UV-space band texture), mean-crease export (the transcript itself doubts it), Eevee bake
(the transcript says it is impossible: rebuild in-engine), and huge light power values.

## 3. Ghibli style procedural rocks (Kristof Dedene, `FHeBI5tAGP0`)
**Carries over**
- Rock shape: a subdivided sphere **displaced by a Voronoi texture (distance squared, global coordinates)**, so every placed rock is unique. Generate 4 to 6 variants offline and reuse them.
- Paint layers: a large Voronoi patch (smooth F1, randomness 0.6) with edges broken by noise (scale 30, mix 0.95). A second Voronoi (scale 27, sweet spot about 7) is soft-light mixed at 0.5 as "paint dabs". **Bake to a small atlas tile.**
- **Hand-placed shadow and highlight gradient** (a linear gradient rotated 90 degrees, multiplied) instead of only lighting. A highlight colour can become a **moss-green top**: use a world-up vertex colour.
- Palette: greys pushed **slightly blue**, dark green, brown/blue grey. Use a blue-ish highlight and a slightly darker, *coloured* shadow. Musgrave rings at scales 2 to 4 give watercolour blotches (khaki green, light blue).
- Outline: solidify with flipped normals and a backface-culled black emission material, about
  -0.01 thick. **A greyish line reads softer than black** on rocks.

**Does not carry over:** per-pixel procedural noise (too costly on GLES2 fill, so bake it) and
object-location randomisation (use an instance-ID UV offset into the atlas instead).

## 4. Toon Shader Tutorial Part 5: Better Shadows (Lightning Boy Studio, `ToX21Z8RXoc`)
**Carries over**
- **Painted shadow masks:** a black/white mask forces shadow under the brows and similar areas. It is multiplied into the light term *before* the ramp, so it blends with real light. For us this is a vertex-colour channel (say alpha or R) that we multiply into N·L before the step.
- **Baked AO combined with a local AO term.** Large-scale occlusion (under belly, tail, head) is baked so it never vanishes. Crunch it with a power or ramp, give it a *colour* (reddish for skin, like SSS) and an opacity, and blend sharp and soft versions.
- **Limit AO to the shadow side** so the lit band stays clean, which suits cel style. Inside shadow, allow only a slight gradient.
- Use 5 flat palette colours per character, mixed by masks, instead of a painted texture. This maps directly onto a vertex-colour or atlas-swatch workflow.

**Does not carry over:** screen-space AO, which pops with zoom (the transcript says so), and
soft shadow radii from point lights (we have no shadow maps on low-end GLES2).

## 5. Anime inspired 2D trees (Kristof Dedene, `WZkUyJaEmA4`)
**Carries over**
- **Card bushes for the far background:** a spherical gradient multiplied by noise, squashed horizontally for flat leaf layers, cut out with alpha-clip, and given a tileable leaf texture for the edge.
- Ramp of **dark blue, lighter green and yellow-green highlight**, with a soft-light gradient inverted so the top is lit and the bottom is shaded.
- **Two layers per tree:** a dark "under-paint" card behind and a lighter card in front. Layer order: **cards higher up sit behind, cards lower down sit in front.** Use 3 layers for big masses (one huge back filler, then smaller ones on top).
- For a crisp but not aliased edge, use two linear ramp stops placed very close together instead of a constant ramp.
- The leaf texture is made seamless with an offset and heal pass at 2000 px. A watercolour leaf brush gets size, angle and scatter jitter.

**Does not carry over:** these cards break when seen side-on (the transcript says so), so use
them only for far, camera-facing rows. Alpha-blend sorting costs on mobile, so prefer alpha-test.

## 6. Anime style clouds and starry night sky (Kristof Dedene, `m4aOZm6auxQ`)
Summary from the caller's notes; the transcript was not re-read here.
- Clouds: Voronoi at scales 3 and 15 mixed, stylised with a ramp, with Musgrave detail soft-light mixed on top. Use a **dome stretched in Z** so low clouds stretch more.
- Shadow layer: the same noise sampled at a 1.03 Z offset, which leaves a **bright rim on cloud tops**. Use a 3-tone blue ramp.
- **Horizon fog:** a gradient blended into the clouds. Stars come from Voronoi at scale 100 to 200, tinted orange, white and blue, and gathered along a Milky Way band.
- For us, **bake the sky dome to a texture** (or 2 to 3 scrolling layers). Do not run per-pixel Voronoi.

---

## Rules we apply to the Sakura rebuild
1. **Foliage means clumped blobs plus normals transferred from a proxy.** Sakura canopies are 3 to 6 sphere clusters per tree, with normals copied from a smoothed lumpy proxy and baked into the mesh. This gives one clean light band with a broken silhouette.
2. **Shadow is hue-shifted, not darkened.** Blossom pink shadows go toward mauve/violet, greens toward blue-teal, and rock greys toward blue. Shadow value is only a little lower than the lit value.
3. **Warm top, cool bottom.** Use a vertex-colour height gradient: light yellow-warm near the top, dusty purple toward the ground on every asset, characters included.
4. **Few large shapes.** Each prop reads as 1 to 3 masses. Exaggerate curvature so the band travels smoothly, and bevel hard edges so flat faces never flip entirely on or off.
5. **Limited palette.** Each biome gets about 5 swatches per material family in one atlas strip, with tree variants as palette rows. No per-asset textures unless needed.
6. **Bake occlusion and painted shadow into vertex colour,** multiplied into N·L before the band step and kept inside the shadow side. Never add live AO.
7. **Rim light is reserved for silhouettes.** It is gated by the lit side, the white tone appears only at the rim, and it is stronger on the player than on the background.
8. **Outlines are thin and tinted.** Use dark plum or brown-grey instead of black, grey on rocks and foliage, and very thin near faces and eyes. Move geometry apart wherever the hull clips.
9. **Background depth uses cards.** Far tree lines are alpha-tested 2-layer cards (dark behind, light in front, lower cards in front of higher ones). Near trees are full 3D blobs.
10. **The sky is baked.** Use a 3-tone gradient dome plus horizon fog matched to the shadow colour, so distant objects fade into the same hue as their shadows.
11. **Bloom is for emissives only.** Only pickups, lanterns and eyes go above 1.0. Everything else stays at or below 1 so the bloom never washes out the palette.
12. **Rocks are displaced and varied.** Use 4 to 6 baked Voronoi-displaced rock meshes with a painted-dab atlas tile and moss-green vertex colour on upward-facing tops.
