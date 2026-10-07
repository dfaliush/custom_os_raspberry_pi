# ROS 2 Jazzy on top of rpi5os-image: runtime, CLI, the official Python demo
# nodes and our counter nodes. Everything lands in /opt/ros/jazzy, as on Ubuntu.
IMAGE_INSTALL:append = " \
    ros-workspace ros-environment \
    rclpy rmw-implementation rmw-fastrtps-cpp \
    ros2cli ros2cli-common-extensions \
    launch-ros ros2launch \
    demo-nodes-py \
    counter-pkg \
    rpi5os-ros \
"
