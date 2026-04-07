# Nav2 调参经验（senior_diff）

持续更新。记录调参过程中发现的有效结论，避免重复踩坑。

## EKF 配置

- **频率**：当前改回 10Hz（202602 版本），目前运算的过来，保持。
- **two_d_mode: true** — 平面机器人必须开启
- **odom0_differential: true** — 差分融合，不直接用绝对位置
- **imu0_relative: true** — IMU 测量为相对变化
- **debug: true** — 调试日志输出到 `/home/wheeltec/debug/file.txt` (但是我没有看到有这个文件产生)

## 行为恢复

- **global_frame 必须设为 map** — 之前注释掉后默认用 odom，但 TF 树里只有 odom_combined，导致 spin/backup 全部失败
- senior_diff 用 Nav2 默认行为树，不用自定义 `omni_nav_bt.xml`

## 雷达

- ls_N10Plus_uart 扫描频率建议 5Hz，太高可能影响性能（commit ad336c5）

## 已知坑

- odom_frame 必须设为 `odom_combined`（和 EKF 输出一致），否则 TF 查找会失败
- **`robot_nav` 必须为 false**（`wheeltec_nav2.launch.py` 第57行）— 设为 true 会让 EKF 加载 `ekf_nav.yaml`（订阅 `/imu/data_filtered` 即 ImuProcessor 输出），导致导航时 local_costmap 和点云天旋地转，完全不可用。原因未完全确认，可能是 ImuProcessor 的 Mahony AHRS（`Quaternion_Solution.cpp`，`SAMPLING_FREQ=20Hz` 硬编码）与 H30 IMU 实际发布频率不匹配，或其静止冻结逻辑在运动中引入姿态跳变。**必须保持 `robot_nav=false`，让 EKF 直接用 H30 原始数据 `/imu/data_raw`。**
- **local_costmap 的 `global_frame: map` 是正确的** — 虽然 Nav2 官方推荐 local_costmap 用 odom 帧，但 Wheeltec 全系车型配置均使用 map，不要改

