from glob import glob

from setuptools import find_packages, setup

package_name = 'counter_pkg'

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
    description='rpi5os: counter publisher/subscriber demo for ROS 2',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'counter_publisher = counter_pkg.publisher:main',
            'counter_subscriber = counter_pkg.subscriber:main',
            'counter_control = counter_pkg.control:main',
        ],
    },
)
