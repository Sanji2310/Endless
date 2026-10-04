#!/usr/bin/env bash
# Shader lab: every toon material and the times of day in the real renderer (GLRenderer replayed on WebGL), on a
# small test set (blender/assets/shader_lab.py) next to Pongo and the cave crystals -> preview/lab_*.png
# Needs the models of a previous tools/build_assets.sh run in build/models (Pongo, coin, cave kit).
#   tools/shader_lab.sh            -> export the lab set, build build/lab/pongo.bin, render
#   tools/shader_lab.sh --no-export -> reuse build/lab/pongo.bin (shader changes only)
set -euo pipefail
cd "$(dirname "$0")/.."
BLENDER="${BLENDER:-blender}"
mkdir -p build/lab
if [ "${1:-}" != "--no-export" ]; then
  "$BLENDER" -b -P blender/run.py -- shader_lab export_lab > build/blender_shader_lab.log 2>&1 || { tail -30 build/blender_shader_lab.log; exit 1; }
  mkdir -p build/assetbuilder
  javac -nowarn -d build/assetbuilder tools/assetbuilder/AssetBuilder.java
  java -cp build/assetbuilder AssetBuilder build/models build/tex build/lab/pongo.bin
fi
rm -rf build/lab/classes && mkdir -p build/lab/classes
javac -nowarn -d build/lab/classes $(find src/com/pongo/core -name '*.java') src/com/pongo/app/GLRenderer.java \
    $(find tools/preview/stubs -name '*.java') tools/preview/ShaderLab.java
java -cp build/lab/classes ShaderLab build/lab/pongo.bin build/lab/gles.bin 540 960
node tools/web/replay.mjs build/lab/gles.bin preview 540 960
