# finance_chatbot_test

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
