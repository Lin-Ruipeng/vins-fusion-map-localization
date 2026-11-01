# 实际构建与修复记录

2026-11-01，宿主 Ubuntu 26.04.1 / x86_64，Docker 29.1.3。工作区及父目录未发现适用 AGENTS.md。原 notes 和旧 VINS-Mono 项目均保留。

## 最终环境

- 官方源码：HKUST-Aerial-Robotics/VINS-Fusion，`be55a937a57436548ddfb1bd324bc1e9a9e828e0`。
- Ubuntu 16.04.7、ROS Kinetic / roscpp 1.12.17、GCC 5.4、CMake 3.5.1。
- ROS 自带 OpenCV 3.3.1-dev、Eigen 3.2.92、Ceres 1.14.0（附源码 tar 与 SHA256）。
- Python 2.7.12 / numpy 1.11.0 / matplotlib 1.5.1；主机仅用 Python 3 标准库下载、解压和校验。
- `Dockerfile` 固定官方 `osrf/ros` 基础镜像 digest，使用 Ubuntu 签名包源。`final_packages.txt` 是实际 dpkg 清单；`final_image_inspect.json` 是最终镜像元数据。
- `vins-fusion-lab-kinetic-ceres1.14.tar.gz` 为已实际使用的完整镜像导出。离线重放可 `gzip -dc ... | docker load`，无须访问旧 apt 源。
- 第一次源码编译借用本机已有 `vins-mono-local:kinetic-ceres1.14` 的依赖。随后按本目录 Dockerfile 真正构建独立镜像，并在独立镜像中重编译、通过退出探针和 MH01/MH02 运行。
- 只构建 `camera_models;vins;loop_fusion`。未使用 GPS 的 global_fusion。

## 已遇到的问题与处理

1. 默认 Codex 沙箱下 `docker version` 返回 socket permission denied，`curl` 域名解析失败；经过工具的沙箱外执行审批后均可用。没有安装宿主 ROS、修改用户组或使用宿主 sudo。
2. DOI/Research Collection 某些 GET 请求返回 `curl: (22) ... 429`；官方 API 的普通 User-Agent 请求成功。官方存档是 12.7 GB 的 `machine_hall.zip`，里面同时包含各序列 bag 和 ASL zip。先从官方读取 ZIP 中央目录，再分段下载所需成员。官方较慢且较高并发触发 429，最终用公开同字节镜像续传；完整成员 CRC32 仍以官方目录为准，并验证内部解压 CRC。详见 `../data/provenance.json` 和 `../logs/euroc_download*.log`。
3. 最初环境 Dockerfile 带入了旧 GUI/noVNC 依赖；`python-babel` 的 pycompile 长时间占满一核且无进展。停止该构建，移除本次无界面流程不需要的依赖。最终 `build_environment_headless.log` 完整构建成功。
4. MH01 原生 `s` 命令完整保存地图后，官方 main 中仍可 join 的 std::thread 析构，出现 `terminate called without an active exception` / SIGABRT。无数据探针也复现了 `loop_native_save=-6, vio_sigint=-6`。补丁让循环响应 `ros::ok()`、键盘线程 poll 输入、退出时 join 线程，修后同一探针为 `0,0`，后续有数据运行也正常退出。第一次保存的地图已逐文件校验完整，未因退出异常损坏。

## 源码补丁范围

`../patches/vins-fusion.patch` 是相对官方固定提交的完整补丁：

- 在实际 `findConnection` 接受分支记录 PnP 对应数、内点数、关键帧索引和序列；保留原来的 `>25`、yaw、平移验收条件。
- 在实际跨序列变换被设置之后记录对齐变换；在地图保存/加载完成之后记录数量。
- 修复上述线程退出行为。

未改动特征匹配、PnP、VIO、图优化代价函数、权重、门限或融合方法。MAPLAB 日志是交付所需的持久验收日志，不是候选图像检索日志。
