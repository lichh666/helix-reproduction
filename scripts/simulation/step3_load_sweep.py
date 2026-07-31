# 2024.10.29 Yixuan Mei
import sys
from simulator.initial_layout.layout_synthesizer import LayoutMethod, LayoutSynthesizer
from simulator.event_simulator.cluster_simulator import ClusterSimulator, ModelName, SchedulingMethod, RequestPhase
from simulator.trace_generator.simulator_query_feeder import OnlineRequestFeeder, OfflineRequestFeeder
from simulator.scheduler.global_maxflow.global_maxflow_scheduler import KVParameters, SchedulingMode


def compute_extended_online_metrics(simulator, analysis_start_time: float,
                                    analysis_end_time: float, duration: float):
    """Compute scheduler-independent online serving metrics."""
    prompt_tokens = 0
    decode_tokens = 0
    prompt_iterations = 0
    decode_iterations = 0
    for finish_time, request in simulator.finished_requests.values():
        if not analysis_start_time <= finish_time <= analysis_end_time:
            continue
        if request.phase == RequestPhase.Initialization:
            prompt_tokens += request.token_seq_length
            prompt_iterations += 1
        elif request.phase == RequestPhase.Increment:
            decode_tokens += request.token_seq_length
            decode_iterations += 1
        else:
            raise ValueError(f"Unknown request phase: {request.phase}")

    query_manager = simulator.query_manager
    finished_queries = list(query_manager.finished_queries.values())
    active_queries = list(query_manager.queries_on_the_fly.values())
    all_queries = [query for _, query in finished_queries] + active_queries
    issued_queries = [
        query for query in all_queries
        if analysis_start_time <= query.creation_time < analysis_end_time
    ]
    completed_queries = [
        query for finish_time, query in finished_queries
        if (analysis_start_time <= query.creation_time < analysis_end_time
            and finish_time <= analysis_end_time)
    ]

    offered_tokens = sum(
        query.input_seq_length + query.output_seq_length
        for query in issued_queries
    )
    served_tokens = prompt_tokens + decode_tokens
    issued_query_count = len(issued_queries)
    completed_query_count = len(completed_queries)

    return {
        "prompt_token_throughput": prompt_tokens / duration,
        "decode_token_throughput": decode_tokens / duration,
        "total_token_throughput": served_tokens / duration,
        "offered_token_throughput": offered_tokens / duration,
        "token_service_ratio": served_tokens / offered_tokens if offered_tokens else 0.0,
        "prompt_iterations": prompt_iterations,
        "decode_iterations": decode_iterations,
        "issued_queries": issued_query_count,
        "completed_queries": completed_query_count,
        "active_queries": issued_query_count - completed_query_count,
        "query_completion_rate": (
            completed_query_count / issued_query_count if issued_query_count else 0.0
        ),
        "query_completion_throughput": completed_query_count / duration,
    }


def print_extended_online_metrics(metrics):
    print(f"Prompt token throughput: {metrics['prompt_token_throughput']:.1f} tokens/s")
    print(f"Decode token throughput: {metrics['decode_token_throughput']:.1f} tokens/s")
    print(f"Total token throughput: {metrics['total_token_throughput']:.1f} tokens/s")
    print(f"Offered token throughput: {metrics['offered_token_throughput']:.1f} tokens/s")
    print(f"Token service ratio: {metrics['token_service_ratio']:.3%}")
    print(f"Prompt iterations completed: {metrics['prompt_iterations']}")
    print(f"Decode iterations completed: {metrics['decode_iterations']}")
    print(f"Queries issued: {metrics['issued_queries']}")
    print(f"Queries completed: {metrics['completed_queries']}")
    print(f"Queries still active: {metrics['active_queries']}")
    print(f"End-of-run query completion rate: {metrics['query_completion_rate']:.3%}")
    print(f"Query completion throughput: {metrics['query_completion_throughput']:.3f} queries/s")


