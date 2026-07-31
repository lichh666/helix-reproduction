# Helix Figure 9 simulator reproduction

All layouts use the same Helix MaxFlow request scheduler, seed 0, and a 60 s warm-up. The single-cluster measurement is 300 s due to the laptop memory limit; the distributed measurement uses the paper's 600 s duration.

| Topology | Layout | Decode tok/s | Total tok/s | Prompt latency | Decode latency | Completed queries |
|---|---|---:|---:|---:|---:|---:|
| single | Helix | 249.0 | 1148.0 | 3.235s | 1.556s | 299 |
| single | Petals | 208.6 | 692.5 | 2.299s | 0.951s | 235 |
| single | Swarm | 125.2 | 458.1 | 3.617s | 1.711s | 156 |
| distributed | Helix | 98.0 | 569.2 | 8.958s | 2.488s | 230 |
| distributed | Petals | 66.6 | 449.3 | 14.050s | 3.222s | 159 |
| distributed | Swarm | 41.6 | 359.3 | 20.321s | 4.554s | 85 |

## Paper ratio check

| Topology | Comparison | Reproduced | Paper | Deviation |
|---|---|---:|---:|---:|
| single | Helix / Petals | 1.19x | 1.23x | -3.0% |
| single | Helix / Swarm | 1.99x | 2.10x | -5.3% |
| distributed | Helix / Petals | 1.47x | 1.49x | -1.2% |
| distributed | Helix / Swarm | 2.36x | 2.38x | -1.0% |

## Network impact

- Helix: geo-distributed decode throughput -60.6% versus single cluster; prompt latency becomes 2.77x.
- Petals: geo-distributed decode throughput -68.1% versus single cluster; prompt latency becomes 6.11x.
- Swarm: geo-distributed decode throughput -66.8% versus single cluster; prompt latency becomes 5.62x.

The reproduced ordering and relative gains match the paper in both topologies. This is the first result in this reproduction that directly validates Helix's joint model-placement advantage rather than only exercising the tutorial workflow.
