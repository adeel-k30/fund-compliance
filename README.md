# Fund Compliance Platform

A regulatory data validation API for financial instrument submissions. It validates EMT (European MiFID Template) fund data files against configurable compliance rules, processes them asynchronously, and returns structured reports of any issues found.

## What It Does

1. A client uploads a CSV or Excel file via the REST API
2. The file is stored in S3 and a Celery task is queued
3. The rule engine validates each row against EMT field rules (format, allowed values, mandatory/conditional fields)
4. Validation issues are persisted to PostgreSQL
5. The client polls for status and retrieves the report

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| Database | PostgreSQL (async via asyncpg + SQLAlchemy 2.0) |
| Migrations | Alembic |
| Task queue | Celery 5 + Redis |
| File storage | AWS S3 (LocalStack for local dev) |
| Auth | JWT (OAuth2 password flow) + bcrypt |
| Data parsing | Pandas + openpyxl |

## Project Structure

```
app/
├── main.py                  # App entry point, loads EMT rules at startup
├── core/
│   └── config.py            # Pydantic BaseSettings (reads from .env)
├── db/
│   ├── models.py            # SQLAlchemy ORM models
│   ├── session.py           # Async engine and session factory
│   ├── deps.py              # FastAPI dependencies (get_db, get_current_user)
│   └── repositories/        # CRUD layer (User, Client, Upload)
├── models/
│   ├── rules.py             # Pydantic models for rule definitions
│   └── validation.py        # Pydantic models for validation results
├── routers/
│   ├── auth.py              # POST /auth/register, POST /auth/token
│   ├── validation.py        # POST /validate/emt, GET /validate/uploads/...
│   └── client.py            # GET /clients/{client_id}
├── services/
│   ├── rule_engine.py       # Core validation logic
│   ├── file_parser.py       # CSV/Excel parsing, strips columns to 5-digit codes
│   ├── s3_service.py        # S3 upload/download/delete
│   └── auth.py              # Password hashing, JWT creation/verification
└── worker/
    ├── celery_app.py        # Celery app config (Redis broker/backend)
    └── tasks.py             # validate_emt_file Celery task
tests/
└── conftest.py              # Async test client
data/
└── emt_rules.json           # EMT field rule definitions
```

## API Endpoints

### Auth

```
POST /auth/register
  Body: { organisation_name, email, password }
  Creates a new client and user account.

POST /auth/token
  Body: { username (email), password }  [OAuth2 form]
  Returns: { access_token, token_type: "bearer" }
```

### Validation

All validation endpoints require `Authorization: Bearer <token>`.

```
POST /validate/emt
  Body: multipart/form-data — file (.csv, .xlsx, .xls), delimiter (optional, default ",")
  Returns: { upload_id, task_id, message }
  Status: 202 Accepted

GET /validate/uploads
  Query: skip (default 0), limit (default 20)
  Returns: list of upload summaries

GET /validate/uploads/{upload_id}
  Returns: upload detail record

GET /validate/uploads/{upload_id}/status
  Returns: { upload_id, status, task_id, total_rows, rows_with_issues, message }
  Statuses: pending | processing | complete | failed
```

### System

```
GET /          Returns API info and link to docs
GET /health    Returns service health status
```

Interactive docs are available at `/docs` when the server is running.

## Setup

### Prerequisites

- Python 3.13+
- PostgreSQL
- Redis
- AWS S3 or LocalStack (for local development)

### Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configure

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

Key variables:

```env
DATABASE_URL=postgresql+asyncpg://funduser:password@localhost:5433/fundcompliance
REDIS_URL=redis://localhost:6379/0
S3_BUCKET_NAME=fund-compliance-uploads

# Leave set for LocalStack local dev; remove for real AWS
S3_ENDPOINT_URL=http://localhost:4566

JWT_SECRET_KEY=your-secret-key
JWT_EXPIRY_MINUTES=30
```

### Run Migrations

```bash
alembic upgrade head
```

### Start the API

```bash
uvicorn app.main:app --reload
```

### Start the Celery Worker

In a separate terminal:

```bash
celery -A app.worker.celery_app worker --loglevel=info
```

## Running Tests

Tests use an in-memory SQLite database and do not require external services.

```bash
pytest                          # Run all tests
pytest -v                       # Verbose output
pytest --cov=app                # With coverage report
```

## EMT Rule Engine

Rules are loaded from `data/emt_rules.json` at startup. Each rule defines:

- `field_code` — 5-digit EMT field identifier
- `field_type` — one of `string`, `integer`, `decimal`, `percentage`, `date`, `datetime`, `boolean`, `isin`, `lei`
- `rule_type` — `format`, `allowed_values`, `expect_value`, `expect_empty`, or `custom`
- `allowed_values` — optional list of permitted values
- `condition` — optional conditional logic (supports `eq`, `neq`, `in_set`, `not_in_set`, `is_empty`, `is_not_empty`, `and`, `or`)

Validation issues are stored per row with the field code, rule type, and a human-readable message.