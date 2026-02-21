# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a ROS2 Humble Hawksbill workspace for Wheeltec robotics platforms. It contains a complete robotics software stack including hardware drivers, SLAM, navigation, vision, and AI components for commercial educational/research robots.

## Build System

**Build Tool:** `colcon` (ROS2's standard build tool)

```bash
# Build entire workspace
colcon build

# Build with symlink install (recommended for development - launch file changes don't require rebuild)
colcon build --symlink-install

# Build specific package
colcon build --packages-select turn_on_wheeltec_robot [--symlink-install]

# Build with limited parallel workers (useful for memory-constrained systems)
colcon build --parallel-workers 2 [--symlink-install]

# Clean build artifacts
rm -rf build/ install/ log/
```

**Package Types:**
- C++ packages use `ament_cmake`
- Python packages use `ament_python` with setuptools

## Testing

```bash
# Test entire workspace
colcon test

# Test specific package
colcon test --packages-select turn_on_wheeltec_robot

# View test results
colcon test-result --verbose
```

**Python Tests:** Each Python package typically has these test files:
- `test_copyright.py` - License header checking (ament_copyright)
- `test_flake8.py` - Python style checking (ament_flake8)
- `test_pep257.py` - Docstring checking (ament_pep257)

## Key Launch Commands

**Core Robot:**
```bash
# Start robot base (main command)
ros2 launch turn_on_wheeltec_robot turn_on_wheeltec_robot.launch.py

# Start sensors (lidar + camera)
ros2 launch turn_on_wheeltec_robot wheeltec_sensors.launch.py

# Keyboard control
ros2 run wheeltec_robot_keyboard wheeltec_keyboard
```

**SLAM (3 options):**
```bash
# Gmapping
ros2 launch slam_gmapping slam_gmapping.launch.py

# SLAM Toolbox
ros2 launch wheeltec_slam_toolbox online_async_launch.py

# Cartographer
ros2 launch wheeltec_cartographer cartographer.launch.py

# Save map
ros2 launch wheeltec_nav2 save_map.launch.py
```

**Navigation:**
```bash
ros2 launch wheeltec_nav2 wheeltec_nav2.launch.py
```

## Architecture

### Hardware Abstraction Layer

**`turn_on_wheeltec_robot`** - Main robot control node (`src/wheeltec_robot.cpp`)
- Communicates with STM32 microcontroller via serial port (`/dev/ttyUSB0`)
- Protocol: Custom binary protocol with BCC checksum (FRAME_HEADER=0x7B, FRAME_TAIL=0x7D)
- Publishes: odometry, IMU (MPU6050/H30), battery voltage, ultrasonic sensors
- Subscribes: cmd_vel (Twist messages)
- Supports multiple robot kinematics: differential drive, Ackermann, Mecanum, Omni, 4WD

**Key Data Structures:**
- `RECEIVE_DATA` (24 bytes): Speed, voltage, IMU data from STM32
- `SEND_DATA` (11 bytes): Velocity commands to STM32
- `DISTANCE_DATA` (19 bytes): 8 ultrasonic sensor readings

### Sensor Drivers

- **`wheeltec_lidar_ros2/`** - LiDAR drivers (RPLidar, LD LiDAR, LS LiDAR)
- **`ros2_astra_camera-master/`** - Astra depth camera (Orbbec)
- **`yesense_ros2/`** - IMU driver (H30 model)
- **`usb_cam-ros2/`** - USB camera driver
- **`wheeltec_gps/`** - UBlox GPS driver
- **`wheeltec_tof/`** - VL53L1X TOF传感器阵列驱动 (支持8个传感器通过TCA9548A I2C扩展板)

### SLAM Stack

- **`wheeltec_robot_slam/`** - Contains three SLAM implementations:
  - `openslam_gmapping/` - Gmapping ROS2 port
  - `wheeltec_slam_toolbox/` - SLAM Toolbox wrapper
  - `wheeltec_cartographer/` - Google Cartographer wrapper
  - `orb_slam_2_ros-ros2/` - ORB-SLAM2 visual SLAM

### Navigation Stack

- **`navigation2-humble/`** - Full Nav2 stack (custom build)
- **`wheeltec_robot_nav2/`** - Wheeltec-specific Nav2 configurations
- **`wheeltec_path_follow/`** - Path recording and playback

### AI/Vision Features

- **`simple_follower_ros2/`** - Laser follower, line follower, visual follower
- **`wheeltec_robot_kcf/`** - KCF tracker
- **`wheeltec_bodyreader/`** - Skeleton detection and pose control
- **`aruco_ros-humble-devel/`** - AR tag detection
- **`wheeltec_robot_rtab/`** - RTAB-Map visual SLAM

### Voice/Interaction

- **`wheeltec_mic/`** - Microphone array
- **`wheeltec_aiui/`** - AI UI with Deepseek integration
- **`tts_make_ros2/`** - Text-to-speech

### Communication

- **`wheeltec_robot_msg/`** - Custom message types
- **`wheeltec_rrt_msg/`** - RRT exploration messages
- **`depend/serial_ros2/`** - Serial library dependency
- **`depend/ackermann_msgs-ros2/`** - Ackermann steering messages

## Configuration

**Robot Model Selection:** Configured via launch parameters in `turn_on_wheeltec_robot.launch.py`. Supported models include:
- Differential: mini_mec, senior_mec, flagship_mec, S100, S200, S300
- Ackermann: mini_akm, senior_akm, flagship_akm, V550, V650
- Omni: mini_omni, senior_omni
- 4WD: mini_tank, senior_tank

**Odometry Calibration:** Parameters in `wheeltec_robot.cpp`:
- `odom_x_scale`, `odom_y_scale` - Linear correction
- `odom_z_scale_positive`, `odom_z_scale_negative` - Angular correction

**IMU Configuration:**
- GYROSCOPE_RATIO = 0.00026644 (rad conversion)
- ACCEl_RATIO = 1671.84 (m/s² conversion)

**TOF传感器配置:**
- 使用VL53L1X传感器，通过TCA9548A I2C扩展板连接最多8个传感器
- 测距范围：最大4米
- 用途：障碍物检测、边缘检测

## Dependencies

Install all ROS dependencies:
```bash
rosdep install --from-paths src --ignore-src -r -y
```

Key external dependencies:
- ROS2 Humble base
- `serial` library (in `depend/serial_ros2/`)
- OpenCV (for vision packages)
- PCL (for point cloud processing)

## Code Style

**注释规范:**
- 所有注释使用中文编写
- 代码提交信息(commit message)使用中文描述

**C++:**
- Google style-based (see `ros2_astra_camera-master/.clang-format`)
- 100 column limit
- 2-space indentation
- Compiler flags: `-Wall -Wextra -Wpedantic`

**Python:**
- ament_flake8 for linting
- ament_pep257 for docstrings

## Common Development Tasks

**View TF tree:**
```bash
ros2 run tf2_tools view_frames
```

**View topics:**
```bash
rqt_graph
```

**View camera feed:**
```bash
rqt_image_view
```

**SSH to robot:**
```bash
ssh -Y wheeltec@192.168.0.100
```

**NFS mount (for development):**
```bash
sudo mount -t nfs 192.168.0.100:/home/wheeltec/wheeltec_ros2 /mnt
```

## File Locations

- Launch files: `src/<package>/launch/`
- Config files: `src/<package>/config/`
- URDF models: `src/wheeltec_robot_urdf/`
- Maps: `src/wheeltec_robot_nav2/map/`
