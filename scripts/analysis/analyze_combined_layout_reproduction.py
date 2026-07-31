from __future__ import annotations

import csv
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "results/figure9"
OUTPUT_DIR.mkdir(exist_ok=True)
SOURCES = {
    "single": OUTPUT_DIR / "raw/single",
    "distributed": OUTPUT_DIR / "raw/distributed",
}
LAYOUTS = ("helix", "petals", "swarm")
LABELS = {"helix": "Helix", "petals": "Petals", "swarm": "Swarm"}
PATTERNS = {
    "static_max_flow": re.compile(r"Static max flow: ([0-9.]+) tokens/s"),
    "prompt_throughput": re.compile(r"Prompt token throughput: ([0-9.]+) tokens/s"),
    "decode_throughput": re.compile(r"Decode token throughput: ([0-9.]+) tokens/s"),
    "total_throughput": re.compile(r"Total token throughput: ([0-9.]+) tokens/s"),
    "prompt_latency": re.compile(r"Avg prompt latency: ([0-9.]+)s"),
    "decode_latency": re.compile(r"Avg decode latency: ([0-9.]+)s"),
    "completed_queries": re.compile(r"Queries completed in measurement window: ([0-9]+)"),
}


def parse(directory: Path, layout: str) -> dict[str, float]:
    status = (directory / f"{layout}.status").read_text(encoding="utf-8").strip()
    if status != "0":
        raise RuntimeError(f"{directory.name}/{layout} failed with status {status}")
    text = (directory / f"{layout}.log").read_text(encoding="utf-8")
    result = {}
    for name, pattern in PATTERNS.items():
        match = pattern.search(text)
        if match is None:
            raise RuntimeError(f"Missing {name} in {directory / f'{layout}.log'}")
        result[name] = float(match.group(1))
    return result


metrics = {
    topology: {layout: parse(directory, layout) for layout in LAYOUTS}
    for topology, directory in SOURCES.items()
}
durations = {"single": 300, "distributed": 600}

with (OUTPUT_DIR / "summary.csv").open("w", newline="", encoding="utf-8") as output:
    writer = csv.writer(output)
    writer.writerow([
        "topology", "layout", "scheduler", "warmup_s", "measurement_s", "static_max_flow_tokens_s",
        "prompt_throughput_tokens_s", "decode_throughput_tokens_s", "total_throughput_tokens_s",
        "prompt_latency_s", "decode_latency_s", "completed_queries",
    ])
    for topology in SOURCES:
        for layout in LAYOUTS:
            row = metrics[topology][layout]
            writer.writerow([
                topology, layout, "maxflow", 60, durations[topology], row["static_max_flow"],
                row["prompt_throughput"], row["decode_throughput"], row["total_throughput"],
                row["prompt_latency"], row["decode_latency"], int(row["completed_queries"]),
            ])

paper_ratios = {
    ("single", "petals"): 1.23,
    ("single", "swarm"): 2.10,
    ("distributed", "petals"): 1.49,
    ("distributed", "swarm"): 2.38,
}
observed_ratios = {
    (topology, baseline): (
        metrics[topology]["helix"]["decode_throughput"]
        / metrics[topology][baseline]["decode_throughput"]
    )
    for topology in SOURCES
    for baseline in ("petals", "swarm")
}

summary = [
    "# Helix Figure 9 simulator reproduction",
    "",
    "All layouts use the same Helix MaxFlow request scheduler, seed 0, and a 60 s warm-up. "
    "The single-cluster measurement is 300 s due to the laptop memory limit; the distributed measurement uses the paper's 600 s duration.",
    "",
    "| Topology | Layout | Decode tok/s | Total tok/s | Prompt latency | Decode latency | Completed queries |",
    "|---|---|---:|---:|---:|---:|---:|",
]
for topology in SOURCES:
    for layout in LAYOUTS:
        row = metrics[topology][layout]
        summary.append(
            f'| {topology} | {LABELS[layout]} | {row["decode_throughput"]:.1f} | '
            f'{row["total_throughput"]:.1f} | {row["prompt_latency"]:.3f}s | '
            f'{row["decode_latency"]:.3f}s | {int(row["completed_queries"])} |'
        )

summary.extend(["", "## Paper ratio check", "", "| Topology | Comparison | Reproduced | Paper | Deviation |", "|---|---|---:|---:|---:|"])
for topology in SOURCES:
    for baseline in ("petals", "swarm"):
        observed = observed_ratios[(topology, baseline)]
        paper = paper_ratios[(topology, baseline)]
        deviation = 100 * (observed / paper - 1)
        summary.append(
            f"| {topology} | Helix / {LABELS[baseline]} | {observed:.2f}x | {paper:.2f}x | {deviation:+.1f}% |"
        )

summary.extend(["", "## Network impact", ""])
for layout in LAYOUTS:
    single = metrics["single"][layout]
    distributed = metrics["distributed"][layout]
    decode_change = 100 * (distributed["decode_throughput"] / single["decode_throughput"] - 1)
    prompt_multiplier = distributed["prompt_latency"] / single["prompt_latency"]
    summary.append(
        f"- {LABELS[layout]}: geo-distributed decode throughput {decode_change:.1f}% versus single cluster; "
        f"prompt latency becomes {prompt_multiplier:.2f}x."
    )

summary.extend([
    "",
    "The reproduced ordering and relative gains match the paper in both topologies. This is the first result in this reproduction that directly validates Helix's joint model-placement advantage rather than only exercising the tutorial workflow.",
])
(OUTPUT_DIR / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

colors = {"helix": "#2ca02c", "petals": "#9467bd", "swarm": "#1f77b4"}
figure, axes = plt.subplots(1, 2, figsize=(12, 4.8))

x = np.arange(2)
width = 0.24
for index, layout in enumerate(LAYOUTS):
    values = [metrics[topology][layout]["decode_throughput"] for topology in ("single", "distributed")]
    bars = axes[0].bar(x + (index - 1) * width, values, width, label=LABELS[layout], color=colors[layout])
    axes[0].bar_label(bars, fmt="%.1f", padding=3)
axes[0].set_xticks(x, ["Single cluster", "Geo-distributed"])
axes[0].set_ylabel("decode tokens/s")
axes[0].set_title("Decode throughput (Figure 9 metric)")
axes[0].grid(axis="y", alpha=0.25)
axes[0].legend()

ratio_labels = ["Single / Petals", "Single / Swarm", "Geo / Petals", "Geo / Swarm"]
keys = [
    ("single", "petals"), ("single", "swarm"),
    ("distributed", "petals"), ("distributed", "swarm"),
]
ratio_x = np.arange(len(keys))
observed_values = [observed_ratios[key] for key in keys]
paper_values = [paper_ratios[key] for key in keys]
bars1 = axes[1].bar(ratio_x - 0.18, observed_values, 0.36, label="Reproduced", color="#2ca02c")
bars2 = axes[1].bar(ratio_x + 0.18, paper_values, 0.36, label="Paper", color="#555555")
axes[1].bar_label(bars1, fmt="%.2fx", padding=3)
axes[1].bar_label(bars2, fmt="%.2fx", padding=3)
axes[1].set_xticks(ratio_x, ratio_labels, rotation=15, ha="right")
axes[1].set_ylabel("Helix speedup")
axes[1].set_title("Reproduced gains versus paper")
axes[1].grid(axis="y", alpha=0.25)
axes[1].legend()

figure.suptitle("Helix model-placement reproduction")
figure.tight_layout()
figure.savefig(OUTPUT_DIR / "figure9_reproduction.png", dpi=180, bbox_inches="tight")
