# 逐步复现指南

本指南默认在 Ubuntu 22.04 / WSL2 中执行。

## 1. 准备源码

```bash
git clone https://github.com/Thesys-lab/Helix-ASPLOS25.git "$HOME/llm-serving-repro/helix"
export HELIX_ROOT="$HOME/llm-serving-repro/helix"
cd "$HELIX_ROOT"
git checkout 8639497a4aaf1eb3b7594614cb0bbd376c1342b3
```

## 2. 创建环境

```bash
cd "$HELIX_ROOT"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
export PYTHONPATH="$HELIX_ROOT"
```

验证导入：

```bash
python -c "from simulator.initial_layout.fake_cluster_generator import FakeClusterGenerator; print('import ok')"
```

## 3. 安装本仓库的实验入口

在 `helix-reproduction` 仓库根目录执行：

```bash
cp scripts/simulation/*.py "$HELIX_ROOT/examples/simulation/"
```

## 4. 官方教程

```bash
cd "$HELIX_ROOT"
export PYTHONPATH="$HELIX_ROOT"
cd examples/simulation

python step1_gen_cluster.py
python step2_model_placement.py petals
ls config layouts
```

## 5. Figure 9

```bash
export HELIX_ROOT="$HOME/llm-serving-repro/helix"
bash scripts/runners/run_figure9.sh
```

单集群分别运行 Helix、Petals、Swarm；分布式集群采用相同 MaxFlow scheduler。

## 6. Figure 10

```bash
export HELIX_ROOT="$HOME/llm-serving-repro/helix"
bash scripts/runners/run_figure10.sh
```

固定 Helix 布局，替换 MaxFlow、Swarm、Random 和 Shortest Queue scheduler。

## 7. Figure 11(a) 24 节点

```bash
export HELIX_ROOT="$HOME/llm-serving-repro/helix"
bash scripts/runners/run_figure11_24.sh
```

不建议在 8 GiB WSL 上运行 42 节点 60+600 秒实验。运行前至少准备 16-24 GiB WSL 内存，并用 `free -h` / `ps` 监控。

## 8. Figure 11(b) 和 Figure 12

需要有效 Gurobi Academic License 才能重新求解。没有许可证时，可以解析上游仓库自带 trace：

```bash
export HELIX_ROOT="$HOME/llm-serving-repro/helix"
python scripts/analysis/analyze_figure11.py
python scripts/analysis/analyze_figure12.py
```

分析脚本通过 `HELIX_ROOT` 定位官方 trace，并把结果写入本仓库 `results/figure11` 和 `results/figure12`。

## 9. 长实验防断连

推荐：

```bash
sudo apt-get install tmux
tmux new -s helix
bash scripts/runners/run_figure10.sh 2>&1 | tee figure10-console.log
```

重新连接：

```bash
tmux attach -t helix
```
