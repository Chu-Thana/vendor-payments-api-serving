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

* FastAPI application
* Health endpoint
* Root endpoint
* Pydantic response model
* Swagger API documentation
* Docker container
* Pytest
* Ruff
* GitHub Actions CI

## API Endpoints

### Root

```http
GET /
```

Example response:

```json
{
  "message": "Vendor Payments API is running",
  "docs": "/docs"
}
```

### Health

```http
GET /health
```

Example response:

```json
{
  "status": "healthy",
  "service": "vendor-payments-api"
}
```

## Project Structure

```text
vendor-payments-api-serving/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── health.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── common.py
│   │
│   ├── repositories/
│   │   └── __init__.py
│   │
│   └── services/
│       └── __init__.py
│
├── tests/
│   └── test_health.py
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── .dockerignore
├── .gitignore
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

The next development phases will add:

* API metadata endpoint
* Batch analytics endpoints
* Streaming analytics endpoints
* Query filtering
* Offset pagination
* Predictable response schemas
* Power BI integration
* Browser-based web dashboard

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
