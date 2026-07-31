# Helix medium offline comparison

Configuration: 60 s warm-up and 300 s measurement window, using the repository's precomputed ILP placement.

| Scheduler | Decode speed (tokens/s) | Prompt latency (s) | Decode latency (s) |
|---|---:|---:|---:|
| maxflow | 249.0 | 3.235 | 1.556 |
| swarm | 189.7 | 2.732 | 1.255 |
| random | 199.4 | 2.684 | 1.194 |

## MaxFlow relative to baselines

- Versus swarm: decode speed +31.3%, prompt latency +18.4%, decode latency +24.0%.
- Versus random: decode speed +24.9%, prompt latency +20.5%, decode latency +30.3%.

Interpretation: under this sustained offline load, MaxFlow achieves higher decode throughput while accepting higher average latency. This is a throughput-latency trade-off, not an across-the-board improvement.

The official example initializes MaxFlow and heuristic schedulers with different initial query counts. Treat this as a reproduction of the repository's example settings; a strictly controlled scheduler comparison should align the offered load in a follow-up experiment.

The original 600 s measurement run exceeded the current WSL memory limit and was killed near simulation time 430 s. This 300 s measurement run completed successfully.
