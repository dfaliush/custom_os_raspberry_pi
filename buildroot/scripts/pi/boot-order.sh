#!/usr/bin/env bash
#
# boot-order.sh sd-first|restore|show: Pi 5 EEPROM boot order.
# Run on Raspberry Pi OS with sudo.
#
#   sd-first → BOOT_ORDER=0xf461: SD → NVMe → USB. With the SD disabled or
#              removed the Pi boots from NVMe.
#   restore  → reapply the config saved before the first sd-first.
#
# Takes effect after reboot: rpi-eeprom-config --apply puts pieeprom.upd/.sig
# and recovery.bin in /boot/firmware, the bootloader flashes the EEPROM and
# renames recovery.bin. Nothing else on the SSD changes.

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
		if [ -e /boot/firmware/pieeprom.upd ]; then echo "є відкладене оновлення EEPROM (pieeprom.upd)"; fi
		;;
	*)
		echo "Usage: $0 sd-first|restore|show" >&2
		exit 1
		;;
esac
