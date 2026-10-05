#!/usr/bin/env bash
# Renders screenshots with the desktop software rasteriser (no device needed).
#   ./preview.sh            -> screenshots into preview/
#   ./preview.sh gif        -> animated gameplay -> preview/gameplay.gif
#   ./preview.sh sim 20     -> 20 headless autopilot runs (level-generator sanity check)
#   ./preview.sh icon       -> regenerate launcher icons into res/
#   ./preview.sh pongo      -> the real Android renderers (world + Pongo toon layer) replayed on WebGL
#                              in headless Chromium -> preview/pongo_*.png (needs node + playwright)
#   ./preview.sh music [ids]  -> the soundtrack rendered to build/music/*.wav, with mix checks (clashing notes,
#                              clipping, brightness); then a scripted run through the music player -> run_demo.wav
#   ./preview.sh zones [dir] -> the same renderers through the tunnel into the Crystal Cavern and back out
#                              -> preview/zone_*.png (pongo.bin from dir, default assets/)
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build/preview
CORE="$(find src/com/endlessrush/core src/com/pongo/core -name '*.java')"
case "${1:-}" in
  music)
    rm -rf build/music-cls && mkdir -p build/music-cls build/music
    javac -nowarn --release 8 -d build/music-cls $(find src/com/pongo/core -name '*.java') \
        tools/preview/MusicSim.java tools/preview/MusicRun.java tools/preview/TuneCheck.java
    shift
    java -cp build/music-cls MusicSim build/music "$@"
    java -cp build/music-cls MusicRun build/music/run_demo.wav build/music-cache
    exit 0 ;;
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
