# PONGO — Design Bible

An anime-styled 3D endless runner. You play **Pongo**, a freerunner dashing along a sakura-lined railway who ends up in caves, rivers, the sky and the roofs of express trains. The art direction is cel-shaded anime: clean shapes, ink outlines, two-tone shadows tinted by the time of day, painted skies, bloom, and a lot of motion effects.

---

## 1. Visual style

| Element | Approach |
|---|---|
| Shading | Cel/toon: a crisp light band plus a tinted shadow colour (cool violet by day, deep blue at night). Rim light on characters. Stylised specular "sparkle" bands on hair, metal and water. |
| Outlines | Inverted-hull ink lines on characters, pickups, obstacles and props. The width stays constant in screen space and is set per vertex, so thin details get thinner lines. |
| Shadows | Real-time sun shadow map with a hard edge and a slight AA blur, in the same tinted colour as the cel shadow band. Blob shadow on LOW quality. |
| Sky | Painted gradient per time of day, anime cumulus clouds with rim light, sun glare, moon and stars at night. |
| Post | Bloom on sun, lanterns, crystals and emissive windows. Anime speed lines at high speed. White impact frame when you crash. |
| Textures | Hand-painted look: soft gradients, simple stroke patterns, Japanese signage (kana/kanji), train liveries, plaid and stripes on clothing, painted eyes. |
| Palette | Saturated but soft: sakura pink, sky cyan, leaf green, sunset orange, night indigo. |

## 2. Characters

| Name | Role | Look | Unlock |
|---|---|---|---|
| **Pongo** | Main hero | 16, spiky navy hair with an ahoge, goggles pushed up, long **orange scarf** that streams in the wind (simulated), white-and-blue hoodie with a "P" patch, black cargo shorts, red high-tops | Free |
| **Hana Sakurai** | Skater | Pink twin-tails with cherry clips (simulated), sailor-collar top, red plaid skirt over leggings, knee pads, white sneakers | 6,000 |
| **Kaito Kurogane** | Parkour ninja | Black hair in a short ponytail, navy mask scarf, dark jacket with crimson trims, arm wraps, split-toe tabi shoes | 12,000 |
| **Yuki Shirane** | Gamer girl | White bob with a blue streak, oversized **cat-ear hoodie** (light blue), big headphones, shorts, striped socks | 20,000 |
| **Tetsu-9** | Retro mecha | Small round robot runner: visor eyes, antenna, jet heels, orange-and-white armour plates | 40,000 |
| **Inspector Daigo** | Chaser | Burly station inspector: navy uniform with brass buttons, peaked cap, huge moustache, whistle | — |
| **Kuro** | Chaser's dog | Black-and-tan shiba inu with a curled tail and a red collar with a bell | — |

Ambient creatures: **Karasu crows** (a flock with flapping wings that perches on wires and scatters), **cave bats**, **koi** that leap from the river, **white herons** in the sky zone.

## 3. Power-ups, currency and equipment

| Name | Type | What it does | Look |
|---|---|---|---|
| **Mon Coins** | Currency | Collect them; spend them in the shop | Gold coin with a square hole and engraved rim |
| **Maneki Magnet** | Power-up | Pulls every nearby coin to you | A golden lucky cat (maneki-neko) floats beside Pongo waving its paw |
| **Hayate Rocket** | Power-up | Fly high over everything and collect sky coins | Red twin-thruster rocket pack with wind-swirl flames |
| **Tobi Boots** | Power-up | Super jumps, high enough to reach train roofs | Springy boots with little wings; wind rings when you jump |
| **Fever Star** | Power-up | Double score. "FEVER!" aura and sparkles | Spinning golden star with a "2X" |
| **Gacha Capsule** | Mystery box | Random coins, Omamori or boards | Two-tone capsule-toy ball that pops open |
| **Omamori** | Revive charm | Spend them to continue after a crash (the cost doubles each time) | Red silk charm bag with gold knot |
| **Kaze Board** | Hoverboard | Double-tap to use. Lasts 30 s and absorbs one crash | Sleek board with wind fins and glowing hover pods |
| **Hotaru Lamp** | Zone gear | Headlamp auto-equipped in the cave, lights the way | Brass headlamp with a warm beam |
| **Nami Board** | Zone gear | Surfboard for the Bamboo River | Wave-painted surfboard |
| **Tsubasa Glider** | Zone gear | Paraglider for Sky Glide | Rainbow canopy with cell ribs, lines and harness |

## 4. Zones (they change the further you run)

The run cycles through **five zones**. Each lasts about 1,400 m. Between zones there's a short **set-piece transition** during which you can't be hurt. The zone's title card slides in, a musical sting plays and the ambient effects crossfade.

