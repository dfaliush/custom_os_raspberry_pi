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
camera_node: camera (rpicam-vid) or files -> sensor_msgs/Image on camera/image_raw.

source:=camera reads the IMX219; any other value is a directory of images or
a video, replayed at fps (loop:=true by default) - for running without a Pi.
If the camera is lost, frames stop and the capture restarts every 2 s.
"""

import threading

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rpi5os_vision.camera import CameraLost, RpicamSource
from rpi5os_vision.source import FileSource, SourceEnded
from sensor_msgs.msg import Image

from .image import to_msg
from .qos import latest_frame_qos

RETRY = 2.0


class CameraNode(Node):
    """Publish frames from a background thread; reopen the camera if lost."""

    def __init__(self):
        super().__init__('camera_node')
        self.source = self.declare_parameter('source', 'camera').value
        self.width = self.declare_parameter('width', 640).value
        self.height = self.declare_parameter('height', 480).value
        self.fps = self.declare_parameter('fps', 30).value
        self.loop = self.declare_parameter('loop', True).value
        self.frame_id = self.declare_parameter('frame_id', 'camera').value
        self.pub = self.create_publisher(Image, 'camera/image_raw', latest_frame_qos())
        self.stopping = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self.get_logger().info(
            f'source {self.source}, {self.width}x{self.height} @ {self.fps} fps'
            ' -> camera/image_raw')

    def _open(self):
        if self.source == 'camera':
            return RpicamSource(self.width, self.height, self.fps)
        return FileSource(self.source, loop=self.loop, fps=self.fps)

    def _run(self):
        while not self.stopping.is_set():
            src = self._open()
            try:
                while not self.stopping.is_set():
                    frame, _ = src.read()
                    self.pub.publish(to_msg(frame, self.get_clock().now().to_msg(), self.frame_id))
            except CameraLost as e:
                self.get_logger().warning(f'camera lost: {e}; retry in {RETRY:.0f} s')
                self.stopping.wait(RETRY)
            except SourceEnded:
                self.get_logger().info('end of files')
                return
            finally:
                src.close()

    def destroy_node(self):
        self.stopping.set()
        self.thread.join(timeout=3)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = CameraNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
