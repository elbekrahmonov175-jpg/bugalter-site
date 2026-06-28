import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
WEB_SECRET = os.getenv("WEB_SECRET", "change_me_in_railway")

EXPENSE_CATEGORIES = ["Еда", "Транспорт", "Покупки", "Развлечения", "Коммунальные", "Другое"]
INCOME_CATEGORIES = ["Зарплата", "Бизнес", "Подарок", "Другое"]
