SUMMARY = "rpi5os: Raspberry Pi 5 + Wi-Fi + SSH, no secrets in the image"
LICENSE = "MIT"

inherit core-image

IMAGE_FEATURES += "ssh-server-openssh"
# kernel-modules, as in the Buildroot image: brcmfmac loads its vendor modules
# (brcmfmac-cyw, ...) on demand, and a missing one leaves wlan0 down.
# The Wi-Fi firmware is only in MACHINE_EXTRA_RRECOMMENDS, which this explicit
# IMAGE_INSTALL doesn't pull in: without it wlan0 never appears.
IMAGE_INSTALL = " \
    packagegroup-core-boot \
    openssh-sftp-server \
    wpa-supplicant iw wireless-regdb-static \
    kernel-modules \
    linux-firmware-rpidistro-bcm43455 linux-firmware-rpidistro-bcm43456 \
    avahi-daemon \
    sudo shadow \
    rpi5os-scripts \
"
IMAGE_LINGUAS = ""

IMAGE_FSTYPES = "wic wic.bmap"
WKS_FILE = "rpi5os-sdimage.wks"

# Config templates on FAT next to config.txt, as in the Buildroot image.
IMAGE_BOOT_FILES:append = " \
    rpi5os-bootfs/userconf.txt.example;userconf.txt.example \
    rpi5os-bootfs/wpa_supplicant.conf.example;wpa_supplicant.conf.example \
"
do_image_wic[depends] += "rpi5os-bootfs:do_deploy"

ROOTFS_POSTPROCESS_COMMAND += "rpi5os_rootfs_fixup "

rpi5os_rootfs_fixup () {
	R=${IMAGE_ROOTFS}

	# wpa-supplicant installs /etc/wpa_supplicant.conf with network={key_mgmt=NONE},
	# i.e. "join any open network". The real config comes from the boot partition.
	rm -f $R${sysconfdir}/wpa_supplicant.conf

	# An empty root password means login without one. '*' matches no password.
	sed -i 's/^root:[^:]*:/root:*:/' $R${sysconfdir}/shadow

	# The userconf.txt user is added to wheel.
	grep -q '^%wheel ALL=(ALL:ALL) ALL' $R${sysconfdir}/sudoers || \
		sed -i '$a %wheel ALL=(ALL:ALL) ALL' $R${sysconfdir}/sudoers

	# The image is public: fail if any secret slipped in.
	for f in etc/ssh/ssh_host_*key* root/.ssh/authorized_keys etc/wpa_supplicant.conf etc/wpa_supplicant/*.conf; do
		for hit in $R/$f; do
			if [ -e "$hit" ]; then
				bbfatal "rpi5os: в образі не має бути ${hit#$R}"
			fi
		done
	done

	# Nor the builder's home path (it carries the user name).
	case "${TOPDIR}" in
		/home/?*)
			home=$(echo "${TOPDIR}" | cut -d/ -f1-3)/
			leaks=$(grep -rlF -- "$home" $R 2>/dev/null || true)
			if [ -n "$leaks" ]; then
				bbfatal "rpi5os: в образі є шлях $home: $leaks"
			fi
			;;
	esac
}
