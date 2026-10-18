# Copyright 2026 Dmytro Faliush
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""sensor_msgs/Image <-> numpy without cv_bridge."""

from builtin_interfaces.msg import Time
import numpy as np
import pytest
from vision_pkg.image import from_msg, to_msg


def test_roundtrip():
    img = np.random.default_rng(0).integers(0, 255, (48, 64, 3), dtype=np.uint8)
    msg = to_msg(img, Time(sec=5), 'camera')
    assert (msg.width, msg.height, msg.encoding, msg.step) == (64, 48, 'bgr8', 64 * 3)
    assert msg.header.frame_id == 'camera' and msg.header.stamp.sec == 5
    np.testing.assert_array_equal(from_msg(msg), img)


def test_padded_step():
    img = np.random.default_rng(1).integers(0, 255, (48, 64, 3), dtype=np.uint8)
    msg = to_msg(img, Time(), 'camera')
    rows = np.zeros((48, 64 * 3 + 16), np.uint8)
    rows[:, :64 * 3] = img.reshape(48, -1)
    msg.step, msg.data = 64 * 3 + 16, rows.tobytes()
    np.testing.assert_array_equal(from_msg(msg), img)


def test_rejects_rgb8():
    msg = to_msg(np.zeros((4, 4, 3), np.uint8), Time(), 'camera')
    msg.encoding = 'rgb8'
    with pytest.raises(ValueError):
        from_msg(msg)
