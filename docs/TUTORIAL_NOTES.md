# Tutorial notes — techniques used for the PONGO assets

Transcripts were pulled through TubeLab and distilled into the concrete settings below. Each section
ends with how it is applied in the asset scripts (`blender/assets/*.py`).

## Modelling (JAEY 3D series: body, body finishing, hand, head 1–2, hair, shirt, T-shirt, cropped pants, canvas shoes, laces, boots, rendering)

- **Body from a cube**: mirror (with clipping) above subdivision; extrude legs/torso/arms; arms start as a
  square cross-section so they subdivide into cylinders; *edge split* at knees and waist to work parts
  separately, merged later; apply subdivision level 1 with *Limit Surface off* to keep the shape; clean edge
  flow with knife + set flow + edge slide; finish the hands/feet and bridge them on with *Bridge Edge Loops*.
- **Head**: cube + subdivision fitted to front/side guides; knife the eye and mouth outlines, then edge loops
  around them; nose by extrude; ears from a cube (subdivision 2), joined by boolean union and re-flowed.
- **Hair from strands**: a strand unit = cube → pointed tip, loop cuts smoothed with *set flow*; duplicate along
  the hair flow; work in sections (back, sides, bangs); a hidden inner base layer; *layer shorter copies on
  top* for richness; vary flow and curvature on the outer units; scale tips for spikes; check density so it
  never looks hollow.
- **Clothes** (shirt/pants/T-shirt): separate overlapping shells built from the body; *Extrude Faces Along
  Normals* (offset even) for real thickness, delete hidden faces; hems/cuffs as *bevelled bands scaled out along
  normals*; collar = copied faces lifted, given thickness, fold made by moving the inner edge; stitch lines
  = bevel an edge, then step the strip inward along normals; waistband as its own thicker ring; belt loops =
  copied waistband faces made into a "ㄷ" shape; buckle from a sphere; loop cuts close to edges keep corners
  sharp under subdivision; a centre seam to finish.
- **Shoes/boots**: cube → shoe form → split into *sole / toe / body* as separate overlapping pieces; the outer
  part slightly larger along normals; panel steps = bevel + scale outward along normals; sole shaped with a
  lattice, loop cuts near corners; tongue copied and pushed inward; eyelets are tori snapped to the surface,
  inner face dark to fake the hole; laces are flat bands bridged between eyelets.
- **Rendering**: camera via *camera to view*, choose focal length; key / fill / back(rim) lights (key makes the
  shadows, back adds depth, rim separates the silhouette); transparent film and composite over a backdrop.

**Applied**: Pongo v6 is built from lofts and cages with these structures — separate overlapping garment shells
with real thickness, stepped stitch strips, bands/cuffs/waistband as their own rings, boots split into
sole/toe/body/shaft with stepped panels, strand-unit hair in sections with layering.

## Faces and hair shading (aVersionOfReality, Lightning Boy Studio)

- **Clean face shading**: replace face normals with normals generated from object coordinates in a box that
  fits the head (sphere shading), bend the lower half around X for the jaw/chin, scale X for cheek width,
  define the nose separately. Topology-independent.
- **Flat-modelled hair**: model clumps flat with clean aligned loops, wrap with curve + simple deform + lattice;
  bridge strands at the roots; minimal intersections.
- **Anisotropic hair highlight**: highlight band from UV-Y through a color ramp, shifted by the camera vector
  (vector transform object→camera, ~30% mix), broken up by stacked noise with bright/contrast; painted dark
  strand lines and painted shadows on a second UV map.

**Applied**: generated face normals (partial for the semi-real head), strand UVs root→tip with a painted
strand texture and a view-shifted highlight band.

## Materials (Ryan King Art, Blender Guru, aVersionOfReality)

- **Woven fabric** (procedural picnic blanket): two *Wave* textures (bands, scale ~60), one rotated 90° and
  offset 0.055, multiplied/added into a weave; color ramp → *Bump* height; distort the master mapping with a
  fine *Noise* (scale 120, detail 15) through *Linear Light* at factor ~0.002 for thread irregularity; a second,
  low-frequency noise bump chained in for folds; Principled *roughness* plus *sheen weight/roughness* for fuzz;
  everything driven by one master mapping, organised in frames and a node group with exposed inputs.
