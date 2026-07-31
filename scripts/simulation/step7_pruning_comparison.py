# Re-run Figure 11a using the official precomputed pruned/unpruned layouts.
import os
import sys

from simulator.initial_layout.layout_synthesizer import LayoutMethod, LayoutSynthesizer
from simulator.event_simulator.cluster_simulator import ClusterSimulator, ModelName, SchedulingMethod
from simulator.trace_generator.simulator_query_feeder import OfflineRequestFeeder
from simulator.scheduler.global_maxflow.global_maxflow_scheduler import KVParameters, SchedulingMode
from step4_layout_comparison import analyze


BASE = "../../artifact_evaluation"
SETUPS = {
    "24": {
        "cluster": f"{BASE}/ablation/config/3cluster24.ini",
        "machine_profile": f"{BASE}/ablation/config/machine_profiles.ini",
        "machine_num_dict": {"A100": 4, "L4": 8, "T4": 12},
        "pruned": (
            f"{BASE}/distributed_clusters/layout_llama70b/ilp/ilp_sol.ini",
            f"{BASE}/distributed_clusters/layout_llama70b/ilp/simulator_cluster.ini",
        ),
        "unpruned": (
            f"{BASE}/ablation/layouts/no_prune_24/ilp_sol.ini",
            f"{BASE}/ablation/layouts/no_prune_24/simulator_cluster.ini",
        ),
    },
    "42": {
        "cluster": f"{BASE}/ablation/config/cluster42.ini",
        "machine_profile": f"{BASE}/ablation/config/machine_profiles.ini",
        "machine_num_dict": {
            "A100": 4, "V100": 6, "L4": 8, "L4x2": 4,
            "T4": 10, "T4x2": 6, "T4x4": 4,
        },
        "pruned": (
            f"{BASE}/high_heterogeneity/layout_llama70b/ilp/ilp_sol.ini",
            f"{BASE}/high_heterogeneity/layout_llama70b/ilp/simulator_cluster.ini",
        ),
        "unpruned": (
            f"{BASE}/ablation/layouts/no_prune_42/ilp_sol.ini",
            f"{BASE}/ablation/layouts/no_prune_42/simulator_cluster.ini",
        ),
    },
}


def simulate(setup_name: str, pruning: str, duration: float, warm_up: float):
    setup = SETUPS[setup_name]
    solution_file, simulator_cluster_file = setup[pruning]
    workspace = f"./sim_files/pruning_comparison/{setup_name}/{pruning}"
    os.makedirs(workspace, exist_ok=True)

    layout_synthesizer = LayoutSynthesizer(
        complete_cluster_file_name=setup["cluster"],
        machine_profile_name=setup["machine_profile"],
        model_name=ModelName.LLaMa70B,
        workspace_path=workspace,
        layout_method=LayoutMethod.LoadExisting,
        machine_num_dict=setup["machine_num_dict"],
    )
    cluster_file_path = layout_synthesizer.synthesize(args={
        "solution_file_name": solution_file,
        "simulator_cluster_file_name": simulator_cluster_file,
    })

    simulator = ClusterSimulator(
        model_name=ModelName.LLaMa70B,
        machine_num_dict=setup["machine_num_dict"],
    )
    simulator.from_ini_file(config_file_name=cluster_file_path)
    simulator.init_scheduler(
        scheduling_method=SchedulingMethod.MaxFlow,
        args={
            "kv_param": KVParameters(expected_kv_hwm=0.85, expected_output_length_ratio=1),
            "scheduling_mode": SchedulingMode.Offline,
        },
    )
    simulator.init_query_manager()
    simulator.mark_as_ready()
    finish_model_loading_time = layout_synthesizer.set_layout(simulator=simulator)
    simulator.update_scheduler()
    max_flow = simulator.scheduler.core.flow_graph.flow_value

    feeder = OfflineRequestFeeder(
        initial_query_count=20,
        start_time=finish_model_loading_time,
        duration=warm_up + duration,
        stop_at_duration=True,
        feed_hwm=0.8,
        seed=0,
    )
    feeder.auto_simulate(
        simulator=simulator,
        watch_items=["all"],
        watch_interval=max(10, min(60, duration)),
    )

    analysis_start_time = finish_model_loading_time + warm_up
    metrics = analyze(
        simulator,
        analysis_start_time,
        analysis_start_time + duration,
        duration,
    )
    print("# ---------------- Pruning Comparison Result ---------------- #")
    print(f"Cluster size: {setup_name}")
    print(f"Pruning: {pruning}")
    print(f"Warm-up duration: {warm_up:.1f}s")
    print(f"Measurement duration: {duration:.1f}s")
    print(f"Static max flow: {max_flow:.3f} tokens/s")
    print(f"Prompt token throughput: {metrics['prompt_token_throughput']:.1f} tokens/s")
    print(f"Decode token throughput: {metrics['decode_token_throughput']:.1f} tokens/s")
    print(f"Total token throughput: {metrics['total_token_throughput']:.1f} tokens/s")
    print(f"Avg prompt latency: {metrics['avg_prompt_latency']:.3f}s")
    print(f"Avg decode latency: {metrics['avg_decode_latency']:.3f}s")
    print(f"Queries completed in measurement window: {metrics['completed_queries']}")
    print(f"Queries active at cutoff: {metrics['active_queries']}")
    print("# ----------------------------------------------------------- #")


def main():
    if len(sys.argv) not in (3, 4, 5):
        raise SystemExit(
            f"Usage: python {sys.argv[0]} <24/42> <pruned/unpruned> "
            "[duration_seconds] [warmup_seconds]"
        )
    setup_name, pruning = sys.argv[1], sys.argv[2]
    if setup_name not in SETUPS:
        raise ValueError(f"Unknown setup: {setup_name}")
    if pruning not in ("pruned", "unpruned"):
        raise ValueError(f"Unknown pruning state: {pruning}")
    duration = float(sys.argv[3]) if len(sys.argv) >= 4 else 300
    warm_up = float(sys.argv[4]) if len(sys.argv) >= 5 else 60
    simulate(setup_name, pruning, duration, warm_up)


if __name__ == "__main__":
    main()
