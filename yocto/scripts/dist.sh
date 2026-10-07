#!/usr/bin/env bash
#
# dist.sh: release artifacts from a finished build (WSL, after build.sh).
#
#   ~/yocto/dist/rpi5os-yocto-v<VERSION>-sdcard.img.xz
#   ~/yocto/dist/layers.txt              layer revisions and the generated local.conf
#   ~/yocto/dist/license.manifest        packages, versions, licenses
#   ~/yocto/dist/rpi5os-yocto-v<VERSION>.spdx.json   SBOM (create-spdx)
#   ~/yocto/dist/SHA256SUMS

set -euo pipefail

PATH="$(printf '%s' "$PATH" | tr ':' '\n' | grep -v '^/mnt/' | paste -sd:)"
export PATH

SRC="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${RPI5OS_YOCTO_WORK:-$HOME/yocto}"
BUILD="$WORK/build"
DIST="$WORK/dist"
DEPLOY="$BUILD/tmp/deploy/images/raspberrypi5"
IMG="$DEPLOY/rpi5os-image-raspberrypi5.rootfs.wic"
VERSION="$(sed -n 's/^DISTRO_VERSION = "\(.*\)"/\1/p' "$SRC/meta-rpi5os/conf/distro/rpi5os.conf")"
NAME="rpi5os-yocto-v${VERSION}"

[ -n "$VERSION" ] || { echo "dist: не знайшов DISTRO_VERSION у rpi5os.conf" >&2; exit 1; }
[ -f "$IMG" ] || { echo "немає $IMG: спершу build.sh" >&2; exit 1; }
# The builder's home path carries the user name; the .xz below can't be grepped.
if grep -qaF -- "$HOME/" "$IMG"; then
	echo "dist: у $(basename "$IMG") є шлях $HOME/" >&2
	exit 1
fi

rm -rf "$DIST"
mkdir -p "$DIST"

xz -T0 -9 -c "$IMG" > "$DIST/${NAME}-sdcard.img.xz"

{
	for l in bitbake openembedded-core meta-raspberrypi meta-openembedded meta-ros; do
		printf '%-20s %s %s\n' "$l" "$(git -C "$WORK/layers/$l" rev-parse HEAD)" \
			"$(git -C "$WORK/layers/$l" describe --tags --always 2>/dev/null)"
	done
	echo
	echo "--- conf/local.conf"
	cat "$BUILD/conf/local.conf"
} | sed "s|$HOME/|~/|g" > "$DIST/layers.txt"

manifest="$(find "$BUILD/tmp/deploy/licenses" -path '*rpi5os-image*' -name license.manifest | head -n1)"
[ -n "$manifest" ] || { echo "dist: немає license.manifest" >&2; exit 1; }
sed "s|$HOME/|~/|g" "$manifest" > "$DIST/license.manifest"

spdx="$DEPLOY/rpi5os-image-raspberrypi5.rootfs.spdx.json"
if [ -f "$spdx" ]; then
	sed "s|$HOME/|~/|g" "$spdx" > "$DIST/${NAME}.spdx.json"
fi

if grep -lF -- "$HOME/" "$DIST"/layers.txt "$DIST"/license.manifest "$DIST"/*.spdx.json 2>/dev/null; then
	echo "dist: в артефактах лишився шлях $HOME/" >&2
	exit 1
fi

( cd "$DIST" && sha256sum -- * > SHA256SUMS )
ls -lh "$DIST"
cat "$DIST/SHA256SUMS"
