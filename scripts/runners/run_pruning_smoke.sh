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
result_root=pruning_smoke_results

mkdir -p "$result_root/24" "$result_root/42"
for setup in 24 42; do
    for pruning in pruned unpruned; do
        "$python_bin" step7_pruning_comparison.py "$setup" "$pruning" 30 0 > "$result_root/$setup/$pruning.log" 2>&1
        echo "$?" > "$result_root/$setup/$pruning.status"
    done
done
