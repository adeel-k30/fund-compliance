# Fund Compliance Platform

A regulatory data validation API for fund submissions. Clients upload an EMT
(European MiFID Template) file; it's stored in S3, validated in the background
against configurable compliance rules, and the results are saved and polled for.

## How it works

1. A client registers and logs in to get a JWT.
2. They `POST` a CSV/Excel file to `/validate/emt`.
3. The API stores the file in S3, writes a `pending` upload record, and queues a
   Celery job. It returns `202` immediately with an `upload_id` and `task_id`.
4. A separate Celery worker downloads the file, runs the rule engine, saves any
   issues, and marks the upload `complete`.
5. The client polls `/validate/uploads/{id}/status` for progress and results.

Everything is scoped to a `client_id` (the tenant), so one customer can never
see another's uploads.

## Tech stack

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn (async) |
| Worker | Celery 5 + Redis |
| Database | PostgreSQL — async (asyncpg) for the API, sync (psycopg2) for the worker |
| Migrations | Alembic |
| File storage | S3 (LocalStack locally) |
| Auth | JWT (OAuth2 password flow) + bcrypt |
| Parsing | Pandas + openpyxl |

## Project structure

```
app/
├── main.py                  # App entry point; loads EMT rules at startup
├── core/config.py           # Settings (reads from .env)
├── db/
│   ├── models.py            # SQLAlchemy ORM models
│   ├── session.py           # Async + sync engines and session factories
│   ├── deps.py              # get_db, get_current_user
│   └── repositories/        # Data access (User, Client, Upload)
├── models/                  # Pydantic models (rules, validation results)
├── routers/                 # auth, validation, client endpoints
├── services/
│   ├── rule_engine.py      # Core validation logic
│   ├── file_parser.py      # CSV/Excel parsing
│   ├── s3_service.py       # S3 upload/download/delete
│   └── auth.py             # Password hashing, JWT
└── worker/
    ├── celery_app.py       # Celery config
    └── tasks.py            # validate_emt_file task
alembic/                     # Migrations
data/emt_rules.json          # EMT rule definitions
tests/                       # Pytest suite
```

## First-time setup

You need Python 3.13+, Docker, and the AWS CLI (for the one-time bucket step).

**1. Install dependencies**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**2. Create the infrastructure containers** (run once — these commands *create*
the containers; you start them with `docker start` afterwards)

```bash
docker run -d --name fund-compliance-db -p 5433:5432 \
  -e POSTGRES_USER=funduser -e POSTGRES_PASSWORD=devpassword \
  -e POSTGRES_DB=fundcompliance postgres:16

docker run -d --name fund-compliance-redis -p 6379:6379 redis:7

docker run -d --name fund-compliance-localstack -p 4566:4566 \
  -e SERVICES=s3 localstack/localstack
```

**3. Create the S3 bucket and the test database** (one time)

```bash
aws --endpoint-url http://localhost:4566 s3 mb s3://fund-compliance-uploads

docker exec -it fund-compliance-db \
  createdb -U funduser fundcompliance_test
```

**4. Create your `.env`** in the project root

```env
DATABASE_URL=postgresql+asyncpg://funduser:devpassword@localhost:5433/fundcompliance
REDIS_URL=redis://localhost:6379/0
S3_BUCKET_NAME=fund-compliance-uploads
S3_ENDPOINT_URL=http://localhost:4566   # remove for real AWS

DEV_CLIENT_ID=<any-uuid>                 # required — app won't start without it
JWT_SECRET_KEY=change-me
JWT_EXPIRY_MINUTES=30
```

**5. Apply migrations**

```bash
alembic upgrade head
```

## Running the app day to day

```bash
# 1. Start the infrastructure (already created above)
docker start fund-compliance-db fund-compliance-redis fund-compliance-localstack

# 2. Apply migrations (only needed when they've changed)
alembic upgrade head

# 3. Start the API
uvicorn app.main:app --reload

# 4. Start the worker (separate terminal)
celery -A app.worker.celery_app worker --loglevel=info
```

API docs: http://localhost:8000/docs · Health check: http://localhost:8000/health

## API endpoints

**Auth**

```
POST /auth/register    { organisation_name, email, password }  → creates client + user
POST /auth/token       { username (email), password }          → { access_token, token_type }
```

**Validation** (all require `Authorization: Bearer <token>`)

```
POST /validate/emt              multipart: file (.csv/.xlsx/.xls), delimiter (optional)
                                → 202 { upload_id, task_id, message }
GET  /validate/uploads          → list of uploads (paginated: skip, limit)
GET  /validate/uploads/{id}     → one upload
GET  /validate/uploads/{id}/status
                                → { status, total_rows, rows_with_issues, ... }
```

## Migrations

```bash
alembic upgrade head                              # apply all pending migrations
alembic revision --autogenerate -m "description"  # create a new migration from model changes
alembic downgrade -1                              # roll back one migration
```

Always review autogenerated migrations before committing them.

## Tests

Tests run against the Postgres **test** database (`fundcompliance_test`) created
in setup — so the `fund-compliance-db` container must be running. They don't need
Redis or S3; those are mocked. Each test runs in a transaction that's rolled back,
so the database stays clean between tests.

```bash
docker start fund-compliance-db   # if not already running
pytest                            # all tests
pytest -v                         # verbose
pytest --cov=app                  # with coverage
```

## Rule engine

Rules live in `data/emt_rules.json` and are loaded at startup. Each rule defines:

- `field_code` — 5-digit EMT field id
- `field_type` — `string`, `integer`, `decimal`, `percentage`, `date`, `datetime`, `boolean`, `isin`, or `lei`
- `rule_type` — `format`, `allowed_values`, `expect_value`, `expect_empty`, or `custom`
- `allowed_values` — optional list of permitted values
- `condition` — optional logic (`eq`, `neq`, `in_set`, `not_in_set`, `is_empty`, `is_not_empty`, `and`, `or`)

Validation runs in two passes per row: first format and allowed-values checks
(which blank out any invalid cell), then mandatory and conditional rules against
the cleaned row. Issues are saved per row with the field code, rule type, and a
human-readable message.