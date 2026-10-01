# No custom packages yet. Any added under package/<name>/ are picked up here.
include $(sort $(wildcard $(BR2_EXTERNAL_RPI5OS_PATH)/package/*/*.mk))
