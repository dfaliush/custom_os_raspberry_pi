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

# Pi 5 Rev 1.1 має кремній BCM2712 D0. Firmware бере базовий bcm2712-rpi-5-b.dtb і
# накладає на нього overlays/bcm2712d0.dtbo. Без цього файлу kernel отримує DT для
# C1 і падає в panic за кілька секунд, ще до монтування rootfs. Беремо overlay з
# того самого дерева kernel, яким зібрано Image, щоб версії збігались.
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
