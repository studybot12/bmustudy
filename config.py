import os

# ─── ОБЯЗАТЕЛЬНО ЗАМЕНИТЬ ─────────────────────────────────────────────────────
ADMIN_ID = int(os.environ.get("ADMIN_ID", "891692774"))   # Твой Telegram ID
CARD_NUMBER = os.environ.get("CARD_NUMBER", "ДОБАВЬ_НОМЕР_КАРТЫ")  # Номер карты
PRICE_PER_SUBJECT = int(os.environ.get("PRICE_PER_SUBJECT", "50000"))  # Цена в сумах
