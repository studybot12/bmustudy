import logging
import os
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)
from database import db
from content import SUBJECTS, get_subject_info, get_flashcards, get_quiz_questions, get_cheatsheet, get_glossary
from config import ADMIN_ID, CARD_NUMBER, PRICE_PER_SUBJECT
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
SUBJECT_PHOTOS = {
    "f1": "https://raw.githubusercontent.com/studybot12/bmustudy/main/f1.png",
    "f3": "https://raw.githubusercontent.com/studybot12/bmustudy/main/f3.png",
    "fm": "https://raw.githubusercontent.com/studybot12/bmustudy/main/fm.png",
    "macro": "https://raw.githubusercontent.com/studybot12/bmustudy/main/macro.png",
}

logger = logging.getLogger(__name__)

(CHOOSING_LANG, MAIN_MENU, CHOOSING_SUBJECT, PAYMENT_SCREENSHOT,
 SUBJECT_MENU, QUIZ_SESSION, FLASHCARD_SESSION, TRIAL_SESSION,
 AI_CHAT_SESSION, BOOKMARKS_SESSION) = range(10)

FREE_QUESTIONS = 3
QUIZ_QUESTIONS_COUNT = 20

TEXTS = {
    "ru": {
        "welcome": "👋 Привет! Добро пожаловать в *Study Hub BMU*\n\nВыберите язык интерфейса:",
        "main_menu": "📚 *Study Hub — British Management University*\n\nВыберите действие:",
        "my_subjects": "📖 Мои предметы",
        "buy_access": "🛒 Купить доступ",
        "trial_quiz": "🎯 Пробный тест",
        "help": "❓ Помощь",
        "choose_subject_buy": "Выберите предмет для покупки доступа:",
        "choose_subject_study": "Выберите предмет для изучения:",
        "choose_trial_subject": "Выберите предмет для пробного теста (бесплатно):",
        "payment_instruction": "💳 *Оплата доступа к «{subject}»*\n\nСтоимость: *{price:,} сум*\n\nПереведите на карту:\n`{card}`\n\nПосле перевода отправьте скриншот подтверждения 👇",
        "screenshot_received": "✅ Скриншот получен! Ваша оплата проверяется.\n\nОбычно это занимает до 30 минут. Вы получите уведомление как только доступ будет открыт.",
        "access_granted": "🎉 *Доступ открыт!*\n\nПредмет *{subject}* теперь доступен в разделе «Мои предметы».",
        "access_denied": "❌ Оплата не подтверждена. Пожалуйста, свяжитесь с администратором.",
        "no_subjects": "У вас пока нет купленных предметов.\n\nПерейдите в раздел «Купить доступ» 🛒",
        "subject_menu": "📘 *{subject}*\n\nВыберите режим:",
        "study_materials": "📖 Конспект",
        "flashcards": "🃏 Флэшкарты",
        "quiz": "✏️ Тест (MCQ)",
        "progress": "📊 Мой прогресс",
        "back": "← Назад",
        "quiz_start": "🧠 *Тест: {subject}*\n\nВопрос {num}/{total}:\n\n{question}",
        "correct": "✅ *Верно!*\n\n{explanation}",
        "wrong": "❌ *Неверно.*\nПравильный ответ: *{correct}*\n\n{explanation}",
        "quiz_done": "🏁 *Тест завершён!*\n\nРезультат: *{score}/{total}*\n{grade}\n\nНажмите кнопку для продолжения:",
        "flashcard_front": "🃏 *Флэшкарта {num}/{total}*\n\n❓ {term}",
        "flashcard_back": "💡 *Ответ:*\n\n{definition}",
        "show_answer": "👁 Показать ответ",
        "next_card": "➡️ Следующая",
        "prev_card": "⬅️ Предыдущая",
        "finish_flashcards": "✅ Завершить",
        "flashcards_done": "🎉 Флэшкарты пройдены! Удачи на экзамене!",
        "help_text": "❓ *Помощь*\n\nПо вопросам оплаты и доступа обратитесь к администратору.\n\nБот работает 24/7. После оплаты доступ открывается в течение 30 минут.",
        "already_has_access": "✅ У вас уже есть доступ к этому предмету!",
        "restart_quiz": "🔄 Новый тест",
        "back_to_subject": "📘 К предмету",
        "grade_excellent": "🌟 Отлично! Вы готовы к экзамену!",
        "grade_good": "👍 Хороший результат! Повторите слабые темы.",
        "grade_ok": "📚 Неплохо, но стоит поучить ещё.",
        "grade_bad": "💪 Не сдавайтесь! Изучите материал и попробуйте снова.",
        "trial_question": "🎯 *Пробный тест: {subject}*\n\nВопрос {num}/3:\n\n{question}",
        "trial_done": "🏁 *Пробный тест завершён!*\n\nВаш результат: *{score}/3*\n\n💡 Понравилось? В полной версии:\n• ✏️ 20 вопросов MCQ\n• 📖 Полный конспект\n• 🃏 Флэшкарты\n• 📊 Ваш прогресс\n\n👇 Купите доступ прямо сейчас!",
        "buy_now": "🛒 Купить полный доступ",
        "progress_text": "📊 *Ваш прогресс — {subject}*\n\n✏️ Тестов пройдено: *{tests}*\nСредний балл: *{avg}%*\nЛучший результат: *{best}%*\n\n🃏 Флэшкарт изучено: *{cards}*",
        "no_progress": "📊 Вы ещё не проходили тесты по этому предмету.\n\nНачните прямо сейчас! ✏️",
        "promo_enter": "🎁 Введите промокод:",
        "promo_valid": "🎉 Промокод активирован! Скидка {discount}%\n\nСтоимость со скидкой: *{price:,} сум*",
        "promo_invalid": "❌ Неверный промокод. Попробуйте ещё раз или нажмите Назад.",
        "enter_promo": "🎁 У меня есть промокод",
        "stats_title": "📈 *Статистика бота*\n\n👥 Всего студентов: *{users}*\n💰 Оплаченных доступов: *{paid}*\n💵 Выручка: *{revenue:,} сум*\n\n📘 По предметам:",
        # AI Chat
        "ai_chat": "🤖 ИИ-преподаватель",
        "ai_chat_intro": "🤖 *ИИ-преподаватель — {subject}*\n\nЗадайте любой вопрос по предмету. Я объясню, приведу примеры и помогу разобраться!\n\n_Введите вопрос:_",
        "ai_thinking": "⏳ Думаю...",
        "ai_clear": "🗑 Очистить историю",
        "ai_history_cleared": "✅ История чата очищена.",
        "ai_unavailable": "⚠️ ИИ-чат временно недоступен. Установите пакет `anthropic` и добавьте `ANTHROPIC_API_KEY`.",
        # Quiz history
        "quiz_history": "📋 История тестов",
        "quiz_history_empty": "📋 Вы ещё не проходили тесты.\n\nНачните прямо сейчас! ✏️",
        "quiz_history_title": "📋 *История тестов — {subject}*\n\n",
        "quiz_history_all": "📋 *Все тесты*\n\n",
        # Bookmarks
        "bookmarks": "🔖 Закладки",
        "bookmark_saved": "🔖 Вопрос добавлен в закладки!",
        "bookmark_exists": "✅ Уже в закладках.",
        "bookmarks_empty": "🔖 Закладок пока нет.\n\nВо время теста нажимайте 🔖, чтобы сохранить сложный вопрос.",
        "bookmarks_title": "🔖 *Мои закладки*\n\n",
        "bookmark_delete": "🗑 Удалить",
        "bookmark_deleted": "✅ Закладка удалена.",
        # Language change
        "change_lang": "🌐 Сменить язык",
        # Cheatsheet
        "cheatsheet": "📝 Мини-конспект",
        "cheatsheet_title": "📝 *Мини-конспект: {subject}*\n\n",
        # Glossary
        "glossary": "📖 Глоссарий",
        # XP / Streak / Leaderboard
        "leaderboard": "🏆 Лидерборд",
        "my_rank": "📊 Мой рейтинг",
        "xp_earned": "⚡ +{xp} XP заработано!",
        "level_up": "🎉 *Новый уровень!* Вы достигли уровня *{level}*!",
        "streak_bonus": "🔥 Бонус за серию +{bonus} XP!",
        "leaderboard_title": "🏆 *Лидерборд — BMU Study Hub*\n\n",
        "my_stats": "⚡ *Мои достижения*\n\n🏅 Уровень: *{level}* {badge}\n⚡ XP: *{xp}*\n🔥 Серия: *{streak}* дней\n\n{progress_bar}\nДо следующего уровня: *{xp_needed}* XP",

        "glossary_intro": "📖 *Глоссарий — {subject}*\n\nВведите термин для поиска:",
        "glossary_not_found": "❌ Термин не найден. Попробуйте другое слово.",
    },
    "en": {
        "welcome": "👋 Hello! Welcome to *Study Hub BMU*\n\nChoose your language:",
        "main_menu": "📚 *Study Hub — British Management University*\n\nChoose an action:",
        "my_subjects": "📖 My Subjects",
        "buy_access": "🛒 Buy Access",
        "trial_quiz": "🎯 Free Trial",
        "help": "❓ Help",
        "choose_subject_buy": "Choose a subject to purchase access:",
        "choose_subject_study": "Choose a subject to study:",
        "choose_trial_subject": "Choose a subject for free trial:",
        "payment_instruction": "💳 *Payment for «{subject}»*\n\nPrice: *{price:,} UZS*\n\nTransfer to card:\n`{card}`\n\nAfter payment, send a screenshot 👇",
        "screenshot_received": "✅ Screenshot received! Your payment is being reviewed.\n\nThis usually takes up to 30 minutes. You'll get a notification once access is granted.",
        "access_granted": "🎉 *Access Granted!*\n\n*{subject}* is now available in «My Subjects».",
        "access_denied": "❌ Payment not confirmed. Please contact the admin.",
        "no_subjects": "You don't have any subjects yet.\n\nGo to «Buy Access» 🛒",
        "subject_menu": "📘 *{subject}*\n\nChoose a mode:",
        "study_materials": "📖 Study Notes",
        "flashcards": "🃏 Flashcards",
        "quiz": "✏️ Practice Test (MCQ)",
        "progress": "📊 My Progress",
        "back": "← Back",
        "quiz_start": "🧠 *Quiz: {subject}*\n\nQuestion {num}/{total}:\n\n{question}",
        "correct": "✅ *Correct!*\n\n{explanation}",
        "wrong": "❌ *Wrong.*\nCorrect answer: *{correct}*\n\n{explanation}",
        "quiz_done": "🏁 *Quiz Complete!*\n\nScore: *{score}/{total}*\n{grade}\n\nPress a button to continue:",
        "flashcard_front": "🃏 *Flashcard {num}/{total}*\n\n❓ {term}",
        "flashcard_back": "💡 *Answer:*\n\n{definition}",
        "show_answer": "👁 Show Answer",
        "next_card": "➡️ Next",
        "prev_card": "⬅️ Previous",
        "finish_flashcards": "✅ Finish",
        "flashcards_done": "🎉 Flashcards complete! Good luck on your exam!",
        "help_text": "❓ *Help*\n\nFor payment & access issues contact the admin.\n\nBot runs 24/7. Access is granted within 30 minutes after payment.",
        "already_has_access": "✅ You already have access to this subject!",
        "restart_quiz": "🔄 New Quiz",
        "back_to_subject": "📘 Back to Subject",
        "grade_excellent": "🌟 Excellent! You're ready for the exam!",
        "grade_good": "👍 Good result! Review your weak areas.",
        "grade_ok": "📚 Not bad, but keep studying.",
        "grade_bad": "💪 Don't give up! Study the material and try again.",
        "trial_question": "🎯 *Trial: {subject}*\n\nQuestion {num}/3:\n\n{question}",
        "trial_done": "🏁 *Trial Complete!*\n\nYour score: *{score}/3*\n\n💡 Liked it? Full version includes:\n• ✏️ 20 MCQ questions\n• 📖 Full study notes\n• 🃏 Flashcards\n• 📊 Your progress\n\n👇 Buy access now!",
        "buy_now": "🛒 Buy Full Access",
        "progress_text": "📊 *Your Progress — {subject}*\n\n✏️ Tests taken: *{tests}*\nAverage score: *{avg}%*\nBest result: *{best}%*\n\n🃏 Flashcards studied: *{cards}*",
        "no_progress": "📊 You haven't taken any tests for this subject yet.\n\nStart now! ✏️",
        "promo_enter": "🎁 Enter your promo code:",
        "promo_valid": "🎉 Promo code applied! Discount: {discount}%\nNew price: *{price:,} UZS*",
        "promo_invalid": "❌ Invalid promo code. Try again or press Back.",
        "enter_promo": "🎁 I have a promo code",
        "stats_title": "📈 *Bot Statistics*\n\n👥 Total students: *{users}*\n💰 Paid accesses: *{paid}*\n💵 Revenue: *{revenue:,} UZS*\n\n📘 By subject:",
        # AI Chat
        "ai_chat": "🤖 AI Tutor",
        "ai_chat_intro": "🤖 *AI Tutor — {subject}*\n\nAsk any question about the subject. I'll explain, give examples, and help you understand!\n\n_Enter your question:_",
        "ai_thinking": "⏳ Thinking...",
        "ai_clear": "🗑 Clear history",
        "ai_history_cleared": "✅ Chat history cleared.",
        "ai_unavailable": "⚠️ AI chat is temporarily unavailable. Install `anthropic` package and add `ANTHROPIC_API_KEY`.",
        # Quiz history
        "quiz_history": "📋 Test History",
        "quiz_history_empty": "📋 You haven't taken any tests yet.\n\nStart now! ✏️",
        "quiz_history_title": "📋 *Test History — {subject}*\n\n",
        "quiz_history_all": "📋 *All Tests*\n\n",
        # Bookmarks
        "bookmarks": "🔖 Bookmarks",
        "bookmark_saved": "🔖 Question saved to bookmarks!",
        "bookmark_exists": "✅ Already bookmarked.",
        "bookmarks_empty": "🔖 No bookmarks yet.\n\nDuring a quiz, press 🔖 to save a tricky question.",
        "bookmarks_title": "🔖 *My Bookmarks*\n\n",
        "bookmark_delete": "🗑 Delete",
        "bookmark_deleted": "✅ Bookmark deleted.",
        # Language change
        "change_lang": "🌐 Change Language",
        # Cheatsheet
        "cheatsheet": "📝 Cheat Sheet",
        "cheatsheet_title": "📝 *Cheat Sheet: {subject}*\n\n",
        # Glossary
        "glossary": "📖 Glossary",
        # XP / Streak / Leaderboard
        "leaderboard": "🏆 Leaderboard",
        "my_rank": "📊 My Rank",
        "xp_earned": "⚡ +{xp} XP earned!",
        "level_up": "🎉 *Level Up!* You reached level *{level}*!",
        "streak_bonus": "🔥 Streak bonus +{bonus} XP!",
        "leaderboard_title": "🏆 *Leaderboard — BMU Study Hub*\n\n",
        "my_stats": "⚡ *My Achievements*\n\n🏅 Level: *{level}* {badge}\n⚡ XP: *{xp}*\n🔥 Streak: *{streak}* days\n\n{progress_bar}\nTo next level: *{xp_needed}* XP",

        "glossary_intro": "📖 *Glossary — {subject}*\n\nEnter a term to search:",
        "glossary_not_found": "❌ Term not found. Try another word.",
    }
}

