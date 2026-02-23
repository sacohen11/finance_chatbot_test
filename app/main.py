"""Minimal entrypoint for pragmatic NL2SQL finance assistant."""

from typing import Optional

from app.services.nl2sql_service import NL2SQLService
from app.services.semantic_model import SemanticModel, build_default_semantic_model


def heuristic_llm_sql_generator(question: str, semantic_model: SemanticModel) -> Optional[str]:
    """Placeholder for LLM SQL generation.

    In production this function should call an LLM with schema + business term
    guidance from ``semantic_model`` and return SQL-only output.
    """

    q = question.lower()
    if "variance" in q:
        return (
            "SELECT department, "
            "SUM(actual_amount) - SUM(budget_amount) AS variance "
            "FROM finance_actuals "
            "GROUP BY department ORDER BY variance DESC"
        )

    if "run-rate" in q or "run rate" in q:
        return (
            "SELECT department, "
            "SUM(actual_amount) / NULLIF(COUNT(DISTINCT period_start), 0) AS run_rate "
            "FROM finance_actuals "
            "GROUP BY department ORDER BY run_rate DESC"
        )

    return None


def build_service() -> NL2SQLService:
    semantic_model = build_default_semantic_model()
    return NL2SQLService(
        semantic_model=semantic_model,
        llm_sql_generator=heuristic_llm_sql_generator,
        dsn="postgresql://readonly_user:readonly_password@localhost:5432/finance",
        statement_timeout_ms=5_000,
        row_limit=200,
    )
