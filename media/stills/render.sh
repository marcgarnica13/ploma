#!/usr/bin/env bash
# Render the four README stills to assets/stills/<n>.png.
#
# `hyperframes capture` turns a website into editable components in a
# directory. It does not write a single PNG, so this script drives the
# HyperFrames Chrome Headless Shell directly.
#
# Browser provisioning (once, from media/):
#   npx -y hyperframes@0.8.166 doctor          # reports Chrome missing
#   npx -y hyperframes@0.8.166 browser ensure  # downloads Chrome Headless Shell
# The path comes from `npx -y hyperframes@0.8.166 browser path`.
# Set CHROME to skip the lookup.
#
# Each page is shot at 1400 by 820 CSS pixels with device scale 2, then
# ffmpeg scales it down to exactly 1400 px wide. The area filter averages
# each 2 by 2 block, so text stays crisp and there is no ringing to bloat the PNG.
# optipng -o2 runs when it is installed.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
OUT="$HERE/out"
DEST="$ROOT/assets/stills"
mkdir -p "$OUT" "$DEST"

if [ -z "${CHROME:-}" ]; then
  CHROME="$(cd "$ROOT/media" && npx -y hyperframes@0.8.166 browser path 2>/dev/null | tail -n 1)"
fi
if [ ! -x "$CHROME" ]; then
  echo "render.sh: no Chrome at '$CHROME'. Run: npx -y hyperframes@0.8.166 browser ensure" >&2
  exit 1
fi

for n in grill spec write ship; do
  # --no-sandbox: the headless shell runs as an unprivileged user without a setuid sandbox helper.
  "$CHROME" --headless --no-sandbox --disable-gpu --hide-scrollbars \
    --force-device-scale-factor=2 --window-size=1400,820 \
    --virtual-time-budget=8000 --run-all-compositor-stages-before-draw \
    --screenshot="$OUT/$n.png" "file://$HERE/$n.html" >"$OUT/$n.log" 2>&1
  ffmpeg -y -loglevel error -i "$OUT/$n.png" -vf "scale=1400:-1:flags=area" "$DEST/$n.png"
  if command -v optipng >/dev/null 2>&1; then
    optipng -quiet -o2 "$DEST/$n.png"
  fi
  printf '%s %s bytes\n' "$DEST/$n.png" "$(wc -c < "$DEST/$n.png")"
done
