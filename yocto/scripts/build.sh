#!/usr/bin/env bash
#
# Build rpi5os with Yocto in WSL / Linux, from scratch to the .wic image.
# From the repo root:
#
#   wsl -d Ubuntu -- bash yocto/scripts/build.sh
#
# Work dir (layers, downloads, sstate, build) is RPI5OS_YOCTO_WORK, ~/yocto by
# default. It must be on ext4, like the Buildroot one. The first build takes
# hours and ~100 GB; later ones reuse sstate.

set -euo pipefail

# Layers pinned to exact revisions: same input, same image.
OE_REV=yocto-6.0.3                                  # openembedded-core and bitbake
RPI_REV=f62c67921474370829d24a4fa01ef88543f3906b    # meta-raspberrypi, branch wrynose

SRC="$(cd "$(dirname "$0")/.." && pwd)"             # yocto/ in the repo
WORK="${RPI5OS_YOCTO_WORK:-$HOME/yocto}"
LAYERS="$WORK/layers"
BUILD="$WORK/build"

case "$WORK" in
	/mnt/*) echo "RPI5OS_YOCTO_WORK=$WORK лежить на диску Windows; потрібна ext4 (наприклад ~/yocto)" >&2; exit 1 ;;
esac

# Same reasons as in buildroot/scripts/build.sh: no Windows dirs (with spaces)
# in PATH.
PATH="$(printf '%s' "$PATH" | tr ':' '\n' | grep -v '^/mnt/' | paste -sd:)"
export PATH

# bitbake insists on en_US.UTF-8. Without it installed system-wide (that needs
# root: locale-gen), build it into the work dir and point glibc there.
if ! locale -a 2>/dev/null | grep -qix 'en_US.utf8'; then
	if [ ! -d "$WORK/locale/en_US.UTF-8" ]; then
		mkdir -p "$WORK/locale"
		localedef -i en_US -f UTF-8 "$WORK/locale/en_US.UTF-8"
	fi
	export LOCPATH="$WORK/locale"
	export BB_ENV_PASSTHROUGH_ADDITIONS="${BB_ENV_PASSTHROUGH_ADDITIONS:-} LOCPATH"
fi
export LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8

checkout() {
	local dir="$1" url="$2" rev="$3"
	[ -d "$dir/.git" ] || git clone -q "$url" "$dir"
	if ! git -C "$dir" rev-parse -q --verify "$rev^{commit}" >/dev/null; then
		git -C "$dir" fetch -q --tags origin
	fi
	git -C "$dir" checkout -q "$rev"
	echo "$(basename "$dir") @ $(git -C "$dir" rev-parse --short HEAD)"
}

mkdir -p "$LAYERS"
checkout "$LAYERS/bitbake" https://git.openembedded.org/bitbake "$OE_REV"
checkout "$LAYERS/openembedded-core" https://git.openembedded.org/openembedded-core "$OE_REV"
checkout "$LAYERS/meta-raspberrypi" https://git.yoctoproject.org/meta-raspberrypi "$RPI_REV"

# Our layer copied to ext4 with explicit modes: drvfs reports arbitrary ones.
rsync -a --delete --no-perms --chmod=D755,F644 "$SRC/meta-rpi5os/" "$LAYERS/meta-rpi5os/"

mkdir -p "$BUILD/conf"
cat > "$BUILD/conf/bblayers.conf" <<EOF
BBPATH = "\${TOPDIR}"
BBFILES ?= ""
BBLAYERS = " \\
    $LAYERS/openembedded-core/meta \\
    $LAYERS/meta-raspberrypi \\
    $LAYERS/meta-rpi5os \\
"
EOF
cat > "$BUILD/conf/local.conf" <<EOF
MACHINE = "raspberrypi5"
DISTRO = "rpi5os"
DL_DIR = "$WORK/downloads"
SSTATE_DIR = "$WORK/sstate"
INHERIT += "rm_work"
# Keep the image's rootfs in tmp/work for inspection after the build.
RM_WORK_EXCLUDE += "rpi5os-image"
CONF_VERSION = "2"
EOF

# oe-init-build-env keeps our conf/ and cds into the build dir.
export BITBAKEDIR="$LAYERS/bitbake"
set +u
# shellcheck disable=SC1091
. "$LAYERS/openembedded-core/oe-init-build-env" "$BUILD" >/dev/null
set -u

bitbake rpi5os-image

DEPLOY="$BUILD/tmp/deploy/images/raspberrypi5"
ls -lhL "$DEPLOY/rpi5os-image-raspberrypi5.rootfs.wic"
sha256sum "$DEPLOY/rpi5os-image-raspberrypi5.rootfs.wic"
