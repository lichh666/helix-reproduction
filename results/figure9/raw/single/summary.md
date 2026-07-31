# Helix model-placement comparison

Configuration: LLaMA-70B, single 24-node heterogeneous cluster, offline saturated serving, MaxFlow scheduler for every layout, seed 0, 60 s warm-up and 300 s measurement.

| Layout | Static max flow | Decode tok/s | Total tok/s | Prompt latency | Decode latency | Completed queries |
|---|---:|---:|---:|---:|---:|---:|
| Helix | 1289.6 | 249.0 | 1148.0 | 3.235s | 1.556s | 299 |
| Petals | 952.1 | 208.6 | 692.5 | 2.299s | 0.951s | 235 |
| Swarm | 757.9 | 125.2 | 458.1 | 3.617s | 1.711s | 156 |
| Homogeneous* | 531.7 | 182.9 | 584.6 | 1.690s | 0.993s | 200 |

## Reproduction check against paper Figure 9

- Helix / Petals decode-throughput ratio: **1.19x**; paper reports **1.23x** (ratio deviation -3.0%).
- Helix / Swarm decode-throughput ratio: **1.99x**; paper reports **2.10x** (ratio deviation -5.3%).

The key ordering and scale are reproduced: Helix > Petals > Swarm under the same scheduler. The measurement window is 300 s instead of the paper's 600 s because the laptop previously exhausted memory near 430 s.

*Homogeneous is an additional repository layout and is not one of the three bars in the paper's Figure 9 placement deep dive.
