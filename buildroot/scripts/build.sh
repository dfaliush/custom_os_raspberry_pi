#!/usr/bin/env bash
#
# Збірка rpi5os у WSL / Linux. Один виклик від нуля до sdcard.img:
#
#   wsl -d Ubuntu -- bash /mnt/d/git/custom_os_raspberry_pi/buildroot/scripts/build.sh
#
# Робоча тека (сирці Buildroot, output) — RPI5OS_WORK, за замовчуванням ~/br.
# Вона має бути на ext4: на /mnt/<диск> збірка ламається на регістрі імен і правах.

set -euo pipefail

BR_VERSION=2026.02.3
BR_URL=https://gitlab.com/buildroot.org/buildroot.git

SRC="$(cd "$(dirname "$0")/.." && pwd)"    # buildroot/ у репо = BR2_EXTERNAL
WORK="${RPI5OS_WORK:-$HOME/br}"
EXT="$WORK/external"
OUT="$WORK/output"

case "$WORK" in
	/mnt/*) echo "RPI5OS_WORK=$WORK лежить на диску Windows; потрібна ext4 (наприклад ~/br)" >&2; exit 1 ;;
esac
mkdir -p "$WORK"

# WSL дописує в PATH теки Windows ("/mnt/c/Program Files/..."). Buildroot
# відмовляється працювати з пробілами в PATH, та й Windows-утиліти збірці не потрібні.
PATH="$(printf '%s' "$PATH" | tr ':' '\n' | grep -v '^/mnt/' | paste -sd:)"
export PATH

# 1. BR2_EXTERNAL копією на ext4 з явними правами. З /mnt/d (drvfs) права
#    читаються як попало, а overlay переносить їх у rootfs як є.
rsync -a --delete --no-perms --chmod=D755,F644 "$SRC/" "$EXT/"
chmod 755 "$EXT"/board/rpi5os/*.sh \
          "$EXT"/board/rpi5os/rootfs-overlay/etc/init.d/* \
          "$EXT"/board/rpi5os/rootfs-overlay/usr/sbin/* \
          "$EXT"/scripts/*.sh

# 2. Buildroot рівно на потрібному тезі.
if [ ! -d "$WORK/buildroot/.git" ]; then
	git clone --depth 1 --branch "$BR_VERSION" "$BR_URL" "$WORK/buildroot"
fi
have="$(git -C "$WORK/buildroot" describe --tags --exact-match 2>/dev/null || echo '?')"
if [ "$have" != "$BR_VERSION" ]; then
	echo "У $WORK/buildroot тег '$have', а потрібен $BR_VERSION" >&2
	exit 1
fi

# 3. Конфіг і збірка.
make -C "$WORK/buildroot" BR2_EXTERNAL="$EXT" O="$OUT" rpi5os_defconfig
make -C "$WORK/buildroot" O="$OUT"

ls -lh "$OUT/images/sdcard.img"
sha256sum "$OUT/images/sdcard.img"
