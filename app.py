from __future__ import annotations

import html
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "app.db"
SESSION_COOKIE = "finance_sid"
sessions: dict[str, int] = {}


@dataclass
class TopicRule:
    name: str
    keywords: tuple[str, ...]
    prompt: str


TOPIC_RULES: tuple[TopicRule, ...] = (
    TopicRule("variance", ("variance", "delta", "actual vs", "gap"), "Show the biggest budget variance by project for this month."),
    TopicRule("forecast", ("forecast", "projection", "run rate", "estimate"), "Generate a 90-day forecast and flag high-risk cost centers."),
    TopicRule("overburn", ("overburn", "overspend", "burn", "over budget"), "Which teams are overburning budget and what is the weekly trend?"),
    TopicRule("top_contractors", ("contractor", "vendor", "consultant", "freelancer"), "List the top contractors by spend with month-over-month change."),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db_conn() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_session_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('user','assistant')),
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS recommended_prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                prompt TEXT NOT NULL,
                topic TEXT NOT NULL,
                score INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )


def parse_cookies(environ: dict) -> dict[str, str]:
    raw = environ.get("HTTP_COOKIE", "")
    items = {}
    for part in raw.split(";"):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            items[k] = v
    return items


def get_form_data(environ: dict) -> dict[str, str]:
    size = int(environ.get("CONTENT_LENGTH") or 0)
    body = environ["wsgi.input"].read(size).decode("utf-8") if size else ""
    parsed = parse_qs(body)
    return {k: (v[0] if v else "") for k, v in parsed.items()}


def get_or_create_user(username: str) -> sqlite3.Row:
    with db_conn() as db:
        row = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if row:
            return row
        db.execute("INSERT INTO users (username, created_at) VALUES (?,?)", (username, utc_now()))
        return db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()


def ensure_chat_session(user_id: int, wanted_id: int | None = None) -> sqlite3.Row:
    with db_conn() as db:
        if wanted_id:
            row = db.execute("SELECT * FROM chat_sessions WHERE id=? AND user_id=?", (wanted_id, user_id)).fetchone()
            if row:
                return row
        now = utc_now()
        title = f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        cur = db.execute(
            "INSERT INTO chat_sessions (user_id,title,created_at,updated_at) VALUES (?,?,?,?)",
            (user_id, title, now, now),
        )
        return db.execute("SELECT * FROM chat_sessions WHERE id=?", (cur.lastrowid,)).fetchone()


def append_message(chat_session_id: int, role: str, message: str) -> None:
    now = utc_now()
    with db_conn() as db:
        db.execute(
            "INSERT INTO chat_messages (chat_session_id,role,message,created_at) VALUES (?,?,?,?)",
            (chat_session_id, role, message, now),
        )
        db.execute("UPDATE chat_sessions SET updated_at=? WHERE id=?", (now, chat_session_id))


def assistant_reply(text: str) -> str:
    return f"Saved. Deterministic recommendations updated from: '{text}'"


def regenerate_recommendations(user_id: int, last_n: int = 30) -> None:
    with db_conn() as db:
        queries = [
            r["message"].lower()
            for r in db.execute(
                """
                SELECT cm.message FROM chat_messages cm
                JOIN chat_sessions cs ON cs.id=cm.chat_session_id
                WHERE cs.user_id=? AND cm.role='user'
                ORDER BY cm.created_at DESC LIMIT ?
                """,
                (user_id, last_n),
            ).fetchall()
        ]

        scores: list[tuple[TopicRule, int]] = []
        for rule in TOPIC_RULES:
            score = sum(1 for q in queries if any(k in q for k in rule.keywords))
            if score > 0:
                scores.append((rule, score))

        scores.sort(key=lambda x: (-x[1], x[0].name))
        db.execute("DELETE FROM recommended_prompts WHERE user_id=?", (user_id,))
        now = utc_now()

        if not scores:
            fallback = TOPIC_RULES[0]
            db.execute(
                "INSERT INTO recommended_prompts (user_id,prompt,topic,score,created_at) VALUES (?,?,?,?,?)",
                (user_id, fallback.prompt, fallback.name, 0, now),
            )
        else:
            for rule, score in scores[:4]:
                db.execute(
                    "INSERT INTO recommended_prompts (user_id,prompt,topic,score,created_at) VALUES (?,?,?,?,?)",
                    (user_id, rule.prompt, rule.name, score, now),
                )


def render_login() -> str:
    return """
    <html><head><title>Login</title><link rel='stylesheet' href='/styles.css'></head>
    <body class='login-page'><main class='login-card'><h1>Finance Assistant</h1>
    <form method='post' action='/'><input name='username' placeholder='Analyst username' required>
    <button type='submit'>Login</button></form></main></body></html>
    """


