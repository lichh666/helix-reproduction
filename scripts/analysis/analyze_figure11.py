from __future__ import annotations

import csv
import os
import re
from pathlib import Path

import matplotlib.pyplot as plt


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
OUTPUT_DIR = REPO_ROOT / "results/figure11"
HELIX_ROOT = Path(os.environ.get("HELIX_ROOT", REPO_ROOT / "third_party/helix"))
TRACE_ROOT = HELIX_ROOT / "artifact_evaluation"


def parse_simulation_log(path: Path) -> dict[str, float]:
    text = path.read_text(encoding="utf-8", errors="replace")
    fields = {
        "decode": r"Decode token throughput:\s*([0-9.]+)",
        "prompt": r"Prompt token throughput:\s*([0-9.]+)",
        "total": r"Total token throughput:\s*([0-9.]+)",
        "completed": r"Queries completed in measurement window:\s*([0-9.]+)",
        "active": r"Queries active at cutoff:\s*([0-9.]+)",
        "duration": r"Measurement duration:\s*([0-9.]+)",
        "warmup": r"Warm-up duration:\s*([0-9.]+)",
    }
    result: dict[str, float] = {}
    for key, pattern in fields.items():
        match = re.search(pattern, text)
        if not match:
            raise ValueError(f"Missing {key!r} in {path}")
        result[key] = float(match.group(1))
    return result


def parse_trace(path: Path) -> dict[str, float]:
    text = path.read_text(encoding="utf-8", errors="replace")
    size = re.search(
        r"Optimize a model with\s+(\d+) rows,\s+(\d+) columns and\s+(\d+) nonzeros",
        text,
    )
    best = re.search(r"Best objective\s+([0-9.eE+-]+)", text)
    if not size or not best:
        raise ValueError(f"Could not parse trace header/tail: {path}")

    target = float(best.group(1))
    first_best_seconds: float | None = None
    for line in text.splitlines():
        stripped = line.lstrip()
        if not stripped.startswith("H"):
            continue
        seconds = re.search(r"([0-9.]+)s\s*$", stripped)
        if not seconds:
            continue
        values = [float(value) for value in re.findall(r"\d+(?:\.\d+)?", stripped)]
        if any(abs(value - target) <= max(1e-3, abs(target) * 1e-7) for value in values):
            first_best_seconds = float(seconds.group(1))
            break

    if first_best_seconds is None:
        raise ValueError(f"Could not find first final-best incumbent: {path}")

    return {
        "constraints": float(size.group(1)),
        "variables": float(size.group(2)),
        "nonzeros": float(size.group(3)),
        "best_objective": target,
        "first_best_seconds": first_best_seconds,
    }


def pct_gain(new: float, old: float) -> float:
    return (new / old - 1.0) * 100.0


def pct_less(fast: float, slow: float) -> float:
    return (1.0 - fast / slow) * 100.0


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


local_24 = {
    "pruned": parse_simulation_log(OUTPUT_DIR / "24_pruned_local.log"),
    "unpruned": parse_simulation_log(OUTPUT_DIR / "24_unpruned_local.log"),
}
local_42_short = {
    "pruned": parse_simulation_log(OUTPUT_DIR / "42_pruned_short.log"),
    "unpruned": parse_simulation_log(OUTPUT_DIR / "42_unpruned_short.log"),
}

# 42-node, 660-second simulation values published in artifact_evaluation/ae_readme.md.
# The local 8 GiB WSL instance cannot retain all events for this run without OOM.
throughput = {
    24: {"pruned": local_24["pruned"]["decode"], "unpruned": local_24["unpruned"]["decode"]},
    42: {"pruned": 645.6, "unpruned": 574.2383333333333},
}
paper_throughput_gain = {24: 16.0, 42: 2.0}

trace_paths = {
    (24, "unpruned"): TRACE_ROOT / "ablation/layouts/no_prune_24/trace.txt",
    (42, "unpruned"): TRACE_ROOT / "ablation/layouts/no_prune_42/trace.txt",
    (24, "raw"): TRACE_ROOT / "ablation/layouts/raw_24/trace.txt",
    (42, "raw"): TRACE_ROOT / "ablation/layouts/raw_42/trace.txt",
    (24, "heuristic"): TRACE_ROOT / "distributed_clusters/layout_llama70b/ilp/trace.txt",
    (42, "heuristic"): TRACE_ROOT / "high_heterogeneity/layout_llama70b/ilp/trace.txt",
}
traces = {key: parse_trace(path) for key, path in trace_paths.items()}

