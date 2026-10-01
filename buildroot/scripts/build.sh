#!/usr/bin/env bash
#
# Build rpi5os in WSL / Linux, from scratch to sdcard.img. From the repo root:
#
#   wsl -d Ubuntu -- bash buildroot/scripts/build.sh
#
# Work dir (Buildroot sources, output) is RPI5OS_WORK, ~/br by default. It must
# be on ext4: on /mnt/<drive> the build breaks on name case and permissions.

set -euo pipefail

BR_VERSION=2026.02.3
BR_URL=https://gitlab.com/buildroot.org/buildroot.git

SRC="$(cd "$(dirname "$0")/.." && pwd)"    # buildroot/ in the repo = BR2_EXTERNAL
WORK="${RPI5OS_WORK:-$HOME/br}"
EXT="$WORK/external"
OUT="$WORK/output"

case "$WORK" in
	/mnt/*) echo "RPI5OS_WORK=$WORK лежить на диску Windows; потрібна ext4 (наприклад ~/br)" >&2; exit 1 ;;
esac
mkdir -p "$WORK"

# WSL appends Windows dirs to PATH ("/mnt/c/Program Files/..."). Buildroot
# refuses a PATH with spaces, and the build needs no Windows tools anyway.
PATH="$(printf '%s' "$PATH" | tr ':' '\n' | grep -v '^/mnt/' | paste -sd:)"
export PATH

# Copy BR2_EXTERNAL to ext4 with explicit modes: drvfs reports arbitrary
# modes, and the overlay carries them into rootfs as is.
rsync -a --delete --no-perms --chmod=D755,F644 "$SRC/" "$EXT/"
chmod 755 "$EXT"/board/rpi5os/*.sh \
          "$EXT"/board/rpi5os/rootfs-overlay/etc/init.d/* \
          "$EXT"/board/rpi5os/rootfs-overlay/usr/sbin/* \
          "$EXT"/scripts/*.sh

if [ ! -d "$WORK/buildroot/.git" ]; then
	git clone --depth 1 --branch "$BR_VERSION" "$BR_URL" "$WORK/buildroot"
fi
have="$(git -C "$WORK/buildroot" describe --tags --exact-match 2>/dev/null || echo '?')"
if [ "$have" != "$BR_VERSION" ]; then
	echo "У $WORK/buildroot тег '$have', а потрібен $BR_VERSION" >&2
	exit 1
fi

make -C "$WORK/buildroot" BR2_EXTERNAL="$EXT" O="$OUT" rpi5os_defconfig
make -C "$WORK/buildroot" O="$OUT"

ls -lh "$OUT/images/sdcard.img"
sha256sum "$OUT/images/sdcard.img"