def render_assistant(user: sqlite3.Row, active_session_id: int | None = None) -> str:
    with db_conn() as db:
        active = ensure_chat_session(user["id"], active_session_id)
        sess = db.execute("SELECT * FROM chat_sessions WHERE user_id=? ORDER BY updated_at DESC LIMIT 10", (user["id"],)).fetchall()
        msgs = db.execute("SELECT * FROM chat_messages WHERE chat_session_id=? ORDER BY id", (active["id"],)).fetchall()
        recs = db.execute("SELECT * FROM recommended_prompts WHERE user_id=? ORDER BY score DESC, topic ASC LIMIT 4", (user["id"],)).fetchall()

    session_html = "".join(
        f"<a class='session-link {'active' if s['id']==active['id'] else ''}' href='/assistant?session_id={s['id']}'><span>{html.escape(s['title'])}</span><small>{s['updated_at'][:16].replace('T',' ')}</small></a>"
        for s in sess
    )
    msg_html = "".join(
        f"<article class='msg {m['role']}'><strong>{m['role']}</strong><p>{html.escape(m['message'])}</p><small>{m['created_at'][:19].replace('T',' ')}</small></article>"
        for m in msgs
    )
    rec_html = "".join(
        f"<button class='chip' type='submit' name='recommended_prompt' value='{html.escape(r['prompt'])}'>{html.escape(r['topic'].replace('_',' '))}</button>"
        for r in recs
    )

    return f"""
    <html><head><title>Assistant</title><link rel='stylesheet' href='/styles.css'></head><body>
    <div class='layout'><aside class='sidebar'><h2>{html.escape(user['username'])}'s sessions</h2>{session_html}</aside>
    <section class='chat-panel'><h1>Assistant</h1><p>Session #{active['id']}</p>
    <div class='messages'>{msg_html}</div>
    <form method='post' action='/assistant' class='composer'>
      <input type='hidden' name='chat_session_id' value='{active['id']}'>
      <div class='chips'>{rec_html}</div>
      <textarea name='message' placeholder='Ask a finance question...'></textarea>
      <button type='submit'>Send</button>
    </form></section></div></body></html>
    """


def app(environ, start_response):
    init_db()
    path = environ.get("PATH_INFO", "/")
    method = environ.get("REQUEST_METHOD", "GET")

    if path == "/styles.css":
        css = (BASE_DIR / "static" / "styles.css").read_text()
        start_response("200 OK", [("Content-Type", "text/css")])
        return [css.encode("utf-8")]

    cookies = parse_cookies(environ)
    sid = cookies.get(SESSION_COOKIE)
    user_id = sessions.get(sid) if sid else None

    if path == "/" and method == "GET":
        start_response("200 OK", [("Content-Type", "text/html")])
        return [render_login().encode("utf-8")]

    if path == "/" and method == "POST":
        form = get_form_data(environ)
        username = form.get("username", "").strip()
        user = get_or_create_user(username)
        sid = secrets.token_hex(16)
        sessions[sid] = user["id"]
        regenerate_recommendations(user["id"])
        start_response("302 Found", [("Location", "/assistant"), ("Set-Cookie", f"{SESSION_COOKIE}={sid}; Path=/")])
        return [b""]

    if path == "/assistant":
        if not user_id:
            start_response("302 Found", [("Location", "/")])
            return [b""]

        with db_conn() as db:
            user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()

        if method == "POST":
            form = get_form_data(environ)
            msg = (form.get("message") or form.get("recommended_prompt") or "").strip()
            session_id = int(form.get("chat_session_id") or 0)
            if msg:
                active = ensure_chat_session(user_id, session_id or None)
                append_message(active["id"], "user", msg)
                append_message(active["id"], "assistant", assistant_reply(msg))
                regenerate_recommendations(user_id)
                start_response("302 Found", [("Location", f"/assistant?session_id={active['id']}")])
                return [b""]

        query = parse_qs(environ.get("QUERY_STRING", ""))
        session_id = int(query.get("session_id", ["0"])[0] or 0)
        page = render_assistant(user, session_id or None)
        start_response("200 OK", [("Content-Type", "text/html")])
        return [page.encode("utf-8")]

    start_response("404 Not Found", [("Content-Type", "text/plain")])
    return [b"Not found"]


if __name__ == "__main__":
    init_db()
    print("Serving on http://localhost:5000")
    with make_server("0.0.0.0", 5000, app) as server:
        server.serve_forever()