- **Fabric textures/stitches** (Blender Guru couch): base color + normal + sheen (fuzz) — don't use displacement;
  correct real-world scale; UVs aligned so the weave runs the same way on every panel; crease/wrinkle maps as
  black-and-white bump; seams via a seam UV strip and a stitch displacement image, used as bump and as a mask
  to color the thread; bump nodes chained (seam → creases → normal).
- **Skin SSS**: Principled subsurface (EEVEE uses Christensen-Burley only); weight, radius with red highest,
  scale in scene units; the base color drives the scatter color.
- **Eyeball**: spherical gradient (object coords) → ramp for pupil/iris/sclera; iris fibres from a Voronoi
  distorted by noise (scale 30, detail 15, roughness 0.6); veins = distorted Voronoi → ramp → slight bump;
  exposed iris/pupil/sclera colors in a group.
- **Dough / cookie surface**: Voronoi bump + noise bump (lumpy at detail 0, fine at detail 10), RGB curves to
  shape the bump, dusty top layer from a high-detail noise (scale 20, detail 15, roughness 1) through a
  contrasty ramp into a two-color mix, subsurface ~0.5.
- **Stylised metal**: fake reflections from reflection coordinates or *matcaps* (normal object→camera space,
  re-centred) — matcaps don't flicker with camera moves like reflection textures; for long flat parts use
  layer-weight facing plus UV stripes shifted by the view.

**Applied**: twill/knit/leather/gold maps painted procedurally (numpy) as seamless tiles with matching normal
maps; Blender materials follow these node structures (master mapping, chained bumps, sheen for fabric, SSS
for
skin); the gilded gear uses a gold matcap in the game shader and Principled metallic in renders, with a cookie
relief (Voronoi lumps + chip studs) on the cookie parts.

## Physics (Blender Guru curtains, CGDive jiggle)

- **Cloth**: enough geometry (subdivide), a *pin group* vertex group for attached parts, self-collision with a
  small distance (0.001–0.002), bending ~0.5, quality steps ~10, collision quality ~5, let it settle over frames,
  shade smooth after.
- **Soft secondary motion**: a separate simplified physics object, cloth with *pin group* (smoothed weights for
  a soft transition), *internal springs* (tension/compression 0.01, max 0.1) and *pressure* (0.5, scale 300,
  fluid density 100), vertex mass 0.5–1; drive the real mesh with *Surface Deform* restricted by a vertex group;
  a *Smooth Corrective* (repeat ~2) cleans shading.

**Applied**: the scarf is a pinned cloth simulation for renders; in the game the scarf ends, hair strands and
loose straps are spring-bone chains.

## Rigging and animation (CG Geek)

- Bone chain from the hips; IK constraints on forearm/shin with control bones and pole targets (pole angle
  ~180°); hands/feet copy the control bone's rotation; control bones don't deform; parent with automatic
  weights.

**Applied**: the game rig stays FK-baked (the clips are authored procedurally), plus spring chains.

## Lighting, rendering, compositing (Blender Guru, JAEY)

- Shadow is as important as light — place the key so it carves form; the light's size sets shadow softness;
  isolate a rim light so it hits the edge without spilling onto the backdrop; desaturated colored backdrops;
  AO ~0.3–0.4.
- Compositing: *Glare* (fog glow, high quality, threshold), streaks added on top; a tiny lens distortion
  (~0.1, fit) and dispersion if any.

## Surrounding effects (Ryan King, Lightning Boy, CG Geek)

- **Fog/god rays**: a big cube with *Principled Volume* (density ~0.02, slightly blue); density from a 4D noise
  (scale 1, detail 15, roughness 0.8) through a ramp; animate W and location linearly; EEVEE volume resolution
  1:2.
- **Painterly clouds**: shader-to-RGB with ramps on a surface, fake soft light with empties (spherical
  gradients) instead of shadowed lights.
- **VFX trails**: particles emitted from objects parented to the mover (start before frame 1, short lifetime,
  random velocity), glare fog-glow in compositing, motion blur ~0.85 shutter.

**Applied**: showcase scene with volumetric light shafts and drifting fog, falling sakura petals, dust motes,
soda-fizz bubbles from the thrusters and wind streaks; the game gets the particle versions.
