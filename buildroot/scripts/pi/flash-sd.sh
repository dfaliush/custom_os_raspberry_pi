#!/usr/bin/env bash
#
# flash-sd.sh IMAGE.img[.xz]: run with sudo on Raspberry Pi OS (booted from SSD).
# Writes rpi5os to this Pi's microSD and puts wpa_supplicant.conf (from the
# current Wi-Fi) and userconf.txt (from the user) on its boot partition.
#
# The SSD is never written: the image and userconf live in /dev/shm (RAM).

set -euo pipefail

IMG="${1:?Usage: $0 IMAGE.img[.xz]}"
SD=/dev/mmcblk0
USERCONF=/dev/shm/rpi5os-userconf.txt
MNT=/mnt/rpi5os-boot

die() { echo "flash-sd: $*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "запускай через sudo"
[ -f "$IMG" ] || die "немає $IMG"
[ -f "$USERCONF" ] || die "немає $USERCONF; створи: printf 'user:%s\n' \"\$(openssl passwd -6)\" > $USERCONF"
grep -qE '^[a-z_][a-z0-9_-]*:\$[56]\$' "$USERCONF" || die "$USERCONF має бути у форматі ім'я:\$6\$..."

# Make sure the target is the microSD, not the system disk.
[ -b "$SD" ] || die "немає $SD"
[ "$(lsblk -dno TRAN "$SD")" = "mmc" ] || die "$SD не mmc"
for m in / /boot/firmware; do
	src="$(findmnt -no SOURCE "$m")"
	parent="/dev/$(lsblk -no PKNAME "$src")"
	[ "$parent" != "$SD" ] || die "$m живе на $SD: це робоча система"
done

RAW=/dev/shm/rpi5os-sdcard.img
case "$IMG" in
	*.xz) xz -dc "$IMG" > "$RAW" ;;
	*)    [ "$IMG" = "$RAW" ] || cp "$IMG" "$RAW" ;;
esac
img_size=$(stat -c %s "$RAW")
sd_size=$(blockdev --getsize64 "$SD")
[ "$img_size" -le "$sd_size" ] || die "образ $img_size B більший за SD $sd_size B"
img_sha=$(sha256sum "$RAW" | cut -d' ' -f1)
echo "образ: $img_size B, sha256 $img_sha"

for p in $(lsblk -lnpo NAME "$SD" | tail -n +2); do
	findmnt -no TARGET "$p" >/dev/null 2>&1 && umount "$p"
done
dd if="$RAW" of="$SD" bs=4M conv=fsync status=progress
sync

# Read back bypassing the page cache.
echo 3 > /proc/sys/vm/drop_caches
sd_sha=$(head -c "$img_size" "$SD" | sha256sum | cut -d' ' -f1)
[ "$sd_sha" = "$img_sha" ] || die "sha256 на SD ($sd_sha) не збігається з образом"
echo "звірка sha256: OK"
rm -f "$RAW"

partprobe "$SD" 2>/dev/null || blockdev --rereadpt "$SD"
udevadm settle

mkdir -p "$MNT"
mount "${SD}p1" "$MNT"
trap 'sync; umount "$MNT" 2>/dev/null || true' EXIT

# Wi-Fi from the active NetworkManager connection: the PSK never leaves this Pi.
con="$(nmcli -t -f NAME,TYPE con show --active | awk -F: '$2 == "802-11-wireless" {print $1; exit}')"
[ -n "$con" ] || die "немає активного Wi-Fi з'єднання"
# Without --escape no, -g backslash-escapes ':' and '\' in the SSID/PSK.
ssid="$(nmcli --escape no -s -g 802-11-wireless.ssid con show "$con")"
psk="$(nmcli --escape no -s -g 802-11-wireless-security.psk con show "$con")"
kmgmt="$(nmcli -g 802-11-wireless-security.key-mgmt con show "$con")"
[ -n "$ssid" ] && [ -n "$psk" ] || die "не вдалося прочитати SSID/PSK з '$con'"
case "$kmgmt" in
	sae) wpa_kmgmt=SAE ;;
	*)   wpa_kmgmt=WPA-PSK ;;
esac
# 64 hex digits is a precomputed PSK, written unquoted.
if printf '%s' "$psk" | grep -qE '^[0-9a-fA-F]{64}$'; then psk_line="psk=$psk"; else psk_line="psk=\"$psk\""; fi
country="$(iw reg get 2>/dev/null | sed -n 's/^country \([A-Z][A-Z]\).*/\1/p' | head -n1)"

umask 077
{
	echo "ctrl_interface=/var/run/wpa_supplicant"
	echo "update_config=0"
	echo "country=${country:-UA}"
	echo
	echo "network={"
	echo "	ssid=\"$ssid\""
	echo "	$psk_line"
	echo "	key_mgmt=$wpa_kmgmt"
	echo "}"
} > "$MNT/wpa_supplicant.conf"
echo "wpa_supplicant.conf: ssid=$ssid, key_mgmt=$wpa_kmgmt, country=${country:-UA}"

cp "$USERCONF" "$MNT/userconf.txt"
echo "userconf.txt: користувач $(cut -d: -f1 "$USERCONF")"
sync
echo "Готово. SD записана й увімкнена; BOOT_ORDER не змінювався."
