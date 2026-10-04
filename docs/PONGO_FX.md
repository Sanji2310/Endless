# PONGO visual effects

The effects system for every zone, the vehicles, the pickups and the power-ups.

| Piece | File | What it does |
|---|---|---|
| Sprites | `blender/assets/tex_fx.py` | 25 effect sprites painted in the Sakura Line look (flat cel fill, violet shade away from the light, thin ink on solid things). Packed into `pongo.bin` by `tools/build_assets.sh`. The cave sprites (`fx_mote`, `fx_drip`, `fx_splash`, `fx_sparkle`, `fx_rockdust`) come from `tex_cave.py` and are reused. |
| Engine | `src/com/pongo/core/Fx.java` | Pooled particles (camera-facing, tumbling, velocity-stretched, flat on the ground or water), ribbon trails, one-frame sprites, and one preset method per effect. |
| Game driver | `src/com/endlessrush/core/FxLayer.java` | Watches `Game` from frame to frame and fires the effects. No hooks in the simulation are needed. It also owns the zone ambience and the toon screen overlay (speed lines, impact flash). |
| Preview | `tools/fx_clips.sh`, `tools/preview/FxPreview.java` | Short showcase clips through the real Android renderers: `tools/fx_clips.sh [scenes] [pongo.bin dir]` writes `preview/fx/<scene>.mp4`, a GIF and a still. |

## What fires automatically (FxLayer)

- **Running**: jump puff, landing dust ring (bigger the harder she lands), lane-change dust kick with wind streaks, slide dust trail, footfall puffs at high speed, stumble sparks, crash impact (white impact frame, radial lines, debris, puffs, dizzy stars), revive (red-gold burst and a ring of petals).
- **Pickups**: coin glints and gold starburst, Gacha confetti pop, key burst.
- **Power-ups**: a burst in its colour when it starts, then while held: Maneki Magnet gold swirl and sparkle streams on pulled coins; Hayate Rocket wind-swirl flames, smoke, flame ribbons and speed lines; Tobi Boots wind rings at take-off and heel sparkles; Fever Star golden aura with orbiting stars; Kaze Board pod glows and cyan hover ribbons, shards when it breaks.
- **Zones**: Sakura Line petals (fireflies at night); Crystal Cavern grit trickles and crystal chimes (on top of ZoneWorld's motes, drips and glints); Bamboo River bamboo leaves, low mist, ripples, leaping koi; Sky Glide cloud wisps and wind streaks; Express Rooftops wind streaks, pantograph sparks and maple leaves.
- Dust takes the zone's colour, and solid sprites take the zone light, so puffs sit in the cave's dark.

## Calls for the vehicle side

`GameRenderer.fxLayer().fx()` returns the `Fx`. Call these from the ride scene at the vehicle's position (game space: x right, y up, z = -distance). `vzRel` is the velocity along z to give the effect, usually 0 for world-fixed splashes.

| Event | Call |
|---|---|
| Ore cart switching track or braking | `cartSparks(x, y, z, intensity 0..1, speed)` |
| Cart grazes a crystal, bats pass a crystal | `crystalChime(x, y, z, Fx.CYAN or Fx.VIOLET)` |
| Rockfall hazard | `rockfall(x, topY, z, size)` |
| Canoe moving (each frame) | `boatSpray(x, waterY, z, speed, steer -1..1, dt)` |
| Paddle stroke enters the water | `paddleSplash(x, waterY, z, vzRel)` |
| Croc snap, stone drop, landing in water | `splash(x, waterY, z, size 0.5..2, vzRel)` |
| Ripple | `ripple(x, waterY, z, size, vzRel)` |
| Glider wingtips | two `Fx.Trail`s: `push(x, y, z, fx.time)` each frame, then `fx.draw(frame, trail)` |
| Gust hazard | `gust(x, y, z, dir -1/+1, size)` |
| Thermal ring (each frame nearby) | `thermal(x, y, z, dt)` |
| Flying through a cloud | `cloudBurst(x, y, z, vzRel)` |
| Crow or crow flock dodged | `feathers(x, y, z, count)` |
| Steam from a train or vent | `steam(x, y, z, riseSpeed, size)` |

`FxLayer.stage` is called once per frame just before the particles are drawn, so a ride scene can hang its per-frame effects there.

## Rebuilding

```
blender -b -P blender/run.py -- tex_fx build_all   # sprites -> build/tex
blender -b -P blender/run.py -- tex_fx preview     # contact sheet -> renders/design/tex_fx_sheet.png
tools/build_assets.sh                              # everything -> assets/pongo.bin
```

Without the fx sprites in `pongo.bin`, `FxLayer.available()` is false and the game runs without the layer.
