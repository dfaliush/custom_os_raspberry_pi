# vision_interfaces from ros2/ in this repo, built the way meta-ros builds its
# generated msg recipes (example-interfaces is the template).
SUMMARY = "rpi5os: TargetOffset message, the target relative to the frame center"
HOMEPAGE = "https://github.com/dfaliush/custom_os_raspberry_pi"
SECTION = "devel"
LICENSE = "Apache-2.0"
LIC_FILES_CHKSUM = "file://LICENSE;md5=3b83ef96387f14655fc854ddc3c6bd57"

inherit ros_distro_${ROS_DISTRO}
inherit ros_component

ROS_CN = "vision_interfaces"
ROS_BPN = "vision_interfaces"

ROS_BUILD_DEPENDS = "std-msgs"
ROS_BUILDTOOL_DEPENDS = " \
    ament-cmake-native \
    rosidl-default-generators-native \
"
ROS_EXPORT_DEPENDS = "std-msgs"
ROS_BUILDTOOL_EXPORT_DEPENDS = ""
ROS_EXEC_DEPENDS = " \
    rosidl-default-runtime \
    std-msgs \
"

# What meta-ros adds to its own msg recipes in bbappends (geometry-msgs): the
# rosidl generators natively, and the target typesupport + runtime, without
# which std_msgs' exported dependencies are not found or link the native ones.
ROS_BUILDTOOL_DEPENDS += " \
    rosidl-parser-native \
    rosidl-adapter-native \
    rosidl-typesupport-fastrtps-cpp-native \
    rosidl-typesupport-fastrtps-c-native \
    python3-numpy-native \
    python3-lark-parser-native \
"
ROS_BUILD_DEPENDS += " \
    rosidl-typesupport-c \
    rosidl-typesupport-cpp \
    rosidl-default-runtime \
"

DEPENDS = "${ROS_BUILD_DEPENDS} ${ROS_BUILDTOOL_DEPENDS}"
DEPENDS += "${ROS_EXPORT_DEPENDS} ${ROS_BUILDTOOL_EXPORT_DEPENDS}"
RDEPENDS:${PN} += "${ROS_EXEC_DEPENDS}"

# Sources straight from the repo: RPI5OS_ROS2_SRC/vision_interfaces (see layer.conf).
FILESEXTRAPATHS:prepend := "${RPI5OS_ROS2_SRC}:"
SRC_URI = "file://vision_interfaces/"
S = "${UNPACKDIR}/vision_interfaces"

ROS_BUILD_TYPE = "ament_cmake"
inherit ros_${ROS_BUILD_TYPE}
