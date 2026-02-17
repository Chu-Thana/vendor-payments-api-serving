# Superstore Analytics API

**Status:** Feature-complete backend prototype with production-style API design.

A production-style analytics backend built with FastAPI on a cleaned Superstore dataset.

This project demonstrates backend API design, validation strategies, pagination patterns, middleware logging, and clean architecture separation.

---

## 🚀 Tech Stack

- Python
- FastAPI
- Pydantic
- SQLite
- Git (feature branching workflow)

---

## 📂 Architecture

project2_api/
│
├── main.py # API layer & middleware
├── db.py # Aggregation & query logic
├── database.py # Database connection
├── schemas.py # Pydantic response models
└── .gitignore

---


### Architecture Principles

- Separation of concerns
- IO layer separated from business logic
- Strict response contract enforcement via Pydantic
- Deterministic pagination strategies

---

## 📊 Available Endpoints

### 1️⃣ Health Check
`GET /health/db`

Checks database connectivity and readiness.

---

### 2️⃣ Daily Sales
`GET /sales/daily`

Returns aggregated sales & profit for a specific date.

---

### 3️⃣ Monthly Sales (Offset / Page-based Pagination)
`GET /sales/monthly`

Supports:

- `limit`
- `page`
- `sort`
- `decimals`

---

### 4️⃣ Monthly Sales (Cursor-based Pagination)
`GET /sales/monthly/cursor`

Supports:

- cursor-based navigation
- `has_more` flag
- `next_cursor`
- `next_url`

Demonstrates deterministic key-based pagination without `OFFSET`.

---

### 5️⃣ Sales by Region
`GET /sales/by-region`

Grouped aggregation with:

- Offset / page-based pagination
- Sorting via Enum validation
- Explicit 400 vs 404 error handling

---

### 6️⃣ Sales by Category
`GET /sales/by-category`

Grouped aggregation with:

- Offset / page-based pagination
- Structured metadata response
- Deterministic error semantics

---

## ✨ Implemented Features

- Offset-based pagination
- Cursor-based pagination
- Enum-based sort validation
- Regex date validation (`YYYY-MM`, `YYYY-MM-DD`)
- Decimal precision control
- Structured Pydantic response models

### Response Metadata

- `generated_at`
- `query_ms`
- `count`
- `total_pages`
- `has_more`

### Explicit HTTP Semantics

- `400` → invalid input / page overflow
- `404` → no data for valid query
- `422` → validation errors

- Middleware execution logging (`etl_run_log`)
- Health check endpoint
- Feature branching & version tagging workflow

---

## 🧠 Middleware Logging

A request-level logging middleware records execution metadata into `etl_run_log`, including:

- execution timestamp
- HTTP status code
- processed row count
- execution time (ms)
- error details (if any)

This design enables observability, debugging, and production-style monitoring patterns.

---

## 📐 Design Decisions

- Offset pagination implemented for UI compatibility and simplicity.
- Cursor pagination implemented to demonstrate scalability trade-offs.
- Explicit 400 vs 404 distinction to enforce API contract clarity.
- Middleware logging added to simulate production observability patterns.

---

## 🎯 Learning Focus

This project emphasizes:

- API contract design
- Pagination strategy trade-offs (offset vs cursor)
- API error semantics (400 vs 404 vs 422 handling)
- Clean backend layering
- Monitoring-ready architecture
- Version-controlled development workflow

---

## 🔮 Future Improvements

- Docker containerization
- Cloud deployment (AWS / GCP)
- Authentication layer (JWT / API key)
- CI/CD integration
- Structured JSON logging
- Rate limiting
- OpenAPI documentation refinement

---

## 🏁 Portfolio Context

Built as part of an end-to-end Data Engineering portfolio:

ETL → Analytics API → (Cloud / Monitoring Layer)

This project represents the backend service layer of the pipeline.
