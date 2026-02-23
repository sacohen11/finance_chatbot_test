# finance_chatbot_test

Minimal FastAPI app with server-rendered templates for contract entry and a financial assistant page.

## Project layout

- `app/main.py` – FastAPI routes and session handling
- `app/templates/` – Jinja2 templates
- `app/static/` – CSS + JS assets
- `app/services/` – business logic services

## Run

```bash
pip install fastapi uvicorn jinja2 python-multipart
uvicorn app.main:app --reload
```

## Demo access

- Analyst login: `analyst / letmein`
- Contractor login: `contractor / contract123`
- Contractor tokenized link: `/contracts?token=contractor-demo-token`
