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
"""camera_node -> detector_node -> decision_node."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    arg = LaunchConfiguration
    return LaunchDescription([
        DeclareLaunchArgument('source', default_value='camera',
                              description='camera, or a directory of images / a video'),
        DeclareLaunchArgument('model_dir', default_value='',
                              description='empty: /var/lib/rpi5os-vision/model, '
                                          'then /usr/share/rpi5os-vision/model'),
        DeclareLaunchArgument('target_class', default_value='',
                              description='empty: any class'),
        DeclareLaunchArgument('stream_port', default_value='8000',
                              description='MJPEG with boxes; 0 disables'),
        # respawn: a node that dies comes back in 2 s. Without it the others
        # keep running, so systemd never restarts the launch, and a crashed
        # detector left decision_node in STOP for good.
        Node(package='vision_pkg', executable='camera_node', output='screen',
             respawn=True, respawn_delay=2.0,
             parameters=[{'source': arg('source')}]),
        Node(package='vision_pkg', executable='detector_node', output='screen',
             respawn=True, respawn_delay=2.0,
             parameters=[{'model_dir': arg('model_dir'),
                          'target_class': arg('target_class'),
                          'stream_port': ParameterValue(arg('stream_port'), value_type=int)}]),
        Node(package='vision_pkg', executable='decision_node', output='screen',
             respawn=True, respawn_delay=2.0),
    ])
