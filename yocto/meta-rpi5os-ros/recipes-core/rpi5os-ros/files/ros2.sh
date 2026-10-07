# rpi5os: ROS 2 environment for every login shell, as on Ubuntu.
# UDPv4 only: Fast DDS shared memory does not work between different users
# (the counter service runs as root, you log in as your user).
export FASTDDS_BUILTIN_TRANSPORTS=UDPv4
if [ -r /opt/ros/@ROS_DISTRO@/setup.sh ]; then
	. /opt/ros/@ROS_DISTRO@/setup.sh
fi
