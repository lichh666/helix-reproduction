#!/usr/bin/env bash
set -uo pipefail

project_root="$HELIX_ROOT"
simulation_dir="$project_root/examples/simulation"
python_bin="$project_root/.venv/bin/python"
results_dir="$simulation_dir/load_sweep_results"

export PYTHONPATH="$project_root"
mkdir -p "$results_dir/load_400"
cd "$simulation_dir"

for scheduler in maxflow swarm random; do
    cp "equal_load_online_results/$scheduler.log" "$results_dir/load_400/$scheduler.log"
done

for load in 700 1000; do
    mkdir -p "$results_dir/load_$load"
    for scheduler in maxflow swarm random; do
        echo "$(date --iso-8601=seconds) Starting load=$load scheduler=$scheduler"
        status=0
        "$python_bin" step3_load_sweep.py online "$scheduler" "$load" > "$results_dir/load_$load/$scheduler.log" 2>&1 || status=$?
        echo "$status" > "$results_dir/load_$load/$scheduler.status"
        echo "$(date --iso-8601=seconds) Completed load=$load scheduler=$scheduler status=$status"
    done
done
