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
"""counter_subscriber: logs every value received on the counter topic."""

from example_interfaces.msg import Int32
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


class CounterSubscriber(Node):
    """Subscribe to the counter topic and report gaps in the sequence."""

    def __init__(self):
        super().__init__('counter_subscriber')
        self.declare_parameter('topic', 'counter')
        topic = self.get_parameter('topic').value

        self._last = None
        self._subscription = self.create_subscription(Int32, topic, self._on_message, 10)
        self.get_logger().info(f'listening on "{topic}"')

    def _on_message(self, msg):
        if self._last is not None and msg.data != self._last + 1:
            self.get_logger().warning(f'gap: got {msg.data} after {self._last}')
        self._last = msg.data
        self.get_logger().info(f'I heard: {msg.data}')


def main(args=None):
    rclpy.init(args=args)
    node = CounterSubscriber()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        # Also destroys the node. A second Ctrl-C while destroy_node() waits
        # for callbacks would otherwise end in a traceback.
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
