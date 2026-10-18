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
decision_node: target -> cmd_vel (geometry_msgs/Twist) and decision (std_msgs/String).

Publishes on its own timer (rate, 10 Hz), whatever the camera does: when
target stops coming (camera lost, detector crashed) the command becomes
STOP within stale_timeout. Nothing drives motors; cmd_vel is for a motor
controller that is not part of this project.
"""

import time

from geometry_msgs.msg import Twist
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String
from vision_interfaces.msg import TargetOffset

from .decision import decide, DecisionParams, TargetSample, twist_for


class DecisionNode(Node):
    """Turn the latest target offset into a command at a fixed rate."""

    def __init__(self):
        super().__init__('decision_node')
        d = DecisionParams()
        self.p = DecisionParams(
            conf_threshold=self.declare_parameter('conf_threshold', d.conf_threshold).value,
            deadband=self.declare_parameter('deadband', d.deadband).value,
            stale_timeout=self.declare_parameter('stale_timeout', d.stale_timeout).value,
            forward_speed=self.declare_parameter('forward_speed', d.forward_speed).value,
            turn_speed=self.declare_parameter('turn_speed', d.turn_speed).value,
        )
        rate = self.declare_parameter('rate', 10.0).value
        self.sample, self.last = None, None
        self.create_subscription(TargetOffset, 'target', self._on_target, 10)
        self.cmd_pub = self.create_publisher(Twist, 'cmd_vel', 10)
        self.decision_pub = self.create_publisher(String, 'decision', 10)
        self.create_timer(1.0 / rate, self._tick)
        self.get_logger().info(f'{rate:.0f} Hz, {self.p}')

    def _on_target(self, msg):
        # Arrival time on this node's clock: header stamps come from another
        # process and are not compared with it.
        self.sample = TargetSample(msg.detected, msg.confidence, msg.dx, time.monotonic())

    def _tick(self):
        cmd = decide(self.sample, time.monotonic(), self.p)
        lin, ang = twist_for(cmd, self.p)
        twist = Twist()
        twist.linear.x, twist.angular.z = lin, ang
        self.cmd_pub.publish(twist)
        self.decision_pub.publish(String(data=cmd))
        if cmd != self.last:
            s = self.sample
            why = (f'dx={s.dx:+.2f} conf={s.confidence:.2f}' if s and s.detected else 'no target')
            self.get_logger().info(f'{cmd} ({why})')
            self.last = cmd


def main(args=None):
    rclpy.init(args=args)
    node = DecisionNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
