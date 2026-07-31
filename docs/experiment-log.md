# 对话驱动的完整实验日志

这份日志由本次对话整理而来，保留关键操作、错误、判断和修复过程。为便于公开，原始用户名和绝对路径被替换为通用变量：

```bash
export HELIX_ROOT="$HOME/llm-serving-repro/helix"
```

## 0. 研究背景和目标

初始情况：刚进入课题组，研究方向是 LLM serving 和 speculative decoding；只有一台笔记本，不熟悉 Linux、Git、Python 环境和论文复现。

在老师给出的论文中选择 Helix 作为第一个可动手实验，原因是其仓库提供离散事件模拟器和预生成布局，不要求本机拥有 A100/L4/T4 等 GPU 就能完成核心流程。

目标逐步明确为：

1. 跑通官方教程。
2. 理解 cluster -> model placement -> request scheduling -> simulation -> analysis 的完整链路。
3. 复现 Figure 9、10、11、12 中适合笔记本的部分。
4. 明确哪些结果是本机实跑，哪些来自官方 trace，哪些因硬件无法完成。

## 1. 检查 Ubuntu 环境

在 VS Code Remote 连接 Ubuntu 22.04 后，首先检查：

```bash
pwd
python3 --version
git --version
df -h ~
```

当时环境：Python 3.12.3、Git 2.43.0，主目录约有 920 GiB 可用空间。说明磁盘和基本工具没有问题。

## 2. 克隆 Helix

```bash
mkdir -p "$HOME/llm-serving-repro"
cd "$HOME/llm-serving-repro"
git clone https://github.com/Thesys-lab/Helix-ASPLOS25.git helix
cd helix
ls
```

仓库包含 `artifact_evaluation/`、`examples/`、`llm_sys/`、`simulator/` 等目录。

本次最终记录的上游 commit：

```text
8639497a4aaf1eb3b7594614cb0bbd376c1342b3
```

## 3. 第一个错误：找不到 simulator

从 `examples/simulation/` 直接运行：

```bash
python step1_gen_cluster.py
```

报错：

```text
ModuleNotFoundError: No module named 'simulator'
```

原因：Python 的模块搜索路径只有当前脚本目录，没有包含 Helix 仓库根目录。

曾经执行：

```bash
cd "$HELIX_ROOT"
python -c "import simulator; print(simulator.__file__)"
```

输出 `None`。这不是失败，而是因为 `simulator` 是 namespace package，没有传统 `__init__.py`，所以 `__file__` 可以为 `None`。

最终修复：

```bash
cd "$HELIX_ROOT"
export PYTHONPATH="$PWD"
cd examples/simulation
python step1_gen_cluster.py
```

为了避免每次重新设置，也可以使用：

```bash
cd "$HELIX_ROOT"
source .venv/bin/activate
pip install -e .
```

## 4. Step 1：生成集群配置

成功输出：

```text
Single cluster configuration file is generated to ./config/single24.ini
Partitioned cluster configuration file is generated to ./config/3cluster24.ini
```

验证：

```bash
ls config
```

可以看到 `single24.ini`、`3cluster24.ini`、`machine_profile.ini`。

这一阶段对应：定义节点类型、GPU 能力、网络带宽和延迟。

## 5. Step 2：生成模型放置

```bash
python step2_model_placement.py petals
ls layouts
```

输出：

```text
Petals layout synthesis is done! (Results in ./layouts/petals)
```

这一阶段决定：每个节点加载哪些 Transformer 层，节点之间形成什么 pipeline。

## 6. Step 3：第一次正式仿真

运行 MaxFlow offline 仿真后，终端长时间输出节点 KV-cache 使用率、active queries、finished queries、last/next event time。

第一次看到输出停在 `End Watch` 附近时，误以为程序卡死。随后发现 VS Code Remote 曾经断开连接。

排查方法：

```bash
ps -eo pid,stat,etime,pcpu,pmem,args | grep '[s]tep3_run_simulation.py'
tail -n 50 maxflow_offline.log
```

经验：

- `ps` 有进程且 CPU 时间增长：程序仍在运行。
- `ps` 没进程且命令提示符返回：程序已经结束或退出。
- 日志停在半行不一定是死锁，可能只是缓冲、断连或进程被终止。
- 长实验建议用 `tee`、`nohup` 或 `tmux` 保存输出。

## 7. 快速仿真与指标口径

为了避免新手阶段等待过久，新增快速仿真入口，并逐步统一统计口径：

- prompt token throughput
- decode token throughput
- total token throughput
- average prompt latency
- average decode latency
- completed / active queries

一次成功的快速结果示例：

```text
Avg decode speed: 25.9 tokens/s
Avg prompt latency: 3.909s
Avg decode latency: 3.301s
```

