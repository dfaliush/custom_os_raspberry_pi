#!/usr/bin/env bash
#
# sd-boot.sh on|off|status: запускається на Raspberry Pi OS (з SSD) і вмикає
# або вимикає завантаження з microSD, не чіпаючи SSD.
#
#   off → boot-файли SD переносяться в disabled/: bootloader вважає SD
#         порожньою і йде далі по BOOT_ORDER (на NVMe)
#   on  → файли повертаються, при наступному reboot стартує rpi5os
#
# Дзеркало usr/sbin/boot-ssd з образу: той вимикає SD зсередини rpi5os.

set -euo pipefail

PART=/dev/mmcblk0p1
MNT=/mnt/rpi5os-boot
# Те, що не є boot-файлами: лишається на місці при off.
KEEP_RE='^(rpi5os-boot\.log|no-fallback|userconf\.txt|wpa_supplicant\.conf|.*\.example)$'

[ "$(id -u)" -eq 0 ] || { echo "Запускай через sudo" >&2; exit 1; }
[ -b "$PART" ] || { echo "Немає $PART: microSD не вставлена?" >&2; exit 1; }

# Ніколи не працюємо з розділом, з якого живе поточна система.
for m in / /boot/firmware; do
	if [ "$(findmnt -no SOURCE "$m" 2>/dev/null)" = "$PART" ]; then
		echo "$PART змонтовано як $m: це робоча система, зупиняюсь" >&2
		exit 1
	fi
done

mounted_here=0
cur="$(findmnt -no TARGET "$PART" 2>/dev/null | head -n1 || true)"
if [ -z "$cur" ]; then
	mkdir -p "$MNT"
	mount "$PART" "$MNT"
	cur="$MNT"
	mounted_here=1
fi
cleanup() { sync; [ "$mounted_here" -eq 1 ] && umount "$MNT"; true; }
trap cleanup EXIT

case "${1:-status}" in
	off)
		mkdir -p "$cur/disabled"
		for f in "$cur"/*; do
			[ -f "$f" ] || continue
			basename "$f" | grep -qE "$KEEP_RE" && continue
			mv "$f" "$cur/disabled/"
		done
		echo "SD-завантаження вимкнено"
		;;
	on)
		if [ -d "$cur/disabled" ]; then
			mv "$cur"/disabled/* "$cur"/ 2>/dev/null || true
			rmdir "$cur/disabled"
		fi
		echo "SD-завантаження увімкнено"
		;;
	status)
		;;
	*)
		echo "Usage: $0 on|off|status" >&2
		exit 1
		;;
esac

if [ -f "$cur/config.txt" ]; then echo "стан: SD завантажувальна"; else echo "стан: SD вимкнена"; fi
echo "BOOT_ORDER: $(rpi-eeprom-config | sed -n 's/^BOOT_ORDER=//p')"
[ -f "$cur/rpi5os-boot.log" ] && { echo "--- останні рядки rpi5os-boot.log"; tail -n 15 "$cur/rpi5os-boot.log"; }
exit 0
