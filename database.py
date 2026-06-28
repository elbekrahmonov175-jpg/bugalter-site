import os
import asyncpg
from typing import Optional, List, Dict, Any
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")

_pool = None


async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    return _pool


class Database:
    async def init_db(self):
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    type VARCHAR(10) NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    amount INTEGER NOT NULL,
                    date TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS debts (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    person_name VARCHAR(100) NOT NULL,
                    amount INTEGER NOT NULL,
                    type VARCHAR(10) NOT NULL,
                    date TIMESTAMPTZ DEFAULT NOW(),
                    is_paid BOOLEAN DEFAULT FALSE
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(100),
                    first_name VARCHAR(100),
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

    async def upsert_user(self, user_id: int, username: str, first_name: str):
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (user_id, username, first_name)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id) DO UPDATE
                SET username = EXCLUDED.username, first_name = EXCLUDED.first_name
            """, user_id, username, first_name)

    async def add_transaction(self, user_id: int, type_: str, category: str, amount: int):
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO transactions (user_id, type, category, amount)
                VALUES ($1, $2, $3, $4)
                RETURNING id, date
            """, user_id, type_, category, amount)
            return dict(row)

    async def get_balance(self, user_id: int) -> Dict[str, int]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) AS income,
                    COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) AS expense
                FROM transactions WHERE user_id = $1
            """, user_id)
            income = row["income"]
            expense = row["expense"]
            return {"income": income, "expense": expense, "balance": income - expense}

    async def get_today_expenses(self, user_id: int) -> int:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT COALESCE(SUM(amount), 0) AS total
                FROM transactions
                WHERE user_id = $1 AND type = 'expense' AND date::date = NOW()::date
            """, user_id)
            return row["total"]

    async def get_month_expenses(self, user_id: int) -> int:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT COALESCE(SUM(amount), 0) AS total
                FROM transactions
                WHERE user_id = $1 AND type = 'expense'
                  AND date_trunc('month', date) = date_trunc('month', NOW())
            """, user_id)
            return row["total"]

    async def get_top_category(self, user_id: int) -> Optional[str]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT category, COUNT(*) AS cnt, SUM(amount) AS total
                FROM transactions
                WHERE user_id = $1 AND type = 'expense'
                GROUP BY category
                ORDER BY cnt DESC, total DESC
                LIMIT 1
            """, user_id)
            if not row:
                return None
            return f"{row['category']} ({row['cnt']} раз, {row['total']} сум)"

    async def get_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, user_id, type, category, amount, date
                FROM transactions WHERE user_id = $1
                ORDER BY date DESC LIMIT $2
            """, user_id, limit)
            return [dict(r) for r in rows]

    async def get_all_transactions(self, user_id: int) -> List[Dict[str, Any]]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, user_id, type, category, amount, date
                FROM transactions WHERE user_id = $1 ORDER BY date DESC
            """, user_id)
            return [dict(r) for r in rows]

    async def add_debt(self, user_id: int, person_name: str, amount: int, type_: str):
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO debts (user_id, person_name, amount, type)
                VALUES ($1, $2, $3, $4)
            """, user_id, person_name, amount, type_)

    async def get_debts(self, user_id: int, is_paid: bool = False) -> List[Dict[str, Any]]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, user_id, person_name, amount, type, date, is_paid
                FROM debts WHERE user_id = $1 AND is_paid = $2
                ORDER BY date DESC
            """, user_id, is_paid)
            return [dict(r) for r in rows]

    async def mark_debt_paid(self, debt_id: int, user_id: int) -> bool:
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE debts SET is_paid = TRUE
                WHERE id = $1 AND user_id = $2
            """, debt_id, user_id)
            return result == "UPDATE 1"

    # ── Web API methods ──────────────────────────────────────────────────────

    async def get_all_users(self) -> List[Dict[str, Any]]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT u.user_id, u.username, u.first_name, u.created_at,
                       COUNT(t.id) AS tx_count
                FROM users u
                LEFT JOIN transactions t ON t.user_id = u.user_id
                GROUP BY u.user_id
                ORDER BY u.created_at DESC
            """)
            return [dict(r) for r in rows]

    async def get_recent_transactions(self, limit: int = 50) -> List[Dict[str, Any]]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT t.id, t.user_id, u.first_name, u.username,
                       t.type, t.category, t.amount, t.date
                FROM transactions t
                LEFT JOIN users u ON u.user_id = t.user_id
                ORDER BY t.date DESC LIMIT $1
            """, limit)
            return [dict(r) for r in rows]

    async def get_global_stats(self) -> Dict[str, Any]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    COUNT(DISTINCT user_id) AS total_users,
                    COUNT(*) AS total_transactions,
                    COALESCE(SUM(CASE WHEN type='income' THEN amount END), 0) AS total_income,
                    COALESCE(SUM(CASE WHEN type='expense' THEN amount END), 0) AS total_expense
                FROM transactions
            """)
            return dict(row)

    async def get_category_stats(self) -> List[Dict[str, Any]]:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT category, type,
                       COUNT(*) AS count,
                       SUM(amount) AS total
                FROM transactions
                GROUP BY category, type
                ORDER BY total DESC
            """)
            return [dict(r) for r in rows]


db = Database()