problem_rows: list[dict[str, object]] = []
for nodes in (24, 42):
    pruned = traces[(nodes, "heuristic")]
    unpruned = traces[(nodes, "unpruned")]
    problem_rows.append(
        {
            "nodes": nodes,
            "pruned_variables": int(pruned["variables"]),
            "unpruned_variables": int(unpruned["variables"]),
            "variable_reduction_pct": round(pct_less(pruned["variables"], unpruned["variables"]), 2),
            "pruned_constraints": int(pruned["constraints"]),
            "unpruned_constraints": int(unpruned["constraints"]),
            "constraint_reduction_pct": round(pct_less(pruned["constraints"], unpruned["constraints"]), 2),
            "pruned_nonzeros": int(pruned["nonzeros"]),
            "unpruned_nonzeros": int(unpruned["nonzeros"]),
            "nonzero_reduction_pct": round(pct_less(pruned["nonzeros"], unpruned["nonzeros"]), 2),
        }
    )
write_csv(OUTPUT_DIR / "table8_problem_size.csv", problem_rows)

throughput_rows: list[dict[str, object]] = []
for nodes in (24, 42):
    values = throughput[nodes]
    throughput_rows.append(
        {
            "nodes": nodes,
            "pruned_decode_tokens_s": round(values["pruned"], 3),
            "unpruned_decode_tokens_s": round(values["unpruned"], 3),
            "artifact_gain_pct": round(pct_gain(values["pruned"], values["unpruned"]), 2),
            "paper_gain_pct": paper_throughput_gain[nodes],
            "source": "local official-parameter run" if nodes == 24 else "artifact README precomputed long run",
        }
    )
write_csv(OUTPUT_DIR / "figure11a_throughput.csv", throughput_rows)

paper_time_reduction = {24: 43.0, 42: 8.0}
time_rows: list[dict[str, object]] = []
for nodes in (24, 42):
    raw = traces[(nodes, "raw")]["first_best_seconds"]
    heuristic = traces[(nodes, "heuristic")]["first_best_seconds"]
    time_rows.append(
        {
            "nodes": nodes,
            "raw_first_best_seconds": int(raw),
            "heuristic_first_best_seconds": int(heuristic),
            "trace_time_reduction_pct": round(pct_less(heuristic, raw), 2),
            "paper_time_reduction_pct": paper_time_reduction[nodes],
        }
    )
write_csv(OUTPUT_DIR / "figure11b_initial_values.csv", time_rows)

short_rows: list[dict[str, object]] = []
for pruning in ("pruned", "unpruned"):
    values = local_42_short[pruning]
    short_rows.append(
        {
            "pruning": pruning,
            "warmup_seconds": values["warmup"],
            "measurement_seconds": values["duration"],
            "decode_tokens_s": values["decode"],
            "completed_queries": int(values["completed"]),
            "active_queries": int(values["active"]),
            "usable_for_paper_comparison": False,
        }
    )
write_csv(OUTPUT_DIR / "42_node_short_run_diagnostic.csv", short_rows)

fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8))
x = [0, 1]
width = 0.34
pruned_values = [throughput[n]["pruned"] for n in (24, 42)]
unpruned_values = [throughput[n]["unpruned"] for n in (24, 42)]
axes[0].bar([v - width / 2 for v in x], pruned_values, width, label="With pruning", color="#3274a1")
axes[0].bar([v + width / 2 for v in x], unpruned_values, width, label="Without pruning", color="#e1812c")
axes[0].set_xticks(x, ["24 nodes", "42 nodes"])
axes[0].set_ylabel("Decode throughput (tokens/s)")
axes[0].set_title("Figure 11(a): Artifact placements")
axes[0].legend(frameon=False)
for i, nodes in enumerate((24, 42)):
    gain = pct_gain(throughput[nodes]["pruned"], throughput[nodes]["unpruned"])
    axes[0].text(i, max(pruned_values[i], unpruned_values[i]) * 1.03, f"+{gain:.1f}%", ha="center")

raw_values = [traces[(n, "raw")]["first_best_seconds"] / 60 for n in (24, 42)]
heuristic_values = [traces[(n, "heuristic")]["first_best_seconds"] / 60 for n in (24, 42)]
axes[1].bar([v - width / 2 for v in x], raw_values, width, label="Raw", color="#c44e52")
axes[1].bar([v + width / 2 for v in x], heuristic_values, width, label="Heuristic start", color="#55a868")
axes[1].set_xticks(x, ["24 nodes", "42 nodes"])
axes[1].set_ylabel("Time to final-best incumbent (minutes)")
axes[1].set_title("Figure 11(b): Bundled Gurobi traces")
axes[1].legend(frameon=False)
for i, nodes in enumerate((24, 42)):
    reduction = pct_less(heuristic_values[i], raw_values[i])
    axes[1].text(i, max(raw_values[i], heuristic_values[i]) * 1.03, f"-{reduction:.1f}%", ha="center")

for axis in axes:
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.grid(axis="y", alpha=0.2)
fig.tight_layout()
fig.savefig(OUTPUT_DIR / "figure11_reproduction.png", dpi=180, bbox_inches="tight")
plt.close(fig)

