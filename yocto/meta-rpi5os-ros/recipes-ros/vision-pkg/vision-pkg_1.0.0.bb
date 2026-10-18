# vision_pkg from ros2/ in this repo: camera, detector and decision nodes.
SUMMARY = "rpi5os: camera, YOLO (NCNN) detector and decision ROS 2 nodes"
HOMEPAGE = "https://github.com/dfaliush/custom_os_raspberry_pi"
SECTION = "devel"
LICENSE = "Apache-2.0"
LIC_FILES_CHKSUM = "file://LICENSE;md5=3b83ef96387f14655fc854ddc3c6bd57"

inherit ros_distro_${ROS_DISTRO}
inherit ros_component

ROS_CN = "vision_pkg"
ROS_BPN = "vision_pkg"

ROS_BUILD_DEPENDS = ""
ROS_BUILDTOOL_DEPENDS = ""
ROS_EXPORT_DEPENDS = ""
ROS_BUILDTOOL_EXPORT_DEPENDS = ""
# package.xml, plus the detector package (not a ROS package: rpi5os-vision).
ROS_EXEC_DEPENDS = " \
    builtin-interfaces \
    geometry-msgs \
    launch-ros \
    python3-numpy \
    python3-opencv \
    rclpy \
    rpi5os-vision \
    sensor-msgs \
    std-msgs \
    vision-interfaces \
"

DEPENDS = "${ROS_BUILD_DEPENDS} ${ROS_BUILDTOOL_DEPENDS}"
DEPENDS += "${ROS_EXPORT_DEPENDS} ${ROS_BUILDTOOL_EXPORT_DEPENDS}"
RDEPENDS:${PN} += "${ROS_EXEC_DEPENDS}"

FILESEXTRAPATHS:prepend := "${RPI5OS_ROS2_SRC}:"
SRC_URI = "file://vision_pkg/"
S = "${UNPACKDIR}/vision_pkg"

ROS_BUILD_TYPE = "ament_python"
inherit ros_${ROS_BUILD_TYPE}
