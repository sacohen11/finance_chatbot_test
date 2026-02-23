from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs


class ContractApp:
    """Minimal WSGI app for contract monthly reports."""

    def __init__(self, database_path: str = "contracts.db") -> None:
        self.database_path = database_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS contract_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_number TEXT NOT NULL,
                    report_month TEXT NOT NULL,
                    planned_spend REAL NOT NULL,
                    actual_spend REAL NOT NULL,
                    planned_labor_hours REAL NOT NULL,
                    actual_labor_hours REAL NOT NULL,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(contract_number, report_month)
                )
                """
            )

    def __call__(self, environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO", "/")

        if method == "GET" and path == "/contracts":
            html = Path("templates/contracts.html").read_text(encoding="utf-8")
            return self._response(start_response, "200 OK", html, "text/html")

        if method == "POST" and path == "/api/reports":
            return self._save_report(environ, start_response)

        if method == "GET" and path.startswith("/api/contracts/") and path.endswith("/reports"):
            contract_number = path[len("/api/contracts/") : -len("/reports")].strip("/")
            return self._lookup_report(contract_number, environ, start_response)

        return self._response(start_response, "404 Not Found", {"error": "Not found"})

    def _save_report(self, environ, start_response):
        payload = self._json_body(environ)
        err = self._validate_payload(payload)
        if err:
            return self._response(start_response, "400 Bad Request", {"error": err})

        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO contract_reports (
                    contract_number, report_month,
                    planned_spend, actual_spend,
                    planned_labor_hours, actual_labor_hours,
                    notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(contract_number, report_month)
                DO UPDATE SET
                    planned_spend=excluded.planned_spend,
                    actual_spend=excluded.actual_spend,
                    planned_labor_hours=excluded.planned_labor_hours,
                    actual_labor_hours=excluded.actual_labor_hours,
                    notes=excluded.notes,
                    updated_at=excluded.updated_at
                """,
                (
                    payload["contract_number"],
                    payload["report_month"],
                    float(payload["planned_spend"]),
                    float(payload["actual_spend"]),
                    float(payload["planned_labor_hours"]),
                    float(payload["actual_labor_hours"]),
                    payload.get("notes", ""),
                    now,
                    now,
                ),
            )
        return self._response(start_response, "200 OK", {"status": "ok"})

    def _lookup_report(self, contract_number: str, environ, start_response):
        month = parse_qs(environ.get("QUERY_STRING", "")).get("month", [""])[0]
        if not month or not self._valid_month(month):
            return self._response(start_response, "400 Bad Request", {"error": "Invalid month"})

        with self._connect() as conn:
            exact = conn.execute(
                "SELECT * FROM contract_reports WHERE contract_number=? AND report_month=?",
                (contract_number, month),
            ).fetchone()
            if exact:
                return self._response(
                    start_response,
                    "200 OK",
                    {"source": "exact", "message": "Loaded exact month data", "report": self._row_to_report(exact)},
                )

            prior = conn.execute(
                """
                SELECT * FROM contract_reports
                WHERE contract_number=? AND report_month < ?
                ORDER BY report_month DESC
                LIMIT 1
                """,
                (contract_number, month),
            ).fetchone()
            if prior:
                return self._response(
                    start_response,
                    "200 OK",
                    {"source": "prior", "message": "Loaded prior month data", "report": self._row_to_report(prior)},
                )

        return self._response(start_response, "404 Not Found", {"error": "No report found"})

    def _row_to_report(self, row: sqlite3.Row) -> dict:
        return {
            "contract_number": row["contract_number"],
            "report_month": row["report_month"],
            "planned_spend": row["planned_spend"],
            "actual_spend": row["actual_spend"],
            "planned_labor_hours": row["planned_labor_hours"],
            "actual_labor_hours": row["actual_labor_hours"],
            "notes": row["notes"] or "",
        }

    def _json_body(self, environ) -> dict:
        length = int(environ.get("CONTENT_LENGTH", "0") or "0")
        raw = environ["wsgi.input"].read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    def _validate_payload(self, payload: dict) -> str | None:
        required = [
            "contract_number",
            "report_month",
            "planned_spend",
            "actual_spend",
            "planned_labor_hours",
            "actual_labor_hours",
        ]
        for key in required:
            if key not in payload or payload[key] in (None, ""):
                return f"Missing required field: {key}"

        if not self._valid_month(str(payload["report_month"])):
            return "Invalid report_month format. Expected YYYY-MM"

        numeric_fields = ["planned_spend", "actual_spend", "planned_labor_hours", "actual_labor_hours"]
        for key in numeric_fields:
            try:
                float(payload[key])
            except (TypeError, ValueError):
                return f"Invalid numeric value for {key}"
        return None

    def _valid_month(self, value: str) -> bool:
        try:
            datetime.strptime(value, "%Y-%m")
        except ValueError:
            return False
        return True

    def _response(self, start_response, status: str, body: dict | str, content_type: str = "application/json") -> Iterable[bytes]:
        if isinstance(body, str):
            payload = body.encode("utf-8")
        else:
            payload = json.dumps(body).encode("utf-8")
        start_response(status, [("Content-Type", content_type), ("Content-Length", str(len(payload)))])
        return [payload]
