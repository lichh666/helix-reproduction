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
result_root=scheduler_smoke_results

mkdir -p "$result_root/single" "$result_root/distributed"
for scheduler in maxflow swarm random; do
    "$python_bin" step6_scheduler_comparison.py single "$scheduler" 30 0 > "$result_root/single/$scheduler.log" 2>&1
    echo "$?" > "$result_root/single/$scheduler.status"
done
for scheduler in maxflow swarm random shortest_queue; do
    "$python_bin" step6_scheduler_comparison.py distributed "$scheduler" 30 0 > "$result_root/distributed/$scheduler.log" 2>&1
    echo "$?" > "$result_root/distributed/$scheduler.status"
done
