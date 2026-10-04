#!/usr/bin/env bash
# Renders screenshots with the desktop software rasteriser (no device needed).
#   ./preview.sh            -> screenshots into preview/
#   ./preview.sh gif        -> animated gameplay -> preview/gameplay.gif
#   ./preview.sh sim 20     -> 20 headless autopilot runs (level-generator sanity check)
#   ./preview.sh icon       -> regenerate launcher icons into res/
#   ./preview.sh pongo      -> the real Android renderers (world + Pongo toon layer) replayed on WebGL
#                              in headless Chromium -> preview/pongo_*.png (needs node + playwright)
#   ./preview.sh zones [dir] -> the same renderers through the tunnel into the Crystal Cavern and back out
#                              -> preview/zone_*.png (pongo.bin from dir, default assets/)
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build/preview
CORE="$(find src/com/endlessrush/core src/com/pongo/core -name '*.java')"
case "${1:-}" in
  pongo|zones)
    rm -rf build/preview-gl && mkdir -p build/preview-gl
    javac -nowarn -d build/preview-gl $CORE src/com/endlessrush/app/GameRenderer.java src/com/pongo/app/GLRenderer.java \
        $(find tools/preview/stubs -name '*.java') tools/Preview.java tools/preview/PongoPreview.java
    if [ "$1" = zones ]; then
      java -Dpongo.assets="${2:-assets}" -cp build/preview-gl PongoPreview build/preview-gl/gles.bin 540 960 zones
    else
      java -cp build/preview-gl PongoPreview build/preview-gl/gles.bin 540 960
    fi
    node tools/web/replay.mjs build/preview-gl/gles.bin preview 540 960
    exit 0 ;;
esac
javac -nowarn -d build/preview $CORE tools/Preview.java
case "${1:-}" in
  sim)  java -cp build/preview Preview build/preview-out sim "${2:-20}" ;;
  gif)  java -cp build/preview Preview preview gif ;;
  icon) java -cp build/preview Preview res icon ;;
  *)    java -cp build/preview Preview preview ;;
esac
