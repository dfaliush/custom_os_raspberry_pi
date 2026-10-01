SUMMARY = "rpi5os: example configs for the boot partition"
DESCRIPTION = "Templates for userconf.txt and wpa_supplicant.conf, visible on the FAT \
partition from any PC after flashing. Same files as in the Buildroot image."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://userconf.txt.example file://wpa_supplicant.conf.example"
S = "${UNPACKDIR}"

inherit deploy nopackages

do_configure[noexec] = "1"
do_compile[noexec] = "1"

do_deploy () {
	install -d ${DEPLOYDIR}/rpi5os-bootfs
	install -m 0644 ${S}/userconf.txt.example ${S}/wpa_supplicant.conf.example ${DEPLOYDIR}/rpi5os-bootfs/
}
addtask deploy after do_install before do_build
