#!/usr/bin/env bash
# Rebuilds assets/pongo.bin (the toon renderer's meshes, skeleton, clips and texture atlas) from the
# Blender scripts in blender/. Needs Blender 4.0 with numpy, and EGL for the painted face textures:
#   sudo apt-get install blender python3-numpy libegl1 libgl1-mesa-dri
#   tools/build_assets.sh
set -euo pipefail
cd "$(dirname "$0")/.."
BLENDER="${BLENDER:-blender}"
rm -rf build/models build/tex
run() { echo "==> blender: $*"; "$BLENDER" -b -P blender/run.py -- "$@" > "build/blender_$1_$2.log" 2>&1 || { tail -30 "build/blender_$1_$2.log"; exit 1; }; }
mkdir -p build
run pongo_g build_face_art      # eyes, mouth, blush decals -> build/tex
run pongo_g export_pongo_g      # Pongo LOD0/LOD1, 30 bones, 15 clips -> build/models (takes a few minutes)
run pickups export_coin         # Mon coin LOD0/LOD1 + test floor
echo "==> AssetBuilder"
mkdir -p build/assetbuilder
javac -nowarn -d build/assetbuilder tools/assetbuilder/AssetBuilder.java
java -cp build/assetbuilder AssetBuilder build/models build/tex assets/pongo.bin
