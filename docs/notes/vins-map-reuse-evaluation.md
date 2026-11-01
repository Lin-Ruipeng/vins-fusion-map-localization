# VINS-Mono / VINS-Fusion 先验地图复用评估

核查日期：2026-11-01。目标：尽快获得“先验地图中的位姿＋视觉惯性连续定位”。用户已确认允许先启动视觉＋IMU，再对视频关键帧做地图定位；第一阶段只用公开数据集，不接硬件。本次阅读官方 README 与源代码，未安装、编译或实测定位效果。

核查版本：

- VINS-Mono：`90dabb5ec79946ae42fd2e1e91d4e69aabe1e25d`。[固定版本](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/tree/90dabb5ec79946ae42fd2e1e91d4e69aabe1e25d)
- VINS-Fusion：`be55a937a57436548ddfb1bd324bc1e9a9e828e0`。[固定版本](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/tree/be55a937a57436548ddfb1bd324bc1e9a9e828e0)

## 结论

**本次首选 VINS-Fusion 的单目＋IMU配置与 loop_fusion；VINS-Mono 是功能接近的备选。**两者都能保存旧图、重新加载、把初始化后的新 VIO 序列对齐到旧图。Fusion 已经发布当前帧的地图坐标 Odometry，对当前原型更省接口适配工作。这个选择基于源码集成成本，不是实测的构建耗时或运行性能排名。

