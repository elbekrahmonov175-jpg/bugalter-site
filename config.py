import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
WEB_SECRET = os.getenv("WEB_SECRET", "change_me_in_railway")

# Публичный адрес сайта (Mini App). Например: https://bugalterbot.up.railway.app
# Используется и в боте (кнопка "Кабинет"), и в самом сайте.
WEBAPP_URL = os.getenv("WEBAPP_URL", "")

EXPENSE_CATEGORIES = ["Еда", "Транспорт", "Покупки", "Развлечения", "Коммунальные", "Другое"]
INCOME_CATEGORIES = ["Зарплата", "Бизнес", "Подарок", "Другое"]

# ── Напоминания и советы ────────────────────────────────────────────────────

# Если расходы за последние 7 дней превышают эту сумму — присылаем уведомление
WEEKLY_ALERT_THRESHOLD = int(os.getenv("WEEKLY_ALERT_THRESHOLD", "200000"))

# Час дня (по Ташкенту), в который бот проверяет активность пользователей
REMINDER_HOUR = int(os.getenv("REMINDER_HOUR", "20"))

TIMEZONE = "Asia/Tashkent"
