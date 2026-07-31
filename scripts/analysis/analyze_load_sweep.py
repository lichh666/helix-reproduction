from __future__ import annotations

import csv
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


SIMULATION_DIR = Path(__file__).resolve().parent
RESULTS_DIR = SIMULATION_DIR / "load_sweep_results"
LOADS = (400, 700, 1000)
SCHEDULERS = ("maxflow", "swarm", "random")
PATTERNS = {
    "decode_speed": re.compile(r"Avg decode speed: ([0-9.]+) tokens/s"),
    "prompt_latency": re.compile(r"Avg prompt latency: ([0-9.]+)s"),
    "decode_latency": re.compile(r"Avg decode latency: ([0-9.]+)s"),
}


def read_metrics(load: int, scheduler: str) -> dict[str, float]:
    log_path = RESULTS_DIR / f"load_{load}" / f"{scheduler}.log"
    text = log_path.read_text(encoding="utf-8")
    values: dict[str, float] = {}
    for name, pattern in PATTERNS.items():
        match = pattern.search(text)
        if match is None:
            raise RuntimeError(f"Missing {name} in {log_path}")
        values[name] = float(match.group(1))
    return values


metrics = {
    load: {scheduler: read_metrics(load, scheduler) for scheduler in SCHEDULERS}
    for load in LOADS
}

with (RESULTS_DIR / "summary.csv").open("w", newline="", encoding="utf-8") as output:
    writer = csv.writer(output)
    writer.writerow(
        ["offered_load_tokens_s", "scheduler", "decode_speed_tokens_s", "prompt_latency_s", "decode_latency_s"]
    )
    for load in LOADS:
        for scheduler in SCHEDULERS:
            row = metrics[load][scheduler]
            writer.writerow([load, scheduler, row["decode_speed"], row["prompt_latency"], row["decode_latency"]])

summary = [
    "# Helix equal-load online sweep",
    "",
    "Configuration: offered loads of 400, 700, and 1000 tokens/s; seed 0; 300 s duration; identical precomputed ILP placement.",
    "",
    "| Load | Scheduler | Decode speed (tokens/s) | Prompt latency (s) | Decode latency (s) |",
    "|---:|---|---:|---:|---:|",
]
for load in LOADS:
    for scheduler in SCHEDULERS:
        row = metrics[load][scheduler]
        summary.append(
            f'| {load} | {scheduler} | {row["decode_speed"]:.1f} | {row["prompt_latency"]:.3f} | {row["decode_latency"]:.3f} |'
        )

summary.extend(["", "## MaxFlow versus Random at each load", ""])
for load in LOADS:
    maxflow = metrics[load]["maxflow"]
    random = metrics[load]["random"]
    speed_change = 100 * (maxflow["decode_speed"] - random["decode_speed"]) / random["decode_speed"]
    prompt_change = 100 * (maxflow["prompt_latency"] - random["prompt_latency"]) / random["prompt_latency"]
    decode_change = 100 * (maxflow["decode_latency"] - random["decode_latency"]) / random["decode_latency"]
    summary.append(
        f"- {load} tokens/s: decode speed {speed_change:+.1f}%, prompt latency {prompt_change:+.1f}%, decode latency {decode_change:+.1f}%."
    )

summary.extend(
    [
        "",
        "No decode-speed crossover was observed through 1000 tokens/s: Random remained 3.9-5.6% faster in this metric, while MaxFlow generally had slightly lower prompt latency and higher decode latency.",
        "",
        "The discrepancy with the saturated offline example is methodologically important. The repository's offline paths use different initial query counts for MaxFlow and heuristics, so the offline throughput gap cannot be attributed only to the scheduler. Under matched online arrival processes, the three schedulers remain close through this range.",
        "",
        "The logs expose decode-token throughput, not total prompt-plus-decode throughput. Before extending beyond 1000 tokens/s, the next instrumentation step should add a common total-token-throughput metric so the MaxFlow objective is measured directly.",
    ]
)
(RESULTS_DIR / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

colors = {"maxflow": "#2ca02c", "swarm": "#1f77b4", "random": "#ff7f0e"}
figure, axes = plt.subplots(1, 3, figsize=(13, 4))
plots = (
    ("decode_speed", "Decode speed", "tokens/s", "higher is better"),
    ("prompt_latency", "Prompt latency", "seconds", "lower is better"),
    ("decode_latency", "Decode latency", "seconds", "lower is better"),
)
for axis, (metric, title, ylabel, direction) in zip(axes, plots):
    for scheduler in SCHEDULERS:
        values = [metrics[load][scheduler][metric] for load in LOADS]
        axis.plot(LOADS, values, marker="o", linewidth=2, label=scheduler.capitalize(), color=colors[scheduler])
    axis.set_title(title)
    axis.set_xlabel(f"offered load (tokens/s)\n{direction}")
    axis.set_ylabel(ylabel)
    axis.grid(alpha=0.3)
    axis.set_xticks(LOADS)
axes[0].legend()
figure.suptitle("Helix equal-load online sweep")
figure.tight_layout()
figure.savefig(RESULTS_DIR / "load_sweep.png", dpi=180, bbox_inches="tight")
