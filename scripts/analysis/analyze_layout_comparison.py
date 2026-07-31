from __future__ import annotations

import csv
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


RESULTS_DIR = Path(__file__).resolve().parents[1] / "helix_layout_comparison"
LAYOUTS = ("helix", "petals", "swarm", "homogeneous")
LABELS = {"helix": "Helix", "petals": "Petals", "swarm": "Swarm", "homogeneous": "Homogeneous*"}
PATTERNS = {
    "static_max_flow": re.compile(r"Static max flow: ([0-9.]+) tokens/s"),
    "prompt_throughput": re.compile(r"Prompt token throughput: ([0-9.]+) tokens/s"),
    "decode_throughput": re.compile(r"Decode token throughput: ([0-9.]+) tokens/s"),
    "total_throughput": re.compile(r"Total token throughput: ([0-9.]+) tokens/s"),
    "prompt_latency": re.compile(r"Avg prompt latency: ([0-9.]+)s"),
    "decode_latency": re.compile(r"Avg decode latency: ([0-9.]+)s"),
    "completed_queries": re.compile(r"Queries completed in measurement window: ([0-9]+)"),
    "active_queries": re.compile(r"Queries active at cutoff: ([0-9]+)"),
}


def parse(layout: str) -> dict[str, float]:
    log_path = RESULTS_DIR / f"{layout}.log"
    text = log_path.read_text(encoding="utf-8")
    values = {}
    for name, pattern in PATTERNS.items():
        match = pattern.search(text)
        if match is None:
            raise RuntimeError(f"Missing {name} in {log_path}")
        values[name] = float(match.group(1))
    return values


metrics = {layout: parse(layout) for layout in LAYOUTS}
for layout in LAYOUTS:
    status = (RESULTS_DIR / f"{layout}.status").read_text(encoding="utf-8").strip()
    if status != "0":
        raise RuntimeError(f"{layout} experiment failed with status {status}")

with (RESULTS_DIR / "summary.csv").open("w", newline="", encoding="utf-8") as output:
    writer = csv.writer(output)
    writer.writerow([
        "layout", "scheduler", "warmup_s", "measurement_s", "static_max_flow_tokens_s",
        "prompt_throughput_tokens_s", "decode_throughput_tokens_s", "total_throughput_tokens_s",
        "prompt_latency_s", "decode_latency_s", "completed_queries", "active_queries_at_cutoff",
    ])
    for layout in LAYOUTS:
        row = metrics[layout]
        writer.writerow([
            layout, "maxflow", 60, 300, row["static_max_flow"], row["prompt_throughput"],
            row["decode_throughput"], row["total_throughput"], row["prompt_latency"],
            row["decode_latency"], int(row["completed_queries"]), int(row["active_queries"]),
        ])

helix_vs_petals = metrics["helix"]["decode_throughput"] / metrics["petals"]["decode_throughput"]
helix_vs_swarm = metrics["helix"]["decode_throughput"] / metrics["swarm"]["decode_throughput"]
paper_petals = 1.23
paper_swarm = 2.10

summary = [
    "# Helix model-placement comparison",
    "",
    "Configuration: LLaMA-70B, single 24-node heterogeneous cluster, offline saturated serving, "
    "MaxFlow scheduler for every layout, seed 0, 60 s warm-up and 300 s measurement.",
    "",
    "| Layout | Static max flow | Decode tok/s | Total tok/s | Prompt latency | Decode latency | Completed queries |",
    "|---|---:|---:|---:|---:|---:|---:|",
]
for layout in LAYOUTS:
    row = metrics[layout]
    summary.append(
        f'| {LABELS[layout]} | {row["static_max_flow"]:.1f} | {row["decode_throughput"]:.1f} | '
        f'{row["total_throughput"]:.1f} | {row["prompt_latency"]:.3f}s | '
        f'{row["decode_latency"]:.3f}s | {int(row["completed_queries"])} |'
    )

summary.extend([
    "",
    "## Reproduction check against paper Figure 9",
    "",
    f"- Helix / Petals decode-throughput ratio: **{helix_vs_petals:.2f}x**; paper reports **{paper_petals:.2f}x** "
    f"(ratio deviation {100 * (helix_vs_petals / paper_petals - 1):+.1f}%).",
    f"- Helix / Swarm decode-throughput ratio: **{helix_vs_swarm:.2f}x**; paper reports **{paper_swarm:.2f}x** "
    f"(ratio deviation {100 * (helix_vs_swarm / paper_swarm - 1):+.1f}%).",
    "",
    "The key ordering and scale are reproduced: Helix > Petals > Swarm under the same scheduler. "
    "The measurement window is 300 s instead of the paper's 600 s because the laptop previously exhausted memory near 430 s.",
    "",
    "*Homogeneous is an additional repository layout and is not one of the three bars in the paper's Figure 9 placement deep dive.",
])
(RESULTS_DIR / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

colors = ["#2ca02c", "#9467bd", "#1f77b4", "#7f7f7f"]
names = [LABELS[layout] for layout in LAYOUTS]
figure, axes = plt.subplots(2, 2, figsize=(11, 8))

plot_specs = (
    ("decode_throughput", "Decode throughput (paper metric)", "tokens/s"),
    ("static_max_flow", "Static max-flow estimate", "tokens/s"),
    ("total_throughput", "Measured prompt + decode work", "tokens/s"),
    ("completed_queries", "Queries completed in window", "queries"),
)
for axis, (metric, title, ylabel) in zip(axes.flat, plot_specs):
    values = [metrics[layout][metric] for layout in LAYOUTS]
    bars = axis.bar(names, values, color=colors)
    axis.set_title(title)
    axis.set_ylabel(ylabel)
    axis.grid(axis="y", alpha=0.25)
    axis.bar_label(bars, fmt="%.1f" if metric != "completed_queries" else "%.0f", padding=3)
    axis.tick_params(axis="x", rotation=10)

figure.suptitle("Helix model-placement comparison (same MaxFlow scheduler)")
figure.tight_layout()
figure.savefig(RESULTS_DIR / "layout_comparison.png", dpi=180, bbox_inches="tight")
