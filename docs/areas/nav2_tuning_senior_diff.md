# Nav2 调参经验（senior_diff）

持续更新。记录调参过程中发现的有效结论，避免重复踩坑。

## EKF 配置

- **频率**：当前 20Hz（ekf.yaml）
- **two_d_mode: true** — 平面机器人必须开启
- **odom0_differential: true** — 差分融合，不直接用绝对位置
- **imu0_relative: true** — IMU 测量为相对变化
- **odom0 不融合 yaw_vel** — 差速车原地旋转时轮子打滑，编码器报告的 yaw_vel 偏小，与 IMU 冲突导致 EKF 低估旋转角度。表现为：物理世界机器人已转 90°，但 TF/RViz 里几乎没转，costmap 看起来在旋转。**解决方案（2026-04-12 验证有效）：从 odom0_config 中去掉 yaw_vel，让 IMU 独占 yaw 信息。这是差速车的标准做法——编码器负责线速度(vx,vy)，IMU 负责角度(yaw,yaw_vel)。**
- **debug: true** — 调试日志输出到 `/home/wheeltec/debug/file.txt`（但未观察到文件产生）

## AMCL 定位

- **recovery_alpha_fast/slow 必须保持 0.0** — 非 0 值会触发 `uniformPoseGenerator`，本地 nav2 fork 中该函数访问 `free_space_indices` 时存在 SIGSEGV bug（2026-04-08 GDB 确认，崩溃栈：`laserReceived → pf_update_resample → uniformPoseGenerator`）
- **更新阈值要够低** — `update_min_d: 0.1`, `update_min_a: 0.1`。原来 0.25m/0.2rad 太高，修正频率不够，odom 漂移在两次修正间累积（2026-04-08 验证有效）
- **粒子数和光束数** — `max_particles: 3000`, `max_beams: 90`（原 2000/60），提升匹配精度（2026-04-08 验证有效）
- **sigma_hit: 0.1**（原 0.2）— 更严格的匹配，减少模糊匹配导致的漂移（2026-04-08 验证有效）

## Footprint

- **实测尺寸**（2026-04-12）：总长 42cm，总宽 40cm，后轮轴心距屁股 10.5cm
- **正确 footprint**：`[-0.11, -0.20], [-0.11, 0.20], [0.32, 0.20], [0.32, -0.20]`（含 0.5cm 安全余量）
- **之前的错误 footprint** `[-0.07,...,0.35,...]` 导致：前端虚报 3.5cm（RViz 里看起来快撞墙），后端短了 3.5cm（轮子 TF 在框外）。base_footprint 在后轮轴心，非对称 footprint 下 consider_footprint 的碰撞检测依赖准确的尺寸
- footprint 需要在 local_costmap 和 global_costmap 两处同步修改

## 行为恢复

- **global_frame 必须设为 map** — 之前注释掉后默认用 odom，但 TF 树里只有 odom_combined，导致 spin/backup 全部失败
- senior_diff 使用自定义行为树 `src/wheeltec_robot_nav2/config/senior_diff_nav_bt.xml`，已在 `param_senior_diff.yaml` 中通过 `default_nav_to_pose_bt_xml` 指定
- **恢复顺序：清costmap → 后退 → 旋转 → 等待**（默认行为树是旋转在前，后退在后）
  - 长方形差速小车在狭窄空间先旋转容易碰撞失败浪费重试次数，先后退脱困再旋转更合理
  - Spin 本身有碰撞检测（基于 costmap + 机器人 footprint 逐帧检测），不会硬转撞墙，但失败了等于浪费一次恢复机会
- 每个恢复动作前先清局部 costmap，避免残留障碍数据导致恢复动作被误判碰撞（参考 omni_nav_bt.xml 的做法）
- **核心矛盾（未解决）**：机器人进入 lethal 区域后，BackUp/Spin 的碰撞预检测发现**当前位置**在碰撞中，直接返回失败（甚至不尝试移动）。ClearCostmap 后 1ms 雷达数据就刷新回来。根本解决需修改 Nav2 fork 中 DriveOnHeading 的碰撞检测逻辑，跳过当前位置只检测移动路径。临时缓解方案：提高 backup_speed（0.05→0.15）和 backup_dist（0.30→0.50），降低 simulate_ahead_time（2.0→0.5）。

