# 《Get Out of My Lab》复现调研

调研日期：2026-11-01（Asia/Singapore）。范围：核对论文、官方源码、版本与文档、数据入口和可复现程度。本次未安装依赖、编译项目或下载大型数据，以下运行方案属于基于源码与文档的建议，尚未经过本机运行验证。

## 结论

用户提供的 [ethz-asl/maplab](https://github.com/ethz-asl/maplab) 是正确的相关官方开源入口。尤其是 [1.3 版 README](https://github.com/ethz-asl/maplab/blob/1.3/README.md#additional-citations)，明确说明部分组件直接使用所列论文的代码，并将《Get Out of My Lab》列在 Localization 下。当前官方文档也将它列为定位组件的基础。[S1][S2]

但是，maplab 是后续整合的研究框架，当前默认分支已经是 maplab 2.0；它自己的主要论文是 maplab（2018）和 maplab 2.0（2023，预印本/初始发布为 2022）。不能把“成功运行当前 maplab/ROVIOLI”直接写成“完整复现 RSS 2015 原论文全部实验”。官方对 ROVIOLI 的定义是 ROVIO 加 maplab 的特征、建图、定位模块。[S1][S3][S4]

## 论文与复现目标

- 准确标题：*Get Out of My Lab: Large-scale, Real-Time Visual-Inertial Localization*。
- 作者：Simon Lynen、Torsten Sattler、Michael Bosse、Joel Hesch、Marc Pollefeys、Roland Siegwart。
- 会议：Robotics: Science and Systems XI，2015 年 7 月，Rome。
- DOI：10.15607/RSS.2015.XI.037。
- [RSS 官方论文页面](https://www.roboticsproceedings.org/rss11/p37.html)；[全文 PDF](https://www.roboticsproceedings.org/rss11/p37.pdf)。[S5]

这项工作研究的是：在已有大规模三维视觉地图中进行实时全局定位，并把全局地图约束融合进局部视觉惯性估计，兼顾计算/内存开销、全局精度和轨迹平滑性。它涉及描述子与地图压缩、快速匹配和估计器融合，不是只调用一次 PnP 即完成的任务。[S5]

可将目标分成三档。下面是本次调研的判断，并非作者对复现难度的承诺。

| 目标 | 可以使用的起点 | 完成后能够声称什么 |
| --- | --- | --- |
| 跑通系统流程 | maplab + ROVIOLI，EuRoC 的 MH01 建参考地图、MH02 查询定位 | 跑通后续官方框架的建图、优化、先验地图定位流程 |
| 复现论文核心方法 | 阅读论文与 loopclosure、descriptor-projection、localizer 源码；固定数据与参数做受控对比 | 在明确列出的数据和实现版本上验证匹配/压缩/融合的设计作用 |
| 严格复现论文图表和数值 | 原实验记录、地图、标定、参考轨迹、压缩配置、评价协议与原估计器 | 只有这些条件对齐后才能做同条件的原表复现；目前不能承诺材料齐全 |

论文原实验与原估计器的详细核对见同目录 `get-out-of-my-lab-paper-research.md`。原文第 V 节使用与 MSCKF 同类的滑窗视觉惯性估计；ROVIOLI 的 ROVIO 估计器与之不同。原文第 VI-A 节的 city-center 建图路线约 1.44 km，使用另一次记录进行评价，参考解通过全批视觉惯性优化生成。EuRoC 示例不能替代成原实验同数据复现。[S5][S4]

## 代码开放到什么程度

仓库公开，主要语言 C++，仓库元数据标识 Apache-2.0。第三方依赖和数据应分别以各自声明为准。[S6]

当前源码中可追踪的链路如下：

| 功能 | 主要位置 | 已核实事实 |
| --- | --- | --- |
| 二值描述子投影 | `algorithms/loopclosure/descriptor-projection` | 将二值描述子映射到低维实数空间；README 另引其基础工作 Placeless Place-Recognition（2014） |
| 描述子检索 | `algorithms/loopclosure/matching-based-loopclosure` | 包含 inverted multi-index、product quantization 和后来加入的 HNSW；二值描述子的默认检索器为 `imi` |
| 匹配过滤与几何验证 | `algorithms/loopclosure/loop-closure-handler` | 官方说明为投影 BRISK/FREAK、2D–3D 匹配、共视过滤、PnP + RANSAC |
| 在线先验地图定位 | `applications/rovioli/src/localizer.cc` | 把 localization summary map 放入数据库并查询，输出位姿与结构匹配 |
| 定位约束融合 | `applications/rovioli/src/rovio-localization-handler.cc` | 默认结构约束，即把 2D–3D 匹配交给 ROVIO 更新；提供可选 6DoF 约束模式 |
| 示例索引资源 | `algorithms/loopclosure/matching-based-loopclosure/share` | 源码树含 BRISK/FREAK 的 projection matrix 与 inverted multi-index quantizer 文件 |

来源：[描述子投影 README](https://github.com/ethz-asl/maplab/blob/master/algorithms/loopclosure/descriptor-projection/README.md)、[匹配模块 README](https://github.com/ethz-asl/maplab/blob/master/algorithms/loopclosure/matching-based-loopclosure/README.md)、[检索默认设置](https://github.com/ethz-asl/maplab/blob/master/algorithms/loopclosure/matching-based-loopclosure/src/detector-settings.cc)、[loopclosure 文档](https://github.com/ethz-asl/maplab/blob/master/docs/pages/tutorials-maplab/basics/F_Understanding-loop-closure.md)、[localizer](https://github.com/ethz-asl/maplab/blob/master/applications/rovioli/src/localizer.cc)、[融合处理器](https://github.com/ethz-asl/maplab/blob/master/applications/rovioli/src/rovio-localization-handler.cc)、[share 目录](https://github.com/ethz-asl/maplab/tree/master/algorithms/loopclosure/matching-based-loopclosure/share)。

需要留意：这些文件证明相关模块已公开，不能据此推断它们与 2015 年原实验的每项默认参数、训练资源和实现细节完全相同。

## 版本与当前维护状态

截至调研日，通过 GitHub API 核实：

| 版本/分支 | 参考提交 | 含义 |
| --- | --- | --- |
| `initial_release` | `63ea0c8acb669904a711817b3cb74e314ecffec7` | release 明确对应 maplab 的 RA-L 论文；发布于 2017-12-21，非 RSS2015 原版标签 |
| `1.3` | `33fcdb92bf16f974a92383ee0c1201883280812d` | README 指向的原始 2018 代 maplab；保留旧说明，定位模块直接引用 RSS2015 代码 |
| `master` | `0b4868efeb292851d71f98d31a1e6bb40ebb244b` | 当前默认分支、maplab 2.0；头提交时间 2023-06-18 |
| `develop` | `fbb02d2ba2c94b2f103582b5d466e603e6f08a5f` | 当前安装文档仍让用户克隆的分支；头提交时间 2022-11-01，不能只凭名称认定比 master 更新 |

来源：[releases](https://github.com/ethz-asl/maplab/releases)、[1.3 ref](https://api.github.com/repos/ethz-asl/maplab/git/refs/tags/1.3)、[initial_release ref](https://api.github.com/repos/ethz-asl/maplab/git/refs/tags/initial_release)、[master 提交列表](https://api.github.com/repos/ethz-asl/maplab/commits?per_page=1)、[develop 提交列表](https://api.github.com/repos/ethz-asl/maplab/commits?sha=develop&per_page=1)。

仓库尚未归档。仓库元数据的 `pushed_at` 是 2024-05-31，但默认分支头提交是 2023-06-18；二者含义不同，不应把前者或 star 引起的 `updated_at` 当成最新代码发布日期。以上事实显示它是一套需要自行处理兼容问题的旧研究栈；“维护不活跃”是据提交与问题情况作出的判断，不等于官方宣布停止维护。[S6]

## 环境与已确认的复现障碍

1. **版本与环境必须配套。** 1.3 README 面向 Ubuntu 14.04/ROS Indigo、16.04/ROS Kinetic；当前源码内安装文档面向 Ubuntu 18.04/ROS Melodic，并把 Ubuntu 20.04/ROS Noetic 标为 experimental。仓库 `deploy/Dockerfile` 使用 Ubuntu 18.04，`deploy/install_ros.sh` 安装 Melodic。没有据此证明现代 Ubuntu 22.04/24.04 可直接安装，也没有验证原 Docker 脚本今天可以无修改构建。[S1][S7][S8]

2. **ROS 1 已结束上游支持。** ROS PMC 将 Noetic EOL 定为 2025-05-31。这会增加重建历史依赖的工作；建议把选定环境封装成容器/虚拟机，并记录镜像与依赖版本。该建议是工程判断，不是要求将项目迁移到 ROS 2。[S9]

3. **教程与源码已存在可直接验证的不一致。** 当前 `tutorial_euroc` 仍传 `--ncamera_calibration`、`--imu_parameters_maplab`；当前 `rovioli-app.cc` 使用的是 `--sensor_calibration_file` 和可选 `--external_imu_parameters_rovio`。因此不能把旧教程命令作为当前 master 已验证的执行方案。issue #414 也有用户报告 unknown flag，后续社区回复提供修正经验；修正参数的依据应优先看本次检出的实际源码，而不是直接照搬回复中的 IMU 噪声值。[S10][S11]

4. **递归依赖布局变了。** 当前 `.gitmodules` 的依赖已在仓库内部的 `dependencies/3rdparty`、`dependencies/internal`，大量 URL 使用 SSH；旧 wiki 的方案则另克隆 `maplab_dependencies`。两代方案不能混用，复现时必须锁定主仓库、子模块以及旧版需要的外置依赖提交。主仓库公开并不意味着当前 SSH 子模块路径能在无密钥环境直接递归克隆。[S12][S13]

5. **编译本身不是结果复现。** 官方要求配置 catkin merge-devel，推荐 Release，并特别提醒直接无目标 `catkin build` 可能碰到多余包缺依赖，应按目标构建 `catkin build maplab`。即便通过，还需要确认相机/IMU 标定、topic、时间同步、地图版本和定位更新有效。[S7][S14]

## 数据可用性

### 可用于先跑通流程的数据

官方定位教程确实给出 **MH01 建图、优化为定位地图，MH02 在该先验地图中定位** 的完整任务结构。输入可以是 full VI map 或 localization summary map；使用未优化地图会影响效果。[S14]

maplab Sample Datasets 页面列有 CLA 多楼层建图/定位 rosbag、标定与 VI maps、Zurich old town 优化地图，以及 EuRoC MH01–MH03。页面的 “from the paper” 不能直接理解为 RSS2015 原论文；这是 maplab 框架的数据文档，单凭名称也不能认定 Zurich old town 地图就是 RSS2015 全部原实验材料。另外，合并优化后的 CLA 地图在所读文档里仍标为 coming soon。[S15]

### 旧地址与新存档

- 2026-03-23 的 [issue #424](https://github.com/ethz-asl/maplab/issues/424) 报告 sample datasets 中的旧下载地址（含 EuRoC MH01）失效；调研时该 issue 没有评论。这是一条具体用户报告，不能扩展成“所有数据都消失了”。
- 本次读取旧 `robotics.ethz.ch/~asl-datasets/` 的相关目录返回超时。超时只说明本次访问失败，不是服务器永久下线的证明。
- [EuRoC 新官方页面](https://projects.asl.ethz.ch/datasets/euroc-mav/) 明确说明数据现已迁至 ETH Research Collection；DOI 为 [10.3929/ethz-b-000690084](https://doi.org/10.3929/ethz-b-000690084)。[S16]
- [ETH 当前存档记录](https://www.research-collection.ethz.ch/items/bcaf173e-5dac-484b-bc37-faf97a594f1f) 列出 Machine Hall 约 12.1 GB、Vicon Room 1/2、标定数据和说明 PDF。因此存在官方恢复入口。本次未下载大文件、验证压缩包内容或 rosbag 是否完整，不能承诺旧教程单个 `.bag` 直链已恢复。[S17]

### 严格复现仍需补齐的材料

本次尚未核实有一个公开打包入口同时提供 RSS2015 的原 city-center 建图记录、独立 query 记录、地图、全批优化参考轨迹、原滤波器快照和全部消融评价脚本。这里的结论是“没有核实齐全”，不是“确定未公开”。后续若以同表同数值为验收目标，应优先针对这些材料继续追索，再决定需要重建多少原实现。[S5]

## 建议的实施顺序

1. **确定验收目标。** 第一阶段采用“后续官方系统的可运行基线”，同时单独记录它与 RSS2015 的差异；如果目标必须是原表数值，先补原数据和协议。
2. **选定一个版本并锁定。** 若希望减少 2.0 传感器接口重构的干扰，可先评估 1.3 和匹配的历史依赖/环境；若要继续开发 2.0，可固定当前 master，并按源码修正参数和标定。1.3 依然不是 2015 原估计器，且老环境恢复成本未实测，不能保证选旧版一定更省事。
3. **拿到 EuRoC MH01、MH02。** 从新 ETH 存档核实数据格式与校验，再配套所选版本的传感器配置。
4. **完成最小闭环。** MH01 运行 VIO 建图，做闭环与地图优化，保存先验定位地图；MH02 分别运行纯 VIO 与地图辅助定位，确认地图匹配与滤波更新确实发生。
5. **补量化与消融。** 在固定参考地图坐标系/对齐协议下比较轨迹误差、定位成功率、首次成功定位时间、运行耗时和地图内存。区分定位器耗时与高频 VIO 耗时。之后再增加描述子/地图压缩和结构约束/6DoF 约束对比。指标定义与是否对应原文图表必须逐项注明，不能把新基线结果混写为原论文结果。

上述顺序是基于公开材料制定的方案。本轮产出是调研与可行性判断，没有生成已运行的性能数字、工时承诺或安装成功声明。

## 主要来源

[S1]: https://github.com/ethz-asl/maplab/blob/1.3/README.md
[S2]: https://github.com/ethz-asl/maplab/blob/master/docs/pages/overview_and_introduction/B_Citing-Maplab.md
[S3]: https://github.com/ethz-asl/maplab/blob/master/README.md
[S4]: https://github.com/ethz-asl/maplab/blob/master/docs/pages/tutorials-rovioli/A_ROVIOLI-Introduction.md
[S5]: https://www.roboticsproceedings.org/rss11/p37.pdf
[S6]: https://api.github.com/repos/ethz-asl/maplab
[S7]: https://github.com/ethz-asl/maplab/blob/master/docs/pages/installation/A_Installation-Ubuntu.md
[S8]: https://github.com/ethz-asl/maplab/blob/master/deploy/Dockerfile
[S9]: https://discourse.ros.org/t/ros-noetic-end-of-life-may-31-2025/43160
[S10]: https://github.com/ethz-asl/maplab/blob/master/applications/rovioli/scripts/tutorials/tutorial_euroc
[S11]: https://github.com/ethz-asl/maplab/blob/master/applications/rovioli/app/rovioli-app.cc
[S12]: https://github.com/ethz-asl/maplab/blob/master/.gitmodules
[S13]: https://github.com/ethz-asl/maplab/wiki/Installation-Ubuntu
[S14]: https://github.com/ethz-asl/maplab/blob/master/docs/pages/tutorials-rovioli/C_Running-ROVIOLI-in-Localization-mode.md
[S15]: https://github.com/ethz-asl/maplab/blob/master/docs/pages/datasets/A_Sample-Datasets.md
[S16]: https://projects.asl.ethz.ch/datasets/euroc-mav/
[S17]: https://www.research-collection.ethz.ch/items/bcaf173e-5dac-484b-bc37-faf97a594f1f
