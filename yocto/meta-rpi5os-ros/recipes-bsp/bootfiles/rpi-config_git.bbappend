# IMX219 camera in the CAM/DISP 0 connector. Not RASPBERRYPI_CAMERA_V2: that
# writes dtoverlay=imx219 without ",cam0", which on the Pi 5 means CAM/DISP 1.
# No auto-detect: the image says which sensor and which port.
RPI_EXTRA_CONFIG:append = "\n# rpi5os: IMX219 in CAM/DISP 0\ncamera_auto_detect=0\ndtoverlay=imx219,cam0\n"
