# Shared by rpi5os init scripts: . /usr/lib/rpi5os/common.sh

# On the FAT partition: readable from Raspberry Pi OS on the SSD even if
# rpi5os never got online.
RPI5OS_LOG=/boot/rpi5os-boot.log

log() {
	# No RTC battery: the date may be 1970, so log uptime too.
	msg="$(date '+%F %T') [up $(cut -d' ' -f1 /proc/uptime)s] $(basename "$0"): $*"
	echo "$msg"
	echo "$msg" >> "$RPI5OS_LOG" 2>/dev/null || true
}
