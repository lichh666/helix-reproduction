#!/usr/bin/env bash
set -euo pipefail

project_root="$HELIX_ROOT"
simulation_dir="$project_root/examples/simulation"
python_bin="$project_root/.venv/bin/python"
results_dir="$simulation_dir/quick_results"

export PYTHONPATH="$project_root"
mkdir -p "$results_dir"
cd "$simulation_dir"

for scheduler in maxflow swarm random; do
    echo "Starting $scheduler"
    "$python_bin" step3_quick_simulation.py offline "$scheduler" > "$results_dir/$scheduler.log" 2>&1
    echo "Completed $scheduler"
done