同时遇到：

```text
FigureCanvasAgg is non-interactive, and thus cannot be shown
```

这只是无图形界面的 WSL 无法执行 `plt.show()` 的警告，不影响数值结果。后续分析脚本统一使用 Agg 后端并保存 PNG。

## 8. 探索性实验

在进入论文图表复现前，先完成：

- quick comparison
- medium-duration comparison
- equal-load online comparison
- load sweep
- unified metrics sweep

这些实验用于回答两个问题：

1. 不同 scheduler/layout 是否真的在同一负载下比较？
2. 应该比较 decode throughput 还是 total throughput？

探索性结果保存在 `results/exploratory/`。它们是方法校准过程，不等同于论文最终图表。

## 9. Figure 9：模型放置对比

为了隔离 model placement 的影响，所有布局都使用同一个 MaxFlow scheduler。

单集群测量 300 秒、预热 60 秒；分布式集群测量 600 秒、预热 60 秒。

结果：

| 场景 | Helix | Petals | Swarm | Helix/Petals | Helix/Swarm |
|---|---:|---:|---:|---:|---:|
| Single | 249.0 | 208.6 | 125.2 | 1.19x | 1.99x |
| Distributed | 98.0 | 66.6 | 41.6 | 1.47x | 2.36x |

论文比例分别为 1.23x / 2.10x 和 1.49x / 2.38x。复现方向一致，最大偏差约 5.3%。

## 10. Figure 10：请求调度对比

为了隔离 scheduler 的影响，固定 Helix model placement，只替换 scheduler。

正式结果：

| 场景 | MaxFlow | Swarm | Random | Shortest Queue |
|---|---:|---:|---:|---:|
| Single | 249.0 | 189.7 | 199.4 | - |
| Distributed | 99.8 | 81.7 | 87.4 | 83.6 |

比例与论文接近。过程中还发现 baseline 需要使用官方给定的 initial query count；如果所有方法错误地使用相同初始请求数，会改变比较结论。

## 11. Figure 11：MILP 消融

### 11.1 Gurobi 许可证

安装的版本为 `gurobipy==11.0.3`，但许可证已于 2025-11-24 过期。因此不能诚实地声称“重新运行了 MILP”。

处理方式：

- cluster pruning 的布局仿真使用仓库预生成布局。
- Table 8 和 heuristic initial values 使用仓库官方 Gurobi trace。
- 报告明确区分 simulator rerun 和 trace analysis。

### 11.2 24 节点剪枝

官方设置：60 秒预热 + 600 秒测量。

```text
With pruning:    98.0 decode tokens/s
Without pruning: 74.9 decode tokens/s
```

本机结果与 artifact README 按显示精度一致。

### 11.3 42 节点内存问题

42 节点完整仿真运行时，Python 进程内存从约 4 GiB 上升到 7.5 GiB，WSL 可用内存降到十几 MiB，并开始大量使用 swap。

为防止 WSL/VS Code 被 OOM 杀死，先停止 runner 和仿真子进程。内存随后恢复到约 500 MiB。

之后运行 15 秒预热 + 30 秒测量的短测试，验证代码和布局能够运行。但只有 3 / 2 个请求完整结束，明确标记为 diagnostic，不用于论文吞吐量结论。完整对比采用 artifact README 的 645.6 / 574.238 tokens/s。

### 11.4 Table 8 与初值

从 trace 解析得到：

- 24 节点变量：1376 -> 876，减少 36.34%。
- 42 节点变量：4004 -> 2144，减少 46.45%。
- 24 节点达到最终 incumbent：5080s -> 2655s，减少 47.7%。
- 42 节点附带 trace：2886s -> 2875s，减少 0.4%，未达到论文报告的 8%。

## 12. Figure 12：模型放置质量

通过官方 `quality/trace.txt` 解析 incumbent 和 upper bound：

- 最优目标：286.587410 tokens/s。
- 277 秒首次找到最优布局。
- 3802.88 秒证明最优。

这复现了论文的核心观点：高质量解很早出现，后续大部分时间是在收紧 upper bound 和证明不存在更优解。

## 13. 当前结论

本次在笔记本上完成的是 Helix 核心 simulator / artifact 复现，不是完整多 GPU 端到端系统复现。

可以公开表述为：

> 在 Ubuntu 22.04 WSL2 笔记本环境中完成 Helix artifact 的核心模拟器复现。Figure 9 和 Figure 10 的相对趋势与论文一致；Figure 11 的 24 节点剪枝实验和 Table 8 问题规模得到复现；Figure 11(b) 与 Figure 12 基于官方 Gurobi trace 完成分析。真实多 GPU 实验、42 节点长仿真和 MILP 重新求解受硬件、内存及许可证限制，未宣称为本机端到端重跑。
