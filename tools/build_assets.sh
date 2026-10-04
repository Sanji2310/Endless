#!/usr/bin/env bash
# Rebuilds assets/pongo.bin (the toon renderer's meshes, skeleton, clips and texture atlas) from the
# Blender scripts in blender/. Needs Blender 4.0 with numpy, and EGL for the painted face textures:
#   sudo apt-get install blender python3-numpy libegl1 libgl1-mesa-dri
#   tools/build_assets.sh                      -> assets/pongo.bin
#   tools/build_assets.sh build/x/pongo.bin    -> somewhere else (e.g. a local preview build)
set -euo pipefail
OUT="${1:-assets/pongo.bin}"
cd "$(dirname "$0")/.."
BLENDER="${BLENDER:-blender}"
rm -rf build/models build/tex
run() { echo "==> blender: $*"; "$BLENDER" -b -P blender/run.py -- "$@" > "build/blender_$1_$2.log" 2>&1 || { tail -30 "build/blender_$1_$2.log"; exit 1; }; }
mkdir -p build
run pongo_g build_face_art      # eyes, mouth, blush decals -> build/tex
run pongo_g export_pongo_g      # Pongo LOD0/LOD1, 30 bones, 15 clips -> build/models (takes a few minutes)
run pickups export_coin         # Mon coin LOD0/LOD1 + test floor
run tex_city build_all          # Sakura Line tiles the tunnel set piece uses (track, cutting, hill)
run tex_cave build_all          # cave tiles and the effect sprites (fx_*)
run cave export_cave            # Crystal Cavern kit: track, shells, deco, props, frames, parting, obstacles
run tunnel export_transition    # tunnel set piece, city_track and the zone title cards
run signs build_all             # window, shopfront, konbini and vending textures, blob shadow
run sakura_line export_world    # Sakura Line pieces: sides, wires, lots, gantry, poles, houses, sakura, crossing
run sakura_line export_density  # roadside clutter strips, far town rows, horizon hills
run sakura_line export_chasers  # Inspector Daigo and Kuro (rigid parts animated in SakuraWorld)
run sakura_line fx_sprites      # run effects: speed lines, petals, puffs, rings, glow, stars, impact
run trains export_trains        # commuter + express cars, ramp, track-works barrier, barricade, slide gantry
run powerups export_powerups    # power-ups, pickups, Kaze Board, worn rocket pack, pickup halo
echo "==> AssetBuilder"
mkdir -p build/assetbuilder
javac -nowarn -d build/assetbuilder tools/assetbuilder/AssetBuilder.java
java -cp build/assetbuilder AssetBuilder build/models build/tex "$OUT"
