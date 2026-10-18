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
"""Frames travel with a queue of one: the detector only ever sees the newest."""

from rclpy.qos import HistoryPolicy, ReliabilityPolicy
from vision_pkg.qos import latest_frame_qos


def test_latest_frame_qos_keeps_one_frame():
    q = latest_frame_qos()
    assert q.history == HistoryPolicy.KEEP_LAST
    assert q.depth == 1


def test_latest_frame_qos_is_best_effort():
    assert latest_frame_qos().reliability == ReliabilityPolicy.BEST_EFFORT
