#!/usr/bin/env bash
# Renders screenshots with the desktop software rasteriser (no device needed).
#   ./preview.sh            -> screenshots into preview/
#   ./preview.sh sim 20     -> 20 headless autopilot runs (level-generator sanity check)
#   ./preview.sh icon       -> regenerate launcher icons into res/
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build/preview
javac -nowarn -d build/preview $(find src/com/endlessrush/core -name '*.java') tools/Preview.java
case "${1:-}" in
  sim)  java -cp build/preview Preview build/preview-out sim "${2:-20}" ;;
  gif)  java -cp build/preview Preview preview gif ;;
  icon) java -cp build/preview Preview res icon ;;
  *)    java -cp build/preview Preview preview ;;
esac