def simulate_maxflow_offline():
    """
    Scheduling method: Helix MaxFlow
    Request arrival pattern: offline
    """
    # ---------------------------------------- Initialization ---------------------------------------- #
    # load the model placement
    # cluster_file_path is "simulator_cluster_file_name" in layout_args
    machine_num_dict = {"A100": 4, "L4": 8, "T4": 12}
    layout_synthesizer = LayoutSynthesizer(
        complete_cluster_file_name="config/single24.ini",
        machine_profile_name="config/machine_profile.ini",
        model_name=ModelName.LLaMa70B,
        workspace_path="./sim_files/maxflow_offline/",
        layout_method=LayoutMethod.LoadExisting,
        machine_num_dict=machine_num_dict
    )
    layout_args = {
        "solution_file_name": "./layouts/ilp/ilp_sol.ini",
        "simulator_cluster_file_name": "./layouts/ilp/simulator_cluster.ini",
    }
    cluster_file_path = layout_synthesizer.synthesize(args=layout_args)

    # initialize the simulator and set scheduler as MaxFlow scheduler
    simulator = ClusterSimulator(model_name=ModelName.LLaMa70B, machine_num_dict=machine_num_dict)
    simulator.from_ini_file(config_file_name=cluster_file_path)
    scheduler_args = {
        "kv_param": KVParameters(expected_kv_hwm=0.85, expected_output_length_ratio=1),
        "scheduling_mode": SchedulingMode.Offline,  # offline
    }
    simulator.init_scheduler(scheduling_method=SchedulingMethod.MaxFlow, args=scheduler_args)
    simulator.init_query_manager()
    simulator.mark_as_ready()

    # load model placement and update scheduler
    finish_model_loading_time = layout_synthesizer.set_layout(simulator=simulator)
    simulator.update_scheduler()

    # print some status information
    print(f"Max compute throughput = {layout_synthesizer.layout_synthesizer.get_flow_upper_bound()}")
    print(f"Max flow = {simulator.scheduler.core.flow_graph.flow_value}")
    simulator.visualize_cluster(title="model_placement", save_path="./sim_files/maxflow_offline/")

    # ------------------------------------------ Simulation ------------------------------------------ #
    # setup simulation and run
    warm_up, duration = 60, 300
    auto_test = OfflineRequestFeeder(initial_query_count=20, start_time=finish_model_loading_time,
                                     duration=warm_up + duration, stop_at_duration=True, feed_hwm=0.8, seed=0)
    auto_test.auto_simulate(simulator=simulator, watch_items=["all"], watch_interval=10)

    # ------------------------------------------- Analysis ------------------------------------------- #
    analysis_start_time = finish_model_loading_time + warm_up
    analysis_end_time = finish_model_loading_time + warm_up + duration

    # compute decode throughput
    # Note: 1. here, each request represent one iteration of an LLM query (either prompt or decode)
    #       2. RequestPhase.Initialization is for prompt, RequestPhase.Increment is for decode
    #       3. token_seq_length is the number of tokens processed in this iteration
    total_tokens = 0
    for request_uid, time_request in simulator.finished_requests.items():
        time, request = time_request
        if request.phase == RequestPhase.Initialization:
            continue
        if analysis_start_time <= time <= analysis_end_time:
            assert request.token_seq_length == 1, "Decode requests should have token_seq_length == 1!"
            total_tokens += request.token_seq_length
    decode_throughput = total_tokens / duration

    # compute prompt and decode latency
    sum_prompt_latency, sum_decode_latency = 0, 0
    valid_prompts, valid_decodes = 0, 0
    for request_uid, time_request in simulator.finished_requests.items():
        time, request = time_request
        if analysis_start_time <= time <= analysis_end_time:
            if request.phase == RequestPhase.Initialization:
                sum_prompt_latency += request.location_history[-1][1] - request.location_history[0][1]
                valid_prompts += 1
            elif request.phase == RequestPhase.Increment:
                sum_decode_latency += request.location_history[-1][1] - request.location_history[0][1]
                valid_decodes += 1
            else:
                assert False, "Found unknown requests phase!"
    avg_prompt_latency = sum_prompt_latency / valid_prompts
    avg_decode_latency = sum_decode_latency / valid_decodes
    # print and plot
    print(f"# ------------------------------------------------------------- #")
    print(f"Simulation Results (time range: {analysis_start_time}s - {analysis_end_time}s)")
    print(f"Avg decode speed: {decode_throughput:.1f} tokens/s")
    print(f"Avg prompt latency: {avg_prompt_latency:.3f}s")
    print(f"Avg decode latency: {avg_decode_latency:.3f}s")
    print(f"# ------------------------------------------------------------- #")
    simulator.plot_inference_speed(max_time=400, save_path="./sim_files/maxflow_offline/throughput.png")
    simulator.plot_request_latency(ignore_initialize=True, save_path="./sim_files/maxflow_offline/latency.png")


