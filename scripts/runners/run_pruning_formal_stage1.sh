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
result_root=pruning_comparison_results

mkdir -p "$result_root/24" "$result_root/42"
: > "$result_root/progress.log"
for pruning in pruned unpruned; do
    echo "START setup=24 pruning=$pruning duration=600 $(date -Iseconds)" | tee -a "$result_root/progress.log"
    "$python_bin" step7_pruning_comparison.py 24 "$pruning" 600 60 > "$result_root/24/$pruning.log" 2>&1
    status=$?
    echo "$status" > "$result_root/24/$pruning.status"
    echo "END setup=24 pruning=$pruning status=$status $(date -Iseconds)" | tee -a "$result_root/progress.log"
done
for pruning in pruned unpruned; do
    echo "START setup=42 pruning=$pruning duration=120 $(date -Iseconds)" | tee -a "$result_root/progress.log"
    "$python_bin" step7_pruning_comparison.py 42 "$pruning" 120 60 > "$result_root/42/$pruning.log" 2>&1
    status=$?
    echo "$status" > "$result_root/42/$pruning.status"
    echo "END setup=42 pruning=$pruning status=$status $(date -Iseconds)" | tee -a "$result_root/progress.log"
done
