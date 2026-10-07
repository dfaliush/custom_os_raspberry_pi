# counter_pkg from ros2/ in this repo, built the way meta-ros builds its
# generated ament_python recipes (demo-nodes-py is the template).
SUMMARY = "rpi5os: ROS 2 counter publisher, subscriber and start/stop control nodes"
HOMEPAGE = "https://github.com/dfaliush/custom_os_raspberry_pi"
SECTION = "devel"
LICENSE = "Apache-2.0"
LIC_FILES_CHKSUM = "file://LICENSE;md5=3b83ef96387f14655fc854ddc3c6bd57"

inherit ros_distro_${ROS_DISTRO}
inherit ros_component

ROS_CN = "counter_pkg"
ROS_BPN = "counter_pkg"

ROS_BUILD_DEPENDS = ""
ROS_BUILDTOOL_DEPENDS = ""
ROS_EXPORT_DEPENDS = ""
ROS_BUILDTOOL_EXPORT_DEPENDS = ""
# package.xml: rclpy, example_interfaces, std_srvs, launch_ros.
ROS_EXEC_DEPENDS = " \
    example-interfaces \
    launch-ros \
    rclpy \
    std-srvs \
"

DEPENDS = "${ROS_BUILD_DEPENDS} ${ROS_BUILDTOOL_DEPENDS}"
DEPENDS += "${ROS_EXPORT_DEPENDS} ${ROS_BUILDTOOL_EXPORT_DEPENDS}"
RDEPENDS:${PN} += "${ROS_EXEC_DEPENDS}"

# Sources straight from the repo: RPI5OS_ROS2_SRC/counter_pkg (see layer.conf).
FILESEXTRAPATHS:prepend := "${RPI5OS_ROS2_SRC}:"
SRC_URI = "file://counter_pkg/"
S = "${UNPACKDIR}/counter_pkg"

ROS_BUILD_TYPE = "ament_python"
inherit ros_${ROS_BUILD_TYPE}
