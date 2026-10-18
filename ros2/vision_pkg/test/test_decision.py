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
"""The decision table and the QA checklist from the lecture, one test per row."""

from vision_pkg.decision import (
    decide, DecisionParams, MOVE_FORWARD, STOP, TargetSample, TURN_LEFT, TURN_RIGHT, twist_for)

P = DecisionParams()


def s(**kw):
    return TargetSample(**{'detected': True, 'confidence': .9, 'dx': 0.0, 'received': 10.0, **kw})


def test_no_message_yet_stops():
    assert decide(None, 10.0, P) == STOP


def test_stale_target_stops():            # camera lost / detector crashed
    assert decide(s(), 10.51, P) == STOP


def test_fresh_target_at_the_edge():
    assert decide(s(), 10.49, P) == MOVE_FORWARD


def test_object_absent_stops():
    assert decide(s(detected=False), 10.0, P) == STOP


def test_low_confidence_stops():
    assert decide(s(confidence=.59), 10.0, P) == STOP


def test_threshold_confidence_moves():
    assert decide(s(confidence=.6), 10.0, P) == MOVE_FORWARD


def test_object_left_turns_left():
    assert decide(s(dx=-.16), 10.0, P) == TURN_LEFT


def test_object_right_turns_right():
    assert decide(s(dx=.16), 10.0, P) == TURN_RIGHT


def test_deadband_edge_is_centered():
    assert decide(s(dx=.15), 10.0, P) == MOVE_FORWARD
    assert decide(s(dx=-.15), 10.0, P) == MOVE_FORWARD


def test_params_change_behavior():
    p = DecisionParams(conf_threshold=.95, deadband=.5)
    assert decide(s(confidence=.9), 10.0, p) == STOP
    assert decide(s(confidence=.96, dx=.4), 10.0, p) == MOVE_FORWARD


def test_twist():
    assert twist_for(STOP, P) == (0.0, 0.0)
    assert twist_for(MOVE_FORWARD, P) == (.2, 0.0)
    assert twist_for(TURN_LEFT, P) == (0.0, .5)       # ROS: +z is counter-clockwise (left)
    assert twist_for(TURN_RIGHT, P) == (0.0, -.5)
