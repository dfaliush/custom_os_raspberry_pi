#!/usr/bin/env bash
#
# flash-to-pi.sh IMAGE.img.xz [HOST]: записати rpi5os на microSD Pi по ssh.
# Запускається з Git Bash на Windows (там ключі ~/.ssh для HOST):
#
#   bash buildroot/scripts/flash-to-pi.sh //wsl.localhost/Ubuntu/home/user/br/dist/rpi5os-buildroot-v1.0.0-sdcard.img.xz
#
# Перед цим на Pi має лежати /dev/shm/rpi5os-userconf.txt (див. README).
# Усе копіюється в /dev/shm (RAM): на SSD Pi нічого не пишеться.

set -euo pipefail

IMG="${1:?Usage: $0 IMAGE.img.xz [user@host]}"
HOST="${2:-user@raspberrypi}"
HERE="$(cd "$(dirname "$0")" && pwd)"

scp "$IMG" "$HERE/pi/flash-sd.sh" "$HERE/pi/sd-boot.sh" "$HERE/pi/boot-order.sh" "$HOST:/dev/shm/"
ssh "$HOST" "sudo bash /dev/shm/flash-sd.sh /dev/shm/$(basename "$IMG") && rm -f /dev/shm/$(basename "$IMG")"
