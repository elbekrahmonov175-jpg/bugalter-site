"""
Flask веб-кабинет — личный кабинет пользователя, открывается как Telegram Mini App.

Использует psycopg2 (синхронный) — без конфликтов с asyncio/asyncpg бота.
Одна и та же таблица transactions читается и пишется и ботом, и сайтом,
поэтому доход/расход, добавленный в одном месте, сразу виден в другом.

Авторизация: Telegram Mini App initData (без паролей — вход автоматический,
как только страница открыта кнопкой из бота).
"""
import hashlib
import hmac
import json
import logging
import os
import time
from functools import wraps
from urllib.parse import parse_qsl

import psycopg2
import psycopg2.extras
from flask import Flask, render_template, jsonify, request, session

import config

log = logging.getLogger("web.app")

app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.secret_key = os.getenv("WEB_SECRET", "change_me_in_railway")

DATABASE_URL = os.getenv("DATABASE_URL", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

EXPENSE_CATEGORIES = config.EXPENSE_CATEGORIES
INCOME_CATEGORIES = config.INCOME_CATEGORIES


# ── DB helpers ────────────────────────────────────────────────────────────

def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


def query(sql, params=None, fetchone=False):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            if fetchone:
                row = cur.fetchone()
                return dict(row) if row else {}
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def execute(sql, params=None, fetchone=False):
    """Для INSERT/UPDATE с RETURNING — коммитит изменения."""
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            result = None
            if fetchone:
                row = cur.fetchone()
                result = dict(row) if row else {}
            conn.commit()
            return result
    finally:
        conn.close()


# ── Telegram Mini App auth ───────────────────────────────────────────────

def validate_init_data(init_data: str, bot_token: str, max_age: int = 86400):
    """Проверяет подпись initData по алгоритму Telegram и возвращает dict с
    данными пользователя, либо None, если подпись неверна / данные устарели."""
    if not init_data or not bot_token:
        return None
    try:
        parsed = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        return None

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        return None

    auth_date = int(parsed.get("auth_date", "0"))
    if max_age and (time.time() - auth_date) > max_age:
        return None

    user_json = parsed.get("user")
    if not user_json:
        return None
    return json.loads(user_json)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "not_authenticated"}), 401
        return f(*args, **kwargs)
    return decorated


@app.route("/api/auth", methods=["POST"])
def api_auth():
    body = request.get_json(silent=True) or {}
    init_data = body.get("initData", "")
    user = validate_init_data(init_data, BOT_TOKEN)
    if not user:
        return jsonify({"error": "invalid_init_data"}), 401

    user_id = user["id"]
    execute("""
        INSERT INTO users (user_id, username, first_name)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE
        SET username = EXCLUDED.username, first_name = EXCLUDED.first_name
    """, (user_id, user.get("username", ""), user.get("first_name", "")))

    session["user_id"] = user_id
    session["first_name"] = user.get("first_name", "")
    return jsonify({"ok": True, "first_name": session["first_name"]})


# ── Pages ─────────────────────────────────────────────────────────────────

@app.route("/")
def root():
    return render_template("landing.html")


@app.route("/app")
def app_page():
    return render_template(
        "app.html",
        expense_categories=EXPENSE_CATEGORIES,
        income_categories=INCOME_CATEGORIES,
        weekly_threshold=config.WEEKLY_ALERT_THRESHOLD,
    )


# ── Personal API (scoped to the logged-in Telegram user) ───────────────────

@app.route("/api/me")
@login_required
def api_me():
    return jsonify({"user_id": session["user_id"], "first_name": session.get("first_name", "")})


@app.route("/api/me/stats")
@login_required
def api_me_stats():
    uid = session["user_id"]
    try:
        totals = query("""
            SELECT
                COALESCE(SUM(CASE WHEN type='income'  THEN amount END), 0) AS income,
                COALESCE(SUM(CASE WHEN type='expense' THEN amount END), 0) AS expense
            FROM transactions WHERE user_id = %s
        """, (uid,), fetchone=True)
        today = query("""
            SELECT COALESCE(SUM(amount), 0) AS total FROM transactions
            WHERE user_id = %s AND type = 'expense' AND date::date = NOW()::date
        """, (uid,), fetchone=True)
        week = query("""
            SELECT COALESCE(SUM(amount), 0) AS total FROM transactions
            WHERE user_id = %s AND type = 'expense' AND date >= NOW() - INTERVAL '7 days'
        """, (uid,), fetchone=True)
        month = query("""
            SELECT COALESCE(SUM(amount), 0) AS total FROM transactions
            WHERE user_id = %s AND type = 'expense'
              AND date_trunc('month', date) = date_trunc('month', NOW())
        """, (uid,), fetchone=True)
        return jsonify({
            "income": totals["income"],
            "expense": totals["expense"],
            "balance": totals["income"] - totals["expense"],
            "today_expense": today["total"],
            "week_expense": week["total"],
            "month_expense": month["total"],
            "weekly_threshold": config.WEEKLY_ALERT_THRESHOLD,
        })
    except Exception as e:
        log.error("api_me_stats error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/me/transactions", methods=["GET"])
