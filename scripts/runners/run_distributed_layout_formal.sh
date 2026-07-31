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
result_root=distributed_layout_comparison_results

mkdir -p "$result_root"
: > "$result_root/progress.log"
date -Iseconds > "$result_root/started_at.txt"
for layout in helix petals swarm; do
    echo "START layout=$layout $(date -Iseconds)" | tee -a "$result_root/progress.log"
    "$python_bin" step5_distributed_layout_comparison.py "$layout" 300 60 > "$result_root/$layout.log" 2>&1
    status=$?
    echo "$status" > "$result_root/$layout.status"
    echo "END layout=$layout status=$status $(date -Iseconds)" | tee -a "$result_root/progress.log"
done
date -Iseconds > "$result_root/finished_at.txt"
