# finance_chatbot_test

Minimal Python WSGI app implementing:

- Persistent `chat_sessions` and `chat_messages`
- Login with loading of recent sessions and reopening
- Rule-based recommendation job that mines recent analyst queries
- `recommended_prompts` displayed as clickable chips above the input box

## Run

```bash
pip install -r requirements.txt
python app.py
```

Then open `http://localhost:5000`.