def simulate_maxflow_online(avg_throughput: float, duration: float = 300):
    # ---------------------------------------- Initialization ---------------------------------------- #
    # load the model placement
    # cluster_file_path is "simulator_cluster_file_name" in layout_args
    machine_num_dict = {"A100": 4, "L4": 8, "T4": 12}
    layout_synthesizer = LayoutSynthesizer(
        complete_cluster_file_name="config/single24.ini",
        machine_profile_name="config/machine_profile.ini",
        model_name=ModelName.LLaMa70B,
        workspace_path="./sim_files/maxflow_online/",
        layout_method=LayoutMethod.LoadExisting,
        machine_num_dict=machine_num_dict
    )
    layout_args = {
        "solution_file_name": "./layouts/ilp/ilp_sol.ini",
        "simulator_cluster_file_name": "./layouts/ilp/simulator_cluster.ini",
    }
    cluster_file_path = layout_synthesizer.synthesize(args=layout_args)

    # initialize the simulator and set scheduler as MaxFlow scheduler
    simulator = ClusterSimulator(model_name=ModelName.LLaMa70B, machine_num_dict=machine_num_dict)
    simulator.from_ini_file(config_file_name=cluster_file_path)
    scheduler_args = {
        # offline
        "kv_param": KVParameters(expected_kv_hwm=0.9, expected_output_length_ratio=0.6),
        "scheduling_mode": SchedulingMode.Online,
    }
    simulator.init_scheduler(scheduling_method=SchedulingMethod.MaxFlow, args=scheduler_args)
    simulator.init_query_manager()
    simulator.mark_as_ready()

    # load the models into the simulator and update scheduler
    finish_model_loading_time = layout_synthesizer.set_layout(simulator=simulator)
    simulator.update_scheduler()

    # print some status information (we don't save the plots here)
    print(f"Upper bound of throughput: {layout_synthesizer.layout_synthesizer.get_flow_upper_bound()}")
    print(f"Max flow in simulator: {simulator.scheduler.core.flow_graph.flow_value}")
    simulator.visualize_cluster(title="model_placement", save_path="./sim_files/maxflow_online/")

    # ------------------------------------------ Simulation ------------------------------------------ #
    # setup simulation and run
    warm_up = 0
    auto_test = OnlineRequestFeeder(cluster_token_throughput=avg_throughput,
                                    start_time=finish_model_loading_time,
                                    duration=duration, seed=0)
    auto_test.auto_simulate(simulator=simulator, watch_items=["all"], watch_interval=10)

    # ------------------------------------------- Analysis ------------------------------------------- #
    analysis_start_time = finish_model_loading_time + warm_up
    analysis_end_time = finish_model_loading_time + warm_up + duration

    # compute decode throughput
    total_tokens = 0
    for request_uid, time_request in simulator.finished_requests.items():
        time, request = time_request
        if request.phase == RequestPhase.Initialization:
            continue
        if analysis_start_time <= time <= analysis_end_time:
            assert request.token_seq_length == 1, "Only count decode requests!"
            total_tokens += request.token_seq_length
    decode_throughput = total_tokens / duration

    # compute and save prompt and decode latency
    prompt_latency_list, decode_latency_list = [], []
    sum_prompt_latency, sum_decode_latency = 0, 0
    valid_prompts, valid_decodes = 0, 0
    for request_uid, time_request in simulator.finished_requests.items():
        time, request = time_request
        if analysis_start_time <= time <= analysis_end_time:
            if request.phase == RequestPhase.Initialization:
                sum_prompt_latency += request.location_history[-1][1] - request.location_history[0][1]
                prompt_latency_list.append((time, request.location_history[-1][1] - request.location_history[0][1]))
                valid_prompts += 1
            elif request.phase == RequestPhase.Increment:
                sum_decode_latency += request.location_history[-1][1] - request.location_history[0][1]
                decode_latency_list.append((time, request.location_history[-1][1] - request.location_history[0][1]))
                valid_decodes += 1
            else:
                assert False, "Found unknown requests phase!"
    avg_prompt_latency = sum_prompt_latency / valid_prompts
    avg_decode_latency = sum_decode_latency / valid_decodes
    extended_metrics = compute_extended_online_metrics(
        simulator=simulator,
        analysis_start_time=analysis_start_time,
        analysis_end_time=analysis_end_time,
        duration=duration,
    )

    # print and plot
    print(f"# ------------------------------------------------------------- #")
    print(f"Simulation Results (time range: {analysis_start_time}s - {analysis_end_time}s)")
    print(f"Avg decode speed: {decode_throughput:.1f} tokens/s")
    print(f"Avg prompt latency: {avg_prompt_latency:.3f}s")
    print(f"Avg decode latency: {avg_decode_latency:.3f}s")
    print_extended_online_metrics(extended_metrics)
    print(f"# ------------------------------------------------------------- #")
    simulator.plot_inference_speed(max_time=400, save_path="./sim_files/maxflow_online/throughput.png")
    simulator.plot_request_latency(ignore_initialize=True, save_path="./sim_files/maxflow_online/latency.png")

    # save the latency data with pickle
    import pickle
    prompt_file_name = "./sim_files/maxflow_online/prompt_latency.pkl"
    decode_file_name = "./sim_files/maxflow_online/decode_latency.pkl"
    with open(prompt_file_name, "wb") as f:
        pickle.dump(prompt_latency_list, f)
    with open(decode_file_name, "wb") as f:
        pickle.dump(decode_latency_list, f)


