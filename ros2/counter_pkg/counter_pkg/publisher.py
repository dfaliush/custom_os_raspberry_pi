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
counter_publisher: publishes 1, 2, 3, ... as example_interfaces/Int32 on one topic.

The ~/enable service (std_srvs/SetBool) starts (data: true) and stops
(data: false) the counter; the value continues from where it stopped.
"""

from example_interfaces.msg import Int32
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_srvs.srv import SetBool


class CounterPublisher(Node):
    """Publish an increasing counter on a timer; ~/enable starts and stops it."""

    def __init__(self):
        super().__init__('counter_publisher')
        self.declare_parameter('topic', 'counter')
        self.declare_parameter('period', 1.0)
        self.declare_parameter('start_enabled', True)
        topic = self.get_parameter('topic').value
        period = self.get_parameter('period').value
        enabled = self.get_parameter('start_enabled').value

        self._count = 0
        self._publisher = self.create_publisher(Int32, topic, 10)
        self._timer = self.create_timer(period, self._tick)
        if not enabled:
            self._timer.cancel()
        self._service = self.create_service(SetBool, '~/enable', self._on_enable)
        state = 'running' if enabled else 'stopped'
        self.get_logger().info(f'publishing to "{topic}" every {period:g} s, {state}')

    def _on_enable(self, request, response):
        running = not self._timer.is_canceled()
        if request.data and not running:
            self._timer.reset()
            response.message = f'counter started at {self._count + 1}'
        elif not request.data and running:
            self._timer.cancel()
            response.message = f'counter stopped at {self._count}'
        else:
            response.message = f'counter already {"running" if running else "stopped"}'
        response.success = True
        self.get_logger().info(response.message)
        return response

    def _tick(self):
        self._count += 1
        msg = Int32(data=self._count)
        self._publisher.publish(msg)
        self.get_logger().info(f'published {msg.data}')


def main(args=None):
    rclpy.init(args=args)
    node = CounterPublisher()
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