这里需要启动的是视觉回环/地图复用组件 **loop_fusion**。仓库中的 **global_fusion** 是 README 展示的 VINS＋GPS 示例，不是完成本次视觉地图定位所需的组件。[Fusion README 3.1 与 4.2](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/README.md#3-euroc-example)

**如果必须输入一张与任何 VIO 序列无关的照片，立即得到地图中的六自由度位姿，两者都不能原生满足。**它们的地图复用是已初始化 VIO 与旧关键帧之间的重定位，并非持久化三维地标地图上的独立单图 PnP 服务。证据见下文的输入门槛、PnP 方向和保存内容。

## 功能对照

| 项目 | VINS-Mono | VINS-Fusion |
|---|---|---|
| 单目＋IMU | 原生支持 | 原生支持 |
| 保存/加载先验图 | README 3.3 明确给出流程 | README 未详述复用，但配置与实现俱全 |
| 保存格式 | 位姿图＋旧关键帧二维点/BRIEF；图像可选 | 同类格式 |
| 单张孤立照片直接定位 | 不支持现成入口 | 不支持现成入口 |
| 当前 VIO 对齐旧图 | 原生 | 原生 |
| 标准消息形式的当前帧全局输出 | pose_graph 回调算出了位姿，但默认只发布相机可视化；需要少量适配 | `/loop_fusion/odometry_rect` 已发布 |
| 原生地图来源 | 自身保存的 pose graph | 自身保存的 pose graph |

输入能力依据：[Mono README](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/blob/90dabb5ec79946ae42fd2e1e91d4e69aabe1e25d/README.md)、[Fusion README](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/README.md)。各项代码证据如下。

## 为什么不是独立单张照片定位

1. 两者的 `pubKeyframe()` 都要求估计器处于 `NON_LINEAR`，并从已求解特征深度生成三维点。也就是说，单目＋IMU情形先要完成视觉惯性初始化与多帧三角化。[Mono visualization.cpp L348–402](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/blob/90dabb5ec79946ae42fd2e1e91d4e69aabe1e25d/vins_estimator/src/utility/visualization.cpp#L348-L402)、[Fusion visualization.cpp L357–412](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/vins_estimator/src/utility/visualization.cpp#L357-L412)
2. 地图复用线程等待图像、关键帧位姿、关键帧点云三类消息同时到齐，再构造当前关键帧；只有图像消息不会走到定位。[Mono pose_graph_node.cpp L294–306、L387–418](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/blob/90dabb5ec79946ae42fd2e1e91d4e69aabe1e25d/pose_graph/src/pose_graph_node.cpp#L294-L418)、[Fusion pose_graph_node.cpp L245–367](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/loop_fusion/src/pose_graph_node.cpp#L245-L367)
3. `findConnection()` 从当前关键帧取 `point_3d`，把这些点所对应的 BRIEF 与旧关键帧二维点匹配。`PnPRANSAC(matched_2d_old_norm, matched_3d, ...)` 求的是**旧相机在当前 VIO 三维坐标系中的位姿**，然后与当前 VIO 位姿组合求相对变换。[Mono keyframe.cpp L259–307、L401–409、L472–487](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/blob/90dabb5ec79946ae42fd2e1e91d4e69aabe1e25d/pose_graph/src/keyframe.cpp#L259-L487)、[Fusion keyframe.cpp L270–312、L414–420、L483–498](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/loop_fusion/src/keyframe.cpp#L270-L498)

因此，看到代码里调用了 OpenCV PnP，不代表它已经具备“查询照片二维点＋已存地图三维地标”的单图定位接口。

## save / load 实际保存什么

两者 `savePoseGraph()` 都写入：

- `pose_graph.txt`：关键帧索引、时间、VIO 位姿、图优化位姿、loop 索引和相对约束、二维点数量。
- 每关键帧的 `_keypoints.txt`：像素坐标与归一化二维坐标。
- 每关键帧的 `_briefdes.dat`：BRIEF 描述子。
- 开启 `save_image` 时额外保存 `_image.png`。

**没有在这个保存流程中保存三维地标、当前 VIO 滑窗、IMU bias 等完整估计器状态。**加载过程重建旧关键帧与检索数据库，新的 VIO 仍需重新初始化。它不是可直接导入任意 PLY 点云、COLMAP 模型或照片目录的通用地图格式。[Mono save L697–750 / load L752–869](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/blob/90dabb5ec79946ae42fd2e1e91d4e69aabe1e25d/pose_graph/src/pose_graph.cpp#L697-L869)、[Fusion save L898–951 / load L953–1070](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/loop_fusion/src/pose_graph.cpp#L898-L1070)

两者在成功发现跨序列连接后，把当前序列变换到已加载图的坐标系。对于 IMU 模式，校正自由度是平移与 yaw；roll/pitch 主要来自惯性估计与重力对齐。[Mono addKeyFrame L85–123](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/blob/90dabb5ec79946ae42fd2e1e91d4e69aabe1e25d/pose_graph/src/pose_graph.cpp#L85-L123)、[Fusion addKeyFrame L111–154](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/loop_fusion/src/pose_graph.cpp#L111-L154)、[Fusion 4DoF/6DoF 选择 L46–58](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/loop_fusion/src/pose_graph.cpp#L46-L58)

## 局部、全局输出及频率

### VINS-Fusion

`loop_fusion` 订阅 `/vins_estimator/odometry`。每收到一条该消息，`vio_callback()` 都执行旧图对齐变换及当前漂移校正，然后发布 `/loop_fusion/odometry_rect`，消息类型为 `nav_msgs/Odometry`。因此，**校正参数由较低频的关键帧匹配/图优化更新，但当前地图位姿按 VIO Odometry 消息频率持续发布**，并不是只能输出图优化频率的历史关键帧。[callback L192–218](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/loop_fusion/src/pose_graph_node.cpp#L192-L218)、[节点名称/命名空间 L400–404 与发布器 L481–492](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/loop_fusion/src/pose_graph_node.cpp#L400-L492)

这个输出是 IMU/body 位姿。需要照片相机的位姿时乘外参 `T_map_camera = T_map_body × T_body_camera`；源码 L222–223 已有同样计算，不过其现成输出是相机可视化 marker。[相机位姿计算](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/loop_fusion/src/pose_graph_node.cpp#L220-L227)

不要把它等同于 IMU 采样频率输出；`odometry_rect` 订阅的是图像/VIO更新的 `odometry`，不是 `imu_propagate`。此外，初始对齐变换为单位变换，callback 在首次匹配旧图之前也会发布，所以 `frame_id=world` 或 topic 存在不代表已在先验图定位成功。[变换初值](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/loop_fusion/src/pose_graph.cpp#L14-L28)、[跨序列对齐成功标记](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/loop_fusion/src/pose_graph.cpp#L134-L154)

### VINS-Mono

- `/vins_estimator/odometry` 是局部 VIO 位姿；`pose_graph` 的 `vio_callback()` 已算当前帧地图坐标，但仅发布相机 marker。[Mono callback L201–226](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/blob/90dabb5ec79946ae42fd2e1e91d4e69aabe1e25d/pose_graph/src/pose_graph_node.cpp#L201-L226)
- 图优化路径 `/pose_graph/pose_graph_path` 是关键帧路径；可从其姿态读取地图坐标，但它不是每次 VIO 回调都更新的当前帧标准 Odometry。[路径注册](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/blob/90dabb5ec79946ae42fd2e1e91d4e69aabe1e25d/pose_graph/src/pose_graph.cpp#L27-L34)
- 估计器的修正路径实际名为 `/vins_estimator/relocalization_path`，不是 `/relo_path`。它使用 `drift_correct_r/t`；这套修正依赖 `FAST_RELOCALIZATION` 的匹配反馈，而 EuRoC 默认配置为 `fast_relocalization: 0`。因此不能默认把它当作已经融合旧图的当前地图位姿。[路径发布 L137–154](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/blob/90dabb5ec79946ae42fd2e1e91d4e69aabe1e25d/vins_estimator/src/utility/visualization.cpp#L137-L154)、[反馈开关 L488–513](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/blob/90dabb5ec79946ae42fd2e1e91d4e69aabe1e25d/pose_graph/src/keyframe.cpp#L488-L513)、[修正计算 L598–609](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/blob/90dabb5ec79946ae42fd2e1e91d4e69aabe1e25d/vins_estimator/src/estimator.cpp#L598-L609)、[默认配置 L65–69](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/blob/90dabb5ec79946ae42fd2e1e91d4e69aabe1e25d/config/euroc/euroc_config.yaml#L65-L69)

如果选择 Mono，最直接的适配是在已经算出校正位姿的 pose_graph callback 内增加 Odometry 发布；Fusion 相应代码可以作为参考。没有必要为了这个接口重新设计融合算法。

## 适合当前目标的最短验证路线

以下是根据代码推导的建议，尚未执行：

1. 使用 VINS-Fusion 官方 EuRoC 单目＋IMU配置，启动 `vins_node` 和 `loop_fusion_node`，先回放同一环境的建图序列。
2. 把 `pose_graph_save_path` 设为已存在的绝对目录并保留结尾 `/`，在 loop_fusion 终端输入 `s` 保存。该实现保存后会 `ros::shutdown()`，第二次运行需重启 loop_fusion。
3. 设置 `load_previous_pose_graph: 1`，重启后回放有场景重叠的新序列，等 VIO 初始化、关键帧匹配成功。
4. 用 `/vins_estimator/odometry` 看局部连续跟踪，用 `/loop_fusion/odometry_rect` 获取对齐旧图的连续位姿。检查首次跨序列连接成功，再将其标为地图定位有效；不要仅凭 topic 存在判断。

运行入口见 [Fusion README 的 EuRoC 示例](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/README.md#3-euroc-example)。保存命令见 [pose_graph_node.cpp L378–390](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/loop_fusion/src/pose_graph_node.cpp#L378-L390)，加载配置见 [L452–470](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/loop_fusion/src/pose_graph_node.cpp#L452-L470)。路径建议来自源码直接拼接文件名并 `fopen`，没有对配置字符串里的 `~` 做 shell 展开：[save 实现 L903–906](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/loop_fusion/src/pose_graph.cpp#L903-L906)。

“绝对位姿”在此指**先验地图坐标中的位姿**。这条流程没有自动赋予地图经纬度或建筑坐标。没有外部坐标对齐时，先验图仍沿用最初建图的坐标原点与朝向。

若用户确认必须有独立 JPG → 地图六自由度位姿的接口，应选择专门保留地图三维地标的单图定位模块，再与 VIO 通过时间戳和坐标变换融合；不能把上述 pose graph 复用流程包装成已经具备此功能。
