# Changelog

## [0.1.0] — 2026-05-28

### Added
- Go mock OWM server with realistic data generation for 10 cities
- Go collector with etcd sharding and tumbling windows
- Apache Arrow Flight server (Go) + Python client
- Rust weather validator with PyO3 Python bindings
- Python analyzer: Polars transforms + DuckDB analytics
- 5 visualizations: timeline, histogram, heatmap, perf, comfort
- asyncio reference collector for benchmarking
- Go vs Python asyncio benchmark with 4 plots
- Kubernetes manifests + HPA (autoscaling/v2)
- kind cluster setup scripts
- Streamlit dashboard with live updates
- Complete prompt log (prompts/00-09)

### Architecture
- Fanout sink: simultaneous publish to Kafka + NATS
- Shared Parquet volume between analyzer and dashboard
- Arrow Flight RPC for zero-copy data transfer
- etcd lease-based shard registration (TTL 15s, keepalive 5s)
