# Same fields as the Buildroot image, so the device tells which build is running.
OS_RELEASE_FIELDS:append = " VARIANT_ID IMAGE_ID IMAGE_VERSION"
VARIANT_ID = "rpi5os"
IMAGE_ID = "rpi5os-yocto"
IMAGE_VERSION = "${DISTRO_VERSION}"
