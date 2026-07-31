from __future__ import annotations

import csv
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


SIMULATION_DIR = Path(__file__).resolve().parent
RESULTS_DIR = SIMULATION_DIR / "quick_results"
SCHEDULERS = ("maxflow", "swarm", "random")

PATTERNS = {
    "decode_speed": re.compile(r"Avg decode speed: ([0-9.]+) tokens/s"),
    "prompt_latency": re.compile(r"Avg prompt latency: ([0-9.]+)s"),
    "decode_latency": re.compile(r"Avg decode latency: ([0-9.]+)s"),
}


def read_metrics(scheduler: str) -> dict[str, float]:
    text = (RESULTS_DIR / f"{scheduler}.log").read_text(encoding="utf-8")
    metrics: dict[str, float] = {}
    for name, pattern in PATTERNS.items():
        match = pattern.search(text)
        if match is None:
            raise RuntimeError(f"Missing {name} in {scheduler}.log")
        metrics[name] = float(match.group(1))
    return metrics


metrics = {scheduler: read_metrics(scheduler) for scheduler in SCHEDULERS}

with (RESULTS_DIR / "summary.csv").open("w", newline="", encoding="utf-8") as output:
    writer = csv.writer(output)
    writer.writerow(["scheduler", "decode_speed_tokens_s", "prompt_latency_s", "decode_latency_s"])
    for scheduler in SCHEDULERS:
        row = metrics[scheduler]
        writer.writerow(
            [scheduler, row["decode_speed"], row["prompt_latency"], row["decode_latency"]]
        )

maxflow = metrics["maxflow"]
summary_lines = [
    "# Helix quick offline comparison",
    "",
    "Configuration: 5 s warm-up and 30 s measurement window, using the repository's precomputed ILP placement.",
    "",
    "| Scheduler | Decode speed (tokens/s) | Prompt latency (s) | Decode latency (s) |",
    "|---|---:|---:|---:|",
]
for scheduler in SCHEDULERS:
    row = metrics[scheduler]
    summary_lines.append(
        f'| {scheduler} | {row["decode_speed"]:.1f} | {row["prompt_latency"]:.3f} | {row["decode_latency"]:.3f} |'
    )

summary_lines.extend(["", "## Relative latency reduction from MaxFlow", ""])
for baseline in ("swarm", "random"):
    row = metrics[baseline]
    prompt_reduction = 100 * (row["prompt_latency"] - maxflow["prompt_latency"]) / row["prompt_latency"]
    decode_reduction = 100 * (row["decode_latency"] - maxflow["decode_latency"]) / row["decode_latency"]
    summary_lines.append(
        f"- Versus {baseline}: prompt latency -{prompt_reduction:.1f}%, decode latency -{decode_reduction:.1f}%."
    )

summary_lines.extend(
    [
        "",
        "This is a smoke test, not a paper-scale reproduction. The shortened horizon makes the scheduler's final total-throughput/theoretical-optimal lines unsuitable for efficiency calculations; compare the metrics from the common 25-55 s analysis window instead.",
    ]
)
(RESULTS_DIR / "summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

labels = [scheduler.capitalize() for scheduler in SCHEDULERS]
colors = ["#2ca02c", "#1f77b4", "#ff7f0e"]
figure, axes = plt.subplots(1, 3, figsize=(12, 4))
plots = (
    ("decode_speed", "Decode speed", "tokens/s", True),
    ("prompt_latency", "Prompt latency", "seconds", False),
    ("decode_latency", "Decode latency", "seconds", False),
)
for axis, (metric, title, ylabel, higher_is_better) in zip(axes, plots):
    values = [metrics[scheduler][metric] for scheduler in SCHEDULERS]
    bars = axis.bar(labels, values, color=colors)
    axis.set_title(title)
    axis.set_ylabel(ylabel)
    axis.grid(axis="y", alpha=0.25)
    axis.set_ylim(0, max(values) * 1.2)
    for bar, value in zip(bars, values):
        axis.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.3g}", ha="center", va="bottom")
    direction = "higher is better" if higher_is_better else "lower is better"
    axis.set_xlabel(direction)

figure.suptitle("Helix quick offline scheduler comparison")
figure.tight_layout()
figure.savefig(RESULTS_DIR / "scheduler_comparison.png", dpi=180, bbox_inches="tight")
