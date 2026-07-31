#!/usr/bin/env bash
set -euo pipefail

project_root="$HELIX_ROOT"
simulation_dir="$project_root/examples/simulation"
python_bin="$project_root/.venv/bin/python"
results_dir="$simulation_dir/full_results"

export PYTHONPATH="$project_root"
mkdir -p "$results_dir"
cd "$simulation_dir"

for scheduler in maxflow swarm random; do
    echo "$(date --iso-8601=seconds) Starting $scheduler"
    "$python_bin" step3_run_simulation.py offline "$scheduler" > "$results_dir/$scheduler.log" 2>&1
    echo "$(date --iso-8601=seconds) Completed $scheduler"
done
