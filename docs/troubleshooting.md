# Troubleshooting

## `ModuleNotFoundError: No module named 'simulator'`

```bash
cd "$HELIX_ROOT"
source .venv/bin/activate
pip install -e .
export PYTHONPATH="$HELIX_ROOT"
```

不要只在 `examples/simulation` 中启动一个没有项目根目录搜索路径的 Python。

## `simulator.__file__` 输出 `None`

不一定是错误。Helix 的 `simulator` 可以作为 namespace package 导入。应测试真实子模块：

```bash
python -c "from simulator.initial_layout.fake_cluster_generator import FakeClusterGenerator; print('ok')"
```

## 终端好久没有新输出

在另一个终端执行：

```bash
ps -eo pid,stat,etime,pcpu,pmem,rss,args | grep '[s]tep'
tail -n 50 experiment.log
free -h
```

- 进程存在、CPU 时间增长：仍在运行。
- 日志 0 字节但进程占 CPU：可能是 Python 输出缓冲。
- 可以设置 `export PYTHONUNBUFFERED=1`。

## VS Code Remote 断开

SSH/WSL 终端断开不等于计算必然停止。使用 `tmux`，并把 stdout/stderr 写入日志。

## `FigureCanvasAgg is non-interactive`

无图形 WSL 中 `plt.show()` 的警告。分析脚本应使用：

```python
import matplotlib
matplotlib.use("Agg")
```

然后用 `plt.savefig(...)` 保存图像。

## Gurobi license expired

当前实验环境的许可证已经过期。可选择：

1. 申请新的 Gurobi Academic License。
2. 不重新求解 MILP，使用上游仓库提供的 `trace.txt` 和预生成布局。
3. 在报告中明确写成 trace reproduction，不写成 solver rerun。

## 42 节点仿真内存占满

不要等到系统被 OOM 杀死。若 RSS 持续接近 WSL 内存上限：

1. 停止 runner，再停止 Python 子进程。
2. 缩短 warm-up / measurement，仅作 smoke test。
3. 正式实验使用更多内存的服务器。
4. 短测试完成请求过少时，不把数字用于论文对比。
