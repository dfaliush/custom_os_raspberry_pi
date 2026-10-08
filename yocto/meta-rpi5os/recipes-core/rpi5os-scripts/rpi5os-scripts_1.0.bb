SUMMARY = "rpi5os: first-boot config from the boot partition, Wi-Fi, SSD fallback"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = " \
    file://common.sh \
    file://bootcfg.sh \
    file://fallback.sh \
    file://boot-ssd \
    file://ssh-keys-only \
    file://rpi5os-bootcfg.service \
    file://rpi5os-fallback.service \
    file://50-wlan0.network \
    file://10-rpi5os.conf \
    file://10-rpi5os-watchdog.conf \
"
S = "${UNPACKDIR}"

inherit systemd allarch

SYSTEMD_SERVICE:${PN} = "rpi5os-bootcfg.service rpi5os-fallback.service"

do_install () {
	install -d ${D}${libdir}/rpi5os
	install -m 0644 ${S}/common.sh ${D}${libdir}/rpi5os/
	install -m 0755 ${S}/bootcfg.sh ${S}/fallback.sh ${D}${libdir}/rpi5os/

	install -d ${D}${sbindir}
	install -m 0755 ${S}/boot-ssd ${S}/ssh-keys-only ${D}${sbindir}/

	install -d ${D}${systemd_system_unitdir}
	install -m 0644 ${S}/rpi5os-bootcfg.service ${S}/rpi5os-fallback.service ${D}${systemd_system_unitdir}/

	install -d ${D}${sysconfdir}/systemd/network
	install -m 0644 ${S}/50-wlan0.network ${D}${sysconfdir}/systemd/network/

	install -d ${D}${sysconfdir}/ssh/sshd_config.d
	install -m 0644 ${S}/10-rpi5os.conf ${D}${sysconfdir}/ssh/sshd_config.d/

	install -d ${D}${sysconfdir}/systemd/system.conf.d
	install -m 0644 ${S}/10-rpi5os-watchdog.conf ${D}${sysconfdir}/systemd/system.conf.d/

	# wpa_supplicant ships the template unit disabled; enable it for wlan0.
	install -d ${D}${sysconfdir}/systemd/system/multi-user.target.wants
	ln -sf ${systemd_system_unitdir}/wpa_supplicant-nl80211@.service \
		${D}${sysconfdir}/systemd/system/multi-user.target.wants/wpa_supplicant-nl80211@wlan0.service
}

FILES:${PN} += "${libdir}/rpi5os ${systemd_system_unitdir} ${sysconfdir}"
RDEPENDS:${PN} = "shadow wpa-supplicant openssh-sshd systemd"
