import asyncio
import os
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, jsonify, request, redirect, url_for, session

app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.secret_key = os.getenv("WEB_SECRET", "change_me_in_railway")

WEB_PASSWORD = os.getenv("WEB_PASSWORD", "admin123")

# ── Helper: run async db calls from sync Flask ────────────────────────────

def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


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


# ── API endpoints ─────────────────────────────────────────────────────────

@app.route("/api/stats")
@login_required
def api_stats():
    from database import db
    stats = run_async(db.get_global_stats())
    return jsonify({
        "total_users": stats["total_users"],
        "total_transactions": stats["total_transactions"],
        "total_income": stats["total_income"],
        "total_expense": stats["total_expense"],
        "balance": stats["total_income"] - stats["total_expense"],
    })


@app.route("/api/transactions")
@login_required
def api_transactions():
    from database import db
    limit = int(request.args.get("limit", 50))
    txs = run_async(db.get_recent_transactions(limit=limit))
    result = []
    for t in txs:
        result.append({
            "id": t["id"],
            "user_id": t["user_id"],
            "name": t.get("first_name") or f"User {t['user_id']}",
            "username": t.get("username") or "",
            "type": t["type"],
            "category": t["category"],
            "amount": t["amount"],
            "date": t["date"].strftime("%d.%m.%Y %H:%M") if hasattr(t["date"], "strftime") else str(t["date"])[:16],
        })
    return jsonify(result)


@app.route("/api/users")
@login_required
def api_users():
    from database import db
    users = run_async(db.get_all_users())
    result = []
    for u in users:
        result.append({
            "user_id": u["user_id"],
            "name": u.get("first_name") or f"User {u['user_id']}",
            "username": u.get("username") or "",
            "tx_count": u["tx_count"],
            "created_at": u["created_at"].strftime("%d.%m.%Y") if hasattr(u["created_at"], "strftime") else str(u["created_at"])[:10],
        })
    return jsonify(result)


@app.route("/api/categories")
@login_required
def api_categories():
    from database import db
    cats = run_async(db.get_category_stats())
    result = []
    for c in cats:
        result.append({
            "category": c["category"],
            "type": c["type"],
            "count": c["count"],
            "total": c["total"],
        })
    return jsonify(result)


def run_web():
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
