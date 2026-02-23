"""Safety checks for LLM-proposed SQL."""

from dataclasses import dataclass
import re
from typing import Iterable, Optional

from app.services.semantic_model import SemanticModel


BLOCKED_KEYWORDS = {
    "insert",
    "update",
    "delete",
    "drop",
    "truncate",
    "alter",
    "create",
    "grant",
    "revoke",
    "merge",
    "call",
    "copy",
    "vacuum",
}


@dataclass
class ValidationResult:
    is_safe: bool
    error: Optional[str] = None


class SQLSafetyValidator:
    """Validates SQL against strict read-only and allowlist constraints."""

    def __init__(self, semantic_model: SemanticModel, default_limit: int = 200) -> None:
        self.semantic_model = semantic_model
        self.default_limit = default_limit

    def validate(self, sql: str) -> ValidationResult:
        normalized = self._normalize(sql)

        if not normalized.startswith("select"):
            return ValidationResult(False, "Only SELECT statements are allowed.")

        if ";" in normalized:
            return ValidationResult(False, "Semicolons are not allowed (single statement only).")

        if self._contains_blocked_keyword(normalized):
            return ValidationResult(False, "SQL contains blocked write/DDL keywords.")

        table_check = self._validate_tables(normalized)
        if table_check:
            return ValidationResult(False, table_check)

        return ValidationResult(True)

    def enforce_limit(self, sql: str) -> str:
        normalized = self._normalize(sql)
        if " limit " in f" {normalized} ":
            return sql
        return f"{sql.rstrip()} LIMIT {self.default_limit}"

    @staticmethod
    def _normalize(sql: str) -> str:
        return re.sub(r"\s+", " ", sql.strip().lower())

    def _contains_blocked_keyword(self, normalized_sql: str) -> bool:
        for kw in BLOCKED_KEYWORDS:
            if re.search(rf"\b{kw}\b", normalized_sql):
                return True
        return False

    def _validate_tables(self, normalized_sql: str) -> Optional[str]:
        referenced_tables = set(self._extract_tables(normalized_sql))
        for table in referenced_tables:
            if table not in self.semantic_model.allowed_tables:
                return f"Table '{table}' is not in the allowlist."
        return None

    @staticmethod
    def _extract_tables(normalized_sql: str) -> Iterable[str]:
        # Simple extraction for FROM/JOIN clauses. This is intentionally pragmatic
        # for v1 and should be upgraded to SQL AST parsing in future versions.
        pattern = re.compile(r"\b(?:from|join)\s+([a-zA-Z_][a-zA-Z0-9_]*)")
        for match in pattern.finditer(normalized_sql):
            yield match.group(1)
