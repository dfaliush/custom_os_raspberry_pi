#!/usr/bin/env bash
#
# Build rpi5os with Yocto in WSL / Linux, from scratch to the .wic image.
# From the repo root:
#
#   wsl -d Ubuntu -- bash yocto/scripts/build.sh              # the image
#   wsl -d Ubuntu -- bash yocto/scripts/build.sh -p           # parse only
#   wsl -d Ubuntu -- bash yocto/scripts/build.sh counter-pkg  # one recipe
#
# Work dir (layers, downloads, sstate, build) is RPI5OS_YOCTO_WORK, ~/yocto by
# default. It must be on ext4, like the Buildroot one. The first build takes
# hours and ~100 GB; later ones reuse sstate.

set -euo pipefail

# Layers pinned to exact revisions: same input, same image.
OE_REV=yocto-6.0.3                                  # openembedded-core and bitbake
RPI_REV=f62c67921474370829d24a4fa01ef88543f3906b    # meta-raspberrypi, branch wrynose

SRC="$(cd "$(dirname "$0")/.." && pwd)"             # yocto/ in the repo
REPO="$(cd "$SRC/.." && pwd)"

# meta-openembedded and meta-ros (ROS 2 Jazzy) are submodules in yocto/layers/;
# their pinned commits come from the git index, so `git submodule update` on
# Windows is not needed: the clones below land on ext4.
submodule_rev() {
	git -C "$REPO" ls-files -s "yocto/layers/$1" | awk '{print $2}'
}
OE_META_REV="$(submodule_rev meta-openembedded)"
ROS_REV="$(submodule_rev meta-ros)"
[ -n "$OE_META_REV" ] && [ -n "$ROS_REV" ] || { echo "немає submodules у yocto/layers (git submodule add ...)" >&2; exit 1; }
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
checkout "$LAYERS/meta-openembedded" https://github.com/openembedded/meta-openembedded.git "$OE_META_REV"
checkout "$LAYERS/meta-ros" https://github.com/ros/meta-ros.git "$ROS_REV"

# Our layers and the ROS 2 sources copied to ext4 with explicit modes: drvfs
# reports arbitrary ones.
rsync -a --delete --no-perms --chmod=D755,F644 "$SRC/meta-rpi5os/" "$LAYERS/meta-rpi5os/"
rsync -a --delete --no-perms --chmod=D755,F644 "$SRC/meta-rpi5os-ros/" "$LAYERS/meta-rpi5os-ros/"
rsync -a --delete --no-perms --chmod=D755,F644 --exclude __pycache__ "$REPO/ros2/" "$WORK/ros2/"

# C++ in ROS (Fast DDS, rcl, rclpy bindings) at -j<nproc> runs out of memory on
# small hosts: about 2 GB per job is safe.
MEM_GB="$(awk '/MemTotal/ { printf "%d", $2 / 1024 / 1024 }' /proc/meminfo)"
JOBS="$(( MEM_GB / 2 ))"
[ "$JOBS" -lt 2 ] && JOBS=2
[ "$JOBS" -gt "$(nproc)" ] && JOBS="$(nproc)"

mkdir -p "$BUILD/conf"
cat > "$BUILD/conf/bblayers.conf" <<EOF
BBPATH = "\${TOPDIR}"
BBFILES ?= ""
BBLAYERS = " \\
    $LAYERS/openembedded-core/meta \\
    $LAYERS/meta-raspberrypi \\
    $LAYERS/meta-openembedded/meta-oe \\
    $LAYERS/meta-openembedded/meta-python \\
    $LAYERS/meta-ros/meta-ros-common \\
    $LAYERS/meta-ros/meta-ros2 \\
    $LAYERS/meta-ros/meta-ros2-jazzy \\
    $LAYERS/meta-rpi5os \\
    $LAYERS/meta-rpi5os-ros \\
"
EOF
cat > "$BUILD/conf/local.conf" <<EOF
MACHINE = "raspberrypi5"
DISTRO = "rpi5os"
DL_DIR = "$WORK/downloads"
SSTATE_DIR = "$WORK/sstate"
# Hash equivalence database next to sstate, else sstate reuse is lost.
BB_HASHSERVE_DB_DIR = "\${SSTATE_DIR}"
INHERIT += "rm_work"
# Keep the image's rootfs and our ROS package in tmp/work for inspection.
RM_WORK_EXCLUDE += "rpi5os-image counter-pkg"
BB_NUMBER_THREADS = "$JOBS"
PARALLEL_MAKE = "-j$JOBS"
# ROS 2: distro and where counter_pkg's sources are (meta-rpi5os-ros).
ROS_DISTRO = "jazzy"
RPI5OS_ROS2_SRC = "$WORK/ros2"
# meta-ros recipes name licenses that are not in oe-core's common-licenses
# (meta-ros's kas configs drop this check too).
ERROR_QA:remove = "license-exists"
CONF_VERSION = "2"
EOF

# oe-init-build-env keeps our conf/ and cds into the build dir.
export BITBAKEDIR="$LAYERS/bitbake"
set +u
# shellcheck disable=SC1091
. "$LAYERS/openembedded-core/oe-init-build-env" "$BUILD" >/dev/null
set -u

# No arguments: the image. Otherwise they go to bitbake as they are, e.g.
# `build.sh -p` (parse only) or `build.sh counter-pkg`.
if [ $# -eq 0 ]; then
	set -- rpi5os-image
fi
bitbake "$@"

if [ "$*" = "rpi5os-image" ]; then
	DEPLOY="$BUILD/tmp/deploy/images/raspberrypi5"
	ls -lhL "$DEPLOY/rpi5os-image-raspberrypi5.rootfs.wic"
	sha256sum "$DEPLOY/rpi5os-image-raspberrypi5.rootfs.wic"
fi
