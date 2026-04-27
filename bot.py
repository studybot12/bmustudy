import logging
import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)
from database import db
from content import SUBJECTS, get_subject_info, get_flashcards, get_quiz_questions
from config import ADMIN_ID, CARD_NUMBER, PRICE_PER_SUBJECT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# States
CHOOSING_LANG, MAIN_MENU, CHOOSING_SUBJECT, PAYMENT_SCREENSHOT, SUBJECT_MENU, QUIZ_SESSION, FLASHCARD_SESSION = range(7)

TEXTS = {
    "ru": {
        "welcome": "👋 Привет! Добро пожаловать в *Study Hub BMU*\n\nВыберите язык интерфейса:",
        "main_menu": "📚 *Study Hub — British Management University*\n\nВыберите действие:",
        "my_subjects": "📖 Мои предметы",
        "buy_access": "🛒 Купить доступ",
        "help": "❓ Помощь",
        "choose_subject_buy": "Выберите предмет для покупки доступа:",
        "choose_subject_study": "Выберите предмет для изучения:",
        "payment_instruction": "💳 *Оплата доступа к «{subject}»*\n\nСтоимость: *{price:,} сум*\n\nПереведите на карту:\n`{card}`\n\nПосле перевода отправьте скриншот подтверждения 👇",
        "screenshot_received": "✅ Скриншот получен! Ваша оплата проверяется.\n\nОбычно это занимает до 30 минут. Вы получите уведомление как только доступ будет открыт.",
        "access_granted": "🎉 *Доступ открыт!*\n\nПредмет *{subject}* теперь доступен в разделе «Мои предметы».",
        "access_denied": "❌ Оплата не подтверждена. Пожалуйста, свяжитесь с @admin или попробуйте снова.",
        "no_subjects": "У вас пока нет купленных предметов.\n\nПерейдите в раздел «Купить доступ» 🛒",
        "subject_menu": "📘 *{subject}*\n\nВыберите режим:",
        "study_materials": "📖 Конспект",
        "flashcards": "🃏 Флэшкарты",
        "quiz": "✏️ Тест (MCQ)",
        "back": "← Назад",
        "quiz_start": "🧠 *Тест: {subject}*\n\nВопрос {num}/10:\n\n{question}",
        "correct": "✅ *Верно!*\n\n{explanation}",
        "wrong": "❌ *Неверно.*\nПравильный ответ: *{correct}*\n\n{explanation}",
        "quiz_done": "🏁 *Тест завершён!*\n\nРезультат: *{score}/10*\n{grade}\n\nНажмите кнопку для продолжения:",
        "flashcard_front": "🃏 *Флэшкарта {num}/{total}*\n\n❓ {term}",
        "flashcard_back": "💡 *Ответ:*\n\n{definition}",
        "show_answer": "👁 Показать ответ",
        "next_card": "➡️ Следующая",
        "prev_card": "⬅️ Предыдущая",
        "finish_flashcards": "✅ Завершить",
        "flashcards_done": "🎉 Флэшкарты пройдены! Удачи на экзамене!",
        "help_text": "❓ *Помощь*\n\nПо вопросам оплаты и доступа: @your_username\n\nБот работает 24/7. После оплаты доступ открывается в течение 30 минут.",
        "already_has_access": "✅ У вас уже есть доступ к этому предмету!",
        "restart_quiz": "🔄 Новый тест",
        "back_to_subject": "📘 К предмету",
        "grade_excellent": "🌟 Отлично! Вы готовы к экзамену!",
        "grade_good": "👍 Хороший результат! Повторите слабые темы.",
        "grade_ok": "📚 Неплохо, но стоит поучить ещё.",
        "grade_bad": "💪 Не сдавайтесь! Изучите материал и попробуйте снова.",
    },
    "en": {
        "welcome": "👋 Hello! Welcome to *Study Hub BMU*\n\nChoose your language:",
        "main_menu": "📚 *Study Hub — British Management University*\n\nChoose an action:",
        "my_subjects": "📖 My Subjects",
        "buy_access": "🛒 Buy Access",
        "help": "❓ Help",
        "choose_subject_buy": "Choose a subject to purchase access:",
        "choose_subject_study": "Choose a subject to study:",
        "payment_instruction": "💳 *Payment for «{subject}»*\n\nPrice: *{price:,} UZS*\n\nTransfer to card:\n`{card}`\n\nAfter payment, send a screenshot 👇",
        "screenshot_received": "✅ Screenshot received! Your payment is being reviewed.\n\nThis usually takes up to 30 minutes. You'll get a notification once access is granted.",
        "access_granted": "🎉 *Access Granted!*\n\n*{subject}* is now available in «My Subjects».",
        "access_denied": "❌ Payment not confirmed. Please contact @admin or try again.",
        "no_subjects": "You don't have any subjects yet.\n\nGo to «Buy Access» 🛒",
        "subject_menu": "📘 *{subject}*\n\nChoose a mode:",
        "study_materials": "📖 Study Notes",
        "flashcards": "🃏 Flashcards",
        "quiz": "✏️ Practice Test (MCQ)",
        "back": "← Back",
        "quiz_start": "🧠 *Quiz: {subject}*\n\nQuestion {num}/10:\n\n{question}",
        "correct": "✅ *Correct!*\n\n{explanation}",
        "wrong": "❌ *Wrong.*\nCorrect answer: *{correct}*\n\n{explanation}",
        "quiz_done": "🏁 *Quiz Complete!*\n\nScore: *{score}/10*\n{grade}\n\nPress a button to continue:",
        "flashcard_front": "🃏 *Flashcard {num}/{total}*\n\n❓ {term}",
        "flashcard_back": "💡 *Answer:*\n\n{definition}",
        "show_answer": "👁 Show Answer",
        "next_card": "➡️ Next",
        "prev_card": "⬅️ Previous",
        "finish_flashcards": "✅ Finish",
        "flashcards_done": "🎉 Flashcards complete! Good luck on your exam!",
        "help_text": "❓ *Help*\n\nFor payment & access issues: @your_username\n\nBot runs 24/7. Access is granted within 30 minutes after payment.",
        "already_has_access": "✅ You already have access to this subject!",
        "restart_quiz": "🔄 New Quiz",
        "back_to_subject": "📘 Back to Subject",
        "grade_excellent": "🌟 Excellent! You're ready for the exam!",
        "grade_good": "👍 Good result! Review your weak areas.",
        "grade_ok": "📚 Not bad, but keep studying.",
        "grade_bad": "💪 Don't give up! Study the material and try again.",
    }
}

