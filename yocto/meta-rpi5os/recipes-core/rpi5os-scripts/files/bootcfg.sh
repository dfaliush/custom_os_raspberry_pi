#!/bin/sh
#
# bootcfg.sh: apply settings from the /boot FAT partition, then delete them.
#
#   /boot/userconf.txt        "name:hash" → user in group wheel
#   /boot/wpa_supplicant.conf → /etc/wpa_supplicant/wpa_supplicant-nl80211-wlan0.conf (600)
#
# The image has no users and no Wi-Fi password: whoever flashes the SD adds them.

. /usr/lib/rpi5os/common.sh

WPA_CONF=/etc/wpa_supplicant/wpa_supplicant-nl80211-wlan0.conf

apply_userconf() {
	f=/boot/userconf.txt
	[ -f "$f" ] || return 0

	line=$(tr -d '\r' < "$f" | grep -v '^[[:space:]]*#' | grep -m1 ':')
	rm -f "$f"
	sync
	name=${line%%:*}
	hash=${line#*:}

	case "$name" in
		''|*[!a-z0-9_-]*) log "userconf: погане ім'я користувача, пропускаю"; return 1 ;;
	esac
	# Only sha256/sha512-crypt, which crypt() in sshd and sudo surely supports.
	case "$hash" in
		'$5$'*|'$6$'*) ;;
		*) log "userconf: hash має бути з 'openssl passwd -6', пропускаю"; return 1 ;;
	esac

	id "$name" >/dev/null 2>&1 || useradd -m -s /bin/sh "$name"
	usermod -a -G wheel "$name"
	usermod -p "$hash" "$name"

	if id -nG "$name" | grep -qw wheel && [ -d "/home/$name" ]; then
		log "userconf: користувач $name готовий (home, група wheel)"
	else
		log "userconf: ПОМИЛКА: $name без home або не в wheel"
	fi
}

apply_wpa() {
	f=/boot/wpa_supplicant.conf
	[ -f "$f" ] || return 0

	umask 077
	mkdir -p "$(dirname "$WPA_CONF")"
	tr -d '\r' < "$f" > "$WPA_CONF.new"
	mv "$WPA_CONF.new" "$WPA_CONF"
	rm -f "$f"
	sync
	log "wpa: конфіг перенесено в $WPA_CONF"
}

apply_userconf
apply_wpa
[ -f "$WPA_CONF" ] || log "немає $WPA_CONF: поклади wpa_supplicant.conf на boot-розділ"
exit 0
