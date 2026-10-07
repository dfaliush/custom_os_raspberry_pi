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
counter_control: start or stop the counter through the publisher's ~/enable service.

Usage: ros2 run counter_pkg counter_control start|stop
"""

import sys

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_srvs.srv import SetBool


class CounterControl(Node):
    """One-shot service client for /counter_publisher/enable."""

    def __init__(self):
        super().__init__('counter_control')
        self.declare_parameter('service', '/counter_publisher/enable')
        service = self.get_parameter('service').value
        self._client = self.create_client(SetBool, service)

    def set_enabled(self, enabled, timeout_sec=5.0):
        if not self._client.wait_for_service(timeout_sec):
            self.get_logger().error(f'service {self._client.srv_name} not available')
            return False
        future = self._client.call_async(SetBool.Request(data=enabled))
        rclpy.spin_until_future_complete(self, future, timeout_sec=timeout_sec)
        if future.result() is None:
            self.get_logger().error('no response from service')
            return False
        self.get_logger().info(future.result().message)
        return future.result().success


def main(args=None):
    rclpy.init(args=args)
    argv = rclpy.utilities.remove_ros_args(args if args is not None else sys.argv)
    if len(argv) != 2 or argv[1] not in ('start', 'stop'):
        print('usage: counter_control start|stop', file=sys.stderr)
        rclpy.try_shutdown()
        return 2
    node = CounterControl()
    try:
        ok = node.set_enabled(argv[1] == 'start')
    except (KeyboardInterrupt, ExternalShutdownException):
        ok = False
    finally:
        rclpy.try_shutdown()
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
