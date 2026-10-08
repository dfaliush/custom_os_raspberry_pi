# A kernel panic reboots the Pi in 10 s instead of leaving it hung (fan at
# full speed, unreachable). If the SD no longer boots, BOOT_ORDER moves on to
# the SSD. A hang without a panic is the watchdog's job (rpi5os-scripts).
CMDLINE:append = " panic=10"
