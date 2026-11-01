# v0.1.0-euroc

公开的 VINS-Fusion 先验地图复用与双目视觉惯性连续定位实验。

```bash
git clone https://github.com/Lin-Ruipeng/vins-fusion-map-localization.git
cd vins-fusion-map-localization
bash scripts/reproduce.sh
```

默认完整入口重新下载并校验 EuRoC、编译固定源码、MH01 建图、保存、重启加载新地图、MH02 定位并自动验收。本次空目录完整流程实际通过：25.6 分钟，1,091 个新关键帧、1,510 对 MH02 位姿、461 次旧图 PnP，统一参考下位置 RMSE 0.193 m；所有节点正常退出。

Linux x86_64 为实测基线。Windows/WSL2 提供配置说明，尚未实机验证。Agent 需要终端、网络和 Docker 权限；附件公开下载无需 GitHub Token。

附件是最初历史运行的 MH01 地图、完整环境镜像和三个输出 bag；新目录验证使用另外重新建立的地图，证据已提交到 reference_results/clean_reproduction。SHA256SUMS 和仓库 artifacts/manifest.json 固定附件字节。环境镜像按镜像 ID 检查，地图恢复逐文件检查。

输出是 body/IMU 位姿，地图纠偏可能跳变。数据与含图像的地图/bag 遵循 EuRoC 官方记录的非商业使用条款；软件许可与数据条款分开，见 THIRD_PARTY_NOTICES.md。
