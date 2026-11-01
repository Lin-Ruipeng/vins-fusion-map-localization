# 《Get Out of My Lab》论文与复现范围核查

调研日期：2026-11-01。范围：论文原文、会议官方记录、maplab 官方说明与示例数据目录。未编译程序，未下载或校验大型数据包。

## 书目信息

- 标题：*Get Out of My Lab: Large-scale, Real-Time Visual-Inertial Localization*。
- 作者：Simon Lynen、Torsten Sattler、Michael Bosse、Joel Hesch、Marc Pollefeys、Roland Siegwart。
- 会议：Robotics: Science and Systems XI，2015 年 7 月，意大利罗马。
- DOI：10.15607/RSS.2015.XI.037。

来源：[RSS 官方论文记录](https://roboticsproceedings.org/rss11/p37.html)；[论文全文](https://roboticsproceedings.org/rss11/p37.pdf)。

## maplab 与论文的关系

**有直接的官方依据支持用户记忆。** maplab 官方引用说明把这篇 RSS 2015 论文列在 Localization 项下，明确表示该模块建立在这项工作之上。同一文件另外把 ROVIOLI 解释为 ROVIO 与 maplab 的组合，并引用 ROVIO 的 2017 年论文。[官方引用说明源文件](https://github.com/ethz-asl/maplab/blob/master/docs/pages/overview_and_introduction/B_Citing-Maplab.md)

当前仓库 README 说明这是 maplab 2.0；原始 maplab 框架论文发表于 2018 年。**据此可判断：maplab 是合理的开源复现入口，但不能直接认定当前完整系统就是 RSS 2015 实验原版。**[仓库 README](https://github.com/ethz-asl/maplab#readme)

## 原文中需对齐的内容

论文核心链路包括：离线视觉惯性建图；地图裁剪与描述子投影、PQ 压缩；倒排多索引匹配、共视过滤与 RANSAC 位姿估计；将全局 2D–3D 约束直接融入局部滤波器。[原文 II–V 节](https://roboticsproceedings.org/rss11/p37.pdf)

V 节采用接近 MSCKF 的滑窗视觉惯性估计器。式 (4) 的 N 个相机姿态是历史姿态窗口，不能据此推导出 N 台实体相机；原文未确认在线自标定。ROVIOLI 的 ROVIO 基础与之存在差异，需另行核对更新实现。[原文 V 节](https://roboticsproceedings.org/rss11/p37.pdf)；[ROVIOLI 官方引用](https://github.com/ethz-asl/maplab/blob/master/docs/pages/overview_and_introduction/B_Citing-Maplab.md)

实验 VI-A 使用自采市中心 1.44 km 建图序列及另录评估序列；参考轨迹由全批视觉惯性 BA 对齐得到。应比较位置、姿态误差、轨迹平滑度、匹配内点、耗时和模型大小，而不只比较一项 ATE。Table III 的 EKF 为 0.17±0.12 m、0.32±0.16°，更新耗时 2.9±1.5 ms，均为均值与标准差；不能称作中位数或套用至当前硬件。[原文 VI 节、Table III](https://roboticsproceedings.org/rss11/p37.pdf)

## 原始材料的公开性

当前官方 sample datasets 页面提供 CLA、Zurich old town 与 EuRoC 的数据或地图入口，页面上下文是 maplab，不能把其中的“from the paper”自动解释为 RSS 2015 的完整实验数据。[官方数据目录源文件](https://github.com/ethz-asl/maplab/blob/master/docs/pages/datasets/A_Sample-Datasets.md)

EuRoC 官方现行页面已声明所有数据迁入 ETH Research Collection，档案 DOI 为 10.3929/ethz-b-000690084。旧地址故障不能据此判断数据已不可得；应使用这个当前入口。[EuRoC 官方现行页面](https://projects.asl.ethz.ch/datasets/euroc-mav/)；[ETH 数据档案 DOI](https://doi.org/10.3929/ethz-b-000690084)

**本次未核实到**有明确标识为 RSS 2015 全套复现实验包的公开下载入口：包括匹配的建图与评估原始序列、相机/IMU 标定、参考轨迹、地图、词典/PQ 模型和生成全部图表的参数脚本。论文官方页面主要提供书目信息与全文，不提供可确认身份的完整实验包。这是“尚未找到并确认”，不等于证明这些材料从未公开。[RSS 官方页面](https://roboticsproceedings.org/rss11/p37.html)；[官方示例目录](https://github.com/ethz-asl/maplab/blob/master/docs/pages/datasets/A_Sample-Datasets.md)

链接存在与下载成功是两个层面的验证；本文件不宣称已下载、解压或校验这些数据。

## 对复现工作的判断

以下是基于上述证据的工作建议，而非作者对复现完整性的承诺：

| 目标 | 判断 | 首要工作 |
|---|---|---|
| 跑通已有地图中的视觉惯性定位 | 有清晰的开源入口 | 固定 maplab/ROVIOLI 版本与依赖，用官方示例建立基线 |
| 重做匹配、压缩、全局约束等方法实验 | 需要逐项核对实现 | 为论文各模块记录代码位置、默认值、训练产物和差异 |
| 重现 RSS 2015 的原始图表和数值 | 当前证据不足以保证 | 先核实原始序列、标定、地图、参考轨迹及原版滤波器是否可取得 |

如果采用 EuRoC/CLA、ROVIOLI 与新的机器，应明确称为“基于公开实现的方法复现实验”，记录与原论文的差异。若目标是逐图逐表的数值复现，应先解决材料身份与算法版本问题，再投入大规模构建和调参。