def simulate_heuristic_offline(scheduling_method: SchedulingMethod, initial_query_num: int):
    # ---------------------------------------- Initialization ---------------------------------------- #
    # load the model placement
    # cluster_file_path is "simulator_cluster_file_name" in layout_args
    machine_num_dict = {"A100": 4, "L4": 8, "T4": 12}
    layout_synthesizer = LayoutSynthesizer(
        complete_cluster_file_name="config/single24.ini",
        machine_profile_name="config/machine_profile.ini",
        model_name=ModelName.LLaMa70B,
        workspace_path="./tmp",
        layout_method=LayoutMethod.LoadExisting,
        machine_num_dict=machine_num_dict
    )
    layout_args = {
        "solution_file_name": "./layouts/ilp/ilp_sol.ini",
        "simulator_cluster_file_name": "./layouts/ilp/simulator_cluster.ini",
    }
    cluster_file_path = layout_synthesizer.synthesize(args=layout_args)

    # initialize the simulator and set scheduler
    simulator = ClusterSimulator(model_name=ModelName.LLaMa70B, machine_num_dict=machine_num_dict)
    simulator.from_ini_file(config_file_name=cluster_file_path)
    simulator.init_scheduler(scheduling_method=scheduling_method, args=None)
    simulator.init_query_manager()
    simulator.mark_as_ready()

    # load the models into the simulator and update scheduler
    finish_model_loading_time = layout_synthesizer.set_layout(simulator=simulator)
    simulator.update_scheduler()

    # print some status information
    print(f"Max compute throughput = {layout_synthesizer.layout_synthesizer.get_flow_upper_bound()}")

    # ------------------------------------------ Simulation ------------------------------------------ #
    # setup simulation and run
    warm_up, duration = 60, 300
    auto_test = OfflineRequestFeeder(initial_query_count=initial_query_num, start_time=finish_model_loading_time,
                                     duration=warm_up + duration, stop_at_duration=True, feed_hwm=0.8, seed=0)
    auto_test.auto_simulate(simulator=simulator, watch_items=["all"], watch_interval=10)

    # ------------------------------------------- Analysis ------------------------------------------- #
    analysis_start_time = finish_model_loading_time + warm_up
    analysis_end_time = finish_model_loading_time + warm_up + duration

    # compute decode throughput
    total_tokens = 0
    for request_uid, time_request in simulator.finished_requests.items():
        time, request = time_request
        if request.phase == RequestPhase.Initialization:
            continue
        if analysis_start_time <= time <= analysis_end_time:
            assert request.token_seq_length == 1, "Only count decode requests!"
            total_tokens += request.token_seq_length
    decode_throughput = total_tokens / duration

    # prompt and decode latency
    sum_prompt_latency, sum_decode_latency = 0, 0
    valid_prompts, valid_decodes = 0, 0
    for request_uid, time_request in simulator.finished_requests.items():
        time, request = time_request
        if analysis_start_time <= time <= analysis_end_time:
            if request.phase == RequestPhase.Initialization:
                sum_prompt_latency += request.location_history[-1][1] - request.location_history[0][1]
                valid_prompts += 1
            elif request.phase == RequestPhase.Increment:
                sum_decode_latency += request.location_history[-1][1] - request.location_history[0][1]
                valid_decodes += 1
            else:
                assert False, "Found unknown requests phase!"
    avg_prompt_latency = sum_prompt_latency / valid_prompts
    avg_decode_latency = sum_decode_latency / valid_decodes
    # print and plot (we don't save the plots here)
    print(f"# ------------------------------------------------------------- #")
    print(f"Simulation Results (time range: {analysis_start_time}s - {analysis_end_time}s)")
    print(f"Avg decode speed: {decode_throughput:.1f} tokens/s")
    print(f"Avg prompt latency: {avg_prompt_latency:.3f}s")
    print(f"Avg decode latency: {avg_decode_latency:.3f}s")
    print(f"# ------------------------------------------------------------- #")
    simulator.plot_inference_speed(max_time=400, save_path=None)
    simulator.plot_request_latency(ignore_initialize=True, save_path=None)


