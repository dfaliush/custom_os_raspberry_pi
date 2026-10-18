# ROS 2 Jazzy on top of rpi5os-image: runtime, CLI, the official Python demo
# nodes, our counter nodes and the vision stack (camera, ncnn detector,
# vision_pkg nodes). ROS lands in /opt/ros/jazzy, as on Ubuntu.
IMAGE_INSTALL:append = " \
    ros-workspace ros-environment \
    rclpy rmw-implementation rmw-fastrtps-cpp \
    ros2cli ros2cli-common-extensions \
    launch-ros ros2launch \
    demo-nodes-py \
    counter-pkg \
    rpi5os-ros \
    libcamera-apps \
    rpi5os-vision \
    vision-interfaces vision-pkg \
"
