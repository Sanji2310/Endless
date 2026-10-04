#!/usr/bin/env bash
# Desktop previews (no device needed).
#   ./preview.sh sim 20     -> 20 headless autopilot runs (level-generator sanity check)
#   ./preview.sh pongo [dir] -> the real Android renderer (Sakura Line, Pongo, trains, power-ups) replayed on WebGL
#                              in headless Chromium -> preview/pongo_*.png (needs node + playwright;
#                              pongo.bin from dir, default assets/)
#   ./preview.sh sakura [dir] -> Sakura Line art in game: trains, track obstacles, every power-up, the chase
#                              -> preview/sakura_*.png (pongo.bin from dir, default assets/)
#   ./preview.sh zones [dir] -> the same renderers through the tunnel into the Crystal Cavern and back out
#                              -> preview/zone_*.png (pongo.bin from dir, default assets/)
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build/preview
CORE="$(find src/com/endlessrush/core src/com/pongo/core -name '*.java')"
case "${1:-}" in
  pongo|zones|sakura)
    rm -rf build/preview-gl && mkdir -p build/preview-gl
    javac -nowarn -d build/preview-gl $CORE src/com/endlessrush/app/GameRenderer.java src/com/pongo/app/GLRenderer.java \
        $(find tools/preview/stubs -name '*.java') tools/Preview.java tools/preview/PongoPreview.java tools/preview/SakuraPreview.java
    if [ "$1" = sakura ]; then
      java -Dpongo.assets="${2:-assets}" -cp build/preview-gl SakuraPreview build/preview-gl/gles.bin 540 960
    elif [ "$1" = zones ]; then
      java -Dpongo.assets="${2:-assets}" -cp build/preview-gl PongoPreview build/preview-gl/gles.bin 540 960 zones
    else
      java -Dpongo.assets="${2:-assets}" -cp build/preview-gl PongoPreview build/preview-gl/gles.bin 540 960
    fi
    node tools/web/replay.mjs build/preview-gl/gles.bin preview 540 960
    exit 0 ;;
esac
case "${1:-}" in
  sim)
    javac -nowarn -d build/preview $CORE tools/Preview.java
    java -cp build/preview Preview sim "${2:-20}" ;;
  *)
    echo "usage: ./preview.sh sim [runs] | pongo [dir] | sakura [dir] | zones [dir]" >&2
    exit 1 ;;
esac
