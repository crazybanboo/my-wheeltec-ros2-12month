# Nav2 202602 版本迁移

## 目标

将 nav2 参数和 robot 配置更新到 202602 版本，改善定位精度。本次调试机器基于senior_diff。

## 当前状态：进行中

## 已完成

- 更新 `param_senior_diff.yaml` 和 `wheeltec_param.yaml` 到 202602 版本
- 定位精度有明显改善
- AMCL 调参改善点云累计偏移（update阈值、粒子数、光束数、sigma_hit），详见 `docs/areas/nav2_tuning_senior_diff.md`
- 移除 costmap 中不存在的 `/scan2` 观测源（单雷达车型不需要）
- 新增 senior_diff 专用行为树 `config/senior_diff_nav_bt.xml`：恢复顺序改为先后退再旋转，适合长方形差速车在狭窄空间脱困
- MPPI 控制器避障调参：提高 repulsion_weight(5.0)、collision_margin_distance(0.35)，降低 GoalCritic(5.0) 防切弯，提高 PathAlignCritic(45.0) 加强路径跟随
- 修正 footprint 宽度为实测 40cm（原 38cm）
- SmacPlannerHybrid cost_penalty 降为 1.5，允许穿过高代价窄通道
- 创建 `debug/check_yaw.py` 用于诊断 costmap 与地图旋转不一致问题

## 已知问题

- ~~地图存在累计误差（随着导航次数的变多，雷达的点云与map的墙壁产生偏移）~~ — 已通过 AMCL 调参大幅改善（2026-04-08）
- ~~nav2_container SIGSEGV 崩溃~~ — 已解决。根因：`recovery_alpha_fast/slow` 非 0 时触发 `uniformPoseGenerator`，该函数在本地 nav2 fork 中访问 `free_space_indices` 时 segfault（GDB 调用栈：`laserReceived → pf_update_resample → uniformPoseGenerator`）。修复：回滚为 0.0
- 【低优先级】controller_server 偶发性控制循环报 `Extrapolation Error looking up target frame: Lookup would require extrapolation into the future`（map→base_footprint），时间差约 1ms，导航功能不受影响但日志刷屏
- 【进行中】转弯切弯/贴墙问题 — MPPI 排斥力已提高，有改善但未完全解决。膨胀参数在"不撞墙"和"能过窄道(80cm)"之间需要继续平衡
- 【进行中】进入 lethal 区域后恢复困难 — 所有恢复动作都因碰撞检测立刻失败，需要研究更好的脱困策略
- 【待排查】偶发 costmap 与地图旋转 90° — 疑似 IMU 启动 yaw 偏移，用 `debug/check_yaw.py` 诊断

## 待办

- 继续优化膨胀半径与 MPPI 排斥力的平衡（当前值：local/global inflation=0.3, cost_scaling=5.0/1.0）
- 排查 IMU 启动 yaw 偏移问题（下次出现时运行 check_yaw.py）
- 考虑是否需要在行为树中添加 DriveOnHeading（前进）作为额外恢复手段
- 【低优先级】排查 TF extrapolation into the future 的 ERROR 日志（`transform_time_offset` 不能改，改了local_costmap在rviz2上会天旋地转）
