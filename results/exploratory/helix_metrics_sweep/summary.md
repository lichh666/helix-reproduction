# Helix unified online serving metrics

Configuration: online arrivals, seed 0, 300 s duration, identical ILP placement and identical offered trace for each scheduler.

| Load | Scheduler | Prompt tok/s | Decode tok/s | Total tok/s | Service ratio | Completed / Issued | Prompt latency | Decode latency |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 700 | maxflow | 504.9 | 64.9 | 569.8 | 86.092% | 76 / 208 | 2.468s | 1.191s |
| 700 | swarm | 504.9 | 67.4 | 572.3 | 86.467% | 74 / 208 | 2.535s | 1.150s |
| 700 | random | 504.9 | 67.5 | 572.3 | 86.474% | 74 / 208 | 2.509s | 1.137s |
| 1000 | maxflow | 753.4 | 76.8 | 830.2 | 84.579% | 83 / 291 | 2.657s | 1.521s |
| 1000 | swarm | 753.4 | 80.2 | 833.6 | 84.924% | 89 / 291 | 2.749s | 1.436s |
| 1000 | random | 753.4 | 80.8 | 834.2 | 84.995% | 87 / 291 | 2.702s | 1.415s |

## MaxFlow versus Random

- Load 700: total throughput -0.44%, service ratio -0.382 percentage points, completed queries +2, prompt latency -1.63%, decode latency +4.75%.
- Load 1000: total throughput -0.48%, service ratio -0.416 percentage points, completed queries -4, prompt latency -1.67%, decode latency +7.49%.

## Interpretation

- Prompt throughput is identical across schedulers at each load, confirming that all methods receive and finish the same prompt work in this 300 s window.
- Once prompt and decode work are combined, scheduler throughput differences are much smaller than the decode-only comparison suggests.
- The end-of-run completion rate is a finite-window backlog indicator, not a request success rate: active queries are unfinished at the cutoff, not failed.
- These runs compare schedulers under one fixed ILP placement. They do not reproduce the paper's placement comparison, topology sweep, model sweep, or real multi-GPU deployment.
