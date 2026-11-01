# 最快跑通“地图定位＋视觉惯性连续定位”的方案评估

日期：2026-11-01。目标已经由严格论文复现调整为功能跑通，可以接受较差精度、较低定位成功率、地图纠偏时的轨迹跳变。

用户确认的条件：

- 允许先启动视觉＋IMU估计，再用视频关键帧做地图定位，不要求一张孤立照片独立冷启动定位。
- 第一阶段使用公开数据集，不接真实相机或 IMU。
- 本文将“绝对位姿”定义为先前保存的地图坐标系中的位置和姿态。地图没有地理配准时，结果不是经纬度或地球坐标。

本轮实际工作为官方文档与源码核查，没有安装、编译、运行或测量构建耗时。下面的“最快”指按已有集成程度和需要新增代码量作出的工程判断，并非实测排名。

## 推荐

**首选 HKUST-Aerial-Robotics/VINS-Fusion 的视觉惯性估计器，加同仓库的 loop_fusion，使用 EuRoC Machine Hall 数据。**

第一轮如果不强制单目，可用官方双目＋IMU配置降低初始化难度；若要严格单目，只需使用同仓库的单目＋IMU配置，定位融合路线不变。两种配置均由官方提供。单目需要 SfM 和视觉惯性初始化；双目配置直接使用三角化与 PnP 初始化，因而判断双目适合首轮功能验证。这个成功率判断尚未经过本机对比测试。[官方使用说明](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/README.md)、[单目配置](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/config/euroc/euroc_mono_imu_config.yaml)、[双目配置](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/config/euroc/euroc_stereo_imu_config.yaml)、[初始化源码](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/vins_estimator/src/estimator/estimator.cpp#L454-L505)。

这里使用的是 **loop_fusion**。同仓库的 **global_fusion** 是 GPS 融合示例，不是本任务需要的照片地图定位后端。[GPS 节点源码](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/global_fusion/src/globalOptNode.cpp)

## 两项功能如何已经接在一起

1. **连续视觉惯性估计。** vins_estimator 接收图像与 IMU，输出局部位姿及带三维特征点的关键帧。
2. **图像地图重定位。** loop_fusion 加载旧位姿图，通过 BRIEF/词袋检索、特征匹配和 PnP RANSAC 发现新旧关键帧的连接。
3. **对齐与纠偏。** 首次跨序列几何匹配成功后，把当前序列变换到旧图坐标系；后续位姿图优化更新漂移修正。
4. **持续输出地图坐标位姿。** 每条局部 VIO Odometry 到达时，loop_fusion 都应用当前对齐与修正，发布 odometry_rect。因此不只是展示旧地图，或分别运行两个互不相干的程序。

源码证据：[关键帧 PnP 与连接](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/loop_fusion/src/keyframe.cpp#L211-L270)、[跨序列对齐](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/loop_fusion/src/pose_graph.cpp#L101-L159)、[连续位姿校正并发布](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/loop_fusion/src/pose_graph_node.cpp#L192-L227)、[订阅与发布注册](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/loop_fusion/src/pose_graph_node.cpp#L481-L492)。

这是局部 VIO 加后端地图约束/位姿图修正的组合方式，不要求把地图误差作为新因子注入 VIO 滑窗。全局输出可能在重定位或图优化后跳变；定位暂时失败时仍靠 VIO 连续跟踪并可能漂移。它满足当前“先组合跑通”的需求，后续是否需要更平滑或更紧的融合可以另做。

## 为什么 Fusion 比 Mono 更适合当前交付目标

VINS-Mono 本身也支持保存地图、加载旧图和跨序列对齐，而且 README 对 MH01 建图、MH02 复用有更明确说明。它是接近等价的备选，不是功能上不可行。[Mono 官方说明](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/blob/90dabb5ec79946ae42fd2e1e91d4e69aabe1e25d/README.md#33-map-reuse)

决定推荐顺序的细节是输出接口：

| 项目 | 地图校正后的当前位姿输出 |
| --- | --- |
| VINS-Fusion | 原生发布标准 nav_msgs/Odometry，即 /loop_fusion/odometry_rect |
| VINS-Mono | pose_graph 的 vio_callback 已计算当前校正位姿，但只发布相机可视化 marker；若要同样的标准当前位姿接口，需要补少量发布代码 |

Mono 的 estimator 还有 relocalization_path，但其漂移修正依赖快速重定位反馈，EuRoC 配置默认 fast_relocalization=0。不能把默认显示出的 path 无条件当成已完成旧地图对齐的连续位姿接口。[Mono callback](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/blob/90dabb5ec79946ae42fd2e1e91d4e69aabe1e25d/pose_graph/src/pose_graph_node.cpp#L201-L226)、[Mono 配置](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/blob/90dabb5ec79946ae42fd2e1e91d4e69aabe1e25d/config/euroc/euroc_config.yaml)、[Mono 输出实现](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/blob/90dabb5ec79946ae42fd2e1e91d4e69aabe1e25d/vins_estimator/src/utility/visualization.cpp)。

更详细的源码对照见同目录 vins-map-reuse-evaluation.md。

## 其他候选的比较

| 方案 | 能否满足当前已确认需求 | 新增接入工作与本次建议 |
| --- | --- | --- |
| VINS-Fusion＋loop_fusion | 是，先 VIO 再旧地图定位，并输出校正位姿 | 首选；已有单目/双目 EuRoC 配置与当前位姿接口 |
| VINS-Mono＋pose_graph | 是 | 第二选择；地图复用文档清楚，标准全局位姿发布需小改 |
| maplab＋ROVIOLI | 是，且原生提供先验地图定位约束 | 功能符合，但依赖规模、历史版本与教程不一致增加首轮构建工作；既然不再追论文，暂不作为最快入口 |
| ORB-SLAM3 | 支持视觉惯性、多地图、PnP 重定位等基础能力 | 不把“加载 Atlas”直接等同于开箱即用的惯性定位模式；官方源码仍有惯性 localization-only 未支持的 TODO，首轮不优先 |
| hloc/COLMAP＋VIO＋外部对齐 | 可以，且适合额外要求独立单张照片定位时 | 要解决两套地图、尺度、时间戳、相机/IMU外参和融合桥接；用户已允许关键帧定位，无须首轮承担这项工作 |

比较依据：

- [maplab 旧版 README](https://github.com/ethz-asl/maplab/blob/1.3/README.md)、[ROVIOLI 定位教程](https://github.com/ethz-asl/maplab/blob/master/docs/pages/tutorials-rovioli/C_Running-ROVIOLI-in-Localization-mode.md)、[maplab 安装说明](https://github.com/ethz-asl/maplab/blob/master/docs/pages/installation/A_Installation-Ubuntu.md)。本工作区已有 get-out-of-my-lab-reproduction-survey.md，记录了实际参数不一致。
- [ORB-SLAM3 README](https://github.com/UZ-SLAMLab/ORB_SLAM3/blob/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/README.md)；[Tracking.cc 的 localization-only 惯性模式 TODO](https://github.com/UZ-SLAMLab/ORB_SLAM3/blob/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/Tracking.cc#L2036-L2043)；[加载旧 Atlas 后创建新地图](https://github.com/UZ-SLAMLab/ORB_SLAM3/blob/4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4/src/System.cc#L154-L182)。这些证据说明此用法需要专门验证，不是说 ORB-SLAM3 完全不能做惯性地图复用。
- [hloc README](https://github.com/cvg/Hierarchical-Localization/blob/master/README.md)；[hloc 的单图 2D–3D 绝对位姿估计](https://github.com/cvg/Hierarchical-Localization/blob/master/hloc/localize_sfm.py#L53-L70)。如果之后增加单张照片独立定位需求，应重新考虑这一类真实三维地标地图。

## 最小运行路线

### 环境

固定 VINS-Fusion 提交 be55a937a57436548ddfb1bd324bc1e9a9e828e0，先按官方测试过的 Ubuntu 18.04／ROS Melodic 这一代隔离环境评估。官方 README 测试系统是 Ubuntu 16.04/18.04。官方 Dockerfile 则基于 ROS Kinetic，锁了 Ceres 1.12.0；不能把它称为已经适配现代系统的一键镜像。需要实际验证旧源、编译器、Ceres/OpenCV 和容器构建，再决定最小兼容修正。[README](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/README.md)、[Dockerfile](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/docker/Dockerfile)

这里的工程建议是冻结环境，避免先做 ROS2 移植、换估计器或添加学习模型。首轮不要求 GPU 或训练网络；CPU上的实时处理能力仍需实测。

### 数据与步骤

1. 从 [EuRoC 新官方入口](https://projects.asl.ethz.ch/datasets/euroc-mav/)／[ETH 存档](https://www.research-collection.ethz.ch/items/bcaf173e-5dac-484b-bc37-faf97a594f1f) 取得 Machine Hall 数据，核实包含所需图像、IMU、时间戳和标定。若取得的是 ASL 图像/CSV格式而非 bag，增加转换或回放，不能继续依赖旧 .bag 直链。
2. 使用一个官方 EuRoC 配置，先启动 vins_node 和 loop_fusion_node，再回放 MH01。把 output_path 和 pose_graph_save_path 改成实际存在、可写的绝对路径，避免示例里的 ~ 字符串与默认目录问题。
3. MH01 完成后在 loop_fusion 节点输入 s 保存位姿图；保存到挂载的持久目录。源码保存命令会结束节点，保存应视作一个会话的结束。
4. 重启节点，设置 load_previous_pose_graph: 1，用相同路径加载地图。首次功能冒烟可先重放 MH01，降低场景差异带来的失败因素；这是同数据功能检查，不能当成独立序列精度测试。
5. 回放 MH02，确认与旧地图的跨序列匹配、PnP 和对齐确实发生，然后记录局部 VIO 与地图校正后的连续位姿。匹配失败时先保留现场日志、匹配图与参数，按跟踪、检索、PnP、跨序列对齐四个环节定位问题。
6. 若首轮使用双目，再切换 euroc_mono_imu_config.yaml 重复流程，即得到单目＋IMU版本，不同时替换数据集或融合方式。

配置与地图复用的直接依据：[Fusion EuRoC 配置](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/config/euroc/euroc_mono_imu_config.yaml)、[保存命令与加载路径](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/loop_fusion/src/pose_graph_node.cpp#L378-L475)。MH01/MH02地图复用任务也由 [Mono 官方 README](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/blob/90dabb5ec79946ae42fd2e1e91d4e69aabe1e25d/README.md#33-map-reuse)明确演示；Fusion 的对应能力本次直接核对了源码，并未声称已经实际运行该任务。

## 验收标准

第一阶段接受较差精度，但应有下列证据：

- 图像＋IMU能够完成初始化并持续输出局部VIO位姿。
- 先前保存的地图被成功加载。
- 新序列至少发生一次与旧序列关键帧的有效 PnP 匹配和坐标对齐；不能仅凭词袋检索候选或 RViz 出现一条 path 判定成功。
- 对齐后 /loop_fusion/odometry_rect 持续输出旧图坐标中的 position 与 orientation，匹配间隔中也有输出；输出频率跟随输入 VIO Odometry，而不是宣称等于原始 IMU 频率。
- 原始 Odometry 和全局修正输出均被记录，能展示地图纠偏的效果。允许首次对齐、图优化后有跳变，允许短时定位缺失和漂移。
- 明确记录第一次地图匹配前为“尚未地图定位”。源码在对齐前也发布 world 帧标签，不能只看话题存在就算满足绝对定位。

原生 odometry_rect 的 pose 是 body/IMU 位姿。若展示照片相机位姿，需要再乘相机到机体外参；源码的相机可视化已包含这两行转换。pose 输出之外的 covariance/velocity 不能未经核对当作完整有效的融合状态。[位姿和相机外参转换源码](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/loop_fusion/src/pose_graph_node.cpp#L192-L227)

IMU模式的全局后端主要优化 x/y/z/yaw，是利用重力方向约束的设计；它仍然输出完整位置和旋转，不是只有四个位姿分量。[图对齐与重力方向处理](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/loop_fusion/src/pose_graph.cpp#L111-L154)

## 边界

本方案不要求孤立单图独立定位。VINS两仓保存的地图主要是位姿图、二维点和BRIEF；PnP使用当前VIO三维点与旧图二维观测，所以必须先有运行中的VIO。这与用户这次确认的需求一致。[Fusion PnP](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/loop_fusion/src/keyframe.cpp#L270-L285)、[地图保存](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/blob/be55a937a57436548ddfb1bd324bc1e9a9e828e0/loop_fusion/src/pose_graph.cpp#L898-L950)

地图坐标系的位姿不等于地图本身精确、也不等于已配准到 EuRoC ground truth。第一阶段把两功能接通作为验收；之后若需误差数字，要规定同一个参考系与对齐方法，不能为每条输出各自随意拟合后宣称绝对精度。
