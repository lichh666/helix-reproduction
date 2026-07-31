#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HELIX_ROOT="${HELIX_ROOT:-$HOME/llm-serving-repro/helix}"
sim_dir="$HELIX_ROOT/examples/simulation"
python_bin="$HELIX_ROOT/.venv/bin/python"
output_root="$sim_dir/reproduction_outputs/figure11/24"

if [[ ! -x "$python_bin" ]]; then
    echo "Python environment not found: $python_bin" >&2
    exit 1
fi

cp "$repo_root/scripts/simulation/step7_pruning_comparison.py" "$sim_dir/"
mkdir -p "$output_root"

cd "$sim_dir"
export PYTHONPATH="$HELIX_ROOT"
export PYTHONUNBUFFERED=1

for pruning in pruned unpruned; do
    "$python_bin" step7_pruning_comparison.py 24 "$pruning" 600 60 \
        > "$output_root/$pruning.log" 2>&1
    echo "$?" > "$output_root/$pruning.status"
done

echo "Figure 11 24-node logs: $output_root"
