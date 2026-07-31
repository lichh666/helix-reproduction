# Helix equal-load online comparison

Configuration: identical 400 tokens/s offered load, seed 0, 300 s duration, and precomputed ILP placement for every scheduler.

| Scheduler | Decode speed (tokens/s) | Prompt latency (s) | Decode latency (s) |
|---|---:|---:|---:|
| maxflow | 45.3 | 2.387 | 0.859 |
| swarm | 46.8 | 2.428 | 0.829 |
| random | 48.0 | 2.389 | 0.810 |

## MaxFlow relative to baselines

- Versus swarm: decode speed -3.2%, prompt latency -1.7%, decode latency +3.6%.
- Versus random: decode speed -5.6%, prompt latency -0.1%, decode latency +6.0%.

Interpretation: 400 tokens/s is about 31% of the MaxFlow bound (1289.56 tokens/s). At this moderate offered load, all schedulers are close and MaxFlow has no throughput advantage. This complements the saturated offline result, where MaxFlow improved decode throughput by roughly 25-31% while trading higher latency.

A load sweep is the appropriate next experiment to locate the point where MaxFlow begins to outperform the heuristic schedulers.
