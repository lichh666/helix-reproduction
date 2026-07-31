# Compare request schedulers using the same Helix model placement.
import os
import sys

from simulator.initial_layout.layout_synthesizer import LayoutMethod, LayoutSynthesizer
from simulator.event_simulator.cluster_simulator import ClusterSimulator, ModelName, SchedulingMethod
from simulator.trace_generator.simulator_query_feeder import OfflineRequestFeeder
from simulator.scheduler.global_maxflow.global_maxflow_scheduler import KVParameters, SchedulingMode
from step4_layout_comparison import analyze


BASE = "../../artifact_evaluation/request_scheduling"
TOPOLOGY_FILES = {
    "single": {
        "cluster": f"{BASE}/config_single/cluster24.ini",
        "machine_profile": f"{BASE}/config_single/machine_profiles.ini",
        "solution": f"{BASE}/layout_single/ilp_sol.ini",
        "simulator_cluster": f"{BASE}/layout_single/simulator_cluster.ini",
    },
    "distributed": {
        "cluster": f"{BASE}/config_distributed/3cluster24.ini",
        "machine_profile": f"{BASE}/config_distributed/machine_profiles.ini",
        "solution": f"{BASE}/layout_distributed/ilp_sol.ini",
        "simulator_cluster": f"{BASE}/layout_distributed/simulator_cluster.ini",
    },
}
SCHEDULERS = {
    "maxflow": SchedulingMethod.MaxFlow,
    "swarm": SchedulingMethod.Swarm,
    "random": SchedulingMethod.Naive,
    "shortest_queue": SchedulingMethod.ShortestQueue,
}


def simulate(topology: str, scheduler_name: str, duration: float, warm_up: float):
    files = TOPOLOGY_FILES[topology]
    machine_num_dict = {"A100": 4, "L4": 8, "T4": 12}
    workspace = f"./sim_files/scheduler_comparison/{topology}/{scheduler_name}"
    os.makedirs(workspace, exist_ok=True)

    layout_synthesizer = LayoutSynthesizer(
        complete_cluster_file_name=files["cluster"],
        machine_profile_name=files["machine_profile"],
        model_name=ModelName.LLaMa70B,
        workspace_path=workspace,
        layout_method=LayoutMethod.LoadExisting,
        machine_num_dict=machine_num_dict,
    )
    cluster_file_path = layout_synthesizer.synthesize(args={
        "solution_file_name": files["solution"],
        "simulator_cluster_file_name": files["simulator_cluster"],
    })

    simulator = ClusterSimulator(model_name=ModelName.LLaMa70B, machine_num_dict=machine_num_dict)
    simulator.from_ini_file(config_file_name=cluster_file_path)
    if scheduler_name == "maxflow":
        simulator.init_scheduler(
            scheduling_method=SchedulingMethod.MaxFlow,
            args={
                "kv_param": KVParameters(expected_kv_hwm=0.85, expected_output_length_ratio=1),
                "scheduling_mode": SchedulingMode.Offline,
            },
        )
        initial_query_count = 20
    else:
        simulator.init_scheduler(scheduling_method=SCHEDULERS[scheduler_name], args=None)
        # The official single-cluster real-system artifact uses 240, while
        # the distributed simulator artifact uses 180.
        initial_query_count = 240 if topology == "single" else 180

    simulator.init_query_manager()
    simulator.mark_as_ready()
    finish_model_loading_time = layout_synthesizer.set_layout(simulator=simulator)
    simulator.update_scheduler()

    feeder = OfflineRequestFeeder(
        initial_query_count=initial_query_count,
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
    analysis_end_time = analysis_start_time + duration
    metrics = analyze(simulator, analysis_start_time, analysis_end_time, duration)

    print("# --------------- Scheduler Comparison Result --------------- #")
    print(f"Topology: {topology}")
    print(f"Scheduler: {scheduler_name}")
    print(f"Initial query count: {initial_query_count}")
    print(f"Warm-up duration: {warm_up:.1f}s")
    print(f"Measurement duration: {duration:.1f}s")
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
            f"Usage: python {sys.argv[0]} <single/distributed> "
            "<maxflow/swarm/random/shortest_queue> [duration_seconds] [warmup_seconds]"
        )
    topology = sys.argv[1]
    scheduler_name = sys.argv[2]
    if topology not in TOPOLOGY_FILES:
        raise ValueError(f"Unknown topology: {topology}")
    if scheduler_name not in SCHEDULERS:
        raise ValueError(f"Unknown scheduler: {scheduler_name}")
    duration = float(sys.argv[3]) if len(sys.argv) >= 4 else 600
    warm_up = float(sys.argv[4]) if len(sys.argv) >= 5 else 60
    simulate(topology, scheduler_name, duration, warm_up)


if __name__ == "__main__":
    main()
