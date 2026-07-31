# Helix equal-load online sweep

Configuration: offered loads of 400, 700, and 1000 tokens/s; seed 0; 300 s duration; identical precomputed ILP placement.

| Load | Scheduler | Decode speed (tokens/s) | Prompt latency (s) | Decode latency (s) |
|---:|---|---:|---:|---:|
| 400 | maxflow | 45.3 | 2.387 | 0.859 |
| 400 | swarm | 46.8 | 2.428 | 0.829 |
| 400 | random | 48.0 | 2.389 | 0.810 |
| 700 | maxflow | 64.9 | 2.468 | 1.191 |
| 700 | swarm | 67.4 | 2.535 | 1.150 |
| 700 | random | 67.5 | 2.509 | 1.137 |
| 1000 | maxflow | 76.8 | 2.657 | 1.521 |
| 1000 | swarm | 80.2 | 2.749 | 1.436 |
| 1000 | random | 80.8 | 2.702 | 1.415 |

## MaxFlow versus Random at each load

- 400 tokens/s: decode speed -5.6%, prompt latency -0.1%, decode latency +6.0%.
- 700 tokens/s: decode speed -3.9%, prompt latency -1.6%, decode latency +4.7%.
- 1000 tokens/s: decode speed -5.0%, prompt latency -1.7%, decode latency +7.5%.

No decode-speed crossover was observed through 1000 tokens/s: Random remained 3.9-5.6% faster in this metric, while MaxFlow generally had slightly lower prompt latency and higher decode latency.

The discrepancy with the saturated offline example is methodologically important. The repository's offline paths use different initial query counts for MaxFlow and heuristics, so the offline throughput gap cannot be attributed only to the scheduler. Under matched online arrival processes, the three schedulers remain close through this range.

The logs expose decode-token throughput, not total prompt-plus-decode throughput. Before extending beyond 1000 tokens/s, the next instrumentation step should add a common total-token-throughput metric so the MaxFlow objective is measured directly.
