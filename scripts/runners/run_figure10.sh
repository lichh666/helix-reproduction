#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HELIX_ROOT="${HELIX_ROOT:-$HOME/llm-serving-repro/helix}"
sim_dir="$HELIX_ROOT/examples/simulation"
python_bin="$HELIX_ROOT/.venv/bin/python"
output_root="$sim_dir/reproduction_outputs/figure10"

if [[ ! -x "$python_bin" ]]; then
    echo "Python environment not found: $python_bin" >&2
    exit 1
fi

cp "$repo_root/scripts/simulation/step6_scheduler_comparison.py" "$sim_dir/"
mkdir -p "$output_root/single" "$output_root/distributed"

cd "$sim_dir"
export PYTHONPATH="$HELIX_ROOT"
export PYTHONUNBUFFERED=1

for scheduler in maxflow swarm random; do
    "$python_bin" step6_scheduler_comparison.py single "$scheduler" 300 60 \
        > "$output_root/single/$scheduler.log" 2>&1
    echo "$?" > "$output_root/single/$scheduler.status"
done

for scheduler in maxflow swarm random shortest_queue; do
    "$python_bin" step6_scheduler_comparison.py distributed "$scheduler" 600 60 \
        > "$output_root/distributed/$scheduler.log" 2>&1
    echo "$?" > "$output_root/distributed/$scheduler.status"
done

echo "Figure 10 logs: $output_root"
