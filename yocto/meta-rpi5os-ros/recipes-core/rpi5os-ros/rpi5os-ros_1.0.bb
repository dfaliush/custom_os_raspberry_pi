SUMMARY = "rpi5os: ROS 2 environment for login shells and the counter nodes as a systemd service"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = " \
    file://ros2.sh \
    file://rpi5os-counter.service \
"
S = "${UNPACKDIR}"

inherit systemd allarch

SYSTEMD_SERVICE:${PN} = "rpi5os-counter.service"

do_install () {
	install -d ${D}${sysconfdir}/profile.d
	sed 's/@ROS_DISTRO@/${ROS_DISTRO}/g' ${S}/ros2.sh > ${D}${sysconfdir}/profile.d/ros2.sh
	chmod 0644 ${D}${sysconfdir}/profile.d/ros2.sh

	install -d ${D}${systemd_system_unitdir}
	sed 's/@ROS_DISTRO@/${ROS_DISTRO}/g' ${S}/rpi5os-counter.service > ${D}${systemd_system_unitdir}/rpi5os-counter.service
	chmod 0644 ${D}${systemd_system_unitdir}/rpi5os-counter.service
}

FILES:${PN} += "${sysconfdir}/profile.d ${systemd_system_unitdir}"
RDEPENDS:${PN} = "counter-pkg ros-workspace ros2launch"
