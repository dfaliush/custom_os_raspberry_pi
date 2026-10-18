SUMMARY = "rpi5os: YOLO (NCNN) object detection from the camera, rpi5os-detect"
HOMEPAGE = "https://github.com/dfaliush/custom_os_raspberry_pi"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

inherit python_setuptools_build_meta

# Sources straight from the repo: RPI5OS_VISION_SRC is the vision/ dir (see layer.conf).
FILESEXTRAPATHS:prepend := "${RPI5OS_VISION_SRC}/..:"
SRC_URI = "file://vision/"
S = "${UNPACKDIR}/vision"

# The model in the image; a model copied to /var/lib/rpi5os-vision/model wins
# (rpi5os_vision.model.DEFAULT_DIRS), so a new one needs no reflash.
do_install:append () {
	install -d ${D}${datadir}/rpi5os-vision/model ${D}${localstatedir}/lib/rpi5os-vision/model
	for f in model.ncnn.param model.ncnn.bin metadata.yaml; do
		install -m 0644 ${S}/models/current/$f ${D}${datadir}/rpi5os-vision/model/
	done
}

FILES:${PN} += "${datadir}/rpi5os-vision ${localstatedir}/lib/rpi5os-vision"
RDEPENDS:${PN} = "libcamera-apps python3-modules python3-numpy python3-opencv python3-ncnn python3-pyyaml"
