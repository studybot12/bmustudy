import os

# ─── ОБЯЗАТЕЛЬНО ЗАМЕНИТЬ ─────────────────────────────────────────────────────
ADMIN_ID = int(os.environ.get("ADMIN_ID", "891692774"))   # Твой Telegram ID
CARD_NUMBER = os.environ.get("CARD_NUMBER", "ДОБАВЬ_НОМЕР_КАРТЫ")  # Номер карты
PRICE_PER_SUBJECT = int(os.environ.get("PRICE_PER_SUBJECT", "50000"))  # Цена за 1 предмет (не используется при оплате за курс)

# ─── ЦЕНЫ ЗА КУРС ─────────────────────────────────────────────────────────────
COURSE_PRICES = {
    "1": int(os.environ.get("PRICE_COURSE_1", "50000")),   # Цена за 1 курс (QM) в сумах
    "2": int(os.environ.get("PRICE_COURSE_2", "200000")),  # Цена за 2 курс (F1, F3, FM, Macro, HRM) в сумах
}
