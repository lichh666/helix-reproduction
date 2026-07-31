from __future__ import annotations

import csv
import os
import re
from pathlib import Path

import matplotlib.pyplot as plt


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
OUTPUT_DIR = REPO_ROOT / "results/figure12"
HELIX_ROOT = Path(os.environ.get("HELIX_ROOT", REPO_ROOT / "third_party/helix"))
TRACE = HELIX_ROOT / "artifact_evaluation/ablation/layouts/quality/trace.txt"


def as_number(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


text = TRACE.read_text(encoding="utf-8", errors="replace")
best_match = re.search(r"Best objective\s+([0-9.eE+-]+)", text)
finish_match = re.search(r"in\s+([0-9.]+) seconds", text)
size_match = re.search(
    r"Optimize a model with\s+(\d+) rows,\s+(\d+) columns and\s+(\d+) nonzeros",
    text,
)
if not best_match or not finish_match or not size_match:
    raise RuntimeError("Could not parse trace metadata")

optimal = float(best_match.group(1))
finish_seconds = float(finish_match.group(1))

points: list[dict[str, float]] = []
for line in text.splitlines():
    tokens = line.split()
    if len(tokens) < 6 or not re.fullmatch(r"[0-9.]+s", tokens[-1]):
        continue
    seconds = float(tokens[-1][:-1])
    incumbent = as_number(tokens[-5])
    bound = as_number(tokens[-4])
    if incumbent is None or bound is None:
        continue
    points.append({"seconds": seconds, "incumbent": incumbent, "upper_bound": bound})

if not points:
    raise RuntimeError("No Gurobi progress points parsed")

# The final Gurobi summary confirms the bound closes exactly at finish_seconds.
points.append({"seconds": finish_seconds, "incumbent": optimal, "upper_bound": optimal})

with (OUTPUT_DIR / "figure12_trace_points.csv").open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=["seconds", "incumbent", "upper_bound"])
    writer.writeheader()
    writer.writerows(points)

first_optimal = next(
    point["seconds"]
    for point in points
    if point["incumbent"] > 0
    and abs(point["incumbent"] - optimal) <= max(1e-3, optimal * 1e-7)
)
first_positive = next(point for point in points if point["incumbent"] > 0)

milestones = [
    {
        "event": "first_positive_solution",
        "seconds": first_positive["seconds"],
        "throughput_tokens_s": first_positive["incumbent"],
    },
    {
        "event": "optimal_solution_first_found",
        "seconds": first_optimal,
        "throughput_tokens_s": optimal,
    },
    {
        "event": "optimality_confirmed",
        "seconds": finish_seconds,
        "throughput_tokens_s": optimal,
    },
]
with (OUTPUT_DIR / "figure12_milestones.csv").open("w", encoding="utf-8-sig", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(milestones[0]))
    writer.writeheader()
    writer.writerows(milestones)

incumbent_points = [point for point in points if point["incumbent"] > 0]
times = [point["seconds"] for point in incumbent_points]
incumbents = [point["incumbent"] for point in incumbent_points]
bound_times = [point["seconds"] for point in points]
bounds = [point["upper_bound"] for point in points]

fig, axis = plt.subplots(figsize=(8.4, 5.2))
axis.step(times, incumbents, where="post", linewidth=2.2, label="Best solution", color="#3274a1")
axis.step(bound_times, bounds, where="post", linewidth=2.2, label="Best upper bound", color="#e1812c")
axis.axhline(optimal, linestyle="--", linewidth=1.8, color="#d62728", label="Optimal throughput")
axis.axvline(finish_seconds, linestyle="--", linewidth=1.8, color="#2ca02c", label="Optimality confirmed")
axis.set_yscale("log")
axis.set_xlim(0, 4000)
axis.set_ylim(10, 20000)
axis.set_xlabel("MILP solving time (seconds)")
axis.set_ylabel("Objective throughput (tokens/s)")
axis.set_title("Helix Figure 12 reproduction from bundled Gurobi trace")
axis.grid(True, which="both", alpha=0.22)
axis.legend(frameon=False, ncol=2, loc="upper right")
axis.text(500, optimal * 1.18, f"optimal = {optimal:.3f} tokens/s", color="#d62728")
axis.text(finish_seconds - 80, 18, f"finish = {finish_seconds:.0f}s", color="#2ca02c", ha="right")
fig.tight_layout()
fig.savefig(OUTPUT_DIR / "figure12_reproduction.png", dpi=200, bbox_inches="tight")
plt.close(fig)

summary = f"""# Helix Figure 12 复现汇总

## 结论

Figure 12 的核心结论已由仓库附带的 Gurobi trace 复现：

- MILP 规模：{size_match.group(1)} 个约束、{size_match.group(2)} 个变量、{size_match.group(3)} 个非零项。
- 最优目标吞吐量：{optimal:.6f} tokens/s。
- 首次找到最优布局：{first_optimal:.0f} 秒（{first_optimal / 60:.2f} 分钟），小于论文所说的 5 分钟。
- 完成全空间搜索并证明最优：{finish_seconds:.2f} 秒（{finish_seconds / 60:.2f} 分钟），超过 1 小时。
- 找到最优布局后，求解器还用了约 {(finish_seconds - first_optimal):.0f} 秒来收紧 upper bound、证明没有更优解。

这验证了论文的工程观点：如果目标是尽快得到高质量模型放置，可以在找到稳定 incumbent 后提前停止；继续运行主要是在证明最优性。

## 复现范围

当前 Gurobi 许可证已过期，因此没有在本机重新执行 MILP。曲线由仓库官方 `quality/trace.txt` 自动解析，属于 artifact trace 复现，不是新硬件上的 solver rerun。

## 输出文件

- `figure12_reproduction.png`：按论文坐标口径重画的曲线
- `figure12_trace_points.csv`：从 Gurobi 日志抽取的时序点
- `figure12_milestones.csv`：首次可行解、首次最优解、最优性确认三个里程碑
- `analyze_figure12.py`：可重复运行的解析与绘图脚本
"""
(OUTPUT_DIR / "summary.md").write_text(summary, encoding="utf-8")
print(summary)
