# FinanceBot + Dashboard

Телеграм-бот для учёта финансов с веб-дашбордом.

## Структура

```
financebot/
├── main.py              # Точка входа (бот + веб-сервер)
├── config.py            # Настройки
├── database.py          # PostgreSQL через asyncpg
├── requirements.txt
├── Procfile
├── railway.toml
├── handlers/
│   ├── __init__.py
│   ├── start.py
│   ├── income.py
│   ├── expense.py
│   ├── balance.py
│   ├── stats.py
│   ├── history.py
│   └── debts.py
├── web/
│   ├── __init__.py
│   └── app.py           # Flask дашборд
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── index.html
│   ├── transactions.html
│   └── users.html
└── static/
    └── css/
        └── style.css
```

## Railway: переменные окружения

| Переменная   | Описание                              |
|--------------|---------------------------------------|
| BOT_TOKEN    | Токен от @BotFather                   |
| DATABASE_URL | Автоматически от Railway PostgreSQL   |
| WEB_SECRET   | Секрет для Flask сессий (любая строка)|
| WEB_PASSWORD | Пароль для входа на дашборд           |
| PORT         | Railway задаёт автоматически          |

## Деплой

1. Создай проект на Railway
2. Добавь **PostgreSQL** сервис (DATABASE_URL подставится автоматически)
3. Загрузи код через GitHub или Railway CLI
4. Установи переменные из таблицы выше
5. Убедись что в настройках сервиса есть **Public Domain** (для дашборда)
6. Deploy!

## Дашборд

Открой Public Domain из Railway — увидишь страницу входа.  
Пароль = значение `WEB_PASSWORD` (по умолчанию `admin123`).

Страницы:
- `/` — Обзор: общая статистика, последние транзакции, топ категории
- `/transactions` — Таблица всех транзакций с фильтрами
- `/users` — Список пользователей бота
