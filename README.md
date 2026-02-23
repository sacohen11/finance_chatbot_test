# finance_chatbot_test

PostgreSQL schema, SQLAlchemy ORM models, and Alembic migration setup for contract form data and chatbot memory.

## Structure

- `app/models.py`: SQLAlchemy ORM models for contractors, contracts, monthly reports, analysts, sessions, messages, and recommended prompts.
- `alembic/versions/20260223_01_create_core_schema.py`: Initial schema migration with required constraints and indexes.
- `alembic.ini` + `alembic/env.py`: Alembic configuration and migration environment.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
alembic upgrade head
```

Update `sqlalchemy.url` in `alembic.ini` to point at your PostgreSQL instance before running migrations.
