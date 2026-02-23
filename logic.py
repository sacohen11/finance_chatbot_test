from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ResultShape:
    is_time_series: bool
    has_category_comparison: bool
    has_budget_actual_share: bool


def _mock_query_result(user_query: str) -> list[dict[str, Any]]:
    q = (user_query or "").lower()

    if any(token in q for token in ["trend", "monthly", "time", "history", "over time"]):
        return [
            {"month": "2025-01", "revenue": 120000},
            {"month": "2025-02", "revenue": 128000},
            {"month": "2025-03", "revenue": 119500},
            {"month": "2025-04", "revenue": 136000},
            {"month": "2025-05", "revenue": 142200},
        ]

    if any(token in q for token in ["budget", "actual", "spend mix", "share"]):
        return [
            {"department": "Marketing", "budget": 50000, "actual": 47000},
            {"department": "Sales", "budget": 72000, "actual": 76000},
            {"department": "R&D", "budget": 90000, "actual": 87000},
            {"department": "Operations", "budget": 60000, "actual": 58000},
        ]

    return [
        {"category": "Subscriptions", "amount": 180000},
        {"category": "Consulting", "amount": 143000},
        {"category": "Licensing", "amount": 96000},
        {"category": "Training", "amount": 64000},
    ]


def _infer_shape(table_data: list[dict[str, Any]]) -> ResultShape:
    if not table_data:
        return ResultShape(False, False, False)

    keys = set(table_data[0].keys())
    is_time_series = any(k in keys for k in ["date", "day", "week", "month", "quarter", "year"])
    has_budget_actual_share = {"budget", "actual"}.issubset(keys)
    has_category_comparison = any(k in keys for k in ["category", "department", "segment", "product"]) and any(
        isinstance(v, (int, float)) for v in table_data[0].values()
    )

    return ResultShape(
        is_time_series=is_time_series,
        has_category_comparison=has_category_comparison,
        has_budget_actual_share=has_budget_actual_share,
    )


def _pick_chart_type(shape: ResultShape, user_query: str) -> str:
    if shape.is_time_series:
        return "line"

    if shape.has_budget_actual_share:
        q = (user_query or "").lower()
        if "share" in q or "composition" in q:
            return "pie"
        return "stacked_bar"

    if shape.has_category_comparison:
        return "bar"

    return "table_only"


def _build_plotly_spec(table_data: list[dict[str, Any]], chart_type: str) -> dict[str, Any] | None:
    if not table_data or chart_type == "table_only":
        return None

    keys = list(table_data[0].keys())

    if chart_type == "line":
        x_key = next((k for k in ["date", "day", "week", "month", "quarter", "year"] if k in keys), keys[0])
        y_keys = [k for k in keys if k != x_key and isinstance(table_data[0].get(k), (int, float))]
        y_key = y_keys[0] if y_keys else keys[1]
        return {
            "data": [
                {
                    "type": "scatter",
                    "mode": "lines+markers",
                    "x": [row[x_key] for row in table_data],
                    "y": [row[y_key] for row in table_data],
                    "name": y_key.title(),
                }
            ],
            "layout": {"title": f"{y_key.title()} over {x_key.title()}", "xaxis": {"title": x_key.title()}, "yaxis": {"title": y_key.title()}},
        }

    if chart_type == "bar":
        category_key = next((k for k in ["category", "department", "segment", "product"] if k in keys), keys[0])
        value_key = next((k for k in keys if k != category_key and isinstance(table_data[0].get(k), (int, float))), keys[1])
        return {
            "data": [
                {
                    "type": "bar",
                    "x": [row[category_key] for row in table_data],
                    "y": [row[value_key] for row in table_data],
                    "name": value_key.title(),
                }
            ],
            "layout": {"title": f"{value_key.title()} by {category_key.title()}", "xaxis": {"title": category_key.title()}, "yaxis": {"title": value_key.title()}},
        }

    if chart_type == "stacked_bar":
        category_key = next((k for k in ["category", "department", "segment", "product"] if k in keys), keys[0])
        return {
            "data": [
                {
                    "type": "bar",
                    "name": "Budget",
                    "x": [row[category_key] for row in table_data],
                    "y": [row["budget"] for row in table_data],
                },
                {
                    "type": "bar",
                    "name": "Actual",
                    "x": [row[category_key] for row in table_data],
                    "y": [row["actual"] for row in table_data],
                },
            ],
            "layout": {
                "title": f"Budget vs Actual by {category_key.title()}",
                "barmode": "stack",
                "xaxis": {"title": category_key.title()},
                "yaxis": {"title": "Amount"},
            },
        }

    if chart_type == "pie":
        category_key = next((k for k in ["category", "department", "segment", "product"] if k in keys), keys[0])
        total_actual = [row.get("actual", 0) for row in table_data]
        return {
            "data": [
                {
                    "type": "pie",
                    "labels": [row[category_key] for row in table_data],
                    "values": total_actual,
                    "textinfo": "label+percent",
                }
            ],
            "layout": {"title": "Actual Spend Share"},
        }

    return None


def build_assistant_response(user_query: str) -> dict[str, Any]:
    table_data = _mock_query_result(user_query)
    shape = _infer_shape(table_data)
    chart_type = _pick_chart_type(shape, user_query)
    chart_spec = _build_plotly_spec(table_data, chart_type)

    answer_text = {
        "line": "Here is the time-series trend rendered as a line chart.",
        "bar": "Here is the category comparison rendered as a bar chart.",
        "stacked_bar": "Here is budget versus actual rendered as a stacked bar chart.",
        "pie": "Here is the budget/actual share rendered as a pie chart (used sparingly for composition).",
        "table_only": "I found tabular results and displayed them as a table.",
    }[chart_type]

    return {
        "answer_text": answer_text,
        "table_data": table_data,
        "chart_spec": chart_spec,
    }