def simulate_heuristic_online(scheduling_method: SchedulingMethod, avg_throughput: float,
                              duration: float = 300):
    # ---------------------------------------- Initialization ---------------------------------------- #
    # load the model placement
    # cluster_file_path is "simulator_cluster_file_name" in layout_args
    machine_num_dict = {"A100": 4, "L4": 8, "T4": 12}
    layout_synthesizer = LayoutSynthesizer(
        complete_cluster_file_name="config/single24.ini",
        machine_profile_name="config/machine_profile.ini",
        model_name=ModelName.LLaMa70B,
        workspace_path="./sim_files",
        layout_method=LayoutMethod.LoadExisting,
        machine_num_dict=machine_num_dict
    )
    layout_args = {
        "solution_file_name": "./layouts/ilp/ilp_sol.ini",
        "simulator_cluster_file_name": "./layouts/ilp/simulator_cluster.ini",
    }
    cluster_file_path = layout_synthesizer.synthesize(args=layout_args)

    # initialize the simulator
    simulator = ClusterSimulator(model_name=ModelName.LLaMa70B, machine_num_dict=machine_num_dict)
    simulator.from_ini_file(config_file_name=cluster_file_path)
    simulator.init_scheduler(scheduling_method=scheduling_method, args=None)
    simulator.init_query_manager()
    simulator.mark_as_ready()

    # load the models into the simulator and update scheduler
    finish_model_loading_time = layout_synthesizer.set_layout(simulator=simulator)
    simulator.update_scheduler()

    # print some status information
    print(f"Upper bound of throughput: {layout_synthesizer.layout_synthesizer.get_flow_upper_bound()}")

    # ------------------------------------------ Simulation ------------------------------------------ #
    # setup simulation and run
    warm_up = 0
    auto_test = OnlineRequestFeeder(cluster_token_throughput=avg_throughput,
                                    start_time=finish_model_loading_time,
                                    duration=duration, seed=0)
    auto_test.auto_simulate(simulator=simulator, watch_items=["all"], watch_interval=10)

    # ------------------------------------------- Analysis ------------------------------------------- #
    analysis_start_time = finish_model_loading_time + warm_up
    analysis_end_time = finish_model_loading_time + warm_up + duration

    # compute decode throughput
    total_tokens = 0
    for request_uid, time_request in simulator.finished_requests.items():
        time, request = time_request
        if request.phase == RequestPhase.Initialization:
            continue
        if analysis_start_time <= time <= analysis_end_time:
            assert request.token_seq_length == 1, "Only count decode requests!"
            total_tokens += request.token_seq_length
    decode_throughput = total_tokens / duration

    # compute and save prompt and decode latency
    prompt_latency_list, decode_latency_list = [], []
    sum_prompt_latency, sum_decode_latency = 0, 0
    valid_prompts, valid_decodes = 0, 0
    for request_uid, time_request in simulator.finished_requests.items():
        time, request = time_request
        if analysis_start_time <= time <= analysis_end_time:
            if request.phase == RequestPhase.Initialization:
                sum_prompt_latency += request.location_history[-1][1] - request.location_history[0][1]
                prompt_latency_list.append((time, request.location_history[-1][1] - request.location_history[0][1]))
                valid_prompts += 1
            elif request.phase == RequestPhase.Increment:
                sum_decode_latency += request.location_history[-1][1] - request.location_history[0][1]
                decode_latency_list.append((time, request.location_history[-1][1] - request.location_history[0][1]))
                valid_decodes += 1
            else:
                assert False, "Found unknown requests phase!"
    avg_prompt_latency = sum_prompt_latency / valid_prompts
    avg_decode_latency = sum_decode_latency / valid_decodes
    extended_metrics = compute_extended_online_metrics(
        simulator=simulator,
        analysis_start_time=analysis_start_time,
        analysis_end_time=analysis_end_time,
        duration=duration,
    )

    # print and plot (we don't save the plots here)
    print(f"# ------------------------------------------------------------- #")
    print(f"Simulation Results (time range: {analysis_start_time}s - {analysis_end_time}s)")
    print(f"Avg decode speed: {decode_throughput:.1f} tokens/s")
    print(f"Avg prompt latency: {avg_prompt_latency:.3f}s")
    print(f"Avg decode latency: {avg_decode_latency:.3f}s")
    print_extended_online_metrics(extended_metrics)
    print(f"# ------------------------------------------------------------- #")
    simulator.plot_inference_speed(max_time=400)
    simulator.plot_request_latency(ignore_initialize=True)

    # save the latency data with pickle
    # import pickle
    # prompt_file_name = "prompt_latency.pkl"
    # decode_file_name = "decode_latency.pkl"
    # with open(prompt_file_name, "wb") as f:
    #     pickle.dump(prompt_latency_list, f)
    # with open(decode_file_name, "wb") as f:
    #     pickle.dump(decode_latency_list, f)


