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
"""sensor_msgs/Image <-> numpy BGR, without cv_bridge (and its Boost)."""

import numpy as np
from sensor_msgs.msg import Image


def to_msg(bgr, stamp, frame_id='camera'):
    """Wrap an HxWx3 uint8 BGR array as a bgr8 Image."""
    msg = Image()
    msg.header.stamp = stamp
    msg.header.frame_id = frame_id
    msg.height, msg.width = bgr.shape[:2]
    msg.encoding = 'bgr8'
    msg.is_bigendian = 0
    msg.step = msg.width * 3
    msg.data = np.ascontiguousarray(bgr).tobytes()
    return msg


def from_msg(msg):
    """HxWx3 uint8 BGR view of a bgr8 Image; drops row padding."""
    if msg.encoding != 'bgr8':
        raise ValueError(f'encoding {msg.encoding}: потрібен bgr8')
    rows = np.frombuffer(msg.data, np.uint8).reshape(msg.height, msg.step)
    return rows[:, :msg.width * 3].reshape(msg.height, msg.width, 3)
