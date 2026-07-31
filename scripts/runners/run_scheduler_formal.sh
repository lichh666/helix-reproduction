#!/usr/bin/env bash
set -uo pipefail

HELIX_ROOT="${HELIX_ROOT:-$HOME/llm-serving-repro/helix}"
if [[ ! -d "$HELIX_ROOT/examples/simulation" ]]; then
    echo "Helix repository not found: $HELIX_ROOT" >&2
    echo "Set HELIX_ROOT to your Helix checkout." >&2
    exit 1
fi
cd "$HELIX_ROOT/examples/simulation"
export PYTHONPATH="$HELIX_ROOT"
python_bin="$HELIX_ROOT/.venv/bin/python"
result_root=scheduler_comparison_results

mkdir -p "$result_root/single" "$result_root/distributed"
: > "$result_root/progress.log"
date -Iseconds > "$result_root/started_at.txt"

for scheduler in maxflow swarm random; do
    echo "START topology=single scheduler=$scheduler $(date -Iseconds)" | tee -a "$result_root/progress.log"
    "$python_bin" step6_scheduler_comparison.py single "$scheduler" 300 60 > "$result_root/single/$scheduler.log" 2>&1
    status=$?
    echo "$status" > "$result_root/single/$scheduler.status"
    echo "END topology=single scheduler=$scheduler status=$status $(date -Iseconds)" | tee -a "$result_root/progress.log"
done

for scheduler in maxflow swarm random shortest_queue; do
    echo "START topology=distributed scheduler=$scheduler $(date -Iseconds)" | tee -a "$result_root/progress.log"
    "$python_bin" step6_scheduler_comparison.py distributed "$scheduler" 600 60 > "$result_root/distributed/$scheduler.log" 2>&1
    status=$?
    echo "$status" > "$result_root/distributed/$scheduler.status"
    echo "END topology=distributed scheduler=$scheduler status=$status $(date -Iseconds)" | tee -a "$result_root/progress.log"
done

date -Iseconds > "$result_root/finished_at.txt"
