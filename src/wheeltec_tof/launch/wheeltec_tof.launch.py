import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    # Parameters for the TOF array node
    i2c_bus = LaunchConfiguration('i2c_bus', default='0')
    tca9548a_addr = LaunchConfiguration('tca9548a_addr', default='0x70')
    vl53l1x_addr = LaunchConfiguration('vl53l1x_addr', default='0x29')
    min_range = LaunchConfiguration('min_range', default='0.01')
    max_range = LaunchConfiguration('max_range', default='4.0')
    collision_threshold = LaunchConfiguration('collision_threshold', default='0.2')
    range_mode = LaunchConfiguration('range_mode', default='1')  # 1=Short, 2=Long
    timing_budget = LaunchConfiguration('timing_budget', default='50')
    inter_measurement = LaunchConfiguration('inter_measurement', default='60')
    publish_rate = LaunchConfiguration('publish_rate', default='10.0')
    power_cycle_on_init = LaunchConfiguration('power_cycle_on_init', default='true')

    # XSHUT pins (BOARD encoding) for 8 sensors
    xshut_pins = LaunchConfiguration('xshut_pins', default='[38, 26, 24, 22, 18, 12, 10, 8]')

    # Frame IDs for 8 sensors (must match URDF)
    frame_ids = LaunchConfiguration(
        'frame_ids',
        default='["tof_link_0", "tof_link_1", "tof_link_2", "tof_link_3", '
                '"tof_link_4", "tof_link_5", "tof_link_6", "tof_link_7"]'
    )

    return LaunchDescription([
        # Declare launch arguments
        DeclareLaunchArgument('i2c_bus', default_value='0',
                              description='I2C bus number (0 for /dev/i2c-0)'),
        DeclareLaunchArgument('tca9548a_addr', default_value='0x70',
                              description='TCA9548A I2C multiplexer address'),
        DeclareLaunchArgument('vl53l1x_addr', default_value='0x29',
                              description='VL53L1X sensor I2C address'),
        DeclareLaunchArgument('xshut_pins', default_value='[38, 26, 24, 22, 18, 12, 10, 8]',
                              description='XSHUT GPIO pins (BOARD encoding) for 8 sensors'),
        DeclareLaunchArgument('frame_ids',
                              default_value='["tof_link_0", "tof_link_1", "tof_link_2", "tof_link_3", '
                                            '"tof_link_4", "tof_link_5", "tof_link_6", "tof_link_7"]',
                              description='TF frame IDs for each sensor (must match URDF)'),
        DeclareLaunchArgument('min_range', default_value='0.01',
                              description='Minimum range in meters'),
        DeclareLaunchArgument('max_range', default_value='4.0',
                              description='Maximum range in meters'),
        DeclareLaunchArgument('collision_threshold', default_value='0.2',
                              description='Collision warning threshold in meters'),
        DeclareLaunchArgument('range_mode', default_value='1',
                              description='Distance mode: 1=Short (up to 1.3m), 2=Long (up to 4m)'),
        DeclareLaunchArgument('timing_budget', default_value='50',
                              description='Measurement timing budget in ms'),
        DeclareLaunchArgument('inter_measurement', default_value='60',
                              description='Inter-measurement period in ms'),
        DeclareLaunchArgument('publish_rate', default_value='10.0',
                              description='Publishing rate in Hz'),
        DeclareLaunchArgument('power_cycle_on_init', default_value='true',
                              description='Power cycle sensors on node initialization'),

        # VL53L1X Array Node
        # Publishes to /tof/range_0 through /tof/range_7
        # Publishes collision warning to /tof/collision_warning
        Node(
            package='wheeltec_tof',
            executable='vl53l1x_array_node',
            name='vl53l1x_array_node',
            output='screen',
            parameters=[{
                'i2c_bus': i2c_bus,
                'tca9548a_addr': tca9548a_addr,
                'vl53l1x_addr': vl53l1x_addr,
                'xshut_pins': xshut_pins,
                'frame_ids': frame_ids,
                'min_range': min_range,
                'max_range': max_range,
                'collision_threshold': collision_threshold,
                'range_mode': range_mode,
                'timing_budget': timing_budget,
                'inter_measurement': inter_measurement,
                'publish_rate': publish_rate,
                'power_cycle_on_init': power_cycle_on_init,
            }]
        ),

        # Note: TF frames (tof_link_0 to tof_link_7) are published by the URDF
        # via robot_state_publisher. No static_transform_publisher needed.
    ])
