"""Semantic layer for the finance NL2SQL assistant.

This module defines the allowlisted data model and approved business terms that
LLM-generated SQL can reference.
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class TableDefinition:
    """Represents a queryable table and its approved columns."""

    name: str
    columns: List[str]
    description: str


@dataclass(frozen=True)
class SemanticModel:
    """Encodes allowed schema objects and approved business metrics."""

    tables: Dict[str, TableDefinition] = field(default_factory=dict)
    business_terms: Dict[str, str] = field(default_factory=dict)

    @property
    def allowed_tables(self) -> List[str]:
        return sorted(self.tables.keys())

    @property
    def allowed_columns(self) -> Dict[str, List[str]]:
        return {name: sorted(table.columns) for name, table in self.tables.items()}


def build_default_semantic_model() -> SemanticModel:
    """Build the v1 semantic model for structured finance analytics."""

    tables = {
        "finance_actuals": TableDefinition(
            name="finance_actuals",
            columns=[
                "period_start",
                "department",
                "account",
                "actual_amount",
                "budget_amount",
                "headcount",
            ],
            description="Monthly actuals and budget by department/account.",
        ),
        "finance_forecast": TableDefinition(
            name="finance_forecast",
            columns=[
                "period_start",
                "department",
                "forecast_amount",
                "forecast_version",
            ],
            description="Rolling forecast snapshots.",
        ),
        "cash_position": TableDefinition(
            name="cash_position",
            columns=[
                "as_of_date",
                "bank_account",
                "currency",
                "ending_balance",
            ],
            description="Daily ending cash balances.",
        ),
    }

    # SQL snippets are intentionally expression-only; validators in sql_safety.py
    # still enforce read-only, allowlisted queries.
    business_terms = {
        "variance": "SUM(actual_amount) - SUM(budget_amount)",
        "variance_pct": "CASE WHEN SUM(budget_amount) = 0 THEN NULL ELSE (SUM(actual_amount) - SUM(budget_amount)) / SUM(budget_amount) END",
        "run-rate": "SUM(actual_amount) / NULLIF(COUNT(DISTINCT period_start), 0)",
        "overburn": "GREATEST(SUM(actual_amount) - SUM(budget_amount), 0)",
    }

    return SemanticModel(tables=tables, business_terms=business_terms)
