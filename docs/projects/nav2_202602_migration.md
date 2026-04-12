# Nav2 202602 版本迁移

## 目标

将 nav2 参数和 robot 配置更新到 202602 版本，改善定位精度和导航安全性。本次调试机器基于senior_diff。

## 当前状态：进行中

## 已完成

### 定位与传感器融合
- 更新 `param_senior_diff.yaml` 和 `wheeltec_param.yaml` 到 202602 版本
- 定位精度有明显改善
- AMCL 调参改善点云累计偏移（update阈值、粒子数、光束数、sigma_hit），详见 `docs/areas/nav2_tuning_senior_diff.md`
- **EKF 修复原地旋转 yaw 偏差**（2026-04-12）：从 odom0_config 去掉 yaw_vel，让 IMU 独占 yaw。解决了差速车原地旋转时轮子打滑导致 TF 与物理世界不一致、costmap 旋转的问题

### 导航安全性
- **开启 `consider_footprint: true`**（2026-04-12）：MPPI 使用矩形 footprint 做碰撞检测，而非点检测。解决了 base_footprint 在后轮轴心导致前端 0.32m 车身不被保护的问题
- **修正 footprint 尺寸**（2026-04-12）：实测整车 42cm×40cm，后轮轴距屁股 10.5cm。从 `[-0.07,...,0.35,...]` 改为 `[-0.11,...,0.32,...]`，修正前端虚报 3.5cm、后端短 3.5cm 的偏差
- **切换 REEDS_SHEPP 运动模型**（2026-04-12）：替代 DUBIN，允许倒车和紧凑转向。DUBIN 在目标在身后时会规划不必要的大 U 弯
- **开启 `enforce_path_inversion: true`**（2026-04-12）：配合 REEDS_SHEPP，让 MPPI 尊重路径中的前进/倒车切换
- **添加 RotationShimController 显式参数**（2026-04-12）：检测 >45° 偏差时原地旋转，避免画弧线切弯
- **降速**（2026-04-12）：vx_max 0.5→0.25，wz_max 2.0→1.0。降低惯性是减少撞墙最有效的手段
- **重平衡 Critic 权重**（2026-04-12）：PathAlign 45→30，PathFollow 35→25，ObstaclesCritic repulsion 保持 5.0。之前路径跟随:避障比值 27:1，避障没话语权；现在 11:1，墙边能偏离路径

### Costmap 调优
- **Global costmap**：inflation_radius=0.35, cost_scaling_factor=5.0 实现走廊路径居中且门口可通过
- **Local costmap**：inflation_radius=0.25, cost_scaling_factor=5.0。过大（0.4）会让 MPPI 候选轨迹在门口全高代价导致犹豫不进
- 移除 costmap 中不存在的 `/scan2` 观测源（单雷达车型不需要）

### 行为树
- 新增 senior_diff 专用行为树 `config/senior_diff_nav_bt.xml`：恢复顺序改为先后退再旋转
- 创建 `debug/check_yaw.py` 用于诊断 costmap 与地图旋转不一致问题

### 计算量优化
- batch_size 2000→1000, time_steps 56→36，降低 ~68% 计算量，为 consider_footprint=true 和 controller_frequency=10Hz 留出 CPU 空间

## 已知问题

- ~~地图存在累计误差~~ — 已通过 AMCL 调参大幅改善（2026-04-08）
- ~~nav2_container SIGSEGV 崩溃~~ — 已解决：`recovery_alpha_fast/slow` 回滚为 0.0（2026-04-08）
- ~~costmap 偶发旋转 90°~~ — 已解决：EKF 去掉 odom yaw_vel 融合（2026-04-12）
- ~~MPPI 用点检测导致前端撞墙~~ — 已解决：开启 consider_footprint + 修正 footprint 尺寸（2026-04-12）
- ~~DUBIN 模型导致不必要大 U 弯~~ — 已解决：切换 REEDS_SHEPP（2026-04-12）
- 【未解决】**进入 lethal 区域后恢复困难** — BackUp/Spin 碰撞预检测发现当前位置在碰撞中，直接返回失败（不尝试移动）。根本解决需修改 Nav2 fork 中 DriveOnHeading 的碰撞检测逻辑
- 【低优先级】controller_server 偶发 `Extrapolation Error`（map→base_footprint），时间差约 1ms，功能不受影响但日志刷屏
- 【低优先级】controller_frequency=10Hz 偶尔 `Control loop missed its desired rate`，如频繁出现可降到 8Hz

## 待办

- 修改 Nav2 fork 中 DriveOnHeading 碰撞预检测逻辑，允许从 lethal 区域后退脱困
- 继续实车验证 REEDS_SHEPP + RotationShimController 在 180° 转弯处的表现
- 考虑提高 backup_speed(0.15) 和降低 simulate_ahead_time(0.5) 作为临时缓解
- 【低优先级】排查 TF extrapolation into the future 的 ERROR 日志
