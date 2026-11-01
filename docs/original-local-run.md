> 历史本机运行说明。新机器入口以仓库根 README 为准；历史结果在 reference_results。

# VINS-Fusion 先验地图复用 + 双目视觉惯性连续定位

实际运行日期：2026-11-01。官方提交 `be55a937a57436548ddfb1bd324bc1e9a9e828e0`，使用 `vins_node` 和 `loop_fusion_node`、官方 `euroc_stereo_imu_config.yaml`。本目录与原有资料隔离。

## 实际验收结果：已跑通

| 项目 | 本次实际结果 |
|---|---|
| 编译、节点启动 | 独立 Docker 镜像中通过；最终 ROS Kinetic / OpenCV 3.3.1 / Ceres 1.14 |
| MH01 全量建图与持久保存 | 1,831 对位姿；1,091 个关键帧；全部关键点、BRIEF、图像完整 |
| MH01 同序列复用检查 | 重启后加载旧图、PnP、对齐通过；30 秒、281 对位姿 |
| MH02 独立跨序列验证 | 全量 151.995 秒传感器数据；461 次指向已加载旧图的有效 PnP |
| 连续地图位姿 | 1,510 对局部/校正消息；实际对齐后 1,495 条；10 Hz，最大时间戳间隔 0.1 秒 |
| 匹配间隔中的运动 | 25.79 秒无旧图 PnP 的间隔中仍发布 128 条位姿，位置变化约 3.40 m、姿态变化约 9.09° |
| 消息与导出核验 | 1,510 对消息逐条核对：实时 CSV 与输出 bag 的数值差为 0；全部位置有限、四元数单位化 |
| 事后位置评价 | 共同参考下 RMSE：地图校正后 0.197 m；冻结首次地图对齐的 VIO 0.268 m；MH01 参考拟合残差 0.168 m |
| MH02 正常退出 | vins、loop_fusion、回放、录包、ROS master 退出码全部为 0 |

逐项断言及精确数据见 `results/mh02_localization/verification.json`；评价仅代表本次运行，参考变换方法见下文。

## 从这里开始

已附实际保存的 MH01 地图、完整源码、编译产物、Dockerfile 和可离线导入的镜像。主机需要能访问 Docker socket，全部 ROS 进程在同一个无界面容器中运行，无需宿主 ROS 或真实硬件。

```bash
cd <original-workspace>/vins_fusion_lab
bash scripts/build.sh
# 直接使用随附地图重新运行 MH02，run 名称必须是新的：
bash scripts/run.sh mh02 0.5 mh02_repeat
bash scripts/export_and_verify.sh mh02_repeat
```

`build.sh` 检查源码版本和补丁，加载已有镜像或从 Dockerfile 构建，并编译所需包。容器统一挂载本目录为 `/work`，以宿主 UID/GID 写入；容器内所有结果路径均为可写的绝对路径。

## 完整建图 → 保存 → 加载 → 定位

数据已获取并校验，正常无需再次下载。新环境需要下载时：

```bash
# 官方来源；若限流，可用公开同字节镜像，仍核对官方 ZIP CRC：
EUROC_SOURCE=mirror DOWNLOAD_WORKERS=8 bash scripts/download_data.sh

# 新建独立地图，保留随附的 maps/mh01/：
MAP_NAME=mh01_rebuilt bash scripts/run.sh build-map 0.5 mh01_rebuilt
python3 scripts/validate_map.py mh01_rebuilt

# 可选：30 秒同序列功能检查（不能当作独立序列验证）：
MAP_NAME=mh01_rebuilt bash scripts/run.sh mh01-check 1.0 mh01_check_again 30

# 独立 MH02 全量回放与导出：
MAP_NAME=mh01_rebuilt bash scripts/run.sh mh02 0.5 mh02_rebuilt
bash scripts/export_and_verify.sh mh02_rebuilt
```

