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
detector_node: camera/image_raw -> YOLO (NCNN) -> target (vision_interfaces/TargetOffset).

Perception only: where the target is relative to the frame center. Every
processed frame yields one /target, detected or not; what to do about it is
decision_node's job. The subscription keeps one frame (best effort), so a
slow detector skips frames instead of lagging. stream_port > 0 serves the
annotated frames as MJPEG.
"""

import sys
import time

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rpi5os_vision.geometry import target_from
from rpi5os_vision.model import locate, ModelNotFound, validate_class
from rpi5os_vision.stream import annotate, MjpegServer
from rpi5os_vision.yolo_ncnn import Detector
from sensor_msgs.msg import Image
from vision_interfaces.msg import TargetOffset

from .image import from_msg

LOG_EVERY = 5.0


class DetectorNode(Node):
    """Run the detector on the newest frame and publish the target offset."""

    def __init__(self):
        super().__init__('detector_node')
        model_dir = self.declare_parameter('model_dir', '').value
        conf = self.declare_parameter('conf', 0.25).value
        # 2, not 4: 4 ncnn threads powered the Pi 5 off (core current peaks
        # of 9.2 A); see rpi5os_vision.run.
        threads = self.declare_parameter('threads', 2).value
        self.target_class = self.declare_parameter('target_class', '').value
        port = self.declare_parameter('stream_port', 8000).value

        info = locate(model_dir or None)
        validate_class(info, self.target_class)
        self.det = Detector(info, conf=conf, threads=threads)
        self.pub = self.create_publisher(TargetOffset, 'target', 10)
        self.create_subscription(
            Image, 'camera/image_raw', self._on_image, qos_profile_sensor_data)
        self.stream = MjpegServer(port).start() if port else None
        self.frames, self.infer, self.t0 = 0, 0.0, time.monotonic()
        self.get_logger().info(
            f'model {info.dir} ({info.imgsz}px, {len(info.names)} classes), '
            f'target {self.target_class or "any"}'
            + (f', stream http://<pi>:{self.stream.port}/' if self.stream else ''))

    def _on_image(self, msg):
        frame = from_msg(msg)
        dets = self.det.detect(frame)
        t = target_from(dets, msg.width, msg.height, self.target_class)
        out = TargetOffset()
        out.header = msg.header
        out.detected, out.confidence = t.detected, float(t.confidence)
        out.dx, out.dy, out.area = float(t.dx), float(t.dy), float(t.area)
        out.class_name = t.class_name
        self.pub.publish(out)
        if self.stream:
            self.stream.publish(annotate(frame, dets, t))
        self._log(t)

    def _log(self, t):
        self.frames += 1
        self.infer += self.det.last_infer_ms
        dt = time.monotonic() - self.t0
        if dt >= LOG_EVERY:
            seen = (f'{t.class_name} {t.confidence:.2f} dx={t.dx:+.2f}'
                    if t.detected else 'no target')
            self.get_logger().info(
                f'{self.frames / dt:.1f} fps, inference {self.infer / self.frames:.0f} ms, {seen}')
            self.frames, self.infer, self.t0 = 0, 0.0, time.monotonic()

    def destroy_node(self):
        if self.stream:
            self.stream.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    try:
        node = DetectorNode()
    except (ModelNotFound, ValueError) as e:
        print(f'detector_node: {e}', file=sys.stderr)
        rclpy.try_shutdown()
        sys.exit(2)
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
