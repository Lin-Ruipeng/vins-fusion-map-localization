# 平台和首次安装

完整复现需要一个能执行终端命令、联网、访问本目录和 Docker 的 Agent。公开附件下载不要求 GitHub 账号或 Token，也不要求宿主安装 ROS、Ceres、OpenCV 或 GPU 工具。

## Linux x86_64

实际基线是 Ubuntu 26.04.1 x86_64 + Docker 29.1.3；具体新目录复现结果见 `reference_results/clean_reproduction/`。其他 Linux 发行版未逐一实测。

准备 Docker Engine、Git、curl、Python >=3.8、gzip、tar、sha256sum 和 flock。Debian/Ubuntu 系统的宿主基础工具可用 `sudo apt-get install git curl python3 gzip tar coreutils util-linux` 安装。Docker 按 [官方 Ubuntu 安装说明](https://docs.docker.com/engine/install/ubuntu/)设置；安装涉及管理员权限时让用户完成授权。

先运行 `docker info`，确保当前用户能访问 daemon。遇到 socket 权限错误，按 Docker 官方说明处理用户组/会话权限；不要在宿主安装 ROS 来解决。Docker 用户组的权限影响见[官方安装后说明](https://docs.docker.com/engine/install/linux-postinstall/)。

建议预算：4 个 CPU 线程、16 GiB 内存、40 GiB 可用磁盘。doctor 将少于 8 GiB 可见内存、少于 25 GiB 可用磁盘视作环境不足。这是工程预留值，不是跨硬件测得的算法最低配置。下载包含约 1 GB 环境镜像和约 2.9 GB EuRoC ZIP；解压、bag、地图和 Docker 层另外占用空间。

## Windows + WSL2（指引已提供，尚未在 Windows 实机验证）

这条路线使用 x86_64 Windows、WSL2 Ubuntu 和 Docker Desktop 的 Linux 容器。不是原生 PowerShell ROS 移植；Windows ARM 和 Apple Silicon 未验证。

1. 按[微软 WSL 安装说明](https://learn.microsoft.com/en-us/windows/wsl/install)，在管理员 PowerShell 执行 `wsl --install`。根据提示重启，首次打开 Ubuntu 后创建 Linux 用户。
2. 安装并启动 [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/)。按[官方 WSL2 指引](https://docs.docker.com/desktop/features/wsl/)启用 WSL2 引擎，并在 Settings → Resources → WSL Integration 启用相应 Ubuntu 分发版。保持 Linux containers 模式。
3. 在 Ubuntu/WSL2 终端运行 `uname -m`（应为 x86_64）和 `docker info`。这条路线通过 Desktop 集成使用 Docker，不在 WSL 内再装一套 Docker Engine。
4. 把项目放在 WSL Linux 文件系统，例如 `~/work/vins-fusion-map-localization`；在这个终端内运行 Agent 和 README 的命令。安装缺失的 Git、curl 和 Python 等基础工具。
5. 运行 `bash scripts/reproduce.sh`。若机器较慢，使用 `bash scripts/reproduce.sh --rate 0.25`。

首次启用虚拟化、管理员授权、重启或学校设备限制可能需要本人/管理员操作。Agent 应说明当前缺少什么，完成能自主处理的准备工作；不应把环境受阻报告成算法已复现。
