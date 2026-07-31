# Helix Figure 12 复现汇总

## 结论

Figure 12 的核心结论已由仓库附带的 Gurobi trace 复现：

- MILP 规模：350 个约束、316 个变量、3002 个非零项。
- 最优目标吞吐量：286.587410 tokens/s。
- 首次找到最优布局：277 秒（4.62 分钟），小于论文所说的 5 分钟。
- 完成全空间搜索并证明最优：3802.88 秒（63.38 分钟），超过 1 小时。
- 找到最优布局后，求解器还用了约 3526 秒来收紧 upper bound、证明没有更优解。

这验证了论文的工程观点：如果目标是尽快得到高质量模型放置，可以在找到稳定 incumbent 后提前停止；继续运行主要是在证明最优性。

## 复现范围

当前 Gurobi 许可证已过期，因此没有在本机重新执行 MILP。曲线由仓库官方 `quality/trace.txt` 自动解析，属于 artifact trace 复现，不是新硬件上的 solver rerun。

## 输出文件

- `figure12_reproduction.png`：按论文坐标口径重画的曲线
- `figure12_trace_points.csv`：从 Gurobi 日志抽取的时序点
- `figure12_milestones.csv`：首次可行解、首次最优解、最优性确认三个里程碑
- `analyze_figure12.py`：可重复运行的解析与绘图脚本