@login_required
def api_me_transactions_get():
    uid = session["user_id"]
    try:
        limit = min(int(request.args.get("limit", 30)), 500)
        rows = query("""
            SELECT id, type, category, amount,
                   to_char(date AT TIME ZONE 'Asia/Tashkent', 'DD.MM.YYYY HH24:MI') AS date
            FROM transactions WHERE user_id = %s
            ORDER BY date DESC LIMIT %s
        """, (uid, limit))
        return jsonify(rows)
    except Exception as e:
        log.error("api_me_transactions_get error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/me/transactions", methods=["POST"])
@login_required
def api_me_transactions_post():
    uid = session["user_id"]
    body = request.get_json(silent=True) or {}
    type_ = body.get("type")
    category = body.get("category")
    amount = body.get("amount")

    if type_ not in ("income", "expense"):
        return jsonify({"error": "invalid_type"}), 400
    valid_categories = INCOME_CATEGORIES if type_ == "income" else EXPENSE_CATEGORIES
    if category not in valid_categories:
        return jsonify({"error": "invalid_category"}), 400
    try:
        amount = int(amount)
        if amount <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_amount"}), 400

    try:
        row = execute("""
            INSERT INTO transactions (user_id, type, category, amount)
            VALUES (%s, %s, %s, %s)
            RETURNING id, date
        """, (uid, type_, category, amount), fetchone=True)
        return jsonify({"ok": True, "id": row["id"]})
    except Exception as e:
        log.error("api_me_transactions_post error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/me/categories")
@login_required
def api_me_categories():
    uid = session["user_id"]
    try:
        rows = query("""
            SELECT category, type, COUNT(*) AS count, SUM(amount) AS total
            FROM transactions WHERE user_id = %s
            GROUP BY category, type ORDER BY total DESC
        """, (uid,))
        return jsonify(rows)
    except Exception as e:
        log.error("api_me_categories error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/me/convert", methods=["POST"])
@login_required
def api_me_convert():
    uid = session["user_id"]
    body = request.get_json(silent=True) or {}
    try:
        cash_amount = int(body.get("cash_amount"))
        fee_percent = float(body.get("fee_percent"))
        if cash_amount <= 0 or not (0 <= fee_percent <= 100):
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_input"}), 400

    fee_amount = round(cash_amount * fee_percent / 100)
    net_amount = cash_amount - fee_amount

    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO conversions (user_id, cash_amount, fee_percent, fee_amount, net_amount)
                VALUES (%s, %s, %s, %s, %s) RETURNING id, date
            """, (uid, cash_amount, fee_percent, fee_amount, net_amount))
            row = dict(cur.fetchone())
            cur.execute("""
                INSERT INTO transactions (user_id, type, category, amount)
                VALUES (%s, 'expense', 'Комиссия за обмен', %s)
            """, (uid, fee_amount))
        conn.commit()
    except Exception as e:
        conn.rollback()
        log.error("api_me_convert error: %s", e)
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

    return jsonify({
        "ok": True, "id": row["id"],
        "cash_amount": cash_amount, "fee_percent": fee_percent,
        "fee_amount": fee_amount, "net_amount": net_amount,
    })


@app.route("/api/me/conversions")
@login_required
def api_me_conversions():
    uid = session["user_id"]
    try:
        rows = query("""
            SELECT id, cash_amount, fee_percent, fee_amount, net_amount,
                   to_char(date AT TIME ZONE 'Asia/Tashkent', 'DD.MM.YYYY HH24:MI') AS date
            FROM conversions WHERE user_id = %s
            ORDER BY date DESC LIMIT 20
        """, (uid,))
        return jsonify(rows)
    except Exception as e:
        log.error("api_me_conversions error: %s", e)
        return jsonify({"error": str(e)}), 500


def run_web():
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
