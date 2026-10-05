#!/usr/bin/env bash
# Tiles renders/audit/<asset>_{front,side,back,high,close}.png into renders/audit/sheet_<asset>.png (labelled).
set -euo pipefail
cd "$(dirname "$0")/.."
for f in renders/audit/*_front.png; do
  a=$(basename "$f" _front.png)
  [ -f "renders/audit/${a}_close.png" ] || continue
  in=()
  for v in front side back high close; do in+=(-i "renders/audit/${a}_${v}.png"); done
  ffmpeg -loglevel error -y "${in[@]}" -filter_complex \
    "[0]drawtext=text='${a} front':x=10:y=10:fontsize=20:fontcolor=white:borderw=2[a];[1]drawtext=text='side':x=10:y=10:fontsize=20:fontcolor=white:borderw=2[b];[2]drawtext=text='back':x=10:y=10:fontsize=20:fontcolor=white:borderw=2[c];[3]drawtext=text='high':x=10:y=10:fontsize=20:fontcolor=white:borderw=2[d];[4]drawtext=text='close':x=10:y=10:fontsize=20:fontcolor=white:borderw=2[e];[a][b][c][d][e]hstack=inputs=5" \
    "renders/audit/sheet_${a}.png"
done
