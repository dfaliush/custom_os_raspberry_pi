#!/bin/sh
#
# fallback.sh: if 3 minutes after boot wlan0 has no address or sshd is down,
# disable SD boot and reboot. The Pi comes back on the SSD (BOOT_ORDER=0xf461:
# SD → NVMe → USB) and the reason stays in /boot/rpi5os-boot.log.
#
# Wi-Fi is the only link, so rpi5os without network would be unreachable.
# To disable (on-site debugging): create /boot/no-fallback.

. /usr/lib/rpi5os/common.sh

TIMEOUT=180
STEP=5

# A DHCP address. 169.254.x.x doesn't count: networkd has link-local off, but
# such an address would mean there is no real network anyway.
wlan_addr() {
	ip -4 -o addr show dev wlan0 2>/dev/null | awk '$4 !~ /^169\.254\./ {print $4; exit}'
}

network_ready() {
	[ -n "$(wlan_addr)" ] && systemctl is-active --quiet sshd.socket
}

if [ -e /boot/no-fallback ]; then
	log "автовідкат вимкнено (/boot/no-fallback)"
	exit 0
fi

waited=0
while [ $waited -lt $TIMEOUT ]; do
	if network_ready; then
		log "OK: $(wlan_addr), sshd працює"
		exit 0
	fi
	sleep $STEP
	waited=$((waited + STEP))
done

log "FAIL: за ${TIMEOUT} с немає IP на wlan0 або sshd. Діагностика нижче."
{
	echo "--- iw dev wlan0 link"; iw dev wlan0 link 2>&1
	echo "--- wpa_supplicant";    systemctl status --no-pager -n 15 wpa_supplicant-nl80211@wlan0.service 2>&1
	echo "--- networkctl";        networkctl status wlan0 --no-pager 2>&1 | head -n 20
	echo "--- dmesg (brcm/wlan/cfg80211)"; dmesg | grep -iE 'brcm|wlan|cfg80211' | tail -n 30
} >> "$RPI5OS_LOG" 2>&1
log "вимикаю завантаження з SD і перезавантажуюсь на SSD"
/usr/sbin/boot-ssd && sync && systemctl reboot
