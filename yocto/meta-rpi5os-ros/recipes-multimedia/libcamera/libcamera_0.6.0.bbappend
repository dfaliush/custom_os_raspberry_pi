# libcamera 0.6.0 from the Raspberry Pi fork instead of git.libcamera.org.
#
# Upstream libcamera expects the mainline rp1-cfe driver (entity names,
# links, embedded data). meta-raspberrypi builds the Raspberry Pi kernel,
# whose rp1-cfe differs: with upstream 0.6.0 the rpi/pisp handler finds no
# camera, and with only the names patched it aborts on the CFE links. The
# fork is what Raspberry Pi OS runs on this kernel. Same 0.6.0 API, so
# rpicam-apps and the rest of the build stay as they are.
SRC_URI:remove = "git://git.libcamera.org/libcamera/libcamera.git;protocol=https;branch=master;tag=v${PV}"
SRC_URI:prepend = "git://github.com/raspberrypi/libcamera.git;protocol=https;nobranch=1 "
# v0.6.0+rpt20251202
SRCREV = "f0e40f1c50bd0afe65727d6e407d0dcb42666ada"
