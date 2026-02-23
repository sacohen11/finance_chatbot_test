import io
import json
import tempfile
from wsgiref.util import setup_testing_defaults

from app import ContractApp


def wsgi_request(app, method, path, query="", body=None):
    environ = {}
    setup_testing_defaults(environ)
    environ["REQUEST_METHOD"] = method
    environ["PATH_INFO"] = path
    environ["QUERY_STRING"] = query
    payload = b""
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
    environ["CONTENT_LENGTH"] = str(len(payload))
    environ["wsgi.input"] = io.BytesIO(payload)

    status_holder = {}

    def start_response(status, headers):
        status_holder["status"] = status
        status_holder["headers"] = headers

    resp = b"".join(app(environ, start_response))
    return status_holder["status"], dict(status_holder["headers"]), resp


def test_contract_page_loads():
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        app = ContractApp(database_path=f.name)
        status, _, body = wsgi_request(app, "GET", "/contracts")
        assert status.startswith("200")
        assert b"Contract Monthly Report" in body


def test_save_and_lookup_exact_month():
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        app = ContractApp(database_path=f.name)
        status, _, _ = wsgi_request(
            app,
            "POST",
            "/api/reports",
            body={
                "contract_number": "CN-1",
                "report_month": "2025-01",
                "planned_spend": 100,
                "actual_spend": 110,
                "planned_labor_hours": 50,
                "actual_labor_hours": 55,
                "notes": "Jan",
            },
        )
        assert status.startswith("200")

        status, _, body = wsgi_request(app, "GET", "/api/contracts/CN-1/reports", query="month=2025-01")
        payload = json.loads(body)
        assert status.startswith("200")
        assert payload["source"] == "exact"


def test_prior_fallback():
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        app = ContractApp(database_path=f.name)
        wsgi_request(
            app,
            "POST",
            "/api/reports",
            body={
                "contract_number": "CN-2",
                "report_month": "2025-03",
                "planned_spend": 100,
                "actual_spend": 90,
                "planned_labor_hours": 40,
                "actual_labor_hours": 38,
                "notes": "March",
            },
        )
        status, _, body = wsgi_request(app, "GET", "/api/contracts/CN-2/reports", query="month=2025-04")
        payload = json.loads(body)
        assert status.startswith("200")
        assert payload["source"] == "prior"
        assert payload["message"] == "Loaded prior month data"


def test_validation():
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        app = ContractApp(database_path=f.name)
        status, _, _ = wsgi_request(
            app,
            "POST",
            "/api/reports",
            body={
                "contract_number": "CN-3",
                "report_month": "2025-13",
                "planned_spend": 100,
                "actual_spend": 90,
                "planned_labor_hours": 40,
                "actual_labor_hours": 38,
            },
        )
        assert status.startswith("400")