脚本等待节点订阅就绪，仅回放 `/cam0/image_raw`、`/cam1/image_raw`、`/imu0`。建图结束自动向 loop_fusion 的 stdin 输入原生 `s`，保存并退出。定位配置为 `load_previous_pose_graph: 1`。地图路径始终保留末尾 `/`。已有地图和同名运行结果会拒绝覆盖。

## 交付文件

- `maps/mh01/`：实际 MH01 地图，1,091 个关键帧；`pose_graph.txt`、每帧图像、关键点和 BRIEF，另附逐文件 SHA256 和 `validation.json`。
- `results/mh01_build/`：MH01 全量建图；1,831 对实际局部/校正位姿。初次保存后的官方退出异常及修复经过见构建记录；地图完整性已校验。
- `results/mh01_replay_check/`：重启并加载地图后的 30 秒 MH01 同序列检查，281 对位姿；所有节点退出码为 0。
- `results/mh02_localization/`：独立 MH02 验证，最终数据以 `verification.json` 为准。
- 每次运行的 `vio_odometry.csv` 和 `map_odometry.csv`：真实消息，列为 `timestamp_ns,receive_wall_s,px,py,pz,qx,qy,qz,qw`。
- `outputs.bag`：局部位姿、地图校正位姿、关键帧、外参、匹配图、地图轨迹和 ROS 事件日志；原始输入 bag 在 `data/`。
- `*_from_bag.csv`、`*.tum`、`bag_export_validation.json`：从实际 bag 复核导出，逐条验证实时 CSV 数值一致。
- `first_cross_sequence_match.png`、`events.json`、`verification.json`、`trajectory_comparison.png`、`continuity_evidence.png`：首次连接、验收事件、连续输出与轨迹对比。
- `environment/BUILD_NOTES.md`、`environment/Dockerfile`、`patches/vins-fusion.patch`：实际环境、遇到的问题和必要修复；`logs/` 保留构建与驱动日志。
- `data/provenance.json`、`data/*/validation.json`：下载来源、CRC/SHA256、标定和原始时间戳核对。

## 验收口径与限制

MH02 首次连接：当前关键帧 `1092` / sequence `1` 对旧图关键帧 `2` / sequence `0`，88 个对应、50 个 PnP 内点；随后实际执行跨序列对齐。`MAP_LOADED`、`PNP_ACCEPT`、`CROSS_SEQUENCE_ALIGN` 分别位于 `loop.log`，也记录在输出 bag。MH01 重放的数字序列同样为 0→1，必须结合输入 bag/`invocation.json` 区分真实数据序列。

`odometry_rect` 在首次匹配前也发布，本报告只把实际旧图对齐之后的消息视为地图定位结果。验收程序用日志里的实际 wall time 与 CSV 的接收 wall time 建立对应，并检查两次旧图 PnP 之间仍有位姿输出。

输出是 **body/IMU 位姿**，不是相机位姿。相机位姿应另算 `T_WC = T_WB * body_T_cam`。只验证 pose 的位置与单位四元数，不把原生校正消息中的速度、协方差当作已验证融合状态。输出约 10 Hz（0.5 倍回放约为墙钟 5 Hz），不等于原始 200 Hz IMU。

Ground truth 只在事后评价使用。轨迹图将 MH01 ground-truth body 位置用一次 SE3、固定尺度 1 对齐到已保存 MH01 优化关键帧，再把同一变换用于 MH02 GT；不针对 MH02 重新拟合。比较中的“冻结首次对齐 VIO”只使用实际第一次地图几何对齐，之后不再更新该变换。

本次验证功能链路和连续发布，不保证精度或轨迹平滑。原生门限、模型和噪声参数保留；地图匹配及图优化可能引入跳变、误闭环或劣于局部 VIO 的误差。没有验证真实硬件、单目、孤立单张照片或地理坐标定位；加载的是位姿图/二维点/BRIEF，新 VIO 会话仍需初始化。
