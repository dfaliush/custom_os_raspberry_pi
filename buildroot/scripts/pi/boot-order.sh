#!/usr/bin/env bash
#
# boot-order.sh sd-first|restore|show: порядок завантаження в EEPROM Pi 5.
# Запускається на Raspberry Pi OS через sudo.
#
#   sd-first → BOOT_ORDER=0xf461: SD → NVMe → USB. З вимкненою або вийнятою
#              SD Pi сама йде на NVMe.
#   restore  → повертає конфіг, збережений перед першим sd-first.
#
# Зміна набуває сили після reboot: rpi-eeprom-config --apply кладе
# pieeprom.upd/.sig і recovery.bin у /boot/firmware, bootloader прошиває EEPROM
# і перейменовує recovery.bin. Інших змін на SSD немає.

set -euo pipefail

BACKUP="${SUDO_USER:+/home/$SUDO_USER}/rpi5os-eeprom-backup.conf"
WANT=0xf461

[ "$(id -u)" -eq 0 ] || { echo "Запускай через sudo" >&2; exit 1; }

current() { rpi-eeprom-config | sed -n 's/^BOOT_ORDER=//p'; }

case "${1:-show}" in
	sd-first)
		[ -f "$BACKUP" ] || { rpi-eeprom-config > "$BACKUP"; echo "бекап: $BACKUP"; }
		if [ "$(current)" = "$WANT" ]; then echo "BOOT_ORDER уже $WANT"; exit 0; fi
		tmp="$(mktemp)"
		rpi-eeprom-config | sed "s/^BOOT_ORDER=.*/BOOT_ORDER=$WANT/" > "$tmp"
		grep -q "^BOOT_ORDER=$WANT$" "$tmp" || echo "BOOT_ORDER=$WANT" >> "$tmp"
		rpi-eeprom-config --apply "$tmp"
		rm -f "$tmp"
		echo "BOOT_ORDER=$WANT застосується після reboot"
		;;
	restore)
		[ -f "$BACKUP" ] || { echo "немає $BACKUP" >&2; exit 1; }
		rpi-eeprom-config --apply "$BACKUP"
		echo "конфіг з $BACKUP застосується після reboot"
		;;
	show)
		echo "BOOT_ORDER зараз: $(current)"
		ls /boot/firmware/pieeprom.upd >/dev/null 2>&1 && echo "є відкладене оновлення EEPROM (pieeprom.upd)"
		;;
	*)
		echo "Usage: $0 sd-first|restore|show" >&2
		exit 1
		;;
esac