def t(user_id, key, **kwargs):
    lang = db.get_user_lang(user_id) or "en"
    text = TEXTS[lang].get(key, key)
    return text.format(**kwargs) if kwargs else text


# ─── /start ───────────────────────────────────────────────────────────────────

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
        [InlineKeyboardButton(t(user_id, "help"), callback_data="menu_help")],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    text = t(user_id, "main_menu")
    if edit:
        await message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await message.reply_text(text, parse_mode="Markdown", reply_markup=markup)


# ─── MAIN MENU ────────────────────────────────────────────────────────────────

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

    elif action == "menu_help":
        keyboard = [[InlineKeyboardButton(t(user_id, "back"), callback_data="back_main")]]
        await query.message.edit_text(t(user_id, "help_text"), parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(keyboard))
        return MAIN_MENU

    elif action == "back_main":
        await show_main_menu(query.message, user_id, edit=True)
        return MAIN_MENU


# ─── SUBJECT SELECTION ────────────────────────────────────────────────────────

async def subject_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "back_main":
        await show_main_menu(query.message, user_id, edit=True)
        return MAIN_MENU

    if data.startswith("already_"):
        subject_key = data.split("_", 1)[1]
        await query.answer(t(user_id, "already_has_access"), show_alert=True)
        return CHOOSING_SUBJECT

    if data.startswith("buy_"):
        subject_key = data.split("_", 1)[1]
        context.user_data["pending_subject"] = subject_key
        info = SUBJECTS[subject_key]
        text = t(user_id, "payment_instruction",
                 subject=info["name"], price=PRICE_PER_SUBJECT, card=CARD_NUMBER)
        keyboard = [[InlineKeyboardButton(t(user_id, "back"), callback_data="back_main")]]
        await query.message.edit_text(text, parse_mode="Markdown",
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
        [InlineKeyboardButton(t(user_id, "study_materials"), callback_data=f"materials_{subject_key}")],
        [InlineKeyboardButton(t(user_id, "flashcards"), callback_data=f"flashcards_{subject_key}")],
        [InlineKeyboardButton(t(user_id, "quiz"), callback_data=f"quiz_{subject_key}")],
        [InlineKeyboardButton(t(user_id, "back"), callback_data="back_main")],
    ]
    text = t(user_id, "subject_menu", subject=info["name"])
    if edit:
        await message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


