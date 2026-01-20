import os
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    # Parameters for the TOF node
    i2c_bus = LaunchConfiguration('i2c_bus', default='0')
    frame_id = LaunchConfiguration('frame_id', default='tof_link')
    collision_threshold = LaunchConfiguration('collision_threshold', default='0.2')

    # Static TF parameters (relative to base_link)
    # Default: 0.1m in front, 0.0m left/right, 0.1m height
    tf_x = LaunchConfiguration('tf_x', default='0.1414')
    tf_y = LaunchConfiguration('tf_y', default='-0.1414')
    tf_z = LaunchConfiguration('tf_z', default='0.0')
    tf_yaw = LaunchConfiguration('tf_yaw', default='-0.7854') # 右转45°
    tf_pitch = LaunchConfiguration('tf_pitch', default='0.0')
    tf_roll = LaunchConfiguration('tf_roll', default='0.0')

    return LaunchDescription([
        DeclareLaunchArgument('i2c_bus', default_value='0'),
        DeclareLaunchArgument('frame_id', default_value='tof_link'),
        DeclareLaunchArgument('collision_threshold', default_value='0.2'),
        
        # TOF Node
        Node(
            package='wheeltec_tof',
            executable='vl53l1x_node',
            name='vl53l1x_node',
            output='screen',
            parameters=[{
                'i2c_bus': i2c_bus,
                'frame_id': frame_id,
                'collision_threshold': collision_threshold,
            }]
        ),

        # Static TF: base_link -> tof_link
        # Format: x y z yaw pitch roll frame_id child_frame_id
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='tof_static_tf',
            arguments=[tf_x, tf_y, tf_z, tf_yaw, tf_pitch, tf_roll, 'base_link', frame_id]
        )
    ])