def t(user_id, key, **kwargs):
    lang = db.get_user_lang(user_id) or "en"
    text = TEXTS[lang].get(key, key)
    return text.format(**kwargs) if kwargs else text


# ── /start ────────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
         InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
    ]
    await update.message.reply_text(
        "👋 *Study Hub BMU*\n\nChoose language / Выберите язык:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSING_LANG

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split("_")[1]
    user = query.from_user
    db.upsert_user(user.id, user.username or "", user.first_name or "", lang)
    await show_main_menu(query.message, user.id, edit=True)
    return MAIN_MENU

async def show_main_menu(message, user_id, edit=False):
    keyboard = [
        [InlineKeyboardButton(t(user_id, "my_subjects"), callback_data="menu_my_subjects")],
        [InlineKeyboardButton(t(user_id, "buy_access"), callback_data="menu_buy_access")],
        [InlineKeyboardButton(t(user_id, "trial_quiz"), callback_data="menu_trial")],
        [InlineKeyboardButton(t(user_id, "bookmarks"), callback_data="menu_bookmarks"),
         InlineKeyboardButton(t(user_id, "change_lang"), callback_data="menu_change_lang")],
        [InlineKeyboardButton(t(user_id, "leaderboard"), callback_data="menu_leaderboard"),
         InlineKeyboardButton(t(user_id, "my_rank"), callback_data="menu_my_rank")],
        [InlineKeyboardButton(t(user_id, "help"), callback_data="menu_help")],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    text = t(user_id, "main_menu")
    if edit:
        await message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await message.reply_text(text, parse_mode="Markdown", reply_markup=markup)


# ── ADMIN COMMANDS ─────────────────────────────────────────────────────────────

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    stats = db.get_stats()
    lang = "ru"
    text = TEXTS[lang]["stats_title"].format(
        users=stats["users"],
        paid=stats["paid"],
        revenue=stats["paid"] * PRICE_PER_SUBJECT
    )
    for key, info in SUBJECTS.items():
        count = stats["by_subject"].get(key, 0)
        text += f"\n• {info['name']}: *{count}* чел."
    await update.message.reply_text(text, parse_mode="Markdown")

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    users = db.get_all_users_with_subjects()
    if not users:
        await update.message.reply_text("Нет студентов.")
        return
    text = "👥 *Список студентов:*\n\n"
    for u in users[:30]:
        username = f"@{u['username']}" if u['username'] else "без username"
        subjects = ", ".join(u['subjects']) if u['subjects'] else "нет"
        text += f"• {u['first_name']} ({username}) — {subjects}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def add_promo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Использование: /addpromo КОД СКИДКА\nПример: /addpromo FRIEND50 50")
        return
    code, discount = args[0].upper(), int(args[1])
    db.add_promo(code, discount)
    await update.message.reply_text(f"✅ Промокод *{code}* со скидкой *{discount}%* добавлен!", parse_mode="Markdown")


# ── MAIN MENU HANDLER ─────────────────────────────────────────────────────────

async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    action = query.data

    if action == "menu_my_subjects":
        subjects = db.get_user_subjects(user_id)
        if not subjects:
            keyboard = [[InlineKeyboardButton(t(user_id, "buy_access"), callback_data="menu_buy_access")],
                        [InlineKeyboardButton(t(user_id, "back"), callback_data="back_main")]]
            await query.message.edit_text(t(user_id, "no_subjects"), parse_mode="Markdown",
                                          reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            buttons = [[InlineKeyboardButton(f"📘 {SUBJECTS[s]['name']}", callback_data=f"study_{s}")] for s in subjects if s in SUBJECTS]
            buttons.append([InlineKeyboardButton(t(user_id, "back"), callback_data="back_main")])
            await query.message.edit_text(t(user_id, "choose_subject_study"), parse_mode="Markdown",
                                          reply_markup=InlineKeyboardMarkup(buttons))
        return CHOOSING_SUBJECT

    elif action == "menu_buy_access":
        subjects = db.get_user_subjects(user_id)
        buttons = []
        for key, info in SUBJECTS.items():
            if key in subjects:
                buttons.append([InlineKeyboardButton(f"✅ {info['name']}", callback_data=f"already_{key}")])
            else:
                buttons.append([InlineKeyboardButton(f"🛒 {info['name']}", callback_data=f"buy_{key}")])
        buttons.append([InlineKeyboardButton(t(user_id, "back"), callback_data="back_main")])
        await query.message.edit_text(t(user_id, "choose_subject_buy"), parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(buttons))
        return CHOOSING_SUBJECT

    elif action == "menu_trial":
        buttons = [[InlineKeyboardButton(f"🎯 {info['name']}", callback_data=f"trial_{key}")] for key, info in SUBJECTS.items()]
        buttons.append([InlineKeyboardButton(t(user_id, "back"), callback_data="back_main")])
        await query.message.edit_text(t(user_id, "choose_trial_subject"), parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(buttons))
        return CHOOSING_SUBJECT

    elif action == "menu_help":
        keyboard = [[InlineKeyboardButton(t(user_id, "back"), callback_data="back_main")]]
        await query.message.edit_text(t(user_id, "help_text"), parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(keyboard))
        return MAIN_MENU

    elif action == "menu_change_lang":
        keyboard = [
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
             InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
            [InlineKeyboardButton(t(user_id, "back"), callback_data="back_main")]
        ]
        await query.message.edit_text("🌐 Выберите язык / Choose language:",
                                      reply_markup=InlineKeyboardMarkup(keyboard))
        return MAIN_MENU

    elif action == "menu_leaderboard":
        await show_leaderboard(query.message, user_id, edit=True)
        return MAIN_MENU

    elif action == "menu_my_rank":
        await show_my_rank(query.message, user_id, edit=True)
        return MAIN_MENU

    elif action == "menu_bookmarks":
        await show_bookmarks(query.message, user_id, edit=True)
        return BOOKMARKS_SESSION

    elif action == "back_main":
        await show_main_menu(query.message, user_id, edit=True)
        return MAIN_MENU


# ── SUBJECT SELECTION ─────────────────────────────────────────────────────────

async def subject_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "back_main":
        await show_main_menu(query.message, user_id, edit=True)
        return MAIN_MENU

    if data == "back_to_buy_list":
        # Back from payment photo screen - send new message with buy list
        subjects = db.get_user_subjects(user_id)
        buttons = []
        for key, info in SUBJECTS.items():
            if key in subjects:
                buttons.append([InlineKeyboardButton(f"✅ {info["name"]}", callback_data=f"already_{key}")])
            else:
                buttons.append([InlineKeyboardButton(f"🛒 {info["name"]}", callback_data=f"buy_{key}")])
        buttons.append([InlineKeyboardButton(t(user_id, "back"), callback_data="back_main")])
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(t(user_id, "choose_subject_buy"), parse_mode="Markdown",
                                              reply_markup=InlineKeyboardMarkup(buttons))
        return CHOOSING_SUBJECT

    if data == "menu_buy_access":
        subjects = db.get_user_subjects(user_id)
        buttons = []
        for key, info in SUBJECTS.items():
            if key in subjects:
                buttons.append([InlineKeyboardButton(f"✅ {info['name']}", callback_data=f"already_{key}")])
            else:
                buttons.append([InlineKeyboardButton(f"🛒 {info['name']}", callback_data=f"buy_{key}")])
        buttons.append([InlineKeyboardButton(t(user_id, "back"), callback_data="back_main")])
        await query.message.edit_text(t(user_id, "choose_subject_buy"), parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(buttons))
        return CHOOSING_SUBJECT

    if data.startswith("already_"):
        await query.answer(t(user_id, "already_has_access"), show_alert=True)
        return CHOOSING_SUBJECT

    if data.startswith("trial_"):
        subject_key = data.split("_", 1)[1]
        # Check if trial already used for this subject
        if db.has_used_trial(user_id, subject_key):
            lang = db.get_user_lang(user_id) or "en"
            msg = "❌ Вы уже использовали пробный тест для этого предмета." if lang == "ru" else "❌ You have already used the free trial for this subject."
            await query.answer(msg, show_alert=True)
            return CHOOSING_SUBJECT
        context.user_data["trial_subject"] = subject_key
        context.user_data["trial_index"] = 0
        context.user_data["trial_score"] = 0
        all_q = get_quiz_questions(subject_key)
        context.user_data["trial_questions"] = random.sample(all_q, min(FREE_QUESTIONS, len(all_q)))
        db.mark_trial_used(user_id, subject_key)
        await show_trial_question(query.message, user_id, context, edit=True)
        return TRIAL_SESSION

    if data.startswith("buy_"):
        subject_key = data.split("_", 1)[1]
        context.user_data["pending_subject"] = subject_key
        context.user_data["promo_discount"] = 0
        info = SUBJECTS[subject_key]
        text = t(user_id, "payment_instruction",
                 subject=info["name"], price=PRICE_PER_SUBJECT, card=CARD_NUMBER)
        keyboard = [
            [InlineKeyboardButton(t(user_id, "enter_promo"), callback_data=f"promo_{subject_key}")],
            [InlineKeyboardButton(t(user_id, "back"), callback_data="back_to_buy_list")]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        photo_url = SUBJECT_PHOTOS.get(subject_key)
        try:
            await query.message.delete()
        except Exception:
            pass
        if photo_url:
            try:
                await query.message.chat.send_photo(
                    photo=photo_url, caption=text,
                    parse_mode="Markdown", reply_markup=markup
                )
                return PAYMENT_SCREENSHOT
            except Exception:
                pass
        await query.message.chat.send_message(text, parse_mode="Markdown", reply_markup=markup)
        return PAYMENT_SCREENSHOT

    if data.startswith("promo_"):
        subject_key = data.split("_", 1)[1]
        context.user_data["pending_subject"] = subject_key
        keyboard = [[InlineKeyboardButton(t(user_id, "back"), callback_data=f"buy_{subject_key}")]]
        await query.message.edit_text(t(user_id, "promo_enter"), parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(keyboard))
        return PAYMENT_SCREENSHOT

    if data.startswith("study_"):
        subject_key = data.split("_", 1)[1]
        context.user_data["current_subject"] = subject_key
        await show_subject_menu(query.message, user_id, subject_key, edit=True)
        return SUBJECT_MENU


async def show_subject_menu(message, user_id, subject_key, edit=False):
    info = SUBJECTS[subject_key]
    keyboard = [
        [InlineKeyboardButton(t(user_id, "study_materials"), callback_data=f"materials_{subject_key}"),
         InlineKeyboardButton(t(user_id, "cheatsheet"), callback_data=f"cheatsheet_{subject_key}")],
        [InlineKeyboardButton(t(user_id, "flashcards"), callback_data=f"flashcards_{subject_key}"),
         InlineKeyboardButton(t(user_id, "glossary"), callback_data=f"glossary_{subject_key}")],
        [InlineKeyboardButton(t(user_id, "quiz"), callback_data=f"quiz_{subject_key}"),
         InlineKeyboardButton(t(user_id, "quiz_history"), callback_data=f"history_{subject_key}")],
        [InlineKeyboardButton(t(user_id, "ai_chat"), callback_data=f"aichat_{subject_key}"),
         InlineKeyboardButton(t(user_id, "progress"), callback_data=f"progress_{subject_key}")],
        [InlineKeyboardButton(t(user_id, "back"), callback_data="back_main")],
    ]
    text = t(user_id, "subject_menu", subject=info["name"])
    markup = InlineKeyboardMarkup(keyboard)
    if edit:
        await message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await message.reply_text(text, parse_mode="Markdown", reply_markup=markup)


# ── PAYMENT ───────────────────────────────────────────────────────────────────

async def receive_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = update.effective_user

    # Handle promo code text input
    if update.message.text and not update.message.photo:
        promo_code = update.message.text.strip().upper()
        discount = db.check_promo(promo_code)
        subject_key = context.user_data.get("pending_subject")
        if discount and subject_key:
            context.user_data["promo_discount"] = discount
            discounted_price = int(PRICE_PER_SUBJECT * (1 - discount / 100))
            info = SUBJECTS[subject_key]
            text = t(user_id, "promo_valid", discount=discount, price=discounted_price)
            text += "\n\n" + t(user_id, "payment_instruction",
                               subject=info["name"], price=discounted_price, card=CARD_NUMBER)
            keyboard = [[InlineKeyboardButton(t(user_id, "back"), callback_data="back_main")]]
            await update.message.reply_text(text, parse_mode="Markdown",
                                            reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            keyboard = [[InlineKeyboardButton(t(user_id, "back"), callback_data="back_main")]]
            await update.message.reply_text(t(user_id, "promo_invalid"), parse_mode="Markdown",
                                            reply_markup=InlineKeyboardMarkup(keyboard))
        return PAYMENT_SCREENSHOT

    subject_key = context.user_data.get("pending_subject")
    if not subject_key:
        await show_main_menu(update.message, user_id)
        return MAIN_MENU

    discount = context.user_data.get("promo_discount", 0)
    final_price = int(PRICE_PER_SUBJECT * (1 - discount / 100))
    info = SUBJECTS[subject_key]
    db.add_pending_payment(user_id, subject_key)

    approve_cb = f"approve_{user_id}_{subject_key}"
    deny_cb = f"deny_{user_id}_{subject_key}"
    admin_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить", callback_data=approve_cb),
         InlineKeyboardButton("❌ Отклонить", callback_data=deny_cb)]
    ])
    name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    username = f"@{user.username}" if user.username else "без username"
    promo_text = f"\n🎁 Промокод: скидка {discount}%" if discount else ""
    admin_text = (f"💰 *Новая оплата*\n\n"
                  f"👤 {name} ({username})\n"
                  f"🆔 `{user_id}`\n"
                  f"📘 Предмет: *{info['name']}*\n"
                  f"💵 Сумма: {final_price:,} сум{promo_text}")

    try:
        if update.message.photo:
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=update.message.photo[-1].file_id,
                caption=admin_text,
                parse_mode="Markdown",
                reply_markup=admin_keyboard
            )
        elif update.message.document:
            await context.bot.send_document(
                chat_id=ADMIN_ID,
                document=update.message.document.file_id,
                caption=admin_text,
                parse_mode="Markdown",
                reply_markup=admin_keyboard
            )
    except Exception as e:
        logger.error(f"Failed to notify admin: {e}")

    keyboard = [[InlineKeyboardButton(t(user_id, "back"), callback_data="back_main")]]
    await update.message.reply_text(
        t(user_id, "screenshot_received"),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return MAIN_MENU


# ── ADMIN APPROVE/DENY ────────────────────────────────────────────────────────

async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    parts = query.data.split("_")
    action = parts[0]
    student_id = int(parts[1])
    subject_key = parts[2]
    info = SUBJECTS[subject_key]

    if action == "approve":
        db.grant_access(student_id, subject_key)
        db.remove_pending(student_id, subject_key)
        student_lang = db.get_user_lang(student_id) or "en"
        msg = TEXTS[student_lang]["access_granted"].format(subject=info["name"])
        go_btn_label = "📘 Перейти к предмету" if student_lang == "ru" else "📘 Go to Subject"
        student_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(go_btn_label, callback_data=f"study_{subject_key}")]
        ])
        try:
            await context.bot.send_message(student_id, msg, parse_mode="Markdown",
                                           reply_markup=student_keyboard)
        except:
            pass
        await query.message.edit_caption(
            query.message.caption + "\n\n✅ *Доступ выдан*", parse_mode="Markdown"
        )
    elif action == "deny":
        db.remove_pending(student_id, subject_key)
        student_lang = db.get_user_lang(student_id) or "en"
        msg = TEXTS[student_lang]["access_denied"]
        try:
            await context.bot.send_message(student_id, msg, parse_mode="Markdown")
        except:
            pass
        await query.message.edit_caption(
            query.message.caption + "\n\n❌ *Отклонено*", parse_mode="Markdown"
        )


