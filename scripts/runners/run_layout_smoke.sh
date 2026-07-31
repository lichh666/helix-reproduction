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
result_root=layout_smoke_results

mkdir -p "$result_root"
: > "$result_root/progress.log"
for layout in helix petals swarm homogeneous; do
    echo "START layout=$layout $(date -Iseconds)" | tee -a "$result_root/progress.log"
    "$python_bin" step4_layout_comparison.py "$layout" 30 0 > "$result_root/$layout.log" 2>&1
    status=$?
    echo "$status" > "$result_root/$layout.status"
    echo "END layout=$layout status=$status $(date -Iseconds)" | tee -a "$result_root/progress.log"
done
