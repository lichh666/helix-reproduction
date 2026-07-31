#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HELIX_ROOT="${HELIX_ROOT:-$HOME/llm-serving-repro/helix}"
sim_dir="$HELIX_ROOT/examples/simulation"
python_bin="$HELIX_ROOT/.venv/bin/python"
output_root="$sim_dir/reproduction_outputs/figure9"

if [[ ! -x "$python_bin" ]]; then
    echo "Python environment not found: $python_bin" >&2
    exit 1
fi

cp "$repo_root/scripts/simulation/step4_layout_comparison.py" "$sim_dir/"
cp "$repo_root/scripts/simulation/step5_distributed_layout_comparison.py" "$sim_dir/"
mkdir -p "$output_root/single" "$output_root/distributed"

cd "$sim_dir"
export PYTHONPATH="$HELIX_ROOT"
export PYTHONUNBUFFERED=1

for layout in helix petals swarm; do
    "$python_bin" step4_layout_comparison.py "$layout" 300 60 \
        > "$output_root/single/$layout.log" 2>&1
    echo "$?" > "$output_root/single/$layout.status"
done

for layout in helix petals swarm; do
    "$python_bin" step5_distributed_layout_comparison.py "$layout" 600 60 \
        > "$output_root/distributed/$layout.log" 2>&1
    echo "$?" > "$output_root/distributed/$layout.status"
done

echo "Figure 9 logs: $output_root"
