# Helix Figure 10 scheduler reproduction

All schedulers use the same Helix ILP model placement and seed 0. MaxFlow starts with 20 queries. Following the official artifact, single-cluster heuristics start with 240 and distributed heuristics with 180 queries.

| Topology | Scheduler | Decode tok/s | Total tok/s | Prompt latency | Decode latency | Completed queries |
|---|---|---:|---:|---:|---:|---:|
| single | MaxFlow | 249.0 | 1148.0 | 3.235s | 1.556s | 299 |
| single | Swarm | 189.7 | 742.8 | 2.732s | 1.255s | 219 |
| single | Random | 199.4 | 739.2 | 2.684s | 1.194s | 214 |
| distributed | MaxFlow | 99.8 | 552.1 | 9.444s | 2.484s | 220 |
| distributed | Swarm | 81.7 | 412.9 | 31.173s | 2.133s | 181 |
| distributed | Random | 87.4 | 424.5 | 32.867s | 2.002s | 182 |
| distributed | Shortest Queue | 83.6 | 430.7 | 33.679s | 2.080s | 186 |

## Paper ratio check

| Topology | Comparison | Reproduced | Paper | Deviation |
|---|---|---:|---:|---:|
| single | MaxFlow / Swarm | 1.31x | 1.30x | +1.0% |
| single | MaxFlow / Random | 1.25x | 1.29x | -3.2% |
| distributed | MaxFlow / Swarm | 1.22x | 1.22x | +0.1% |
| distributed | MaxFlow / Random | 1.14x | 1.15x | -0.7% |
| distributed | MaxFlow / Shortest Queue | 1.19x | 1.19x | +0.3% |

## Interpretation

- Every reproduced speedup ratio is within 3.2% of the paper value.
- In the distributed topology, heuristic schedulers have 31-34 s prompt latency versus 9.4 s for MaxFlow, reproducing the congestion behavior discussed in the paper.
- Lower decode latency for some heuristics does not imply higher system throughput: they leave more capacity under-utilized, while MaxFlow completes more decode work and more full queries.
