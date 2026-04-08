# 硬件配置与测试流程

## 当前硬件配置

- **底盘**: senior_diff（高级差速轮）
- **LiDAR**: ls_N10Plus_uart
- **IMU**: H30（yesense_ros2 驱动）

## 构建方式

工作空间使用 `colcon build --symlink-install` 构建，YAML 配置文件、launch 文件等非编译文件修改后**无需重新构建**，直接重启节点即可生效。只有修改 C++ 源码等需要编译的文件才需要重新 `colcon build`。

## 实车测试流程

### 启动顺序

1. 确保机器人放在已知地图的起始位置
2. `ros2 launch wheeltec_nav2 wheeltec_nav2.launch.py`
3. 等待所有节点启动（观察终端无报错）
4. 在 RViz 中确认定位是否正确（粒子云收敛）
5. 发送导航目标测试

### 建图流程

1. `ros2 launch slam_gmapping slam_gmapping.launch.py`
2. 手动遥控或键盘控制遍历环境
3. `ros2 launch slam_gmapping slam_gmapping.launch.py` 保存地图

### 常见问题排查

- **定位漂移**: 先检查 ekf.yaml，再检查 AMCL 参数
- **导航卡顿**: 检查 controller_frequency 和雷达频率是否匹配
- **恢复动作失败**: 检查 behavior_server 的 global_frame 是否为 map
