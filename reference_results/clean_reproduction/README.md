# 从空工作区执行完整复现

2026-11-01，完整入口实际通过。此目录是本次执行完成后的历史证据副本。完整耗时 25.6 分钟；新 MH01 地图 1091 个关键帧；MH02 1510 对位姿、461 次旧图 PnP。校正后位置 RMSE 0.193 m。

- 总状态：summary.json
- MH02 验收：mh02_verification.json
- 逐条 CSV/bag 核对：bag_export_validation.json
- 初始条件和附件传输说明：validation_context.json
- 两组重新下载的 ZIP 完整性：input_integrity.json

总报告中的 results/... 路径保留实际运行目录名称；本目录中的副本以 mh01_/mh02_ 前缀区分。候选镜像经匿名本机 HTTP 下载，字节与正式 Release 一致；源码与数据从公开网络重新获取。最终 GitHub 匿名访问检查另列于 publication_validation.json。
