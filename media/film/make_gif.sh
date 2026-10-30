#!/usr/bin/env bash
# Turn the rendered film into the README GIF, the still and (if small enough) the MP4.
# Run after: npx hyperframes render -c compositions/main.html --fps 30 --output out/ploma-hero.mp4
# The still is taken at STILL_AT seconds: the moment the reveal has landed on 27.4%
# while the compile result is still on screen.
set -euo pipefail
cd "$(dirname "$0")"
DEST=../../assets/film
FPS=${FPS:-15}
WIDTH=${WIDTH:-1000}
STILL_AT=${STILL_AT:-17.7}
mkdir -p "$DEST"

ffmpeg -y -loglevel error -i out/ploma-hero.mp4 \
  -vf "fps=$FPS,scale=$WIDTH:-1:flags=lanczos,palettegen=max_colors=192" out/palette.png
ffmpeg -y -loglevel error -i out/ploma-hero.mp4 -i out/palette.png \
  -lavfi "fps=$FPS,scale=$WIDTH:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5" \
  "$DEST/ploma-hero.gif"
ffmpeg -y -loglevel error -ss "$STILL_AT" -i out/ploma-hero.mp4 -frames:v 1 "$DEST/ploma-hero.png"

if [ "$(wc -c < out/ploma-hero.mp4)" -le 4000000 ]; then
  cp out/ploma-hero.mp4 "$DEST/"
else
  rm -f "$DEST/ploma-hero.mp4"
  echo "make_gif.sh: out/ploma-hero.mp4 is over 4 MB, not copied" >&2
fi

for f in "$DEST"/ploma-hero.*; do printf '%s %s bytes\n' "$f" "$(wc -c < "$f")"; done
gif=$(wc -c < "$DEST/ploma-hero.gif")
if [ "$gif" -gt 6000000 ]; then
  echo "make_gif.sh: GIF is $gif bytes, over 6 MB. Retry with FPS=12, then WIDTH=900." >&2
  exit 1
fi
