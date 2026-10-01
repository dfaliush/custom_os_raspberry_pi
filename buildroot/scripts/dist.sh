#!/usr/bin/env bash
#
# dist.sh: release artifacts from a finished build (WSL, after build.sh).
#
#   ~/br/dist/rpi5os-buildroot-v<VERSION>-sdcard.img.xz
#   ~/br/dist/buildroot.config            full .config
#   ~/br/dist/legal-info-manifest.csv     packages, versions, licenses (make legal-info)
#   ~/br/dist/SHA256SUMS

set -euo pipefail

PATH="$(printf '%s' "$PATH" | tr ':' '\n' | grep -v '^/mnt/' | paste -sd:)"
export PATH

SRC="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${RPI5OS_WORK:-$HOME/br}"
OUT="$WORK/output"
DIST="$WORK/dist"
VERSION="$(cat "$SRC/VERSION")"
NAME="rpi5os-buildroot-v${VERSION}"

[ -f "$OUT/images/sdcard.img" ] || { echo "немає $OUT/images/sdcard.img: спершу build.sh" >&2; exit 1; }

rm -rf "$DIST"
mkdir -p "$DIST"

xz -T0 -9 -c "$OUT/images/sdcard.img" > "$DIST/${NAME}-sdcard.img.xz"
cp "$OUT/.config" "$DIST/buildroot.config"
make -C "$WORK/buildroot" O="$OUT" legal-info >/dev/null
cp "$OUT/legal-info/manifest.csv" "$DIST/legal-info-manifest.csv"

( cd "$DIST" && sha256sum -- * > SHA256SUMS )
ls -lh "$DIST"
cat "$DIST/SHA256SUMS"
