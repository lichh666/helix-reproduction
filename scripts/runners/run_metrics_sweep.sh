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
result_root=metrics_sweep_results

mkdir -p "$result_root"
date -Iseconds > "$result_root/started_at.txt"

for load in 700 1000; do
    mkdir -p "$result_root/load_$load"
    for scheduler in maxflow swarm random; do
        log_file="$result_root/load_$load/$scheduler.log"
        status_file="$result_root/load_$load/$scheduler.status"
        echo "START load=$load scheduler=$scheduler $(date -Iseconds)" | tee -a "$result_root/progress.log"
        "$python_bin" step3_load_sweep_metrics.py online "$scheduler" "$load" 300 > "$log_file" 2>&1
        status=$?
        echo "$status" > "$status_file"
        echo "END load=$load scheduler=$scheduler status=$status $(date -Iseconds)" | tee -a "$result_root/progress.log"
    done
done

date -Iseconds > "$result_root/finished_at.txt"
