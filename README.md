# Superstore Analytics API

# Superstore Analytics API

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Production--Style-green)
![Docker](https://img.shields.io/badge/Docker-Enabled-blue)
![Redis](https://img.shields.io/badge/Cache-Redis-red)
![PostgreSQL](https://img.shields.io/badge/Logs-PostgreSQL-blue)

Production-style FastAPI analytics backend with Redis caching, PostgreSQL run logs, structured middleware observability, operational metrics, and containerized deployment.

---

## 🧠 Design Goals

This project simulates a production-ready analytics backend service.

Key objectives:

- Demonstrate production-style backend architecture
- Enforce strict API contracts with deterministic error semantics
- Implement structured request-level observability
- Apply measurable Redis caching strategies
- Separate analytics data layer from operational logging layer
- Prepare the codebase for containerized & cloud deployment

---

## 🚀 Tech Stack

- Python 3.11
- FastAPI
- Pydantic
- SQLite (analytics dataset)
- PostgreSQL (operational run logs & metrics)
- Redis (cache layer)
- Docker & Docker Compose
- Git (feature branching workflow)

---

## 📂 Project Structure

```text
superstore-fastapi-analytics/
│
├── main.py              # API layer & middleware
├── db.py                # Analytics query logic (SQLite)
├── db_pg.py             # Operational logging & metrics (PostgreSQL)
├── cache.py             # Redis cache abstraction
├── logging_setup.py     # Structured logging configuration
├── config.py            # Environment configuration
├── schemas.py           # Strict Pydantic response models
├── docker-compose.yml   # Multi-service orchestration
├── Dockerfile
└── requirements.txt
```

## 🏗 Architecture Overview

The system separates responsibilities into distinct layers:

### 1️⃣ Analytics Layer (SQLite)
- Aggregated sales queries
- Offset & cursor pagination strategies
- Deterministic sorting & validation

### 2️⃣ Operational Layer (PostgreSQL)
- Request execution logs (`api_run_log`)
- Latency tracking
- Error tracking
- Time-windowed metrics aggregation

### 3️⃣ Cache Layer (Redis)
- Read-through caching
- TTL-based expiration
- HIT / MISS / BYPASS / ERROR classification
- Cache metadata surfaced via response headers

### 4️⃣ Middleware Layer
- Request ID generation
- Execution timing (`request_ms`, `query_ms`)
- Structured log persistence
- Consistent SUCCESS / FAILED semantics

---

## 📊 Observability & Metrics

The API exposes operational metrics computed from PostgreSQL run logs.

### Endpoint

GET /metrics?window_minutes=60

### Returned Insights

- `requests_total`
- `success_total`
- `failed_total`
- `error_rate`
- `avg_request_ms`
- `p95_request_ms`
- Cache hit ratio
- Slowest endpoints ranking

This enables monitoring-style visibility without external APM tools.

---

## 📊 Available Endpoints

### Health

- GET /health/db
- GET /health/pg
- GET /health/cache

---

### Analytics

#### Daily Sales
GET /sales/daily

Returns aggregated sales & profit for a specific date.

---

#### Monthly Sales (Offset Pagination)
GET /sales/monthly

Supports:

- `limit`
- `page`
- `sort`
- `decimals`

---

#### Monthly Sales (Cursor Pagination)
GET /sales/monthly/cursor

- Deterministic key-based pagination
- `has_more`
- `next_cursor`
- `next_url`

Demonstrates scalable alternative to OFFSET.

---

#### Sales by Region
GET /sales/by-region

- Offset pagination
- Enum-based sort validation
- Explicit 400 vs 404 semantics

---

#### Sales by Category
GET /sales/by-category

- Deterministic pagination
- Structured metadata
- Contract-enforced validation

---

## 📦 Response Metadata

Analytics responses may include:

- `generated_at`
- `query_ms`
- `count`
- `total_pages`
- `has_more`

Response headers:

- `X-Request-ID`
- `X-Query-MS`
- `X-Cache`
- `X-Cache-Key`

---

## 🔍 Explicit HTTP Semantics

- 400 → invalid input / pagination overflow
- 404 → valid query but no data found
- 422 → schema validation error
- 500 → unexpected internal error

This enforces deterministic API contracts.

---

## 🐳 Deployment

Run locally with Docker:

```bash
docker compose up -d --build
```

Services started:

- FastAPI application
- PostgreSQL
- Redis

The architecture is container-ready and cloud-portable.

---

## 📐 Key Design Decisions

- Offset pagination implemented for UI compatibility.
- Cursor pagination implemented to demonstrate scalability trade-offs.
- Operational logs separated from analytics database.
- Middleware ensures logging never breaks user response.
- Cache strategy intentionally measurable via metrics endpoint.

---

## 🎯 Engineering Focus

This project emphasizes:

- Backend API contract design
- Observability-first architecture
- Pagination strategy trade-offs
- Measurable caching patterns
- Deterministic error handling
- Containerized service orchestration
- Production-style logging patterns

---

## 🔮 Future Improvements

- JWT authentication
- Rate limiting
- CI/CD pipeline
- OpenTelemetry integration
- Cloud deployment (AWS ECS / GCP Cloud Run)
- Prometheus / Grafana monitoring

---

## 🏁 Portfolio Context

Part of an end-to-end Data Engineering portfolio:

ETL → Analytics API → Operational Metrics → Cloud Deployment

This repository represents the backend service layer with production-grade observability and contract enforcement.