def main():
    """
    Finally, we can run the simulator to see how the model placement and request scheduling perform.
    """
    assert len(sys.argv) in (4, 5), (
        f"Usage: python {sys.argv[0]} <online/offline> "
        "<maxflow/swarm/random/shortest_queue> <offered_load_tokens_per_second> "
        "[duration_seconds]"
    )
    mode = sys.argv[1]
    scheduler = sys.argv[2]
    offered_load = float(sys.argv[3])
    duration = float(sys.argv[4]) if len(sys.argv) == 5 else 300

    if mode == "offline":
        if scheduler == "maxflow":
            # Scheduling method: Helix MaxFlow
            # Request arrival pattern: offline
            simulate_maxflow_offline()

        elif scheduler == "swarm":
            # Scheduling method: Swarm
            # Request arrival pattern: offline
            simulate_heuristic_offline(scheduling_method=SchedulingMethod.Swarm, initial_query_num=240)

        elif scheduler == "random":
            # Scheduling method: Random
            # Request arrival pattern: offline
            simulate_heuristic_offline(scheduling_method=SchedulingMethod.Naive, initial_query_num=240)

        elif scheduler == "shortest_queue":
            # Scheduling method: Shortest Queue
            # Request arrival pattern: offline
            simulate_heuristic_offline(scheduling_method=SchedulingMethod.ShortestQueue,
                                       initial_query_num=240)

        else:
            raise ValueError("Unknown scheduler!")

    elif mode == "online":
        if scheduler == "maxflow":
            # Scheduling method: Helix MaxFlow
            # Request arrival pattern: online
            simulate_maxflow_online(avg_throughput=offered_load, duration=duration)

        elif scheduler == "swarm":
            # Scheduling method: Swarm
            # Request arrival pattern: online
            simulate_heuristic_online(scheduling_method=SchedulingMethod.Swarm,
                                      avg_throughput=offered_load, duration=duration)

        elif scheduler == "random":
            # Scheduling method: Random
            # Request arrival pattern: online
            simulate_heuristic_online(scheduling_method=SchedulingMethod.Naive,
                                      avg_throughput=offered_load, duration=duration)

        elif scheduler == "shortest_queue":
            # Scheduling method: Shortest Queue
            # Request arrival pattern: online
            simulate_heuristic_online(scheduling_method=SchedulingMethod.ShortestQueue,
                                      avg_throughput=offered_load, duration=duration)

        else:
            raise ValueError("Unknown scheduler!")

    else:
        raise ValueError("Unknown mode!")


if __name__ == '__main__':
    main()
