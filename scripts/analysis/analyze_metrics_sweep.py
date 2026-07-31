from __future__ import annotations

import csv
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


RESULTS_DIR = Path(__file__).resolve().parents[1] / "helix_metrics_sweep"
LOADS = (700, 1000)
SCHEDULERS = ("maxflow", "swarm", "random")
PATTERNS = {
    "prompt_latency": re.compile(r"Avg prompt latency: ([0-9.]+)s"),
    "decode_latency": re.compile(r"Avg decode latency: ([0-9.]+)s"),
    "prompt_throughput": re.compile(r"Prompt token throughput: ([0-9.]+) tokens/s"),
    "decode_throughput": re.compile(r"Decode token throughput: ([0-9.]+) tokens/s"),
    "total_throughput": re.compile(r"Total token throughput: ([0-9.]+) tokens/s"),
    "offered_throughput": re.compile(r"Offered token throughput: ([0-9.]+) tokens/s"),
    "service_ratio": re.compile(r"Token service ratio: ([0-9.]+)%"),
    "issued_queries": re.compile(r"Queries issued: ([0-9]+)"),
    "completed_queries": re.compile(r"Queries completed: ([0-9]+)"),
    "active_queries": re.compile(r"Queries still active: ([0-9]+)"),
    "completion_rate": re.compile(r"End-of-run query completion rate: ([0-9.]+)%"),
    "query_throughput": re.compile(r"Query completion throughput: ([0-9.]+) queries/s"),
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

csv_fields = [
    "offered_load_tokens_s", "scheduler", "prompt_token_throughput", "decode_token_throughput",
    "total_token_throughput", "measured_offered_token_throughput", "token_service_ratio_percent",
    "prompt_latency_s", "decode_latency_s", "queries_issued", "queries_completed",
    "queries_active_at_end", "completion_rate_percent", "query_completion_throughput",
]
with (RESULTS_DIR / "summary.csv").open("w", newline="", encoding="utf-8") as output:
    writer = csv.writer(output)
    writer.writerow(csv_fields)
    for load in LOADS:
        for scheduler in SCHEDULERS:
            row = metrics[load][scheduler]
            writer.writerow([
                load, scheduler, row["prompt_throughput"], row["decode_throughput"],
                row["total_throughput"], row["offered_throughput"], row["service_ratio"],
                row["prompt_latency"], row["decode_latency"], int(row["issued_queries"]),
                int(row["completed_queries"]), int(row["active_queries"]), row["completion_rate"],
                row["query_throughput"],
            ])

summary = [
    "# Helix unified online serving metrics",
    "",
    "Configuration: online arrivals, seed 0, 300 s duration, identical ILP placement and identical offered trace for each scheduler.",
    "",
    "| Load | Scheduler | Prompt tok/s | Decode tok/s | Total tok/s | Service ratio | Completed / Issued | Prompt latency | Decode latency |",
    "|---:|---|---:|---:|---:|---:|---:|---:|---:|",
]
for load in LOADS:
    for scheduler in SCHEDULERS:
        row = metrics[load][scheduler]
        summary.append(
            f'| {load} | {scheduler} | {row["prompt_throughput"]:.1f} | '
            f'{row["decode_throughput"]:.1f} | {row["total_throughput"]:.1f} | '
            f'{row["service_ratio"]:.3f}% | {int(row["completed_queries"])} / '
            f'{int(row["issued_queries"])} | {row["prompt_latency"]:.3f}s | '
            f'{row["decode_latency"]:.3f}s |'
        )

summary.extend(["", "## MaxFlow versus Random", ""])
for load in LOADS:
    maxflow = metrics[load]["maxflow"]
    random = metrics[load]["random"]
    total_change = 100 * (maxflow["total_throughput"] - random["total_throughput"]) / random["total_throughput"]
    service_change = maxflow["service_ratio"] - random["service_ratio"]
    completed_change = int(maxflow["completed_queries"] - random["completed_queries"])
    prompt_latency_change = 100 * (maxflow["prompt_latency"] - random["prompt_latency"]) / random["prompt_latency"]
    decode_latency_change = 100 * (maxflow["decode_latency"] - random["decode_latency"]) / random["decode_latency"]
    summary.append(
        f"- Load {load}: total throughput {total_change:+.2f}%, service ratio {service_change:+.3f} percentage points, "
        f"completed queries {completed_change:+d}, prompt latency {prompt_latency_change:+.2f}%, "
        f"decode latency {decode_latency_change:+.2f}%."
    )

summary.extend([
    "",
    "## Interpretation",
    "",
    "- Prompt throughput is identical across schedulers at each load, confirming that all methods receive and finish the same prompt work in this 300 s window.",
    "- Once prompt and decode work are combined, scheduler throughput differences are much smaller than the decode-only comparison suggests.",
    "- The end-of-run completion rate is a finite-window backlog indicator, not a request success rate: active queries are unfinished at the cutoff, not failed.",
    "- These runs compare schedulers under one fixed ILP placement. They do not reproduce the paper's placement comparison, topology sweep, model sweep, or real multi-GPU deployment.",
])
(RESULTS_DIR / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

colors = {"maxflow": "#2ca02c", "swarm": "#1f77b4", "random": "#ff7f0e"}
figure, axes = plt.subplots(2, 2, figsize=(11, 8))
plots = (
    ("total_throughput", "Total token throughput", "tokens/s", 1.0),
    ("service_ratio", "Token service ratio", "% of offered work", 1.0),
    ("completed_queries", "Queries completed by cutoff", "queries", 1.0),
    ("decode_latency", "Average decode latency", "seconds", 1.0),
)
for axis, (metric, title, ylabel, scale) in zip(axes.flat, plots):
    for scheduler in SCHEDULERS:
        values = [metrics[load][scheduler][metric] * scale for load in LOADS]
        axis.plot(LOADS, values, marker="o", linewidth=2, label=scheduler.capitalize(), color=colors[scheduler])
    axis.set_title(title)
    axis.set_xlabel("configured offered load (tokens/s)")
    axis.set_ylabel(ylabel)
    axis.set_xticks(LOADS)
    axis.grid(alpha=0.3)
axes[0, 0].legend()
figure.suptitle("Helix unified online metrics (300 s, seed 0)")
figure.tight_layout()
figure.savefig(RESULTS_DIR / "metrics_comparison.png", dpi=180, bbox_inches="tight")
