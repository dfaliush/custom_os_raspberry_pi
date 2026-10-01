#!/bin/sh
# Rootfs fixups before packing; $1 = TARGET_DIR. The overlay copies files
# as is, this script patches the files Buildroot generates.

set -eu

TARGET="$1"
EXT="${BR2_EXTERNAL_RPI5OS_PATH}"
VERSION="$(cat "${EXT}/VERSION")"

# FAT has no permissions: without umask=0077 anyone could read userconf.txt
# and wpa_supplicant.conf on it.
mkdir -p "${TARGET}/boot"
grep -q '[[:space:]]/boot[[:space:]]' "${TARGET}/etc/fstab" || \
	echo '/dev/mmcblk0p1	/boot	vfat	defaults,noatime,umask=0077	0	0' >> "${TARGET}/etc/fstab"

# Buildroot's skeleton has no /home, and adduser can't create a home directory without it.
mkdir -p "${TARGET}/home"

# An empty root password means login without one. '*' matches no password.
sed -i 's/^root:[^:]*:/root:*:/' "${TARGET}/etc/shadow"

# The first occurrence wins in sshd_config, so our options go on top.
SSHD="${TARGET}/etc/ssh/sshd_config"
if ! grep -q '^# rpi5os:begin' "${SSHD}"; then
	{
		echo '# rpi5os:begin (see buildroot/board/rpi5os/post-build.sh)'
		echo 'PermitRootLogin no'
		echo '# For the first login only; sudo ssh-keys-only switches it to "no".'
		echo 'PasswordAuthentication yes'
		echo 'KbdInteractiveAuthentication no'
		echo 'PubkeyAuthentication yes'
		echo '# rpi5os:end'
		echo
		cat "${SSHD}"
	} > "${SSHD}.new"
	mv "${SSHD}.new" "${SSHD}"
fi

# The userconf.txt user is added to wheel. sudoers is mode 0440, so ">>"
# fails, while sed -i replaces the file and keeps the mode.
grep -q '^%wheel ALL=(ALL:ALL) ALL' "${TARGET}/etc/sudoers" || \
	sed -i '$a %wheel ALL=(ALL:ALL) ALL' "${TARGET}/etc/sudoers"

OSR="${TARGET}/usr/lib/os-release"
[ -f "${OSR}" ] || OSR="${TARGET}/etc/os-release"
sed -i '/^VARIANT_ID=/d; /^IMAGE_ID=/d; /^IMAGE_VERSION=/d' "${OSR}"
{
	echo 'VARIANT_ID=rpi5os'
	echo 'IMAGE_ID=rpi5os-buildroot'
	echo "IMAGE_VERSION=${VERSION}"
} >> "${OSR}"

# The wpa_supplicant package installs /etc/wpa_supplicant.conf with
# network={key_mgmt=NONE}, i.e. "join any open network", and S41wifi treats
# the file as configured Wi-Fi. The real config comes from the boot partition.
rm -f "${TARGET}/etc/wpa_supplicant.conf"

# The image is public: fail if any secret slipped in.
for f in etc/ssh/ssh_host_*key* root/.ssh/authorized_keys etc/wpa_supplicant.conf; do
	for hit in ${TARGET}/${f}; do
		if [ -e "${hit}" ]; then
			echo "post-build: в образі не має бути ${hit#${TARGET}}" >&2
			exit 1
		fi
	done
done
