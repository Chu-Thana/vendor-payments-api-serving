# Vendor Payments API Serving

FastAPI serving layer for trusted Vendor Payments batch and streaming analytics data.

This project is part of the Vendor Payments Data Engineering Portfolio.

## Architecture

![Vendor Payments API Serving Architecture](assets/vendor-payments-api/streaming/00_vendor-payments-api-serving-architecture.png)

```text
Analytics Consumers
        ↓ Request
Middleware Layer
Request ID • Request Timing • Structured Logging
        ↓
FastAPI Endpoint Layer
        ↓
Cache Layer
Cache HIT → Return cached response
Cache MISS → Continue processing
        ↓
Service Layer
        ↓
Repository Layer
        ↓
Analytics Data Sources

Analytics Data Sources
        ↑ Returned Data
Repository Layer
        ↑
Service Layer
        ↑
Cache Layer
Store successful response with TTL
        ↑
FastAPI Endpoint Layer
        ↑
Middleware Layer
Response Headers • Completion Logging
        ↑ JSON Response
Analytics Consumers
```

API contracts are enforced at the FastAPI boundary through Pydantic models, query validation, and OpenAPI documentation.

The middleware layer provides request tracking, request timing, structured completion logs, and structured error logs for all API requests.

The cache layer uses an in-memory cache-aside strategy to reuse successful Batch and Streaming API responses. Cache entries expire after 60 seconds, and cache behavior is exposed through the `X-Cache-Status` response header.

Project-wide quality checks are provided by Pytest, Ruff, Docker builds, and GitHub Actions CI.

## Current Features

- FastAPI application
- Root, health, and metadata endpoints
- Batch analytics endpoints backed by trusted Gold marts
- Streaming event and analytics summary endpoints
- Pydantic request and response validation
- Fiscal year and text-based filtering
- Limit and offset pagination
- Request ID generation and propagation
- API request processing-time measurement
- Structured request completion logging
- Structured unhandled-error logging
- Observability response headers
- Runtime capability metadata
- In-memory API response caching
- Cache-aside request flow
- TTL-based cache expiration
- Stable cache keys built from endpoint query parameters
- Cache HIT and MISS response headers
- Batch and Streaming endpoint cache coverage
- Swagger/OpenAPI documentation
- Docker container support
- Pytest automated tests
- Ruff linting
- GitHub Actions CI

## Middleware Observability

Every API request passes through the observability middleware before reaching the endpoint layer.

The middleware provides:

- A unique request ID for request tracing
- Preservation of a client-provided request ID
- API processing-time measurement
- Structured JSON logs for completed requests
- Structured JSON logs for unhandled errors
- Response headers for request tracking and performance inspection

### Response Headers

Successful API responses include:

```text
X-Request-ID
X-Process-Time-MS
```

Example:

```text
X-Request-ID: c31a25fa-e360-411d-9415-c6588feb3d7c
X-Process-Time-MS: 0.51
```

When a client sends an `X-Request-ID` header, the API preserves that value and returns it in the response. If no request ID is provided, the middleware generates a new UUID.

### Structured Completion Log

Example:

```json
{
  "event": "api_request_completed",
  "request_id": "c31a25fa-e360-411d-9415-c6588feb3d7c",
  "method": "GET",
  "path": "/health",
  "status_code": 200,
  "process_time_ms": 0.51
}
```

### Structured Error Log

Unhandled exceptions are logged with request context before the exception is re-raised for application-level handling.

Example:

```json
{
  "event": "api_request_error",
  "request_id": "error-test-001",
  "method": "GET",
  "path": "/raise-error",
  "process_time_ms": 1.24
}
```

## API Response Cache

The API uses an in-memory cache-aside strategy for Batch and Streaming analytics endpoints.

Request flow:

```text
API Request
    ↓
Build cache key from endpoint and query parameters
    ↓
Cache lookup
    ├── HIT  → Return cached response
    └── MISS → Call Service Layer
                  ↓
              Store successful result with TTL
                  ↓
              Return response
```

### Cache Behavior

