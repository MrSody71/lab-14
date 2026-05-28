# Weather Pipeline — Architecture

## Overview

```
OpenWeatherMap (mock)
        │
        ▼
  Go Collector (collector/)
  ├── HTTP client → mock OWM server
  ├── etcd shard coordination
  ├── 1-minute tumbling windows
  └── Kafka + NATS dual sink
        │
        ├──────────────────────┐
        ▼                      ▼
  Redpanda (Kafka API)    NATS JetStream
        │                      │
        └──────────┬───────────┘
                   ▼
         Python Consumer (pipeline/)
         ├── Polars transforms
         ├── Rust validator (PyO3)
         ├── DuckDB analytics
         └── Parquet sink
                   │
                   ▼
        Arrow Flight Server (arrowsrv/)
                   │
                   ▼
        Streamlit Dashboard (dashboard/)
```

## Components

| Component | Language | Description |
|-----------|----------|-------------|
| `mock-owm/` | Go | Mock OpenWeatherMap HTTP server |
| `collector/` | Go | Weather data collector with sharding |
| `arrowsrv/` | Go | Apache Arrow Flight gRPC server |
| `validator/` | Rust + PyO3 | Data validation native extension |
| `pipeline/` | Python | Polars transforms, DuckDB, Parquet |
| `dashboard/` | Python | Streamlit real-time dashboard |

## Data Flow

1. **Collector** polls mock OWM every 30 s per city
2. **etcd** coordinates shard assignments across collector instances
3. **Aggregator** computes 1-minute tumbling windows (avg/min/max temp, humidity, pressure, wind)
4. **Dual sink** publishes to Redpanda (Kafka) and NATS JetStream simultaneously
5. **Python pipeline** consumes, validates via Rust, stores as Parquet
6. **Dashboard** reads Parquet or falls back to mock generator; live-updates every 5 s

## Dashboard Screenshots

### Full View
![Dashboard Full View](screenshots/dashboard-full.png)

### KPI Cards
![KPI Cards](screenshots/dashboard-kpi.png)

### Temperature Timeline
![Temperature Timeline](screenshots/dashboard-timeline.png)

### Comfort Gauges
![Comfort Gauges](screenshots/dashboard-gauges.png)

> **Note:** Screenshots above are placeholders.
> Run `cd dashboard && uv run streamlit run src/dashboard/app.py`
> to view the live dashboard at http://localhost:8501

## Kubernetes

See [kubernetes.md](kubernetes.md) for cluster setup and deployment instructions.
