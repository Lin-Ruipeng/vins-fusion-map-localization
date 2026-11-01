# 失败后的处理

每次完整运行会生成 `results/<run-id>/summary.json`。先看 `status`、`current_stage`、`error` 和该阶段 `.log`。仅 `status: passed` 才是这次完整复现通过。

| 情况 | 处理 |
|---|---|
| 缺少 docker / daemon 未启动 / socket 权限 | 参照 `platforms.md` 让当前 Linux/WSL2 会话能运行 `docker info`；然后重新运行入口 |
| Docker 显示 ARM 或 Windows containers | 使用 x86_64 Linux 容器环境；本版本未提供 ARM 原生环境 |
| Release 404 | 检查仓库 Release `v0.1.0-euroc` 是否正式发布；正式地址在 `artifacts/manifest.json` |
| 网络中断或超时 | 重跑同一下载命令，保留 `.partial` 和数据分段；EuRoC 默认先镜像、失败时切换官方，可用 `EUROC_SOURCE=official` 调整优先级 |
| SHA256 / CRC 不符 | 保留故障日志和坏文件，移走明确指出的坏缓存后重试；校验失败的镜像/地图不会加载 |
| 无 PnP 或 VIO 落后于播放 | 先核对 `vins.log` 初始化和时间戳；较慢 CPU 以 `--rate 0.25` 重新开始。保持原始几何验收条件 |
| 已有同名结果或地图 | 入口默认自动创建新 ID；手动指定 `--run-id` 时改用一个未使用名称，已有结果不会覆盖 |
| 运行超过总预算 | 默认总超时 120 分钟；网络正常但确实很慢时可用 `--timeout-minutes 240`，下载断点会复用 |
| Agent 只有网页聊天能力 | 改用能访问终端/文件系统和 Docker 的执行环境；公开报告只能用于阅读 |

修好原因后，重新运行 `bash scripts/reproduce.sh`。它会创建新的运行 ID，复用已校验下载，但重新建 MH01 地图、重新运行 MH02。中断时仅清理本次运行标签下的容器，保留日志与已有成果。

可单独恢复发布附件：`bash scripts/download_artifacts.sh image`、`map`、`bags` 或 `all`。默认 `map`。map 是历史 MH01 地图；bags 恢复到参考结果目录，均不构成本次完整复现。

数据到 ROS bag 的传感器时间戳会逐条与 ASL CSV 核对。定位入口只播放双目图像和 IMU；ground truth 只在之后评估中读取。位姿为 body/IMU，输出速率跟随 VIO，地图纠偏允许跳变。
