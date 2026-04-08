# Nav2 调参经验（senior_diff）

持续更新。记录调参过程中发现的有效结论，避免重复踩坑。

## EKF 配置

- **频率**：当前改回 10Hz（202602 版本），目前运算的过来，保持。
- **two_d_mode: true** — 平面机器人必须开启
- **odom0_differential: true** — 差分融合，不直接用绝对位置
- **imu0_relative: true** — IMU 测量为相对变化
- **debug: true** — 调试日志输出到 `/home/wheeltec/debug/file.txt` (但是我没有看到有这个文件产生)

## AMCL 定位

- **recovery_alpha_fast/slow 必须保持 0.0** — 非 0 值会触发 `uniformPoseGenerator`，本地 nav2 fork 中该函数访问 `free_space_indices` 时存在 SIGSEGV bug（2026-04-08 GDB 确认，崩溃栈：`laserReceived → pf_update_resample → uniformPoseGenerator`）
- **更新阈值要够低** — `update_min_d: 0.1`, `update_min_a: 0.1`。原来 0.25m/0.2rad 太高，修正频率不够，odom 漂移在两次修正间累积（2026-04-08 验证有效）
- **粒子数和光束数** — `max_particles: 3000`, `max_beams: 90`（原 2000/60），提升匹配精度（2026-04-08 验证有效）
- **sigma_hit: 0.1**（原 0.2）— 更严格的匹配，减少模糊匹配导致的漂移（2026-04-08 验证有效）

## 行为恢复

- **global_frame 必须设为 map** — 之前注释掉后默认用 odom，但 TF 树里只有 odom_combined，导致 spin/backup 全部失败
- senior_diff 用 Nav2 默认行为树，不用自定义 `omni_nav_bt.xml`

## 雷达

- ls_N10Plus_uart 扫描频率建议 5Hz，太高可能影响性能（commit ad336c5）

## 绝对不能动的参数

- **EKF `transform_time_offset` 必须保持 0.0** — 改为 0.01 会导致 nav2_container SIGSEGV 崩溃（2026-04-08 确认）

## 已知坑

- odom_frame 必须设为 `odom_combined`（和 EKF 输出一致），否则 TF 查找会失败
- **`robot_nav` 必须为 false**（`wheeltec_nav2.launch.py` 第57行）— 设为 true 会让 EKF 加载 `ekf_nav.yaml`（订阅 `/imu/data_filtered` 即 ImuProcessor 输出），导致导航时 local_costmap 和点云天旋地转，完全不可用。原因未完全确认，可能是 ImuProcessor 的 Mahony AHRS（`Quaternion_Solution.cpp`，`SAMPLING_FREQ=20Hz` 硬编码）与 H30 IMU 实际发布频率不匹配，或其静止冻结逻辑在运动中引入姿态跳变。**必须保持 `robot_nav=false`，让 EKF 直接用 H30 原始数据 `/imu/data_raw`。**
- **local_costmap 的 `global_frame: map` 是正确的** — 虽然 Nav2 官方推荐 local_costmap 用 odom 帧，但 Wheeltec 全系车型配置均使用 map，不要改
- **costmap 的 observation_sources 只配实际存在的话题** — 单雷达车型不要配 scan2，否则订阅不存在的话题可能引发潜在问题

## GDB 调试 Nav2 崩溃

Nav2 所有节点跑在同一个 `component_container_isolated` 进程里，崩溃时日志只显示 `Magick: abort due to signal 11`（这是 GraphicsMagick 的全局信号处理器，不是崩溃源头，因为 nav2_map_server 链接了 GraphicsMagick 加载地图图片）。要定位真正的崩溃点，需要用 GDB。

### 步骤

1. **终端 1** — 正常启动导航：
   ```bash
   ros2 launch wheeltec_robot_nav2 wheeltec_nav2.launch.py
   ```

2. **终端 2** — 在发导航目标之前 attach GDB：
   ```bash
   pid=$(pgrep -f component_container_isolated)
   sudo gdb -p $pid -batch \
     -ex "handle SIGINT pass" \
     -ex "continue" \
     -ex "bt full" \
     -ex "info threads" \
     -ex "thread apply all bt" \
     -ex "quit"
   ```

3. 在 RViz 中发导航目标触发崩溃，GDB 会自动打印所有线程的完整调用栈。

### 读 GDB 输出的要点

- 找 `received signal SIGSEGV` 所在的线程，那个才是崩溃线程
- 看 `#0` 帧的函数名就是崩溃点，往上看调用链理解上下文
- 其他线程的栈（大多在 `pthread_cond_wait`、`rcl_wait`）可以忽略，它们只是在等待
- `Magick:` 的报错永远不是根因，只是信号处理器的输出

