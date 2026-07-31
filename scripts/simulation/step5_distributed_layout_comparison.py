"""Run the layout comparison on the official three-cluster artifact."""
import step4_layout_comparison as comparison


BASE = "../../artifact_evaluation/model_placement"
comparison.COMPLETE_CLUSTER_FILE = f"{BASE}/config_distributed/3cluster24.ini"
comparison.MACHINE_PROFILE_FILE = f"{BASE}/config_distributed/machine_profiles.ini"
comparison.LAYOUT_FILES = {
    "helix": (
        f"{BASE}/layout_distributed/ilp/ilp_sol.ini",
        f"{BASE}/layout_distributed/ilp/simulator_cluster.ini",
    ),
    "petals": (
        f"{BASE}/layout_distributed/petals/petals_sol.ini",
        f"{BASE}/layout_distributed/petals/simulator_cluster.ini",
    ),
    "swarm": (
        f"{BASE}/layout_distributed/swarm/swarm_sol.ini",
        f"{BASE}/layout_distributed/swarm/simulator_cluster.ini",
    ),
}


if __name__ == "__main__":
    comparison.main()
