from __future__ import annotations

import csv
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


SIMULATION_DIR = Path(__file__).resolve().parent
RESULTS_DIR = SIMULATION_DIR / "medium_results"
SCHEDULERS = ("maxflow", "swarm", "random")
PATTERNS = {
    "decode_speed": re.compile(r"Avg decode speed: ([0-9.]+) tokens/s"),
    "prompt_latency": re.compile(r"Avg prompt latency: ([0-9.]+)s"),
    "decode_latency": re.compile(r"Avg decode latency: ([0-9.]+)s"),
}


def read_metrics(scheduler: str) -> dict[str, float]:
    text = (RESULTS_DIR / f"{scheduler}.log").read_text(encoding="utf-8")
    values: dict[str, float] = {}
    for name, pattern in PATTERNS.items():
        match = pattern.search(text)
        if match is None:
            raise RuntimeError(f"Missing {name} in {scheduler}.log")
        values[name] = float(match.group(1))
    return values


metrics = {scheduler: read_metrics(scheduler) for scheduler in SCHEDULERS}

with (RESULTS_DIR / "summary.csv").open("w", newline="", encoding="utf-8") as output:
    writer = csv.writer(output)
    writer.writerow(["scheduler", "decode_speed_tokens_s", "prompt_latency_s", "decode_latency_s"])
    for scheduler in SCHEDULERS:
        row = metrics[scheduler]
        writer.writerow([scheduler, row["decode_speed"], row["prompt_latency"], row["decode_latency"]])

summary = [
    "# Helix medium offline comparison",
    "",
    "Configuration: 60 s warm-up and 300 s measurement window, using the repository's precomputed ILP placement.",
    "",
    "| Scheduler | Decode speed (tokens/s) | Prompt latency (s) | Decode latency (s) |",
    "|---|---:|---:|---:|",
]
for scheduler in SCHEDULERS:
    row = metrics[scheduler]
    summary.append(
        f'| {scheduler} | {row["decode_speed"]:.1f} | {row["prompt_latency"]:.3f} | {row["decode_latency"]:.3f} |'
    )

maxflow = metrics["maxflow"]
summary.extend(["", "## MaxFlow relative to baselines", ""])
for baseline in ("swarm", "random"):
    row = metrics[baseline]
    speed_gain = 100 * (maxflow["decode_speed"] - row["decode_speed"]) / row["decode_speed"]
    prompt_change = 100 * (maxflow["prompt_latency"] - row["prompt_latency"]) / row["prompt_latency"]
    decode_change = 100 * (maxflow["decode_latency"] - row["decode_latency"]) / row["decode_latency"]
    summary.append(
        f"- Versus {baseline}: decode speed +{speed_gain:.1f}%, prompt latency +{prompt_change:.1f}%, decode latency +{decode_change:.1f}%."
    )

summary.extend(
    [
        "",
        "Interpretation: under this sustained offline load, MaxFlow achieves higher decode throughput while accepting higher average latency. This is a throughput-latency trade-off, not an across-the-board improvement.",
        "",
        "The official example initializes MaxFlow and heuristic schedulers with different initial query counts. Treat this as a reproduction of the repository's example settings; a strictly controlled scheduler comparison should align the offered load in a follow-up experiment.",
        "",
        "The original 600 s measurement run exceeded the current WSL memory limit and was killed near simulation time 430 s. This 300 s measurement run completed successfully.",
    ]
)
(RESULTS_DIR / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

labels = [scheduler.capitalize() for scheduler in SCHEDULERS]
colors = ["#2ca02c", "#1f77b4", "#ff7f0e"]
figure, axes = plt.subplots(1, 3, figsize=(12, 4))
plots = (
    ("decode_speed", "Decode speed", "tokens/s", "higher is better"),
    ("prompt_latency", "Prompt latency", "seconds", "lower is better"),
    ("decode_latency", "Decode latency", "seconds", "lower is better"),
)
for axis, (metric, title, ylabel, direction) in zip(axes, plots):
    values = [metrics[scheduler][metric] for scheduler in SCHEDULERS]
    bars = axis.bar(labels, values, color=colors)
    axis.set_title(title)
    axis.set_ylabel(ylabel)
    axis.set_xlabel(direction)
    axis.grid(axis="y", alpha=0.25)
    axis.set_ylim(0, max(values) * 1.2)
    for bar, value in zip(bars, values):
        axis.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.3g}", ha="center", va="bottom")

figure.suptitle("Helix medium offline scheduler comparison")
figure.tight_layout()
figure.savefig(RESULTS_DIR / "scheduler_comparison.png", dpi=180, bbox_inches="tight")
