# Compare model placements with the same Helix MaxFlow scheduler.
import os
import sys

from simulator.initial_layout.layout_synthesizer import LayoutMethod, LayoutSynthesizer
from simulator.event_simulator.cluster_simulator import (
    ClusterSimulator,
    ModelName,
    SchedulingMethod,
    RequestPhase,
)
from simulator.trace_generator.simulator_query_feeder import OfflineRequestFeeder
from simulator.scheduler.global_maxflow.global_maxflow_scheduler import KVParameters, SchedulingMode


LAYOUT_FILES = {
    "helix": ("./layouts/ilp/ilp_sol.ini", "./layouts/ilp/simulator_cluster.ini"),
    "petals": ("./layouts/petals/petals_sol.ini", "./layouts/petals/simulator_cluster.ini"),
    "swarm": ("./layouts/swarm/swarm_sol.ini", "./layouts/swarm/simulator_cluster.ini"),
    "homogeneous": (
        "./layouts/homogeneous/homogeneous_sol.ini",
        "./layouts/homogeneous/simulator_cluster.ini",
    ),
}
COMPLETE_CLUSTER_FILE = "./config/single24.ini"
MACHINE_PROFILE_FILE = "./config/machine_profile.ini"


def analyze(simulator, analysis_start_time: float, analysis_end_time: float, duration: float):
    prompt_tokens = 0
    decode_tokens = 0
    prompt_latencies = []
    decode_latencies = []

    for finish_time, request in simulator.finished_requests.values():
        if not analysis_start_time <= finish_time <= analysis_end_time:
            continue
        latency = request.location_history[-1][1] - request.location_history[0][1]
        if request.phase == RequestPhase.Initialization:
            prompt_tokens += request.token_seq_length
            prompt_latencies.append(latency)
        elif request.phase == RequestPhase.Increment:
            assert request.token_seq_length == 1
            decode_tokens += request.token_seq_length
            decode_latencies.append(latency)
        else:
            raise ValueError(f"Unknown request phase: {request.phase}")

    completed_queries = sum(
        analysis_start_time <= finish_time <= analysis_end_time
        for finish_time, _ in simulator.query_manager.finished_queries.values()
    )
    active_queries = len(simulator.query_manager.queries_on_the_fly)

    return {
        "prompt_token_throughput": prompt_tokens / duration,
        "decode_token_throughput": decode_tokens / duration,
        "total_token_throughput": (prompt_tokens + decode_tokens) / duration,
        "avg_prompt_latency": (
            sum(prompt_latencies) / len(prompt_latencies) if prompt_latencies else float("nan")
        ),
        "avg_decode_latency": (
            sum(decode_latencies) / len(decode_latencies) if decode_latencies else float("nan")
        ),
        "prompt_iterations": len(prompt_latencies),
        "decode_iterations": len(decode_latencies),
        "completed_queries": completed_queries,
        "active_queries": active_queries,
    }


def simulate(layout_name: str, duration: float, warm_up: float):
    solution_file_name, simulator_cluster_file_name = LAYOUT_FILES[layout_name]
    machine_num_dict = {"A100": 4, "L4": 8, "T4": 12}
    workspace = f"./sim_files/layout_comparison/{layout_name}"
    os.makedirs(workspace, exist_ok=True)

    layout_synthesizer = LayoutSynthesizer(
        complete_cluster_file_name=COMPLETE_CLUSTER_FILE,
        machine_profile_name=MACHINE_PROFILE_FILE,
        model_name=ModelName.LLaMa70B,
        workspace_path=workspace,
        layout_method=LayoutMethod.LoadExisting,
        machine_num_dict=machine_num_dict,
    )
    cluster_file_path = layout_synthesizer.synthesize(args={
        "solution_file_name": solution_file_name,
        "simulator_cluster_file_name": simulator_cluster_file_name,
    })

    simulator = ClusterSimulator(model_name=ModelName.LLaMa70B, machine_num_dict=machine_num_dict)
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
    max_compute_throughput = layout_synthesizer.layout_synthesizer.get_flow_upper_bound()
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
    analysis_end_time = analysis_start_time + duration
    metrics = analyze(simulator, analysis_start_time, analysis_end_time, duration)

    print("# ---------------- Layout Comparison Result ---------------- #")
    print(f"Layout: {layout_name}")
    print("Scheduler: maxflow")
    print(f"Warm-up duration: {warm_up:.1f}s")
    print(f"Measurement duration: {duration:.1f}s")
    print(f"Max compute throughput: {max_compute_throughput:.3f} tokens/s")
    print(f"Static max flow: {max_flow:.3f} tokens/s")
    print(f"Prompt token throughput: {metrics['prompt_token_throughput']:.1f} tokens/s")
    print(f"Decode token throughput: {metrics['decode_token_throughput']:.1f} tokens/s")
    print(f"Total token throughput: {metrics['total_token_throughput']:.1f} tokens/s")
    print(f"Avg prompt latency: {metrics['avg_prompt_latency']:.3f}s")
    print(f"Avg decode latency: {metrics['avg_decode_latency']:.3f}s")
    print(f"Prompt iterations completed: {metrics['prompt_iterations']}")
    print(f"Decode iterations completed: {metrics['decode_iterations']}")
    print(f"Queries completed in measurement window: {metrics['completed_queries']}")
    print(f"Queries active at cutoff: {metrics['active_queries']}")
    print("# ---------------------------------------------------------- #")


def main():
    if len(sys.argv) not in (2, 3, 4):
        raise SystemExit(
            f"Usage: python {sys.argv[0]} <helix/petals/swarm/homogeneous> "
            "[duration_seconds] [warmup_seconds]"
        )
    layout_name = sys.argv[1]
    if layout_name not in LAYOUT_FILES:
        raise ValueError(f"Unknown layout: {layout_name}")
    duration = float(sys.argv[2]) if len(sys.argv) >= 3 else 300
    warm_up = float(sys.argv[3]) if len(sys.argv) >= 4 else 60
    simulate(layout_name=layout_name, duration=duration, warm_up=warm_up)


if __name__ == "__main__":
    main()
