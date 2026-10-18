from glob import glob

from setuptools import find_packages, setup

package_name = 'vision_pkg'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Dmytro Faliush',
    maintainer_email='17968056+dfaliush@users.noreply.github.com',
    description='rpi5os: camera, YOLO (NCNN) detector and decision nodes',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'camera_node = vision_pkg.camera_node:main',
            'detector_node = vision_pkg.detector_node:main',
            'decision_node = vision_pkg.decision_node:main',
        ],
    },
)
