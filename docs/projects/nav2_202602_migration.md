# Nav2 202602 版本迁移

## 目标

将 nav2 参数和 robot 配置更新到 202602 版本，改善定位精度。本次调试机器基于senior_diff。

## 当前状态：进行中

## 已完成

- 更新 `param_senior_diff.yaml` 和 `wheeltec_param.yaml` 到 202602 版本
- 定位精度有明显改善
- AMCL 调参改善点云累计偏移（update阈值、粒子数、光束数、sigma_hit），详见 `docs/areas/nav2_tuning_senior_diff.md`
- 移除 costmap 中不存在的 `/scan2` 观测源（单雷达车型不需要）

## 已知问题

- ~~地图存在累计误差（随着导航次数的变多，雷达的点云与map的墙壁产生偏移）~~ — 已通过 AMCL 调参大幅改善（2026-04-08）
- ~~nav2_container SIGSEGV 崩溃~~ — 已解决。根因：`recovery_alpha_fast/slow` 非 0 时触发 `uniformPoseGenerator`，该函数在本地 nav2 fork 中访问 `free_space_indices` 时 segfault（GDB 调用栈：`laserReceived → pf_update_resample → uniformPoseGenerator`）。修复：回滚为 0.0
- 【低优先级】controller_server 偶发性控制循环报 `Extrapolation Error looking up target frame: Lookup would require extrapolation into the future`（map→base_footprint），时间差约 1ms，导航功能不受影响但日志刷屏

## 待办

- 【低优先级】排查 TF extrapolation into the future 的 ERROR 日志（`transform_time_offset` 不能改，改了local_costmap在rviz2上会天旋地转）
