"""
Фоновая проверка активности пользователей.
Раз в час смотрит, не наступил ли час напоминаний (config.REMINDER_HOUR по Ташкенту),
и если да — раз в день шлёт каждому пользователю:
  1) предупреждение, если расходы за 7 дней превысили порог;
  2) напоминание записать траты, если сегодня ещё ничего не вносили.
Чтобы не спамить, каждое уведомление отправляется не больше одного раза за период
(неделя для порога, день для напоминания) — это отслеживается в таблице notifications.
"""
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot

import config

log = logging.getLogger("reminders")

TZ = ZoneInfo(config.TIMEZONE)


def _week_key(now: datetime) -> str:
    iso = now.isocalendar()
    return f"{iso.year}-W{iso.week}"


def _day_key(now: datetime) -> str:
    return now.strftime("%Y-%m-%d")


async def _check_user(bot: Bot, user_id: int, now: datetime):
    from database import db

    week_total = await db.get_week_expenses(user_id)
    if week_total >= config.WEEKLY_ALERT_THRESHOLD:
        wk = _week_key(now)
        if not await db.was_notified(user_id, "weekly_threshold", wk):
            weekday = now.strftime("%A")
            try:
                await bot.send_message(
                    user_id,
                    f"👀 Бро, сегодня {weekday}, а ты за последние 7 дней уже потратил "
                    f"<b>{week_total:,} сум</b>.\n"
                    "Заходи в «📊 Статистика», глянь на что уходит — может, пора притормозить?",
                )
            except Exception as e:
                log.warning("Failed to send weekly alert to %s: %s", user_id, e)
            await db.mark_notified(user_id, "weekly_threshold", wk)

    has_today = await db.has_transaction_today(user_id)
    if not has_today:
        dk = _day_key(now)
        if not await db.was_notified(user_id, "no_entry_today", dk):
            try:
                await bot.send_message(
                    user_id,
                    "🤔 За сегодня у тебя нет ни одной записи.\n"
                    "Совсем ничего не тратил и не зарабатывал, или просто забыл записать? "
                    "Занеси хотя бы пару строк — «➕ Доход» / «➖ Расход» ждут.",
                )
            except Exception as e:
                log.warning("Failed to send daily nudge to %s: %s", user_id, e)
            await db.mark_notified(user_id, "no_entry_today", dk)


async def _run_checks(bot: Bot):
    from database import db

    now = datetime.now(TZ)
    user_ids = await db.get_all_user_ids()
    for uid in user_ids:
        try:
            await _check_user(bot, uid, now)
        except Exception as e:
            log.error("Reminder check failed for %s: %s", uid, e)


async def reminders_loop(bot: Bot):
    """Раз в час проверяет время; в назначенный час запускает проверку по всем пользователям."""
    log.info("Reminders loop started (hour=%s, tz=%s)", config.REMINDER_HOUR, config.TIMEZONE)
    last_run_key = None
    while True:
        now = datetime.now(TZ)
        run_key = _day_key(now)
        if now.hour == config.REMINDER_HOUR and last_run_key != run_key:
            log.info("Running daily reminder check")
            await _run_checks(bot)
            last_run_key = run_key
        await asyncio.sleep(60 * 30)  # проверяем время каждые 30 минут
