import json
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data.db"
MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def parse_month(month):
    if not month or not MONTH_RE.match(month):
        return False
    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError:
        return False
    return True


def parse_numeric(name, data):
    value = data.get(name)
    if value is None or value == "":
        return None, f"{name} is required"
    try:
        num = float(value)
    except (ValueError, TypeError):
        return None, f"{name} must be a number"
    if num < 0 or num > 1_000_000_000:
        return None, f"{name} must be between 0 and 1000000000"
    return num, None


class ContractApp:
    def __init__(self, database_path=None):
        self.database_path = str(database_path or DB_PATH)
        self._init_db()

    def _db(self):
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._db() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS contracts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_number TEXT UNIQUE NOT NULL
                );

                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_id INTEGER NOT NULL,
                    report_month TEXT NOT NULL,
                    planned_spend REAL NOT NULL,
                    actual_spend REAL NOT NULL,
                    planned_labor_hours REAL NOT NULL,
                    actual_labor_hours REAL NOT NULL,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(contract_id, report_month),
                    FOREIGN KEY(contract_id) REFERENCES contracts(id)
                );
                """
            )

    def _json(self, start_response, status, payload):
        body = json.dumps(payload).encode("utf-8")
        start_response(status, [("Content-Type", "application/json"), ("Content-Length", str(len(body)))])
        return [body]

    def _text(self, start_response, status, body, content_type="text/html; charset=utf-8"):
        data = body.encode("utf-8")
        start_response(status, [("Content-Type", content_type), ("Content-Length", str(len(data)))])
        return [data]

    def _get_contract(self, db, contract_number):
        return db.execute("SELECT id, contract_number FROM contracts WHERE contract_number = ?", (contract_number,)).fetchone()

    def _get_or_create_contract(self, db, contract_number):
        contract = self._get_contract(db, contract_number)
        if contract:
            return contract
        db.execute("INSERT INTO contracts (contract_number) VALUES (?)", (contract_number,))
        return self._get_contract(db, contract_number)

    def handle_lookup(self, start_response, contract_number, query):
        month = (query.get("month") or [""])[0]
        if not parse_month(month):
            return self._json(start_response, "400 Bad Request", {"error": "month must be in YYYY-MM format"})

        with self._db() as db:
            contract = self._get_contract(db, contract_number)
            if not contract:
                return self._json(start_response, "404 Not Found", {"source": "none", "message": "No data found", "report": None})

            exact = db.execute(
                "SELECT report_month, planned_spend, actual_spend, planned_labor_hours, actual_labor_hours, notes FROM reports WHERE contract_id = ? AND report_month = ?",
                (contract["id"], month),
            ).fetchone()
            if exact:
                return self._json(start_response, "200 OK", {"source": "exact", "message": "Loaded exact month data", "report": dict(exact)})

            prior = db.execute(
                "SELECT report_month, planned_spend, actual_spend, planned_labor_hours, actual_labor_hours, notes FROM reports WHERE contract_id = ? AND report_month < ? ORDER BY report_month DESC LIMIT 1",
                (contract["id"], month),
            ).fetchone()
            if prior:
                return self._json(start_response, "200 OK", {"source": "prior", "message": "Loaded prior month data", "report": dict(prior)})

        return self._json(start_response, "404 Not Found", {"source": "none", "message": "No data found", "report": None})

    def handle_save(self, environ, start_response):
        try:
            length = int(environ.get("CONTENT_LENGTH") or "0")
        except ValueError:
            length = 0
        raw = environ["wsgi.input"].read(length)
        payload = json.loads(raw.decode("utf-8") or "{}")

        contract_number = (payload.get("contract_number") or "").strip()
        month = payload.get("report_month")
        if not contract_number:
            return self._json(start_response, "400 Bad Request", {"error": "contract_number is required"})
        if not parse_month(month):
            return self._json(start_response, "400 Bad Request", {"error": "report_month must be in YYYY-MM format"})

        planned_spend, err = parse_numeric("planned_spend", payload)
        if err:
            return self._json(start_response, "400 Bad Request", {"error": err})
        actual_spend, err = parse_numeric("actual_spend", payload)
        if err:
            return self._json(start_response, "400 Bad Request", {"error": err})
        planned_labor_hours, err = parse_numeric("planned_labor_hours", payload)
        if err:
            return self._json(start_response, "400 Bad Request", {"error": err})
        actual_labor_hours, err = parse_numeric("actual_labor_hours", payload)
        if err:
            return self._json(start_response, "400 Bad Request", {"error": err})

        notes = payload.get("notes") or ""
        now = datetime.utcnow().isoformat()
        with self._db() as db:
            contract = self._get_or_create_contract(db, contract_number)
            db.execute(
                """
                INSERT INTO reports (contract_id, report_month, planned_spend, actual_spend, planned_labor_hours, actual_labor_hours, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(contract_id, report_month)
                DO UPDATE SET
                    planned_spend=excluded.planned_spend,
                    actual_spend=excluded.actual_spend,
                    planned_labor_hours=excluded.planned_labor_hours,
                    actual_labor_hours=excluded.actual_labor_hours,
                    notes=excluded.notes,
                    updated_at=excluded.updated_at
                """,
                (contract["id"], month, planned_spend, actual_spend, planned_labor_hours, actual_labor_hours, notes, now, now),
            )

        return self._json(start_response, "200 OK", {"message": "Saved successfully"})

    def __call__(self, environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO", "/")
        query = parse_qs(environ.get("QUERY_STRING", ""))

        if method == "GET" and path == "/contracts":
            return self._text(start_response, "200 OK", (BASE_DIR / "templates" / "contracts.html").read_text())

        if method == "GET" and path == "/static/contracts.js":
            return self._text(start_response, "200 OK", (BASE_DIR / "static" / "contracts.js").read_text(), "text/javascript; charset=utf-8")

        if method == "GET" and path.startswith("/api/contracts/") and path.endswith("/reports"):
            contract_number = path.split("/")[3]
            return self.handle_lookup(start_response, contract_number, query)

        if method == "POST" and path == "/api/reports":
            return self.handle_save(environ, start_response)

        return self._json(start_response, "404 Not Found", {"error": "Not found"})


if __name__ == "__main__":
    app = ContractApp()
    port = int(os.environ.get("PORT", "5000"))
    with make_server("0.0.0.0", port, app) as server:
        print(f"Serving on http://0.0.0.0:{port}")
        server.serve_forever()
