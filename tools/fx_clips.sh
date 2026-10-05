#!/usr/bin/env bash
# Effect showcase clips through the real Android renderers (tools/preview/FxPreview.java), replayed in headless
# Chromium, then encoded with ffmpeg:
#   tools/fx_clips.sh [scenes] [pongo.bin dir] [width height]   -> preview/fx/<scene>.mp4, .gif and a mid-clip still
#   scenes: comma list of run,coins,magnet,fever,boots,rocket,board,crash,cave,river,sky,rooftops (default all)
set -euo pipefail
cd "$(dirname "$0")/.."
SCENES="${1:-all}"; ASSETS="${2:-assets}"; W="${3:-432}"; H="${4:-768}"
OUT=preview/fx
rm -rf build/preview-fx && mkdir -p build/preview-fx build/preview-fx/frames "$OUT"
javac -nowarn -d build/preview-fx $(find src/com/endlessrush/core src/com/pongo/core -name '*.java') \
    src/com/endlessrush/app/GameRenderer.java src/com/pongo/app/GLRenderer.java \
    $(find tools/preview/stubs -name '*.java') tools/Preview.java tools/preview/FxPreview.java
[ "$SCENES" = all ] && SCENES=run,coins,magnet,fever,boots,rocket,board,crash,cave,river,sky,rooftops
# one recording per scene (a long stream of frames is too much for one headless page), JOBS at a time
export ASSETS W H
# each scene in parts of 36 frames (FxPreview -Dfx.part), up to 3 parts
for s in ${SCENES//,/ }; do for p in 0 1 2; do echo "$s $p"; done; done | xargs -P "${JOBS:-3}" -L1 sh -c '
  java -Dpongo.assets="$ASSETS" -Dfx.part=$1 -cp build/preview-fx FxPreview build/preview-fx/$0_$1.bin "$W" "$H" $0 > /dev/null &&
  node tools/web/replay.mjs build/preview-fx/$0_$1.bin build/preview-fx/frames "$W" "$H" > /dev/null &&
  rm -f build/preview-fx/$0_$1.bin && echo "rendered $0 part $1"'
for first in build/preview-fx/frames/*_000.png; do
  name="$(basename "$first" _000.png)"
  ffmpeg -loglevel error -y -framerate 30 -i "build/preview-fx/frames/${name}_%03d.png" \
      -c:v libx264 -pix_fmt yuv420p -crf 20 "$OUT/$name.mp4"
  ffmpeg -loglevel error -y -i "$OUT/$name.mp4" \
      -vf "fps=20,scale=360:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=160[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" \
      "$OUT/$name.gif"
  n=$(ls build/preview-fx/frames/${name}_*.png | wc -l)
  cp "build/preview-fx/frames/${name}_$(printf %03d $((n / 2))).png" "$OUT/${name}_still.png"
  echo "clip $OUT/$name.mp4 ($n frames)"
done
