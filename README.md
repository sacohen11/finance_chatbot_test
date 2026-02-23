# finance_chatbot_test

Simple finance assistant demo with unified text + table + chart responses.

## Run
Pragmatic first version of a finance chatbot that uses **LLM-driven NL2SQL** against PostgreSQL.

## Design decisions (v1)

- Use NL2SQL for structured/tabular finance data in PostgreSQL.
- Skip full RAG for now because the primary source is relational data.
- Skip MCP for now because this version does not require interoperability with many external systems.

## Implemented flow

1. User question is converted to SQL by an LLM generator function.
2. SQL is validated with strict safety checks:
   - read-only `SELECT` only
   - block DDL/DML keywords
   - enforce allowlisted tables from semantic model
   - enforce single-statement mode (no semicolons)
3. Safe SQL gets a default `LIMIT` if missing.
4. SQL executes under:
   - read-only transaction
   - statement timeout
5. Assistant returns explanation plus result rows.
6. If generation/validation fails, assistant returns clarification prompts.

## Semantic layer

`app/services/semantic_model.py` defines:

- approved tables/columns
- business term mappings to SQL-safe expressions (e.g., `variance`, `run-rate`, `overburn`)

## Key files

- `app/services/semantic_model.py` – allowlisted schema + finance business term expressions
- `app/services/sql_safety.py` – SQL validation and limit enforcement
- `app/services/nl2sql_service.py` – question → SQL → validate → execute → response/fallback
- `app/main.py` – minimal service wiring with a placeholder SQL generator
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
pip install -r requirements.txt
python app.py
```

Open: `http://localhost:8000/assistant`

## Unified payload

`POST /api/assistant`

```json
{
  "answer_text": "...",
  "table_data": [{"...": "..."}],
  "chart_spec": {"data": [], "layout": {}}
}
```

Chart recommendation defaults:
- Time series → line chart
- Category comparison → bar chart
- Budget vs actual share → stacked bar or pie (pie only when share/composition is explicitly requested)

Exports in UI:
- Table CSV download
- Chart PNG export (Plotly)

## Tests

```bash
python -m unittest
```
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
