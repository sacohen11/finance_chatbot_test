# finance_chatbot_test

Simple finance assistant demo with unified text + table + chart responses.

## Run

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