## 全局规划器（SmacPlannerHybrid）

### 运动模型选择

- **必须用 REEDS_SHEPP，不能用 DUBIN**（2026-04-12 验证）— DUBIN 只允许前进+转弯，当目标在机器人身后时会规划一个巨大的 U 型弯绕过去。差速车可以原地旋转和倒车，REEDS_SHEPP 允许这些动作，规划出更紧凑合理的路径
- **`enforce_path_inversion: true`** — 配合 REEDS_SHEPP 使用。如果为 false，MPPI 会忽略路径中的方向变化（前进→倒车的切换），导致不遵循规划路径

### 转弯半径

- **`minimum_turning_radius: 0.25`** — 0.15 太小导致规划路径紧贴墙壁转弯（机器人前角扫过半径 ~0.40m，远超路径弧线）；0.35-0.40 太大导致窄门口规划失败（`no valid path found`）。0.25 是折中值
- **`minimum_turning_radius` 不能设为 0.0** — Dubin/Reeds-Shepp 运动模型在数学上要求 > 0（2026-04-11 确认）

### 代价惩罚

- **`cost_penalty: 1.3`**（原 1.5）— 降低让规划器更愿意穿过有代价的窄通道（门口等）。配合 global costmap inflation_radius=0.35 使用

## MPPI 控制器

### consider_footprint（关键参数）

- **必须开启 `consider_footprint: true`**（2026-04-12 验证）— 关闭时 MPPI 把机器人当点（base_footprint 位置），对于非对称 footprint（前端 0.32m，后端 0.11m），base_footprint 在后轮轴心，MPPI 看到"点离墙 0.25m 安全"但实际前端已撞进墙 0.07m
- **`consider_footprint: true` 必须配合降低排斥参数** — 否则 2000 条候选轨迹用矩形检测全被判危险，Optimizer fail to compute path。经验组合：`batch_size≤1000` + `repulsion_weight≤5.0` + `collision_margin_distance≤0.15`

### 速度与控制频率

- **`vx_max: 0.25`, `vx_min: -0.25`** — 降速是减少撞墙最直接有效的方法。0.5→0.35 有改善，0.35→0.25 进一步改善。用户不在意速度，优先安全
- **`wz_max: 1.0`**（原 2.0）— 旋转速度减半。2.0 rad/s 时矩形车身角甩出范围大，转弯惯性大容易冲进 lethal 区
- **`controller_frequency: 10.0`** — 但 CPU 偶尔跟不上（`Control loop missed its desired rate`），如果频繁出现考虑降到 8.0。5.0 太低会导致控制粒度不够

### 计算量控制

- **`batch_size: 1000`**（原 2000）— 配合 `consider_footprint: true` 减少计算量。矩形碰撞检测比点检测贵很多
- **`time_steps: 36`**（原 56）— 前瞻从 11.2s→7.2s（约 1.8m@0.25m/s）。过长的前瞻让 MPPI "看到"弯道后面的路径导致切弯
- 总计算量：1000×36=36K 次矩形碰撞检测/轮（原 2000×56=112K），降低约 68%

### Critic 权重平衡（关键经验）

路径跟随权重 vs 避障权重的比值决定了机器人在路径贴墙时是跟路径（撞墙）还是偏离路径（安全）：

| Critic | 当前权重 | 作用 |
|--------|---------|------|
| PathAlignCritic | 30.0 | 贴合路径方向 |
| PathFollowCritic | 25.0 | 沿路径前进 |
| ObstaclesCritic repulsion | 5.0 | 远离障碍物 |
| ObstaclesCritic critical | 25.0 | 碰撞边距内强排斥 |
| GoalCritic | 5.0 | 靠近目标 |

- 之前 PathAlign=45 + PathFollow=35（总 80）vs repulsion=3（比值 27:1），避障没有话语权，机器人跟着路径撞墙
- 当前 PathAlign=30 + PathFollow=25（总 55）vs repulsion=5（比值 11:1），走廊居中 + 墙边能偏离
- GoalCritic=5.0（原更高）降低是为了减少"直奔目标"导致的切弯

### RotationShimController