# ── SUBJECT MENU HANDLER ──────────────────────────────────────────────────────

async def subject_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "back_main":
        await show_main_menu(query.message, user_id, edit=True)
        return MAIN_MENU

    if data.startswith("back_subject_"):
        subject_key = data.split("back_subject_")[1]
        await show_subject_menu(query.message, user_id, subject_key, edit=True)
        return SUBJECT_MENU

    if data.startswith("progress_"):
        subject_key = data.split("_", 1)[1]
        prog = db.get_progress(user_id, subject_key)
        if not prog or prog["tests"] == 0:
            text = t(user_id, "no_progress")
        else:
            text = t(user_id, "progress_text",
                     subject=SUBJECTS[subject_key]["name"],
                     tests=prog["tests"],
                     avg=prog["avg"],
                     best=prog["best"],
                     cards=prog["cards"])
        keyboard = [[InlineKeyboardButton(t(user_id, "back"), callback_data=f"back_subject_{subject_key}")]]
        await query.message.edit_text(text, parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(keyboard))
        return SUBJECT_MENU

    if data.startswith("materials_"):
        subject_key = data.split("_", 1)[1]
        await send_materials(query.message, user_id, subject_key)
        return SUBJECT_MENU

    if data.startswith("cheatsheet_"):
        subject_key = data.split("_", 1)[1]
        sheet = get_cheatsheet(subject_key)
        text = t(user_id, "cheatsheet_title", subject=SUBJECTS[subject_key]["name"]) + sheet
        keyboard = [[InlineKeyboardButton(t(user_id, "back"), callback_data=f"back_subject_{subject_key}")]]
        await query.message.edit_text(text, parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(keyboard))
        return SUBJECT_MENU

    if data.startswith("glossary_"):
        subject_key = data.split("_", 1)[1]
        context.user_data["glossary_subject"] = subject_key
        keyboard = [[InlineKeyboardButton(t(user_id, "back"), callback_data=f"back_subject_{subject_key}")]]
        await query.message.edit_text(
            t(user_id, "glossary_intro", subject=SUBJECTS[subject_key]["name"]),
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data["awaiting_glossary"] = True
        return SUBJECT_MENU

    if data.startswith("history_"):
        subject_key = data.split("_", 1)[1]
        history = db.get_quiz_history(user_id, subject_key)
        if not history:
            text = t(user_id, "quiz_history_empty")
        else:
            text = t(user_id, "quiz_history_title", subject=SUBJECTS[subject_key]["name"])
            for i, h in enumerate(history, 1):
                pct = int(h["score"] / h["total"] * 100)
                date = h["taken_at"][:10] if h["taken_at"] else "—"
                emoji = "🌟" if pct >= 90 else "👍" if pct >= 70 else "📚" if pct >= 50 else "💪"
                text += f"{emoji} {date}: *{h['score']}/{h['total']}* ({pct}%)\n"
        keyboard = [[InlineKeyboardButton(t(user_id, "back"), callback_data=f"back_subject_{subject_key}")]]
        await query.message.edit_text(text, parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(keyboard))
        return SUBJECT_MENU

    if data.startswith("aichat_"):
        subject_key = data.split("_", 1)[1]
        context.user_data["ai_subject"] = subject_key
        context.user_data["in_ai_chat"] = True
        keyboard = [
            [InlineKeyboardButton(t(user_id, "ai_clear"), callback_data=f"ai_clear_{subject_key}")],
            [InlineKeyboardButton(t(user_id, "back"), callback_data=f"back_subject_{subject_key}")]
        ]
        await query.message.edit_text(
            t(user_id, "ai_chat_intro", subject=SUBJECTS[subject_key]["name"]),
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return AI_CHAT_SESSION

    if data.startswith("ai_clear_"):
        subject_key = data.split("ai_clear_")[1]
        db.clear_ai_history(user_id, subject_key)
        keyboard = [
            [InlineKeyboardButton(t(user_id, "ai_clear"), callback_data=f"ai_clear_{subject_key}")],
            [InlineKeyboardButton(t(user_id, "back"), callback_data=f"back_subject_{subject_key}")]
        ]
        await query.answer(t(user_id, "ai_history_cleared"), show_alert=False)
        await query.message.edit_text(
            t(user_id, "ai_chat_intro", subject=SUBJECTS[subject_key]["name"]),
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return AI_CHAT_SESSION

    if data.startswith("flashcards_"):
        subject_key = data.split("_", 1)[1]
        context.user_data["flashcard_subject"] = subject_key
        context.user_data["flashcard_index"] = 0
        context.user_data["flashcard_showing_answer"] = False
        db.increment_cards(user_id, subject_key)
        await show_flashcard(query.message, user_id, subject_key, 0, False, edit=True)
        return FLASHCARD_SESSION

    if data.startswith("quiz_"):
        subject_key = data.split("_", 1)[1]
        await start_quiz(query.message, context, user_id, subject_key, edit=True)
        return QUIZ_SESSION


async def send_materials(message, user_id, subject_key):
    info = get_subject_info(subject_key)
    chapters = info.get("chapters", [])
    header = f"📘 *{info['name']}*\n{'─' * 30}\n\n"
    await message.edit_text(header + "⏳ Loading...", parse_mode="Markdown")

    full_text = header
    for i, chapter in enumerate(chapters, 1):
        full_text += f"*{i}. {chapter['title']}*\n"
        full_text += chapter['content'] + "\n\n"

    chunks = []
    while len(full_text) > 4000:
        split_at = full_text.rfind('\n\n', 0, 4000)
        if split_at == -1:
            split_at = 4000
        chunks.append(full_text[:split_at])
        full_text = full_text[split_at:]
    chunks.append(full_text)

    keyboard = [[InlineKeyboardButton(t(user_id, "back"), callback_data=f"back_subject_{subject_key}")]]
    markup = InlineKeyboardMarkup(keyboard)
    await message.edit_text(chunks[0], parse_mode="Markdown", reply_markup=markup if len(chunks) == 1 else None)
    for i, chunk in enumerate(chunks[1:], 1):
        is_last = (i == len(chunks) - 1)
        await message.reply_text(chunk, parse_mode="Markdown", reply_markup=markup if is_last else None)


# ── FLASHCARDS ────────────────────────────────────────────────────────────────

async def show_flashcard(message, user_id, subject_key, index, showing_answer, edit=True):
    cards = get_flashcards(subject_key)
    total = len(cards)
    card = cards[index]

    if not showing_answer:
        text = t(user_id, "flashcard_front", num=index+1, total=total, term=card["term"])
        keyboard = [
            [InlineKeyboardButton(t(user_id, "show_answer"), callback_data="fc_show")],
            [InlineKeyboardButton(t(user_id, "back"), callback_data=f"back_subject_{subject_key}")]
        ]
    else:
        text = (t(user_id, "flashcard_front", num=index+1, total=total, term=card["term"]) +
                "\n\n" + t(user_id, "flashcard_back", definition=card["definition"]))
        row = []
        if index > 0:
            row.append(InlineKeyboardButton(t(user_id, "prev_card"), callback_data="fc_prev"))
        if index < total - 1:
            row.append(InlineKeyboardButton(t(user_id, "next_card"), callback_data="fc_next"))
        keyboard = [row] if row else []
        if index == total - 1:
            keyboard.append([InlineKeyboardButton(t(user_id, "finish_flashcards"), callback_data="fc_finish")])
        keyboard.append([InlineKeyboardButton(t(user_id, "back"), callback_data=f"back_subject_{subject_key}")])

    markup = InlineKeyboardMarkup(keyboard)
    if edit:
        await message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await message.reply_text(text, parse_mode="Markdown", reply_markup=markup)

async def flashcard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    subject_key = context.user_data.get("flashcard_subject")
    index = context.user_data.get("flashcard_index", 0)

    if data == "back_main":
        await show_main_menu(query.message, user_id, edit=True)
        return MAIN_MENU
    if data.startswith("back_subject_"):
        sk = data.split("back_subject_")[1]
        await show_subject_menu(query.message, user_id, sk, edit=True)
        return SUBJECT_MENU
    if data == "fc_show":
        context.user_data["flashcard_showing_answer"] = True
        await show_flashcard(query.message, user_id, subject_key, index, True)
    elif data == "fc_next":
        new_index = index + 1
        context.user_data["flashcard_index"] = new_index
        context.user_data["flashcard_showing_answer"] = False
        db.increment_cards(user_id, subject_key)
        await show_flashcard(query.message, user_id, subject_key, new_index, False)
    elif data == "fc_prev":
        new_index = index - 1
        context.user_data["flashcard_index"] = new_index
        context.user_data["flashcard_showing_answer"] = False
        await show_flashcard(query.message, user_id, subject_key, new_index, False)
    elif data == "fc_finish":
        keyboard = [[InlineKeyboardButton(t(user_id, "back"), callback_data=f"back_subject_{subject_key}")]]
        await query.message.edit_text(t(user_id, "flashcards_done"), parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(keyboard))
        return SUBJECT_MENU
    return FLASHCARD_SESSION


# ── QUIZ ──────────────────────────────────────────────────────────────────────

async def start_quiz(message, context, user_id, subject_key, edit=False):
    all_q = get_quiz_questions(subject_key)
    questions = random.sample(all_q, min(QUIZ_QUESTIONS_COUNT, len(all_q)))
    context.user_data["quiz_questions"] = questions
    context.user_data["quiz_index"] = 0
    context.user_data["quiz_score"] = 0
    context.user_data["quiz_subject"] = subject_key
    await show_quiz_question(message, user_id, context, edit=edit)

async def show_quiz_question(message, user_id, context, edit=False):
    questions = context.user_data["quiz_questions"]
    index = context.user_data["quiz_index"]
    subject_key = context.user_data["quiz_subject"]
    total = len(questions)
    q = questions[index]
    text = t(user_id, "quiz_start", subject=SUBJECTS[subject_key]["name"],
             num=index+1, total=total, question=q["question"])
    keyboard = [[InlineKeyboardButton(opt, callback_data=f"quiz_ans_{i}")] for i, opt in enumerate(q["options"])]
    markup = InlineKeyboardMarkup(keyboard)
    if edit:
        await message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await message.reply_text(text, parse_mode="Markdown", reply_markup=markup)

async def quiz_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "back_main":
        await show_main_menu(query.message, user_id, edit=True)
        return MAIN_MENU
    if data.startswith("back_subject_"):
        sk = data.split("back_subject_")[1]
        await show_subject_menu(query.message, user_id, sk, edit=True)
        return SUBJECT_MENU
    if data.startswith("quiz_restart_"):
        subject_key = data.split("quiz_restart_")[1]
        await start_quiz(query.message, context, user_id, subject_key, edit=True)
        return QUIZ_SESSION
    if data.startswith("quiz_ans_"):
        answer_index = int(data.split("_")[2])
        questions = context.user_data["quiz_questions"]
        index = context.user_data["quiz_index"]
        subject_key = context.user_data["quiz_subject"]
        total = len(questions)
        q = questions[index]
        correct_index = q["correct"]
        is_correct = (answer_index == correct_index)
        context.user_data["last_answer_correct"] = is_correct
        context.user_data["last_q_index"] = index
        if is_correct:
            context.user_data["quiz_score"] += 1
            result_text = t(user_id, "correct", explanation=q.get("explanation", ""))
        else:
            result_text = t(user_id, "wrong", correct=q["options"][correct_index],
                            explanation=q.get("explanation", ""))
        # Bookmark button for wrong answers
        bookmark_btn = []
        if not is_correct:
            already = db.bookmark_exists(user_id, q["question"])
            bm_label = t(user_id, "bookmark_exists") if already else "🔖 " + ("Сохранить" if (db.get_user_lang(user_id) or "en") == "ru" else "Bookmark")
            bookmark_btn = [InlineKeyboardButton(bm_label, callback_data=f"bookmark_quiz_{index}")]
        next_index = index + 1
        context.user_data["quiz_index"] = next_index
        if next_index >= total:
            score = context.user_data["quiz_score"]
            pct = int(score / total * 100)
            if pct >= 90: grade = t(user_id, "grade_excellent")
            elif pct >= 70: grade = t(user_id, "grade_good")
            elif pct >= 50: grade = t(user_id, "grade_ok")
            else: grade = t(user_id, "grade_bad")
            db.save_quiz_result(user_id, subject_key, score, total)
            # XP reward
            xp_gain = max(10, int(score / total * 50))
            xp_result = db.add_xp(user_id, xp_gain)
            xp_notification = f"\n\n⚡ *+{xp_gain} XP*"
            if xp_result.get("leveled_up"):
                xp_notification += f"\n🎉 *Новый уровень {xp_result['level']}!*" if (db.get_user_lang(user_id) or "en") == "ru" else f"\n🎉 *Level up! Level {xp_result['level']}!*"
            done_text = (
                result_text + "\n\n" +
                t(user_id, "quiz_done", score=score, total=total, grade=grade) +
                xp_notification
            )
            keyboard = [
                [InlineKeyboardButton(t(user_id, "restart_quiz"), callback_data=f"quiz_restart_{subject_key}")],
                [InlineKeyboardButton(t(user_id, "back_to_subject"), callback_data=f"back_subject_{subject_key}")],
                [InlineKeyboardButton(t(user_id, "back"), callback_data="back_main")],
            ]
            await query.message.edit_text(done_text, parse_mode="Markdown",
                                          reply_markup=InlineKeyboardMarkup(keyboard))
            return SUBJECT_MENU
        else:
            next_row = [InlineKeyboardButton("➡️ Next Question", callback_data="quiz_next")]
            keyboard = [bookmark_btn, next_row] if bookmark_btn else [[next_row[0]]]
            await query.message.edit_text(result_text, parse_mode="Markdown",
                                          reply_markup=InlineKeyboardMarkup(keyboard))
            return QUIZ_SESSION
    if data.startswith("bookmark_quiz_"):
        q_index = int(data.split("bookmark_quiz_")[1])
        questions = context.user_data.get("quiz_questions", [])
        subject_key = context.user_data.get("quiz_subject")
        if q_index < len(questions):
            q = questions[q_index]
            if not db.bookmark_exists(user_id, q["question"]):
                db.add_bookmark(user_id, subject_key, q["question"],
                                q["options"][q["correct"]], q.get("explanation", ""))
                await query.answer(t(user_id, "bookmark_saved"))
            else:
                await query.answer(t(user_id, "bookmark_exists"))
        # Redraw same message but with bookmark button updated (already saved)
        q = questions[q_index] if q_index < len(questions) else None
        if q:
            is_correct_prev = context.user_data.get("last_answer_correct", True)
            if is_correct_prev:
                result_text = t(user_id, "correct", explanation=q.get("explanation", ""))
            else:
                correct_index = q["correct"]
                result_text = t(user_id, "wrong", correct=q["options"][correct_index],
                                explanation=q.get("explanation", ""))
            lang = db.get_user_lang(user_id) or "en"
            bm_label = "✅ Сохранено" if lang == "ru" else "✅ Saved"
            next_row = [InlineKeyboardButton("➡️ " + ("Следующий" if lang == "ru" else "Next Question"), callback_data="quiz_next")]
            keyboard = [[InlineKeyboardButton(bm_label, callback_data="noop")], next_row]
            await query.message.edit_text(result_text, parse_mode="Markdown",
                                          reply_markup=InlineKeyboardMarkup(keyboard))
        return QUIZ_SESSION
    if data == "noop":
        await query.answer()
        return QUIZ_SESSION
    if data == "quiz_next":
        await show_quiz_question(query.message, user_id, context, edit=True)
        return QUIZ_SESSION


# ── TRIAL QUIZ ────────────────────────────────────────────────────────────────

async def show_trial_question(message, user_id, context, edit=False):
    questions = context.user_data["trial_questions"]
    index = context.user_data["trial_index"]
    subject_key = context.user_data["trial_subject"]
    q = questions[index]
    text = t(user_id, "trial_question", subject=SUBJECTS[subject_key]["name"],
             num=index+1, question=q["question"])
    keyboard = [[InlineKeyboardButton(opt, callback_data=f"trial_ans_{i}")] for i, opt in enumerate(q["options"])]
    markup = InlineKeyboardMarkup(keyboard)
    if edit:
        await message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await message.reply_text(text, parse_mode="Markdown", reply_markup=markup)

async def trial_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "back_main":
        await show_main_menu(query.message, user_id, edit=True)
        return MAIN_MENU
    if data.startswith("trial_ans_"):
        answer_index = int(data.split("_")[2])
        questions = context.user_data["trial_questions"]
        index = context.user_data["trial_index"]
        subject_key = context.user_data["trial_subject"]
        q = questions[index]
        correct_index = q["correct"]
        is_correct = (answer_index == correct_index)
        if is_correct:
            context.user_data["trial_score"] += 1
            result_text = t(user_id, "correct", explanation=q.get("explanation", ""))
        else:
            result_text = t(user_id, "wrong", correct=q["options"][correct_index],
                            explanation=q.get("explanation", ""))
        next_index = index + 1
        context.user_data["trial_index"] = next_index
        if next_index >= FREE_QUESTIONS:
            score = context.user_data["trial_score"]
            done_text = result_text + "\n\n" + t(user_id, "trial_done", score=score)
            keyboard = [
                [InlineKeyboardButton(t(user_id, "buy_now"), callback_data=f"buy_{subject_key}")],
                [InlineKeyboardButton(t(user_id, "back"), callback_data="back_main")],
            ]
            await query.message.edit_text(done_text, parse_mode="Markdown",
                                          reply_markup=InlineKeyboardMarkup(keyboard))
            return CHOOSING_SUBJECT
        else:
            keyboard = [[InlineKeyboardButton("➡️ Next Question", callback_data="trial_next")]]
            await query.message.edit_text(result_text, parse_mode="Markdown",
                                          reply_markup=InlineKeyboardMarkup(keyboard))
            return TRIAL_SESSION
    if data == "trial_next":
        await show_trial_question(query.message, user_id, context, edit=True)
        return TRIAL_SESSION


# ── AI CHAT ───────────────────────────────────────────────────────────────────

async def ai_chat_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    subject_key = context.user_data.get("ai_subject")

    if not subject_key:
        await show_main_menu(update.message, user_id)
        return MAIN_MENU

    if not GEMINI_AVAILABLE or not os.environ.get("GEMINI_API_KEY"):
        keyboard = [[InlineKeyboardButton(t(user_id, "back"), callback_data=f"back_subject_{subject_key}")]]
        await update.message.reply_text(t(user_id, "ai_unavailable"), parse_mode="Markdown",
                                        reply_markup=InlineKeyboardMarkup(keyboard))
        return AI_CHAT_SESSION

    thinking_msg = await update.message.reply_text(t(user_id, "ai_thinking"))

    subject_name = SUBJECTS[subject_key]["name"]
    history = db.get_ai_history(user_id, subject_key, limit=10)
    db.save_ai_message(user_id, subject_key, "user", text)

    lang = db.get_user_lang(user_id) or "en"
    system_prompt = (
        f"You are a helpful tutor for the subject '{subject_name}' at British Management University. "
        f"Answer only questions related to this subject. Be concise but thorough. "
        f"Use {'Russian' if lang == 'ru' else 'English'} language. "
        f"Format answers clearly with bullet points or numbered lists when appropriate."
    )

    messages = history + [{"role": "user", "content": text}]

    try:
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        gemini_history = [
            {"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]}
            for m in history
        ]
        model_client = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=system_prompt
        )
        chat = model_client.start_chat(history=gemini_history)
        response = chat.send_message(text)
        ai_reply = response.text
        db.save_ai_message(user_id, subject_key, "assistant", ai_reply)

        keyboard = [
            [InlineKeyboardButton(t(user_id, "ai_clear"), callback_data=f"ai_clear_{subject_key}")],
            [InlineKeyboardButton(t(user_id, "back"), callback_data=f"back_subject_{subject_key}")]
        ]
        await thinking_msg.delete()
        await update.message.reply_text(f"🤖 {ai_reply}", parse_mode="Markdown",
                                        reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"AI chat error: {e}")
        await thinking_msg.edit_text("⚠️ Ошибка ИИ. Попробуйте позже." if lang == "ru" else "⚠️ AI error. Try again later.")

    return AI_CHAT_SESSION


# ── BOOKMARKS ─────────────────────────────────────────────────────────────────

async def show_bookmarks(message, user_id, edit=False):
    bookmarks = db.get_bookmarks(user_id)
    if not bookmarks:
        text = t(user_id, "bookmarks_empty")
        keyboard = [[InlineKeyboardButton(t(user_id, "back"), callback_data="back_main")]]
    else:
        text = t(user_id, "bookmarks_title")
        keyboard = []
        for b in bookmarks[:10]:
            subj_name = SUBJECTS.get(b["subject_key"], {}).get("name", b["subject_key"])
            short_q = b["question"][:50] + "…" if len(b["question"]) > 50 else b["question"]
            text += f"📌 *{subj_name}*\n_{short_q}_\n✅ {b['answer']}\n\n"
            keyboard.append([InlineKeyboardButton(
                f"🗑 {short_q[:30]}…" if len(b["question"]) > 30 else f"🗑 {b['question']}",
                callback_data=f"del_bookmark_{b['id']}"
            )])
        keyboard.append([InlineKeyboardButton(t(user_id, "back"), callback_data="back_main")])
    markup = InlineKeyboardMarkup(keyboard)
    if edit:
        await message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await message.reply_text(text, parse_mode="Markdown", reply_markup=markup)

async def bookmarks_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "back_main":
        await show_main_menu(query.message, user_id, edit=True)
        return MAIN_MENU

    if data.startswith("del_bookmark_"):
        bookmark_id = int(data.split("del_bookmark_")[1])
        db.delete_bookmark(bookmark_id, user_id)
        await query.answer(t(user_id, "bookmark_deleted"))
        await show_bookmarks(query.message, user_id, edit=True)
        return BOOKMARKS_SESSION

    return BOOKMARKS_SESSION



def xp_badge(level):
    badges = {1: "🌱", 2: "📗", 3: "⭐", 4: "🌟", 5: "💫", 6: "🔥", 7: "💎", 8: "👑"}
    return badges.get(level, "🌱")

def xp_progress_bar(xp, level):
    thresholds = [0, 100, 250, 500, 1000, 2000, 5000, 10000]
    if level >= len(thresholds):
        return "▓▓▓▓▓▓▓▓▓▓ MAX"
    current = thresholds[level - 1]
    next_th = thresholds[level]
    filled = int((xp - current) / (next_th - current) * 10)
    filled = max(0, min(10, filled))
    bar = "▓" * filled + "░" * (10 - filled)
    return f"[{bar}]"

async def show_leaderboard(message, user_id, edit=False):
    leaders = db.get_leaderboard(10)
    lang = db.get_user_lang(user_id) or "en"
    title = TEXTS[lang]["leaderboard_title"]
    text = title
    medals = ["🥇", "🥈", "🥉"]
    for i, u in enumerate(leaders):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = u["first_name"] or "Student"
        badge = xp_badge(u["level"])
        highlight = " ←" if u["user_id"] == user_id else ""
        text += f"{medal} {badge} *{name}* — {u['xp']} XP 🔥{u['streak']}{highlight}\n"
    if not leaders:
        text += "No data yet. Be the first!" if lang == "en" else "Пока нет данных. Будь первым!"
    keyboard = [
        [InlineKeyboardButton(TEXTS[lang]["my_rank"], callback_data="menu_my_rank")],
        [InlineKeyboardButton(TEXTS[lang]["back"], callback_data="back_main")]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    if edit:
        try:
            await message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
        except Exception:
            await message.reply_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await message.reply_text(text, parse_mode="Markdown", reply_markup=markup)

async def show_my_rank(message, user_id, edit=False):
    lang = db.get_user_lang(user_id) or "en"
    data = db.get_or_create_xp(user_id)
    xp = data["xp"]
    level = data["level"]
    streak = data["streak"]
    thresholds = [0, 100, 250, 500, 1000, 2000, 5000, 10000]
    next_th = thresholds[min(level, len(thresholds)-1)]
    xp_needed = max(0, next_th - xp)
    badge = xp_badge(level)
    bar = xp_progress_bar(xp, level)
    text = TEXTS[lang]["my_stats"].format(
        level=level, badge=badge, xp=xp, streak=streak,
        progress_bar=bar, xp_needed=xp_needed
    )
    keyboard = [
        [InlineKeyboardButton(TEXTS[lang]["leaderboard"], callback_data="menu_leaderboard")],
        [InlineKeyboardButton(TEXTS[lang]["back"], callback_data="back_main")]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    if edit:
        try:
            await message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
        except Exception:
            await message.reply_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await message.reply_text(text, parse_mode="Markdown", reply_markup=markup)


async def access_granted_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles study_KEY button from access granted notification message."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    if data.startswith("study_"):
        subject_key = data.split("_", 1)[1]
        context.user_data["current_subject"] = subject_key
        info = SUBJECTS.get(subject_key, {})
        photo_url = SUBJECT_PHOTOS.get(subject_key)
        lang = db.get_user_lang(user_id) or "en"
        keyboard = [
            [InlineKeyboardButton(TEXTS[lang]["study_materials"], callback_data=f"materials_{subject_key}"),
             InlineKeyboardButton(TEXTS[lang]["cheatsheet"], callback_data=f"cheatsheet_{subject_key}")],
            [InlineKeyboardButton(TEXTS[lang]["flashcards"], callback_data=f"flashcards_{subject_key}"),
             InlineKeyboardButton(TEXTS[lang]["glossary"], callback_data=f"glossary_{subject_key}")],
            [InlineKeyboardButton(TEXTS[lang]["quiz"], callback_data=f"quiz_{subject_key}"),
             InlineKeyboardButton(TEXTS[lang]["quiz_history"], callback_data=f"history_{subject_key}")],
            [InlineKeyboardButton(TEXTS[lang]["ai_chat"], callback_data=f"aichat_{subject_key}"),
             InlineKeyboardButton(TEXTS[lang]["progress"], callback_data=f"progress_{subject_key}")],
            [InlineKeyboardButton(TEXTS[lang]["back"], callback_data="back_main")],
        ]
        text = TEXTS[lang]["subject_menu"].format(subject=info.get("name", subject_key))
        markup = InlineKeyboardMarkup(keyboard)
        try:
            await query.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)
        except Exception:
            pass

async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        user_id = update.effective_user.id

        # Handle glossary search
        if context.user_data.get("awaiting_glossary"):
            subject_key = context.user_data.get("glossary_subject")
            term = update.message.text.strip().lower()
            glossary = get_glossary(subject_key)
            result = None
            for entry in glossary:
                if term in entry["term"].lower():
                    result = entry
                    break
            context.user_data["awaiting_glossary"] = False
            keyboard = [
                [InlineKeyboardButton(t(user_id, "glossary"), callback_data=f"glossary_{subject_key}")],
                [InlineKeyboardButton(t(user_id, "back"), callback_data=f"back_subject_{subject_key}")]
            ]
            if result:
                text = f"📖 *{result['term']}*\n\n{result['definition']}"
            else:
                text = t(user_id, "glossary_not_found")
            await update.message.reply_text(text, parse_mode="Markdown",
                                            reply_markup=InlineKeyboardMarkup(keyboard))
            return SUBJECT_MENU

        await show_main_menu(update.message, user_id)
    return MAIN_MENU


def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN not set!")
    db.init()

    app = Application.builder().token(token).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_LANG: [CallbackQueryHandler(set_language, pattern="^lang_")],
            MAIN_MENU: [CallbackQueryHandler(main_menu_handler)],
            CHOOSING_SUBJECT: [CallbackQueryHandler(subject_handler)],
            PAYMENT_SCREENSHOT: [
                MessageHandler(filters.PHOTO | filters.Document.ALL | filters.TEXT, receive_screenshot),
                CallbackQueryHandler(subject_handler),
            ],
            SUBJECT_MENU: [CallbackQueryHandler(subject_menu_handler)],
            QUIZ_SESSION: [CallbackQueryHandler(quiz_handler)],
            FLASHCARD_SESSION: [CallbackQueryHandler(flashcard_handler)],
            TRIAL_SESSION: [CallbackQueryHandler(trial_handler)],
            AI_CHAT_SESSION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ai_chat_message_handler),
                CallbackQueryHandler(subject_menu_handler),
            ],
            BOOKMARKS_SESSION: [CallbackQueryHandler(bookmarks_handler)],
        },
        fallbacks=[CommandHandler("start", start), MessageHandler(filters.ALL, fallback)],
        allow_reentry=True,
    )

    app.add_handler(CallbackQueryHandler(admin_action, pattern="^(approve|deny)_"))
    app.add_handler(CallbackQueryHandler(access_granted_handler, pattern="^study_"))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("users", admin_users))
    app.add_handler(CommandHandler("addpromo", add_promo_cmd))
    app.add_handler(conv)
    app.run_polling(drop_pending_updates=True, close_loop=False)

if __name__ == "__main__":
    main()