# ─── PAYMENT SCREENSHOT ───────────────────────────────────────────────────────

async def receive_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = update.effective_user
    subject_key = context.user_data.get("pending_subject")

    if not subject_key:
        await show_main_menu(update.message, user_id)
        return MAIN_MENU

    info = SUBJECTS[subject_key]
    db.add_pending_payment(user_id, subject_key)

    # Notify admin
    approve_cb = f"approve_{user_id}_{subject_key}"
    deny_cb = f"deny_{user_id}_{subject_key}"
    admin_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить", callback_data=approve_cb),
         InlineKeyboardButton("❌ Отклонить", callback_data=deny_cb)]
    ])
    name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    username = f"@{user.username}" if user.username else "без username"
    admin_text = (f"💰 *Новая оплата*\n\n"
                  f"👤 {name} ({username})\n"
                  f"🆔 `{user_id}`\n"
                  f"📘 Предмет: *{info['name']}*\n"
                  f"💵 Сумма: {PRICE_PER_SUBJECT:,} сум")

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


# ─── ADMIN APPROVE/DENY ───────────────────────────────────────────────────────

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
        try:
            await context.bot.send_message(student_id, msg, parse_mode="Markdown")
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


# ─── SUBJECT MENU HANDLER ─────────────────────────────────────────────────────

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

    if data.startswith("materials_"):
        subject_key = data.split("_", 1)[1]
        await send_materials(query.message, user_id, subject_key)
        return SUBJECT_MENU

    if data.startswith("flashcards_"):
        subject_key = data.split("_", 1)[1]
        context.user_data["flashcard_subject"] = subject_key
        context.user_data["flashcard_index"] = 0
        context.user_data["flashcard_showing_answer"] = False
        await show_flashcard(query.message, user_id, subject_key, 0, False, edit=True)
        return FLASHCARD_SESSION

    if data.startswith("quiz_"):
        subject_key = data.split("_", 1)[1]
        await start_quiz(query.message, context, user_id, subject_key, edit=True)
        return QUIZ_SESSION


async def send_materials(message, user_id, subject_key):
    info = get_subject_info(subject_key)
    lang = db.get_user_lang(user_id) or "en"
    chapters = info.get("chapters", [])

    header = f"📘 *{info['name']}*\n{'─' * 30}\n\n"
    await message.edit_text(
        header + "⏳ Loading study notes...",
        parse_mode="Markdown"
    )

    full_text = header
    for i, chapter in enumerate(chapters, 1):
        full_text += f"*{i}. {chapter['title']}*\n"
        full_text += chapter['content'] + "\n\n"

    # Telegram message limit is 4096 chars
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


# ─── FLASHCARDS ───────────────────────────────────────────────────────────────

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
    showing = context.user_data.get("flashcard_showing_answer", False)

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


# ─── QUIZ ─────────────────────────────────────────────────────────────────────

