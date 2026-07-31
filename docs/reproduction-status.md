# Helix 论文实验复现总状态

更新时间：2026-07-31

## 总结

当前已经完成了**适合单台 8 GiB WSL 笔记本的 Helix 核心模拟器复现**，包括模型放置、请求调度、cluster pruning、MILP 初值消融和模型放置质量曲线。

这还不是论文全部端到端实验的 100% 重跑。论文中的真实系统实验依赖多台异构 GPU 和真实跨区域网络；本机不具备这些硬件。部分 MILP 实验还受到 Gurobi 许可证过期限制。

## 已完成

### 1. 环境、仓库和教程流程

- Ubuntu 22.04 + VS Code Remote 已可用。
- Python 虚拟环境、依赖、`PYTHONPATH` 已验证。
- `step1_gen_cluster.py`：生成集群配置成功。
- `step2_model_placement.py`：生成 Petals 等布局成功。
- `step3_quick_simulation.py` / MaxFlow offline：仿真成功并获得吞吐量、延迟结果。

### 2. Figure 9：Model placement

在相同 MaxFlow scheduler 下对比 Helix、Petals、Swarm：

| 场景 | Helix | Petals | Swarm | Helix/Petals | Helix/Swarm |
|---|---:|---:|---:|---:|---:|
| Single cluster | 249.0 | 208.6 | 125.2 | 1.19x | 1.99x |
| Geo-distributed | 98.0 | 66.6 | 41.6 | 1.47x | 2.36x |

比例与论文接近，最大相对偏差约 5.3%。

输出目录：`tmp/helix_layout_reproduction/`

### 3. Figure 10：Request scheduling

固定 Helix 布局，对比 MaxFlow、Swarm、Random、Shortest Queue：

| 场景 | MaxFlow | Swarm | Random | Shortest Queue |
|---|---:|---:|---:|---:|
| Single cluster | 249.0 | 189.7 | 199.4 | - |
| Geo-distributed | 99.8 | 81.7 | 87.4 | 83.6 |

相对比例与论文基本一致，偏差约 0.1% 至 3.2%。

输出目录：`tmp/helix_scheduler_reproduction/`

### 4. Figure 11(a) + Table 8：Cluster pruning

- 24 节点官方参数完整本机实跑：剪枝后 98.0 token/s，未剪枝 74.9 token/s。
- 42 节点完整 660 秒仿真会占满 8 GiB WSL 内存，因此没有冒险跑完；报告采用 artifact README 提供的长跑结果 645.6 / 574.238 token/s。
- Table 8 的变量数完整复现：24 节点减少 36.34%，42 节点减少 46.45%，与论文的 36% / 46% 一致。

输出目录：`tmp/helix_pruning_reproduction/`

### 5. Figure 11(b)：Heuristic initial values

由于本机 Gurobi 许可证已过期，使用仓库自带官方 trace，按“首次达到 trace 最终最佳 incumbent”统计：

| 节点数 | Raw | Heuristic initial values | trace 中减少 | 论文 |
|---:|---:|---:|---:|---:|
| 24 | 5080s | 2655s | 47.7% | 43% |
| 42 | 2886s | 2875s | 0.4% | 8% |

24 节点趋势与数量级一致；42 节点官方 trace 未复现论文的 8%，符合文中“结果依赖硬件和具体 MILP 实例”的限制说明。

### 6. Figure 12：Model placement quality

从仓库官方 Gurobi trace 重画曲线：

- 最优吞吐目标：286.587410 token/s。
- 首次找到最优布局：277 秒（4.62 分钟）。
- 证明最优：3802.88 秒（63.38 分钟）。

完整复现论文“5 分钟内找到最优布局，但证明最优需要超过 1 小时”的结论。

输出目录：`tmp/helix_quality_reproduction/`

## 尚未完成或无法在当前笔记本完成

1. **真实系统 GPU 实验**：Figure 6-8 中的端到端实机结果需要 A100、L4、T4、V100 等多台 GPU 和真实网络。
2. **42 节点 660 秒本机长仿真**：事件历史占用超过 8 GiB 内存，会导致 swap 激增并存在 WSL/VS Code 断连风险。
3. **重新求解 MILP**：当前 Gurobi 11.0.3 许可证已于 2025-11-24 过期；Figure 11(b)、Figure 12 只能分析官方 trace。
4. **论文所有负载组合**：尚未逐一重跑 Figure 6-8 的每个模型、在线/离线、布局和调度组合。

## 当前可以怎样表述成果

推荐写法：

> 在单台笔记本的 Ubuntu 22.04 / WSL 环境中完成了 Helix artifact 的核心模拟器复现。Figure 9 和 Figure 10 的主要相对趋势与论文一致；Figure 11 的 24 节点剪枝实验和 Table 8 问题规模得到复现；Figure 11(b) 与 Figure 12 基于官方 Gurobi trace 完成分析。真实多 GPU 实验、42 节点长仿真和 MILP 重新求解受硬件、内存及许可证限制，未宣称为本机端到端重跑。

## 下一阶段需要的资源

- 若要补 42 节点长仿真：建议给 WSL 至少 16-24 GiB 内存。
- 若要重新求解 MILP：申请有效的 Gurobi Academic License。
- 若要完成论文端到端复现：需要实验室异构 GPU 集群，优先从单集群 LLaMA 30B 离线实验开始。
