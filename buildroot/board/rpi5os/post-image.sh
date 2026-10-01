#!/bin/bash
# Збирає sdcard.img. Логіка як у board/raspberrypi/post-image.sh з Buildroot,
# але з нашим genimage.cfg.in і прикладами конфігів на boot-розділі.

set -euo pipefail

BOARD_DIR="$(dirname "$0")"
GENIMAGE_CFG="${BINARIES_DIR}/genimage.cfg"
GENIMAGE_TMP="${BUILD_DIR}/genimage.tmp"

# Приклади лягають на FAT поруч із config.txt: їх видно з Windows після запису.
install -m 0644 "${BOARD_DIR}/bootfs/wpa_supplicant.conf.example" "${BINARIES_DIR}/rpi-firmware/"
install -m 0644 "${BOARD_DIR}/bootfs/userconf.txt.example"        "${BINARIES_DIR}/rpi-firmware/"

FILES=()
for i in "${BINARIES_DIR}"/*.dtb "${BINARIES_DIR}"/rpi-firmware/*; do
	FILES+=( "${i#${BINARIES_DIR}/}" )
done
KERNEL=$(sed -n 's/^kernel=//p' "${BINARIES_DIR}/rpi-firmware/config.txt")
FILES+=( "${KERNEL}" )

BOOT_FILES=$(printf '\\t\\t\\t"%s",\\n' "${FILES[@]}")
sed "s|#BOOT_FILES#|${BOOT_FILES}|" "${BOARD_DIR}/genimage.cfg.in" > "${GENIMAGE_CFG}"

# Порожній rootpath: rootfs.ext4 уже зібраний, genimage лише вставляє його.
ROOTPATH_TMP="$(mktemp -d)"
trap 'rm -rf "${ROOTPATH_TMP}"' EXIT
rm -rf "${GENIMAGE_TMP}"

genimage \
	--rootpath "${ROOTPATH_TMP}" \
	--tmppath "${GENIMAGE_TMP}" \
	--inputpath "${BINARIES_DIR}" \
	--outputpath "${BINARIES_DIR}" \
	--config "${GENIMAGE_CFG}"
