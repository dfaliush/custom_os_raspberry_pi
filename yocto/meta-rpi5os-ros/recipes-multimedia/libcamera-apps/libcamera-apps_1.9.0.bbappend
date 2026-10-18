# rpicam-apps 1.9.0 against libcamera 0.6.0 (see PREFERRED_VERSION_libcamera).
FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
SRC_URI += "file://0001-libcamera-0.6-model-string-view.patch"
