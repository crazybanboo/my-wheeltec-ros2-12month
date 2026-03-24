# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Wheeltec ROS2 mobile robot platform running on ROS2 Humble. Supports 30+ robot model variants (omni-wheel, mecanum, 4WD, differential, tank) with configurable sensor suites (LiDAR, depth cameras, ToF, IMU, ultrasonic, microphone). Currently configured as **top_omni** with **ls_N10Plus_uart** LiDAR and **H30** IMU.

## Build & Run Commands

```bash
# Build entire workspace
cd ~/wheeltec_ros2 && colcon build

# Build a single package
colcon build --packages-select <package_name>

# Build with dependencies
colcon build --packages-up-to <package_name>

# Source workspace after building
source install/setup.bash

# Launch the robot base
ros2 launch turn_on_wheeltec_robot turn_on_wheeltec_robot.launch.py

# Launch navigation (includes robot base + lidar + nav2)
ros2 launch wheeltec_robot_nav2 wheeltec_nav2.launch.py

# Save map
ros2 launch wheeltec_robot_nav2 save_map.launch.py
```

## Architecture

### Package Organization (`src/`)

**Core robot control:**
- `turn_on_wheeltec_robot` — Main robot node: serial comms with base, publishes odom/IMU/ultrasonic, light strip control, charging. Entry point for most launch sequences.
- `wheeltec_robot_msg` — Custom messages: `Data.msg` (3D vector), `Supersonic.msg` (8-channel ultrasonic)

**Navigation stack:**
- `wheeltec_robot_nav2` — Nav2 configuration, launch files, maps, per-robot-type parameter files in `param/wheeltec_params/param_*.yaml`
- `navigation2-humble` — Modified Nav2 stack (local fork)
- `nav2_waypoint_cycle` — Cyclic waypoint navigation (Python)
- `wheeltec_path_follow` — Path recording and following

**Sensor drivers:**
- `wheeltec_lidar_ros2` — Meta-package for multiple LiDAR drivers (rplidar, lslidar, ldlidar)
- `wheeltec_tof` — VL53L1X Time-of-Flight sensor array (Python)
- `usb_cam-ros2` — USB camera driver
- `ros2_astra_camera-master` — Depth camera driver
- `yesense_ros2` — H30 IMU driver
- `wheeltec_mic` — Microphone array for radar tracking

**Vision/tracking:**
- `aruco_ros-humble-devel` — ArUco marker detection
- `wheeltec_robot_kcf` — KCF object tracking
- `simple_follower_ros2` — Object following (Python)

**Voice/AI:**
- `wheeltec_aiui` — iFlytek voice recognition
- `tts_make_ros2` — Text-to-speech
- `ollama_ros_chat` — LLM chat integration (Python)

**Robot description:**
- `wheeltec_robot_urdf` — URDF/Xacro models for all robot variants

### Configuration Flow

1. `turn_on_wheeltec_robot/config/wheeltec_param.yaml` — Master config: selects car mode, lidar type, IMU type, camera type
2. `turn_on_wheeltec_robot/config/robot_model.yaml` — TF offsets for 30+ robot models (base→laser, base→camera, etc.)
3. `turn_on_wheeltec_robot/config/ekf.yaml` — EKF sensor fusion config (odom + IMU, 2D mode, 5Hz)
4. `wheeltec_robot_nav2/param/wheeltec_params/param_<model>.yaml` — Nav2 parameters per robot type (AMCL, controllers, planners, costmaps)
5. `wheeltec_robot_nav2/config/omni_nav_bt.xml` — Custom behavior tree for omni navigation

### Launch Chain

`wheeltec_nav2.launch.py` → includes `turn_on_wheeltec_robot.launch.py` (base + EKF + URDF) + lidar driver + `nav2_bringup`

`turn_on_wheeltec_robot.launch.py` → includes `base_serial.launch.py` (selects STM32 vs H30 IMU) + `wheeltec_ekf.launch.py` + `robot_mode_description.launch.py`

### Languages

- **C++ (C++14):** Core robot control, navigation, hardware drivers, tracking
- **Python 3:** ToF sensors, keyboard teleop, auto-recharge, waypoint cycling, follower, LLM chat
- Build system: `ament_cmake` for C++, `ament_python` for Python packages
