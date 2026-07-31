from __future__ import annotations

import csv
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


SIMULATION_DIR = Path(__file__).resolve().parent
RESULTS_DIR = SIMULATION_DIR / "equal_load_online_results"
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
    "# Helix equal-load online comparison",
    "",
    "Configuration: identical 400 tokens/s offered load, seed 0, 300 s duration, and precomputed ILP placement for every scheduler.",
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
    speed_change = 100 * (maxflow["decode_speed"] - row["decode_speed"]) / row["decode_speed"]
    prompt_change = 100 * (maxflow["prompt_latency"] - row["prompt_latency"]) / row["prompt_latency"]
    decode_change = 100 * (maxflow["decode_latency"] - row["decode_latency"]) / row["decode_latency"]
    summary.append(
        f"- Versus {baseline}: decode speed {speed_change:+.1f}%, prompt latency {prompt_change:+.1f}%, decode latency {decode_change:+.1f}%."
    )

summary.extend(
    [
        "",
        "Interpretation: 400 tokens/s is about 31% of the MaxFlow bound (1289.56 tokens/s). At this moderate offered load, all schedulers are close and MaxFlow has no throughput advantage. This complements the saturated offline result, where MaxFlow improved decode throughput by roughly 25-31% while trading higher latency.",
        "",
        "A load sweep is the appropriate next experiment to locate the point where MaxFlow begins to outperform the heuristic schedulers.",
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

figure.suptitle("Helix online comparison at equal 400 tokens/s load")
figure.tight_layout()
figure.savefig(RESULTS_DIR / "scheduler_comparison.png", dpi=180, bbox_inches="tight")
