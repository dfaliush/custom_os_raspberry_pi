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
"""
Decision logic: target offset -> STOP / TURN_LEFT / TURN_RIGHT / MOVE_FORWARD.

AI result -> validation -> decision -> action: a stale, missing or unsure
detection is STOP, never a guess. Pure functions, so the table is tested
without ROS.
"""

from dataclasses import dataclass

STOP = 'STOP'
TURN_LEFT = 'TURN_LEFT'
TURN_RIGHT = 'TURN_RIGHT'
MOVE_FORWARD = 'MOVE_FORWARD'


@dataclass(frozen=True)
class DecisionParams:
    """Thresholds and speeds; decision_node exposes each as a parameter."""

    conf_threshold: float = 0.6
    deadband: float = 0.15
    stale_timeout: float = 0.5
    forward_speed: float = 0.2
    turn_speed: float = 0.5


@dataclass(frozen=True)
class TargetSample:
    """The last /target, with the node's monotonic time when it arrived."""

    detected: bool
    confidence: float
    dx: float
    received: float


def decide(sample, now, p):
    """Return the command for the last target sample at monotonic time now."""
    if sample is None or now - sample.received > p.stale_timeout:
        return STOP
    if not sample.detected or sample.confidence < p.conf_threshold:
        return STOP
    if sample.dx < -p.deadband:
        return TURN_LEFT
    if sample.dx > p.deadband:
        return TURN_RIGHT
    return MOVE_FORWARD


def twist_for(command, p):
    """(linear.x, angular.z) for a command; +z turns left (REP 103)."""
    return {
        STOP: (0.0, 0.0),
        MOVE_FORWARD: (p.forward_speed, 0.0),
        TURN_LEFT: (0.0, p.turn_speed),
        TURN_RIGHT: (0.0, -p.turn_speed),
    }[command]
