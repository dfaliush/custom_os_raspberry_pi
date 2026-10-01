# Спільне для init-скриптів rpi5os. Підключається через ". /usr/lib/rpi5os/common.sh".

# Лог на FAT-розділі: його можна прочитати з Raspberry Pi OS на SSD,
# навіть якщо rpi5os так і не вийшла в мережу.
RPI5OS_LOG=/boot/rpi5os-boot.log

log() {
	# RTC без батарейки: дата може бути 1970, тому поруч ще uptime.
	msg="$(date '+%F %T') [up $(cut -d' ' -f1 /proc/uptime)s] $(basename "$0"): $*"
	echo "$msg"
	echo "$msg" >> "$RPI5OS_LOG" 2>/dev/null || true
}
