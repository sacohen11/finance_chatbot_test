# finance_chatbot_test

Minimal Python WSGI app implementing:

- Persistent `chat_sessions` and `chat_messages`
- Login with loading of recent sessions and reopening
- Rule-based recommendation job that mines recent analyst queries
- `recommended_prompts` displayed as clickable chips above the input box
- Conversation history persisted in the same Postgres database as finance data (configurable via `DATABASE_URL`)

## Run

```bash
pip install -r requirements.txt
export DATABASE_URL=postgresql://<user>:<password>@<host>:5432/<finance_db>
python app.py
```

Then open `http://localhost:5000`.
