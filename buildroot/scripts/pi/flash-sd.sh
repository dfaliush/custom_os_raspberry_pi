#!/usr/bin/env bash
#
# flash-sd.sh IMAGE.img[.xz]: запускається на Raspberry Pi OS (з SSD) через sudo.
# Записує образ rpi5os на microSD у слоті цієї ж Pi і кладе на boot-розділ
# wpa_supplicant.conf (з поточного Wi-Fi) і userconf.txt (від користувача).
#
# SSD не чіпаємо: образ і userconf лежать у /dev/shm (RAM), запис тільки в mmcblk0.
# Викликається з flash-to-pi.sh, але працює й сам.

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

# --- 1. Чи це справді та microSD, а не робочий диск ---
[ -b "$SD" ] || die "немає $SD"
[ "$(lsblk -dno TRAN "$SD")" = "mmc" ] || die "$SD не mmc"
for m in / /boot/firmware; do
	src="$(findmnt -no SOURCE "$m")"
	parent="/dev/$(lsblk -no PKNAME "$src")"
	[ "$parent" != "$SD" ] || die "$m живе на $SD: це робоча система"
done

# --- 2. Розпакувати в RAM, перевірити розмір ---
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

# --- 3. Відмонтувати старі розділи SD і записати ---
for p in $(lsblk -lnpo NAME "$SD" | tail -n +2); do
	findmnt -no TARGET "$p" >/dev/null 2>&1 && umount "$p"
done
dd if="$RAW" of="$SD" bs=4M conv=fsync status=progress
sync

# --- 4. Звірка: читаємо назад повз page cache ---
echo 3 > /proc/sys/vm/drop_caches
sd_sha=$(head -c "$img_size" "$SD" | sha256sum | cut -d' ' -f1)
[ "$sd_sha" = "$img_sha" ] || die "sha256 на SD ($sd_sha) не збігається з образом"
echo "звірка sha256: OK"
rm -f "$RAW"

partprobe "$SD" 2>/dev/null || blockdev --rereadpt "$SD"
udevadm settle

# --- 5. Конфіги на boot-розділ ---
mkdir -p "$MNT"
mount "${SD}p1" "$MNT"
trap 'sync; umount "$MNT" 2>/dev/null || true' EXIT

# Wi-Fi з активного з'єднання NetworkManager. PSK не залишає цю Pi.
con="$(nmcli -t -f NAME,TYPE con show --active | awk -F: '$2 == "802-11-wireless" {print $1; exit}')"
[ -n "$con" ] || die "немає активного Wi-Fi з'єднання"
# --escape no: інакше -g екранує ':' і '\' у SSID/PSK зворотним слешем.
ssid="$(nmcli --escape no -s -g 802-11-wireless.ssid con show "$con")"
psk="$(nmcli --escape no -s -g 802-11-wireless-security.psk con show "$con")"
kmgmt="$(nmcli -g 802-11-wireless-security.key-mgmt con show "$con")"
[ -n "$ssid" ] && [ -n "$psk" ] || die "не вдалося прочитати SSID/PSK з '$con'"
case "$kmgmt" in
	sae) wpa_kmgmt=SAE ;;
	*)   wpa_kmgmt=WPA-PSK ;;
esac
# 64 hex-символи = вже готовий PSK, пишеться без лапок.
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
