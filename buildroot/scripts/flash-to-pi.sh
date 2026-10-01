#!/usr/bin/env bash
#
# flash-to-pi.sh IMAGE.img.xz [HOST]: write rpi5os to the Pi's microSD over ssh.
# Run from Git Bash on Windows, where the ~/.ssh keys for HOST are:
#
#   bash buildroot/scripts/flash-to-pi.sh //wsl.localhost/Ubuntu/home/<user>/br/dist/rpi5os-buildroot-v1.0.0-sdcard.img.xz
#
# The Pi must already have /dev/shm/rpi5os-userconf.txt (see README).
# Everything goes to /dev/shm (RAM), nothing is written to the Pi's SSD.

set -euo pipefail

IMG="${1:?Usage: $0 IMAGE.img.xz [user@host]}"
HOST="${2:-user@raspberrypi}"
HERE="$(cd "$(dirname "$0")" && pwd)"

scp "$IMG" "$HERE/pi/flash-sd.sh" "$HERE/pi/sd-boot.sh" "$HERE/pi/boot-order.sh" "$HOST:/dev/shm/"
ssh "$HOST" "sudo bash /dev/shm/flash-sd.sh /dev/shm/$(basename "$IMG") && rm -f /dev/shm/$(basename "$IMG")"
