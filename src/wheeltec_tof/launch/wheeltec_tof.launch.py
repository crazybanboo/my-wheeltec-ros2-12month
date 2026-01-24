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
    tf_x = '0.1414'
    tf_y = '-0.1414'
    tf_z = '0.0'
    tf_yaw = '-0.7854' # 右转45°
    tf_pitch = '0.0'
    tf_roll = '0.0'

    return LaunchDescription([
        # DeclareLaunchArgument 是用来“定义”开关的, 而 LaunchConfiguration 是用来“读取”开关状态的。
        # 如果你输入：ros2 launch your_package your_launch.py i2c_bus:=1 ,DeclareLaunchArgument 抓到了 1。LaunchConfiguration 把 1 传给了 Node。你的 TOF 传感器就会去打开 /dev/i2c-1。
        DeclareLaunchArgument('i2c_bus', default_value='0'),
        DeclareLaunchArgument('frame_id', default_value='tof_link'),
        DeclareLaunchArgument('collision_threshold', default_value='0.2'),
        
        # TOF Node
        Node(
            package='wheeltec_tof', # 功能包的名字。ROS 2 会去这个包里找程序。
            executable='vl53l1x_node', # 可执行文件的名字（在 setup.py 或 CMakeLists.txt 中定义的入口）。
            name='vl53l1x_node', # 节点启动后的运行名称。如果你有多个传感器，可以通过改名来区分（如 tof_front, tof_back）。
            # output='screen', # 关键调试参数。设置为 screen 后，该节点的 log 信息（如距离数值、错误报警）会直接打印在你的终端屏幕上。
            parameters=[{ # 这是核心配置项，以字典形式传递给硬件：
                'i2c_bus': i2c_bus, # 指定传感器接在主板的哪个 I2C 总线（例如 1 代表 /dev/i2c-1）。
                'frame_id': frame_id, # 给传感器数据打上“坐标系标签”，告诉系统这些数据是从哪个位置发出的。
                'collision_threshold': collision_threshold, # 碰撞阈值。当传感器检测到障碍物小于这个距离时，可能会触发避障逻辑。
            }]
        ),

        # Static TF: base_link -> tof_link
        # Format: x y z yaw pitch roll frame_id child_frame_id
        # 静态坐标变换节点, 这个节点非常重要，它告诉 ROS “传感器安装在机器人的什么位置”。
        Node(
            package='tf2_ros',
            executable='static_transform_publisher', # 这是 ROS 2 官方提供的标准工具，不需要你自己写代码，直接调用即可。
            name='tof_static_tf',
            # tf_x, tf_y, tf_z 偏移量（单位：米）。相对于机器人中心（base_link），传感器装在前方多少米、左边多少米、高度是多少。
            # tf_yaw, tf_pitch, tf_roll: 旋转角度（单位：弧度）。 yaw: 偏航角（左右转）。 pitch: 俯仰角（上下抬头）。roll: 翻滚角（侧倾）。
            # 'base_link' 父坐标系。通常是机器人的旋转中心。
            # frame_id: 子坐标系。必须和上面 TOF 节点里定义的 frame_id 完全一致。
            arguments=[tf_x, tf_y, tf_z, tf_yaw, tf_pitch, tf_roll, 'base_link', frame_id] 
        )
    ])
