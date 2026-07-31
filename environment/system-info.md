# Reproduction environment

Recorded on 2026-07-31.

| Component | Value |
|---|---|
| Host | Windows laptop |
| Linux environment | Ubuntu 22.04 on WSL2 |
| WSL kernel | 6.6.87.2-microsoft-standard-WSL2 |
| Python | 3.12.3 |
| Git | 2.43.0 |
| WSL memory | 7.6 GiB |
| WSL swap | 2.0 GiB |
| GPU | No GPU used; simulator-only reproduction |
| Helix commit | `8639497a4aaf1eb3b7594614cb0bbd376c1342b3` |
| Gurobi | 11.0.3; local license expired on 2025-11-24 |

Important packages:

```text
gurobipy==11.0.3
matplotlib==3.8.4
networkx==3.2.1
numpy==1.26.4
```

The official 42-node, 660-second simulation retained enough event history to exhaust the 7.6 GiB WSL memory allocation. It was stopped before OOM and replaced by a short diagnostic run plus the official precomputed artifact result.
