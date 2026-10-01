#!/bin/bash
# Builds sdcard.img like Buildroot's board/raspberrypi/post-image.sh, but with
# our genimage.cfg.in and example configs on the boot partition.

set -euo pipefail

BOARD_DIR="$(dirname "$0")"
GENIMAGE_CFG="${BINARIES_DIR}/genimage.cfg"
GENIMAGE_TMP="${BUILD_DIR}/genimage.tmp"

# On FAT next to config.txt, so they are visible from any PC after flashing.
install -m 0644 "${BOARD_DIR}/bootfs/wpa_supplicant.conf.example" "${BINARIES_DIR}/rpi-firmware/"
install -m 0644 "${BOARD_DIR}/bootfs/userconf.txt.example"        "${BINARIES_DIR}/rpi-firmware/"

# Pi 5 Rev 1.1 has a BCM2712 D0. The firmware loads bcm2712-rpi-5-b.dtb and
# applies overlays/bcm2712d0.dtbo on top; without it the kernel gets the C1
# device tree and panics before mounting rootfs. Taken from the same kernel
# tree as Image so the versions match.
D0_OVERLAY="$(ls "${BUILD_DIR}"/linux-*/arch/arm64/boot/dts/overlays/bcm2712d0.dtbo 2>/dev/null | head -n1)"
[ -n "${D0_OVERLAY}" ] || { echo "post-image: немає bcm2712d0.dtbo у дереві kernel" >&2; exit 1; }
install -D -m 0644 "${D0_OVERLAY}" "${BINARIES_DIR}/rpi-firmware/overlays/bcm2712d0.dtbo"

FILES=()
for i in "${BINARIES_DIR}"/*.dtb "${BINARIES_DIR}"/rpi-firmware/*; do
	FILES+=( "${i#${BINARIES_DIR}/}" )
done
KERNEL=$(sed -n 's/^kernel=//p' "${BINARIES_DIR}/rpi-firmware/config.txt")
FILES+=( "${KERNEL}" )

BOOT_FILES=$(printf '\\t\\t\\t"%s",\\n' "${FILES[@]}")
sed "s|#BOOT_FILES#|${BOOT_FILES}|" "${BOARD_DIR}/genimage.cfg.in" > "${GENIMAGE_CFG}"

# Empty rootpath: rootfs.ext4 is already built, genimage only embeds it.
ROOTPATH_TMP="$(mktemp -d)"
trap 'rm -rf "${ROOTPATH_TMP}"' EXIT
rm -rf "${GENIMAGE_TMP}"

genimage \
	--rootpath "${ROOTPATH_TMP}" \
	--tmppath "${GENIMAGE_TMP}" \
	--inputpath "${BINARIES_DIR}" \
	--outputpath "${BINARIES_DIR}" \
	--config "${GENIMAGE_CFG}"
