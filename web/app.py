"""
Flask веб-дашборд.
Использует psycopg2 (синхронный) — без конфликтов с asyncio/asyncpg бота.
"""
import os
import logging

import psycopg2
import psycopg2.extras
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from functools import wraps

log = logging.getLogger("web.app")

app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.secret_key = os.getenv("WEB_SECRET", "change_me_in_railway")

WEB_PASSWORD = os.getenv("WEB_PASSWORD", "admin123")
DATABASE_URL = os.getenv("DATABASE_URL", "")


# ── DB helper ─────────────────────────────────────────────────────────────

def get_conn():
    """Открывает новое синхронное соединение для каждого запроса."""
    return psycopg2.connect(DATABASE_URL, sslmode="require")


def query(sql, params=None, fetchone=False):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            if fetchone:
                return dict(cur.fetchone()) if cur.rowcount != 0 else {}
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ── Auth ──────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == WEB_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        error = "Неверный пароль"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── Pages ─────────────────────────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/transactions")
@login_required
def transactions_page():
    return render_template("transactions.html")


@app.route("/users")
@login_required
def users_page():
    return render_template("users.html")


# ── API ───────────────────────────────────────────────────────────────────

@app.route("/api/stats")
@login_required
def api_stats():
    try:
        row = query("""
            SELECT
                COUNT(DISTINCT user_id)  AS total_users,
                COUNT(*)                 AS total_transactions,
                COALESCE(SUM(CASE WHEN type='income'  THEN amount END), 0) AS total_income,
                COALESCE(SUM(CASE WHEN type='expense' THEN amount END), 0) AS total_expense
            FROM transactions
        """, fetchone=True)
        row["balance"] = row["total_income"] - row["total_expense"]
        return jsonify(row)
    except Exception as e:
        log.error("api_stats error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/transactions")
@login_required
def api_transactions():
    try:
        limit = min(int(request.args.get("limit", 50)), 500)
        rows = query("""
            SELECT t.id, t.user_id,
                   COALESCE(u.first_name, 'User ' || t.user_id::text) AS name,
                   COALESCE(u.username, '')  AS username,
                   t.type, t.category, t.amount,
                   to_char(t.date AT TIME ZONE 'Asia/Tashkent', 'DD.MM.YYYY HH24:MI') AS date
            FROM transactions t
            LEFT JOIN users u ON u.user_id = t.user_id
            ORDER BY t.date DESC
            LIMIT %s
        """, (limit,))
        return jsonify(rows)
    except Exception as e:
        log.error("api_transactions error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/users")
@login_required
def api_users():
    try:
        rows = query("""
            SELECT u.user_id,
                   COALESCE(u.first_name, 'User ' || u.user_id::text) AS name,
                   COALESCE(u.username, '') AS username,
                   COUNT(t.id) AS tx_count,
                   to_char(u.created_at AT TIME ZONE 'Asia/Tashkent', 'DD.MM.YYYY') AS created_at
            FROM users u
            LEFT JOIN transactions t ON t.user_id = u.user_id
            GROUP BY u.user_id
            ORDER BY u.created_at DESC
        """)
        return jsonify(rows)
    except Exception as e:
        log.error("api_users error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/categories")
@login_required
def api_categories():
    try:
        rows = query("""
            SELECT category, type,
                   COUNT(*)    AS count,
                   SUM(amount) AS total
            FROM transactions
            GROUP BY category, type
            ORDER BY total DESC
        """)
        return jsonify(rows)
    except Exception as e:
        log.error("api_categories error: %s", e)
        return jsonify({"error": str(e)}), 500


def run_web():
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
