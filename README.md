# finance_chatbot_test

Flask app providing a contract monthly report page with historical lookup and upsert save.
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
Minimal FastAPI app with server-rendered templates for contract entry and a financial assistant page.

## Project layout

- `app/main.py` – FastAPI routes and session handling
- `app/templates/` – Jinja2 templates
- `app/static/` – CSS + JS assets
- `app/services/` – business logic services

## Run

```bash
pip install -r requirements.txt
python app.py
```

Visit `http://localhost:5000/contracts`.

## Test

```bash
pytest
```
pip install fastapi uvicorn jinja2 python-multipart
uvicorn app.main:app --reload
```

## Demo access

- Analyst login: `analyst / letmein`
- Contractor login: `contractor / contract123`
- Contractor tokenized link: `/contracts?token=contractor-demo-token`