p24_gain = pct_gain(throughput[24]["pruned"], throughput[24]["unpruned"])
p42_gain = pct_gain(throughput[42]["pruned"], throughput[42]["unpruned"])
t24_gain = pct_less(traces[(24, "heuristic")]["first_best_seconds"], traces[(24, "raw")]["first_best_seconds"])
t42_gain = pct_less(traces[(42, "heuristic")]["first_best_seconds"], traces[(42, "raw")]["first_best_seconds"])

summary = f"""# Helix Figure 11 / Table 8 复现汇总

## 结论

- Table 8 的变量规模完全复现：24 节点从 1376 降至 876（-{problem_rows[0]['variable_reduction_pct']:.2f}%），42 节点从 4004 降至 2144（-{problem_rows[1]['variable_reduction_pct']:.2f}%），与论文的 36% / 46% 一致。
- Figure 11(a) 的方向复现：仓库当前 artifact 布局中，剪枝后的解码吞吐量更高。
- Figure 11(b) 的方向只在 24 节点 trace 中明显复现；42 节点仓库 trace 的差异远小于论文报告值。
- 本机 Gurobi 许可证已过期，因此没有重新求解 MILP；本部分使用仓库自带的官方 trace。

## Figure 11(a)：Cluster pruning

| 节点数 | 剪枝后 (token/s) | 未剪枝 (token/s) | 当前 artifact 提升 | 论文提升 | 数据来源 |
|---:|---:|---:|---:|---:|---|
| 24 | {throughput[24]['pruned']:.1f} | {throughput[24]['unpruned']:.3f} | {p24_gain:.1f}% | 16% | 本机按官方参数完整实跑 |
| 42 | {throughput[42]['pruned']:.1f} | {throughput[42]['unpruned']:.3f} | {p42_gain:.1f}% | 2% | artifact README 的完整长跑结果 |

24 节点本机日志的 98.0 / 74.9 与 artifact README 的 98.0 / 74.923 按日志显示精度一致。当前 artifact 布局相对论文成稿时的布局有差异，所以提升比例不是论文图中的 16%；论文也明确说明加速幅度随具体 MILP 实例变化。

42 节点官方设置需要 60 秒预热 + 600 秒测量。8 GiB WSL 在运行时占满内存并开始使用 swap，因此为避免系统 OOM 已安全停止。随后完成的 15+30 秒短跑只有 3 / 2 个请求完整结束，只能验证代码能运行，不能作为论文吞吐量结论；其原始数据保存在 `42_node_short_run_diagnostic.csv`。

## Table 8：MILP 问题规模

| 节点数 | 剪枝后变量 | 未剪枝变量 | 变量减少 | 剪枝后约束 | 未剪枝约束 | 约束减少 |
|---:|---:|---:|---:|---:|---:|---:|
| 24 | {problem_rows[0]['pruned_variables']} | {problem_rows[0]['unpruned_variables']} | {problem_rows[0]['variable_reduction_pct']:.2f}% | {problem_rows[0]['pruned_constraints']} | {problem_rows[0]['unpruned_constraints']} | {problem_rows[0]['constraint_reduction_pct']:.2f}% |
| 42 | {problem_rows[1]['pruned_variables']} | {problem_rows[1]['unpruned_variables']} | {problem_rows[1]['variable_reduction_pct']:.2f}% | {problem_rows[1]['pruned_constraints']} | {problem_rows[1]['unpruned_constraints']} | {problem_rows[1]['constraint_reduction_pct']:.2f}% |

## Figure 11(b)：Initial values

这里把“达到该 trace 最终最佳 incumbent 的首次时间”作为统一口径。

| 节点数 | Raw | Heuristic 初值 | trace 中耗时减少 | 论文报告 |
|---:|---:|---:|---:|---:|
| 24 | {traces[(24, 'raw')]['first_best_seconds']:.0f}s | {traces[(24, 'heuristic')]['first_best_seconds']:.0f}s | {t24_gain:.1f}% | 43% |
| 42 | {traces[(42, 'raw')]['first_best_seconds']:.0f}s | {traces[(42, 'heuristic')]['first_best_seconds']:.0f}s | {t42_gain:.1f}% | 8% |

24 节点与论文趋势和数量级一致。42 节点随仓库附带 trace 计算只有约 {t42_gain:.1f}% 差异，未复现论文的 8%；论文和 artifact 文档均提示该时间高度依赖硬件、Gurobi 许可证与具体求解实例。

## 可复查文件

- `figure11_reproduction.png`：吞吐量和求解时间汇总图
- `figure11a_throughput.csv`：剪枝吞吐量
- `figure11b_initial_values.csv`：初值消融 trace 结果
- `table8_problem_size.csv`：MILP 规模
- `24_pruned_local.log` / `24_unpruned_local.log`：本机正式仿真原始日志
- `42_node_short_run_diagnostic.csv`：42 节点短跑诊断（不纳入论文对比）
- `analyze_figure11.py`：可重复运行的分析脚本
"""
(OUTPUT_DIR / "summary.md").write_text(summary, encoding="utf-8")

print(summary)
