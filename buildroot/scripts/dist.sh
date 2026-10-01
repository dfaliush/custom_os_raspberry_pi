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
# The builder's home path carries the user name; the .xz below can't be grepped.
if grep -qaF -- "$HOME/" "$OUT/images/sdcard.img"; then
	echo "dist: у sdcard.img є шлях $HOME/" >&2
	exit 1
fi

rm -rf "$DIST"
mkdir -p "$DIST"

xz -T0 -9 -c "$OUT/images/sdcard.img" > "$DIST/${NAME}-sdcard.img.xz"
# .config holds absolute paths under the builder's home, which carry the user name.
sed "s|$HOME/|~/|g" "$OUT/.config" > "$DIST/buildroot.config"
make -C "$WORK/buildroot" O="$OUT" legal-info >/dev/null
sed "s|$HOME/|~/|g" "$OUT/legal-info/manifest.csv" > "$DIST/legal-info-manifest.csv"

if grep -lF -- "$HOME/" "$DIST/buildroot.config" "$DIST/legal-info-manifest.csv"; then
	echo "dist: в артефактах лишився шлях $HOME/" >&2
	exit 1
fi

( cd "$DIST" && sha256sum -- * > SHA256SUMS )
ls -lh "$DIST"
cat "$DIST/SHA256SUMS"
