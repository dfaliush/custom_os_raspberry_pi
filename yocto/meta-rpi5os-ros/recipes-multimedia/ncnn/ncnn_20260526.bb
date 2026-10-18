SUMMARY = "ncnn: neural network inference on CPU, with Python bindings"
DESCRIPTION = "Runs the YOLO model exported by Ultralytics (format=ncnn) for rpi5os-vision."
HOMEPAGE = "https://github.com/Tencent/ncnn"
SECTION = "libs"
# ncnn itself is BSD-3-Clause; LICENSE.txt lists bundled code under Zlib and BSD-2-Clause.
LICENSE = "BSD-3-Clause & Zlib & BSD-2-Clause"
LIC_FILES_CHKSUM = "file://LICENSE.txt;md5=d2141d1a2c978a089d3de7a67db0bbd2"

# Tag 20260526, the same release as the PyPI wheel ncnn==1.0.20260526 used on the PC.
SRC_URI = "git://github.com/Tencent/ncnn.git;protocol=https;nobranch=1"
SRCREV = "e54f7b1f88434e1d844ea0551b880a1cfb079ce1"

inherit cmake python3native python3targetconfig

# pybind11 from meta-python instead of ncnn's git submodule.
DEPENDS = "python3 python3-pybind11"

EXTRA_OECMAKE = " \
    -DNCNN_VULKAN=OFF \
    -DNCNN_SHARED_LIB=ON \
    -DNCNN_BUILD_TOOLS=OFF \
    -DNCNN_BUILD_EXAMPLES=OFF \
    -DNCNN_BUILD_BENCHMARK=OFF \
    -DNCNN_BUILD_TESTS=OFF \
    -DNCNN_PYTHON=ON \
    -DNCNN_SYSTEM_PYBIND11=ON \
    -DPYBIND11_USE_CROSSCOMPILING=ON \
    -DPython_EXECUTABLE=${PYTHON} \
"

# ncnn's CMake has no install rule for the Python module: put the package
# (python/ncnn/*.py) and the built extension into site-packages.
do_install:append () {
	dst=${D}${PYTHON_SITEPACKAGES_DIR}/ncnn
	install -d $dst
	cp -r --no-preserve=ownership ${S}/python/ncnn/. $dst/
	find $dst -name '*.so' -delete
	install -m 0755 ${B}/python/ncnn/ncnn*.so $dst/
}

PACKAGES =+ "python3-ncnn"
FILES:python3-ncnn = "${PYTHON_SITEPACKAGES_DIR}/ncnn"
RDEPENDS:python3-ncnn = "${PN} python3-core python3-numpy"

# pybind11_add_module strips the extension in Release builds itself; ncnn's
# CMake has no switch for it. libncnn.so is stripped by Yocto as usual.
# The check runs before the split into packages, so it reads the recipe's PN.
INSANE_SKIP:${PN} += "already-stripped"
