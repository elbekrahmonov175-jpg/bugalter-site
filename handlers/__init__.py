from aiogram import Router


def get_handlers_router() -> Router:
    from . import start, income, expense, balance, stats, history, debts

    router = Router()
    router.include_router(start.router)
    router.include_router(income.router)
    router.include_router(expense.router)
    router.include_router(balance.router)
    router.include_router(stats.router)
    router.include_router(history.router)
    router.include_router(debts.router)
    return router