- 已添加显式参数（2026-04-12）：`forward_sampling_distance: 0.8`, `angular_dist_threshold: 0.785`(45°), `rotate_to_heading_angular_vel: 0.5`, `max_angular_accel: 1.0`
- 作用：检测到路径方向与当前朝向偏差 >45° 时，先原地旋转对准再让 MPPI 接管
- 配合 REEDS_SHEPP + enforce_path_inversion=true 使用，让 180° 掉头走"停→转→走"而不是画弧线切弯

### 当前参数快照（2026-04-12）

- `footprint: [-0.11,-0.20] to [0.32,0.20]`（实测修正）
- `consider_footprint: true`, `repulsion_weight: 5.0`, `critical_weight: 25.0`, `collision_margin_distance: 0.15`
- `batch_size: 1000`, `time_steps: 36`, `model_dt: 0.2`
- `vx_max: 0.25`, `wz_max: 1.0`, `controller_frequency: 10.0`
- `PathAlignCritic: 30.0`, `PathFollowCritic: 25.0`, `GoalCritic: 5.0`
- `enforce_path_inversion: true`, `motion_model_for_search: REEDS_SHEPP`
- `minimum_turning_radius: 0.25`, `cost_penalty: 1.3`
- `local_costmap`: inflation_radius=0.25, cost_scaling_factor=5.0
- `global_costmap`: inflation_radius=0.35, cost_scaling_factor=5.0

## Costmap 膨胀参数

### Global costmap（影响全局路径规划）

- **`inflation_radius: 0.35`**, **`cost_scaling_factor: 5.0`** — 让全局路径在走廊居中
- inflation_radius 和 cost_scaling_factor 必须一起调：
  - 0.6 + 3.0：门口被堵死，规划失败
  - 0.45 + 5.0：门口仍被堵
  - 0.35 + 5.0：门口可通过，走廊居中效果保留 ✓
- cost_scaling_factor 越大衰减越快。在窄门口（~80cm），0.35m 膨胀 + 5.0 衰减下中央代价约 48（可通过）

### Local costmap（影响 MPPI 控制器）

- **`inflation_radius: 0.25`**, **`cost_scaling_factor: 5.0`**
- local inflation 不宜过大（0.4 时门口被填满，MPPI 候选轨迹全高代价，机器人犹豫不进门口）
- 真正的避障由 ObstaclesCritic + consider_footprint 负责，local inflation 只需提供基本代价梯度

### 两个 costmap 的职责分工

- **global costmap inflation**：大一些（0.35），驱动规划器生成居中路径
- **local costmap inflation**：小一些（0.25），不干扰 MPPI 的门口通过能力
- **ObstaclesCritic + consider_footprint**：精确矩形碰撞检测，是避障的主力

## 雷达

- ls_N10Plus_uart 扫描频率建议 5Hz，太高可能影响性能（commit ad336c5）

## 绝对不能动的参数

- **EKF `transform_time_offset` 必须保持 0.0** — 改为 0.01 会导致 nav2_container SIGSEGV 崩溃（2026-04-08 确认）
- **SmacPlannerHybrid `minimum_turning_radius` 不能设为 0.0** — Dubin/Reeds-Shepp 运动模型在数学上要求 > 0（2026-04-11 确认）
- **AMCL `recovery_alpha_fast/slow` 必须保持 0.0** — 触发 uniformPoseGenerator SIGSEGV（2026-04-08 确认）

## 已知坑

- odom_frame 必须设为 `odom_combined`（和 EKF 输出一致），否则 TF 查找会失败
- **`robot_nav` 必须为 false**（`wheeltec_nav2.launch.py` 第57行）— 设为 true 会让 EKF 加载 `ekf_nav.yaml`（订阅 ImuProcessor 输出），导致 local_costmap 天旋地转。必须让 EKF 直接用 H30 原始数据 `/imu/data_raw`
- **local_costmap 的 `global_frame: map` 是正确的** — 虽然 Nav2 官方推荐用 odom 帧，但 Wheeltec 全系车型配置均使用 map，不要改
- **costmap 的 observation_sources 只配实际存在的话题** — 单雷达车型不要配 scan2
- **EKF odom0 不要融合 yaw_vel** — 差速车原地旋转时轮子打滑导致编码器 yaw_vel 偏小，与 IMU 冲突（2026-04-12 确认）

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
