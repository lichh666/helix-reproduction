# Helix quick offline comparison

Configuration: 5 s warm-up and 30 s measurement window, using the repository's precomputed ILP placement.

| Scheduler | Decode speed (tokens/s) | Prompt latency (s) | Decode latency (s) |
|---|---:|---:|---:|
| maxflow | 25.9 | 3.909 | 3.301 |
| swarm | 25.9 | 9.121 | 3.616 |
| random | 26.0 | 9.172 | 3.520 |

## Relative latency reduction from MaxFlow

- Versus swarm: prompt latency -57.1%, decode latency -8.7%.
- Versus random: prompt latency -57.4%, decode latency -6.2%.

This is a smoke test, not a paper-scale reproduction. The shortened horizon makes the scheduler's final total-throughput/theoretical-optimal lines unsuitable for efficiency calculations; compare the metrics from the common 25-55 s analysis window instead.
