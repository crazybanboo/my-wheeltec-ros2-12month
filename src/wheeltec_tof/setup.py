from setuptools import find_packages, setup

package_name = 'wheeltec_tof'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/wheeltec_tof.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='wheeltec',
    maintainer_email='704996718@qq.com',
    description='VL53L1X TOF sensor driver for WHEELTEC robot',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'vl53l1x_node = wheeltec_tof.vl53l1x_node:main',
            'vl53l1x_array_node = wheeltec_tof.vl53l1x_array_node:main'
        ],
    },
)
