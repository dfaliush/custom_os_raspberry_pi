# Власних пакетів поки немає: усе, що потрібно, вже є в Buildroot.
# Коли з'являться, вони лягатимуть у package/<назва>/ і підхоплюватимуться так:
include $(sort $(wildcard $(BR2_EXTERNAL_RPI5OS_PATH)/package/*/*.mk))