async def start_quiz(message, context, user_id, subject_key, edit=False):
    all_q = get_quiz_questions(subject_key)
    questions = random.sample(all_q, min(10, len(all_q)))
    context.user_data["quiz_questions"] = questions
    context.user_data["quiz_index"] = 0
    context.user_data["quiz_score"] = 0
    context.user_data["quiz_subject"] = subject_key
    await show_quiz_question(message, user_id, context, edit=edit)


async def show_quiz_question(message, user_id, context, edit=False):
    questions = context.user_data["quiz_questions"]
    index = context.user_data["quiz_index"]
    subject_key = context.user_data["quiz_subject"]
    q = questions[index]

    text = t(user_id, "quiz_start",
             subject=SUBJECTS[subject_key]["name"],
             num=index+1, question=q["question"])

    options = q["options"][:]
    keyboard = [[InlineKeyboardButton(opt, callback_data=f"quiz_ans_{i}")] for i, opt in enumerate(options)]
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
        q = questions[index]
        correct_index = q["correct"]
        is_correct = (answer_index == correct_index)

        if is_correct:
            context.user_data["quiz_score"] += 1
            result_text = t(user_id, "correct", explanation=q.get("explanation", ""))
        else:
            result_text = t(user_id, "wrong",
                            correct=q["options"][correct_index],
                            explanation=q.get("explanation", ""))

        next_index = index + 1
        context.user_data["quiz_index"] = next_index

        if next_index >= len(questions):
            score = context.user_data["quiz_score"]
            if score >= 9:
                grade = t(user_id, "grade_excellent")
            elif score >= 7:
                grade = t(user_id, "grade_good")
            elif score >= 5:
                grade = t(user_id, "grade_ok")
            else:
                grade = t(user_id, "grade_bad")

            done_text = result_text + "\n\n" + t(user_id, "quiz_done", score=score, grade=grade)
            keyboard = [
                [InlineKeyboardButton(t(user_id, "restart_quiz"), callback_data=f"quiz_restart_{subject_key}")],
                [InlineKeyboardButton(t(user_id, "back_to_subject"), callback_data=f"back_subject_{subject_key}")],
                [InlineKeyboardButton(t(user_id, "back"), callback_data="back_main")],
            ]
            await query.message.edit_text(done_text, parse_mode="Markdown",
                                          reply_markup=InlineKeyboardMarkup(keyboard))
            return SUBJECT_MENU
        else:
            keyboard = [[InlineKeyboardButton("➡️ Next Question", callback_data="quiz_next")]]
            await query.message.edit_text(result_text, parse_mode="Markdown",
                                          reply_markup=InlineKeyboardMarkup(keyboard))
            return QUIZ_SESSION

    if data == "quiz_next":
        await show_quiz_question(query.message, user_id, context, edit=True)
        return QUIZ_SESSION


# ─── FALLBACK ─────────────────────────────────────────────────────────────────

async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        user_id = update.effective_user.id
        await show_main_menu(update.message, user_id)
    return MAIN_MENU


def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN environment variable not set!")

    db.init()
    app = Application.builder().token(token).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_LANG: [CallbackQueryHandler(set_language, pattern="^lang_")],
            MAIN_MENU: [CallbackQueryHandler(main_menu_handler)],
            CHOOSING_SUBJECT: [CallbackQueryHandler(subject_handler)],
            PAYMENT_SCREENSHOT: [
                MessageHandler(filters.PHOTO | filters.Document.ALL, receive_screenshot),
                CallbackQueryHandler(main_menu_handler, pattern="^back_main$"),
            ],
            SUBJECT_MENU: [CallbackQueryHandler(subject_menu_handler)],
            QUIZ_SESSION: [CallbackQueryHandler(quiz_handler)],
            FLASHCARD_SESSION: [CallbackQueryHandler(flashcard_handler)],
        },
        fallbacks=[CommandHandler("start", start), MessageHandler(filters.ALL, fallback)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(admin_action, pattern="^(approve|deny)_"))
    app.run_polling()


if __name__ == "__main__":
    main()
