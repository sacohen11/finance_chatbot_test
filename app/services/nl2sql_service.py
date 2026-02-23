"""End-to-end NL2SQL flow for structured finance questions."""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from app.services.semantic_model import SemanticModel
from app.services.sql_safety import SQLSafetyValidator


@dataclass
class QueryResponse:
    ok: bool
    explanation: str
    rows: List[Dict[str, Any]]
    sql: Optional[str] = None


class NL2SQLService:
    """Generates, validates, and executes read-only SQL for finance questions."""

    def __init__(
        self,
        semantic_model: SemanticModel,
        llm_sql_generator: Callable[[str, SemanticModel], Optional[str]],
        dsn: str,
        statement_timeout_ms: int = 5_000,
        row_limit: int = 200,
    ) -> None:
        self.semantic_model = semantic_model
        self.llm_sql_generator = llm_sql_generator
        self.dsn = dsn
        self.statement_timeout_ms = statement_timeout_ms
        self.validator = SQLSafetyValidator(semantic_model, default_limit=row_limit)

    def answer(self, question: str) -> QueryResponse:
        proposed_sql = self.llm_sql_generator(question, self.semantic_model)

        if not proposed_sql:
            return self._clarify("I could not derive a safe SQL query from that request.")

        validation = self.validator.validate(proposed_sql)
        if not validation.is_safe:
            return self._clarify(
                f"I could not safely run that query ({validation.error}). "
                "Please clarify the metric, department, and time range."
            )

        safe_sql = self.validator.enforce_limit(proposed_sql)
        rows = self._execute_read_only(safe_sql)
        explanation = (
            "Query executed in read-only mode with semantic allowlist checks, "
            f"row limit enforcement, and {self.statement_timeout_ms}ms timeout."
        )
        return QueryResponse(ok=True, explanation=explanation, rows=rows, sql=safe_sql)

    def _execute_read_only(self, sql: str) -> List[Dict[str, Any]]:
        import psycopg

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SET TRANSACTION READ ONLY")
                cur.execute(f"SET LOCAL statement_timeout = {self.statement_timeout_ms}")
                cur.execute(sql)
                columns = [desc.name for desc in cur.description]
                data = cur.fetchall()

        return [dict(zip(columns, row)) for row in data]

    @staticmethod
    def _clarify(prefix: str) -> QueryResponse:
        clarification = (
            f"{prefix} Try prompts like: 'Show variance by department for 2025-Q1' "
            "or 'What is monthly run-rate for Engineering in the last 6 months?'"
        )
        return QueryResponse(ok=False, explanation=clarification, rows=[])