- Cache backend: In-memory Python cache
- Cache strategy: Cache-aside
- Default TTL: 60 seconds
- Cached responses: Successful Batch and Streaming analytics responses
- Invalid requests: Not cached
- Server errors: Not cached
- Query-aware keys: Filters, limits, and offsets are included in cache keys
- Text normalization: Text parameters are trimmed and case-normalized

### Cache Response Header

Cached endpoints include:

```text
X-Cache-Status
```

Possible values:

```text
MISS
HIT
```

Example first request:

```text
X-Cache-Status: MISS
```

Example identical request within the TTL:

```text
X-Cache-Status: HIT
```

The response also retains the observability headers:

```text
X-Request-ID
X-Process-Time-MS
X-Cache-Status
```

### Current Limitations

The current cache is process-local and is cleared whenever the API process restarts. It is suitable for local development and demonstrating cache behavior, but it is not shared between multiple API instances.

Redis-backed shared caching remains a planned production improvement.

## API Endpoints

### Core APIs

#### Root

```http
GET /
```

#### Health

```http
GET /health
```

#### Metadata

```http
GET /api/v1/metadata
```

Returns service information, data availability, and enabled runtime capabilities.

Example response:

```json
{
  "service": "Vendor Payments API",
  "version": "1.0.0",
  "batch_data_available": true,
  "streaming_data_available": true,
  "middleware_enabled": true,
  "request_id_enabled": true,
  "request_timing_enabled": true,
  "structured_logging_enabled": true,
  "cache_enabled": true
}
```

## Batch Analytics

### Spending by Fiscal Year

```http
GET /api/v1/batch/spending-by-fiscal-year
```

Returns trusted spending metrics aggregated by fiscal year.

### Spending by Department

```http
GET /api/v1/batch/spending-by-department
```

Supported query parameters:

- `fiscal_year`
- `department`
- `limit`
- `offset`

Example:

```http
GET /api/v1/batch/spending-by-department?fiscal_year=2007&limit=5
```

### Top Suppliers

```http
GET /api/v1/batch/top-suppliers
```

Supported query parameters:

- `supplier_name`
- `limit`
- `offset`

Example:

```http
GET /api/v1/batch/top-suppliers?supplier_name=BANK&limit=10
```

### Pending by Department

```http
GET /api/v1/batch/pending-by-department
```

Supported query parameters:

- `fiscal_year`
- `department`
- `limit`
- `offset`

Example:

```http
GET /api/v1/batch/pending-by-department?department=Public%20Health&limit=5
```

### Fund Category Summary

```http
GET /api/v1/batch/fund-category-summary
```

Supported query parameters:

- `fiscal_year`
- `fund_type`
- `fund_category`
- `limit`
- `offset`

Example:

```http
GET /api/v1/batch/fund-category-summary?fund_type=General%20Fund&fund_category=Operating&limit=5
```

## Streaming Analytics

### Streaming Events

```http
GET /api/v1/streaming/events
```

Returns paginated vendor payment events from the validated streaming sample dataset.

Supported query parameters:

- `fiscal_year`
- `department`
- `supplier_name`
- `dedup_status`
- `limit`
- `offset`

Example:

```http
GET /api/v1/streaming/events?fiscal_year=2021&supplier_name=ERIE&limit=5
```

### Streaming Summary

```http
GET /api/v1/streaming/summary
```

Returns dashboard-ready streaming metrics, including:

- Total event count
- Total payment amount
- Unique department count
- Unique supplier count
- Minimum and maximum fiscal year
- Event counts grouped by fiscal year
- Event counts grouped by deduplication status

### Department Summary

```http
GET /api/v1/streaming/department-summary
```

Returns department-level streaming metrics.

Supported query parameters:

- `fiscal_year`
- `department`
- `limit`
- `offset`

Example:

```http
GET /api/v1/streaming/department-summary?fiscal_year=2021&limit=5
```

### Supplier Summary

```http
GET /api/v1/streaming/supplier-summary
```

Returns supplier-level streaming metrics.

Supported query parameters:

- `fiscal_year`
- `supplier_name`
- `limit`
- `offset`

Example:

```http
GET /api/v1/streaming/supplier-summary?supplier_name=MEDLINE%20INDUSTRIES%20INC&limit=5
```

## Project Structure

```text
vendor-payments-api-serving/
│
├── app/
│   ├── main.py
│   ├── config.py
│   │
│   ├── api/
│   │   ├── health.py
│   │   ├── metadata.py
│   │   ├── batch.py
│   │   └── streaming.py
│   │
│   ├── cache/
│   │   ├── __init__.py
│   │   ├── in_memory.py
│   │   └── keys.py
│   │
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── observability.py
│   │
│   ├── models/
│   │   ├── common.py
│   │   ├── batch.py
│   │   └── streaming.py
│   │
│   ├── repositories/
│   │   ├── batch_repository.py
│   │   └── streaming_repository.py
│   │
│   └── services/
│       ├── batch_service.py
│       └── streaming_service.py
│
├── assets/
│   └── vendor-payments-api/
│       ├── batch/
│       └── streaming/
│
├── data/
│   ├── batch/
│   │   ├── mart_spending_by_fiscal_year.csv
│   │   ├── mart_spending_by_department.csv
│   │   ├── mart_spending_by_supplier_top_n.csv
│   │   ├── mart_pending_by_department.csv
│   │   └── mart_fund_category_summary.csv
│   │
│   └── streaming/
│       └── vendor_payments_streaming_sample.jsonl
│
├── tests/
│   ├── test_health.py
│   ├── test_metadata.py
│   ├── test_middleware.py
│   ├── test_cache.py
│   ├── test_batch_endpoints.py
│   └── test_streaming_endpoints.py
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Run Locally

Create and activate the virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run the API:

```powershell
python -m uvicorn app.main:app --reload
```

Open Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

Open the health endpoint:

```text
http://127.0.0.1:8000/health
```

## Run with Docker

Build and start the API container:

```powershell
docker compose up --build
```

Open Swagger documentation:

```text
http://localhost:8000/docs
```

Open the health endpoint:

```text
http://localhost:8000/health
```

Stop the container:

```powershell
docker compose down
```

## Validation

Run the automated test suite:

```powershell
python -m pytest -v
```

Run Ruff:

```powershell
python -m ruff check app tests
```

Build the Docker image:

```powershell
docker build -t vendor-payments-api-serving:test .
```

Current validation covers:

- Root, health, and metadata endpoints
- Batch analytics endpoints
- Streaming events and summary endpoints
- Fiscal year and text filters
- Combined filters
- Limit and offset pagination
- Invalid pagination responses
- Expected JSON response structures
- Request ID response headers
- Client-provided request ID preservation
- Request processing-time headers
- Unique generated request IDs
- Structured successful-request logging
- Structured unhandled-error logging
- Middleware capability metadata
- In-memory cache storage and retrieval
- TTL expiration behavior
- Stable and normalized cache keys
- Cache MISS followed by HIT for identical requests
- Different query parameters creating separate cache entries
- Invalid requests not being cached
- Batch and Streaming cache coverage
- Cache capability metadata

Current local validation result:

```text
57 tests passed
Ruff passed
```

## Continuous Integration

GitHub Actions validates the project by running:

```text
Ruff
→ Pytest
→ Docker image build
```

## Planned Development

- Redis-backed shared cache
- Cache invalidation and administration controls
- Power BI integration
- Browser-based web dashboard
- Cloud-backed data source integration
- Production deployment
- API authentication and authorization
- Rate limiting
- Centralized monitoring and observability

## Portfolio Integration

This API acts as the serving layer for the wider Vendor Payments Data Engineering Portfolio:

```text
Project 1 — Batch ETL Pipeline
Project 2 — API and Serving Layer
Project 3 — Kafka Streaming Pipeline
Project 4 — Airflow Orchestration
Project 5 — Cloud Data Platform
```

The goal is to expose trusted analytics-ready data to Power BI, web dashboards, and other external consumers without requiring them to read local files or cloud storage objects directly.