| # | Zone | Mode | Obstacles | Scenery & effects |
|---|---|---|---|---|
| 1 | **Sakura Line** 桜線 | Run on rails | Commuter trains, oncoming **bullet trains**, ramps, crossing barriers (jump), sign gantries (roll), buffer stops (dodge) | Overhead catenary wires, utility poles with crows, tiled-roof houses, konbini, vending machines, sakura trees shedding **falling petals**, level crossings that go *kan-kan-kan*, a torii shrine, distant mountains |
| 2 | **Crystal Cavern** 水晶洞窟 | Run on mine rails | Ore-cart trains, wooden ramps, rock piles (jump), timber beams (roll), boulders/crystal clusters (dodge) | Glowing crystals, stalactites, lanterns, mine timbers, bats, water drips, dust motes, echoing sounds, **Hotaru Lamp** light pool |
| 3 | **Bamboo River** 竹の川 | Surf down a river | Floating logs (jump), bamboo bridges/branches (duck), rocks & whirlpools (dodge), waterfall drops (auto big-air) | Bamboo forest, stone lanterns, torii in the water, **koi jumping**, spray trail, splashes, mist, rainbows |
| 4 | **Sky Glide** 空の道 | Paraglide | Swipe up to climb, down to dive: kites (climb), wind-chime cables (dive), balloons, rock spires, crow flocks (dodge) | Valley panorama: rice terraces, villages, sea, huge anime clouds, herons, wind streaks, cloud puffs |
| 5 | **Express Rooftops** 特急の屋根 | Run on the roofs of moving trains | Roof units (jump), gaps between cars (jump), catenary gantries & low bridges (roll), cargo stacks (dodge) | Countryside flying past: rice paddies, farmhouses, rivers, a Fuji-like mountain, wind streaks, sparks from the pantographs |

Transitions: Sakura Line → tunnel mouth → **Cavern** → underground river, board drops in → **Bamboo River** → waterfall off a cliff, glider opens → **Sky Glide** → land on a passing express → **Express Rooftops** → the train pulls into the city, hop down → **Sakura Line**.

## 5. Times of day

Time moves on as you run (about every 1,100 m) and blends smoothly between five phases. When a new phase starts, a small title card appears and its signature effects start:

| Phase | Light | Signature effects & sound |
|---|---|---|
| **Asa** (Dawn) 朝 | Pink-gold low sun, lilac shadows, morning mist | Birdsong, mist layers, dew sparkles |
| **Hiru** (Day) 昼 | Bright high sun, cyan sky, crisp shadows | Cicadas, big white clouds |
| **Yūyake** (Sunset) 夕焼け | Orange sun, long shadows, crimson clouds | **Crow flocks crossing**, temple bell, heavy bloom |
| **Tasogare** (Dusk) 黄昏 | Purple-blue sky, street lamps & windows switch on | Lamps flicker on one by one, first fireflies |
| **Yoru** (Night) 夜 | Indigo, moonlight, glowing windows, lanterns, neon | Stars, moon, fireflies, crickets |

## 6. Effects

- **Falling leaves and petals**: sakura petals in the city, bamboo leaves by the river, maple leaves at sunset. They tumble, flutter and swirl behind you.
- **Crows**: a boids flock perches, takes off, circles and scatters when you run past.
- **Trails**: Pongo's scarf, the Kaze Board's hover ribbons, Hayate Rocket flame ribbons, glider wingtip vortices, the board's water spray.
- **Speed lines** at high speed and during boosts. An **impact frame** (white flash with radial lines) when you crash.
- Dust puffs on landing and stumbling, sparks when you graze a train, coin glints and pickup starbursts, the Fever aura, the magnet's pull swirl, splash crowns, mist, cave drips, fireflies, cloud wisps.

## 7. Sound design

Every action has its own layered, synthesized sound effect:

- **Movement**: footsteps that match the surface (gravel, wood, metal, rock, roof), a whoosh when you switch lanes, a jump with a spring and air, a landing thud, a roll swish, a fast-drop slam.
- **Collecting**: a coin chime whose pitch climbs with your streak, a power-up sparkle, "nyan" for the Maneki Magnet, a spring boing for Tobi Boots, the Hayate Rocket ignition and roar, a Fever fanfare, the Gacha pop and reveal, a bell for the Omamori.
- **Hazards**: a stumble, a crash with debris, Daigo's whistle, Kuro barking, the bullet-train horn and a Doppler pass-by, the level-crossing bell, the Kaze Board's hum and break.
- **Zone ambience**: city wind with crows, cave drips and echo, the river's rush and splashes, sky wind and cloth flutter, a train roof with wind and rail clatter.
- **Stings**: new zone, new time of day, mission complete, multiplier up, high score, and a 3-2-1-GO countdown.
- **Music**: an anime-style loop for each zone and one for the menu.

## 8. Controls

These work the same in every zone: swipe left/right to change lanes, swipe up to jump (climb on the glider), swipe down to roll (duck on the board, dive on the glider), double-tap for the Kaze Board. Arrow keys and WASD also work.
