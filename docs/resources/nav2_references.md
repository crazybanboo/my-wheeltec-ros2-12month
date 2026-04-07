# Nav2 参考资料

## 官方文档

- AMCL 参数: https://docs.nav2.org/configuration/packages/configuring-amcl.html
- MPPI 控制器: https://docs.nav2.org/configuration/packages/configuring-mppic.html
- BT Navigator: https://docs.nav2.org/configuration/packages/configuring-bt-navigator.html
- Waypoint Follower: https://docs.nav2.org/configuration/packages/configuring-waypoint-follower.html

## 项目内关键配置文件

- 主配置: `src/turn_on_wheeltec_robot/config/wheeltec_param.yaml`
- EKF: `src/turn_on_wheeltec_robot/config/ekf.yaml`
- Nav2 参数 (senior_diff): `src/wheeltec_robot_nav2/param/wheeltec_params/param_senior_diff.yaml`
- 地图文件: `src/wheeltec_robot_nav2/map/WHEELTEC.yaml`
