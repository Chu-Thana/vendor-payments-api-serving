# Vendor Payments API Serving

FastAPI serving layer for trusted Vendor Payments batch and streaming analytics data.

This project is part of the Vendor Payments Data Engineering Portfolio.

## Current Architecture
→ FastAPI
→ JSON Responses
→ Power BI
→ Web Dashboard
```

## Current Features

- FastAPI application
- Health and metadata endpoints
- Batch analytics endpoints backed by trusted Gold marts
- Pydantic request and response validation
- Fiscal year and text-based filtering
- Limit and offset pagination
- Swagger API documentation
- Docker container
- Pytest
- Ruff
- GitHub Actions CI

## API Endpoints

### Root

```http
GET /
```

### Health

```http
GET /health
```

### Metadata

```http
GET /api/v1/metadata
```

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

* `fiscal\_year`
* `department`
* `limit`
* `offset`

Example:

```http
GET /api/v1/batch/spending-by-department?fiscal\_year=2007\&limit=5
```

### Top Suppliers

```http
GET /api/v1/batch/top-suppliers
```

Supported query parameters:

* `supplier\_name`
* `limit`
* `offset`

Example:

```http
GET /api/v1/batch/top-suppliers?supplier\_name=BANK\&limit=10
```

### Pending by Department

```http
GET /api/v1/batch/pending-by-department
```

Supported query parameters:

* `fiscal\_year`
* `department`
* `limit`
* `offset`

Example:

```http
GET /api/v1/batch/pending-by-department?department=Public%20Health\&limit=5
```

### Fund Category Summary

```http
GET /api/v1/batch/fund-category-summary
```

Supported query parameters:

* `fiscal\_year`
* `fund\_type`
* `fund\_category`
* `limit`
* `offset`

Example:

```http
GET /api/v1/batch/fund-category-summary?fund\_type=General%20Fund\&fund\_category=Operating\&limit=5
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
│   │   └── batch.py
│   │
│   ├── models/
│   │   ├── common.py
│   │   └── batch.py
│   │
│   ├── repositories/
│   │   └── batch_repository.py
│   │
│   └── services/
│       └── batch_service.py
│
├── data/
│   └── batch/
│       ├── mart_spending_by_fiscal_year.csv
│       ├── mart_spending_by_department.csv
│       ├── mart_spending_by_supplier_top_n.csv
│       ├── mart_pending_by_department.csv
│       └── mart_fund_category_summary.csv
│
├── tests/
│   ├── test_health.py
│   ├── test_metadata.py
│   └── test_batch_endpoints.py
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

## Run Tests

```powershell
python -m pytest -v
```

Current foundation tests cover:

* Root endpoint
* Health endpoint
* HTTP status codes
* Expected JSON response structures

## Run Ruff

```powershell
python -m ruff check app tests
```

## Continuous Integration

GitHub Actions validates the project by running:

```text
Ruff
→ Pytest
→ Docker image build
```

## Planned Development

- Streaming analytics endpoints
- API response metadata improvements
- Power BI integration
- Browser-based web dashboard
- Cloud-backed data source integration
- Production deployment and monitoring

## Portfolio Integration

This API acts as the serving layer for the wider Vendor Payments Data Engineering Portfolio:

```text
Project 1 — Batch ETL Pipeline
Project 2 — API and Serving Layer
Project 3 — Kafka Streaming Pipeline
Project 4 — Airflow Orchestration
Project 5 — Cloud Data Platform
```

The final goal is to expose trusted analytics-ready data to Power BI, web dashboards, and other external consumers without requiring them to read local files or cloud storage objects directly.
