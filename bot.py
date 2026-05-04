import logging
import os
import random
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)
from database import db
from content import SUBJECTS, get_subject_info, get_flashcards, get_quiz_questions, get_cheatsheet, get_glossary, get_true_false, get_videos
from config import ADMIN_ID, CARD_NUMBER, PRICE_PER_SUBJECT
try:
    from google import genai as genai_client
    from google.genai import types as genai_types
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

# ── RATE LIMITER (AI tools cooldown) ─────────────────────────────────────────
_ai_last_call: dict = {}  # user_id -> timestamp
AI_COOLDOWN_SECONDS = 10

def check_ai_rate_limit(user_id: int) -> float:
    """Returns 0 if allowed, or seconds remaining if on cooldown."""
    now = time.time()
    last = _ai_last_call.get(user_id, 0)
    remaining = AI_COOLDOWN_SECONDS - (now - last)
    if remaining > 0:
        return remaining
    _ai_last_call[user_id] = now
    return 0

# ── ADMIN ACTION GUARD (prevent double-click) ─────────────────────────────────
_processed_admin_actions: set = set()

(CHOOSING_LANG, MAIN_MENU, CHOOSING_SUBJECT, PAYMENT_SCREENSHOT,
 SUBJECT_MENU, QUIZ_SESSION, FLASHCARD_SESSION, TRIAL_SESSION,
 AI_CHAT_SESSION, BOOKMARKS_SESSION, TF_SESSION, EXAM_DATE_INPUT,
 ONBOARDING) = range(13)

FREE_QUESTIONS = 3
QUIZ_QUESTIONS_COUNT = 20

TEXTS = {
    "ru": {
        "welcome": "✨ *Добро пожаловать в BMU Study Hub!*\n\n🎓 Умная подготовка к экзаменам\n📚 Конспекты · Тесты · Флэшкарты · ИИ\n\n━━━━━━━━━━━━━━━\n🌐 Выберите язык:",
        # Onboarding
        "onboarding_skip": "Пропустить →",
        "onboarding_next": "Далее →",
        "onboarding_start": "Начать →",
        "onboarding_1": (
            "👋 *Привет, {name}!*\n\n"
            "━━━━━━━━━━━━━━━\n"
            "Добро пожаловать в *BMU Study Hub* —\n"
            "твой личный помощник для подготовки к экзаменам.\n\n"
            "За 20 секунд покажу что умею 👇\n\n"
            "_1 из 3_"
        ),
        "onboarding_2": (
            "🎓 *Что есть в боте:*\n\n"
            "━━━━━━━━━━━━━━━\n"
            "✏️ MCQ тесты и ⚡ True/False\n"
            "📖 Теории по каждой теме\n"
            "🃏 Флэшкарты для запоминания\n"
            "🎬 Видео с объяснениями\n"
            "🤖 ИИ-преподаватель 24/7\n"
            "📊 Прогресс и статистика\n\n"
            "━━━━━━━━━━━━━━━\n"
            "🆓 *Бесплатно:* AI Humanizer · AI Detector · Демо-тест\n\n"
            "_2 из 3_"
        ),
        "onboarding_3": (
            "🚀 *Готов начать?*\n\n"
            "━━━━━━━━━━━━━━━\n"
            "Попробуй прямо сейчас — бесплатно,\n"
            "без регистрации и оплаты 👇\n\n"
            "_3 из 3_"
        ),
        "main_menu": "🎓 *BMU Study Hub*\n_British Management University_\n\n━━━━━━━━━━━━━━━\n\nЧто будем делать сегодня?",
        "my_subjects": "💎 Мои курсы",
        "buy_access": "💳 Купить доступ",
        "trial_quiz": "🆓 Демо-тест",
        "help": "💬 Поддержка",
        "choose_subject_buy": "🛒 *Купить доступ*\n\n━━━━━━━━━━━━━━━\nВыберите предмет:",
        "choose_subject_study": (
            "💎 *Мои курсы*\n\n"
            "━━━━━━━━━━━━━━━\n"
            "✏️ MCQ  ⚡ True/False  📖 Теории\n"
            "🃏 Флэшкарты  🎬 Видео\n"
            "🤖 ИИ-преподаватель  📊 Прогресс\n\n"
            "━━━━━━━━━━━━━━━\n"
            "Выберите предмет:"
        ),
        "choose_trial_subject": "🎯 *Пробный режим — бесплатно*\n\n━━━━━━━━━━━━━━━\nВыберите предмет\n_без оплаты_",
        "trial_choose_type": "🎯 *Пробный режим: {subject}*\n\n━━━━━━━━━━━━━━━\nЧто хотите попробовать?",
        "trial_type_mcq": "✏️ MCQ Тест (3 вопроса)",
        "trial_type_tf": "⚡ True / False (5 вопросов)",
        "trial_tf_done": "🏁 *Пробный True/False завершён!*\n\n━━━━━━━━━━━━━━━\n📊 Ваш результат: *{score} / {total}*\n\n━━━━━━━━━━━━━━━\n💎 *Полная версия включает:*\n✏️ 20 вопросов MCQ\n⚡ True/False полный\n📖 Теории\n🃏 Флэшкарты\n📊 История и прогресс\n🤖 ИИ-преподаватель\n\n👇 Купите доступ прямо сейчас!",
        "admin_profile_not_found": "❌ Студент с ID `{user_id}` не найден.",
        "admin_profile_text": "👤 *Профиль студента*\n\n━━━━━━━━━━━━━━━\n🔹 Имя: *{first_name}*\n🔹 Username: *{username}*\n🆔 ID: `{user_id}`\n🌐 Язык: *{lang}*\n📅 Регистрация: *{created_at}*\n\n━━━━━━━━━━━━━━━\n📚 *Предметы:* {subjects}\n\n📊 *Активность:*\n✏️ Тестов пройдено: *{tests}*\n📈 Средний балл: *{avg}%*\n⚡ XP: *{xp}*\n🏅 Уровень: *{level}*\n🔥 Серия: *{streak}* дней\n📆 Последняя активность: *{last_activity}*",
        "admin_giveaccess_usage": "Использование: /giveaccess USER_ID SUBJECT_KEY\nПример: /giveaccess 123456789 f1\nДля всех предметов: /giveaccess 123456789 all",
        "admin_giveaccess_done": "✅ Доступ к *{subject}* выдан студенту `{user_id}`",
        "admin_giveaccess_all_done": "✅ Доступ ко *всем предметам* выдан студенту `{user_id}`",
        "payment_instruction": "💳 *Оплата доступа*\n\n📘 Предмет: *{subject}*\n💰 Стоимость: *{price:,} сум*\n\n━━━━━━━━━━━━━━━\n🏦 Переведите на карту:\n`{card}`\n\n━━━━━━━━━━━━━━━\n📸 После оплаты отправьте скриншот перевода 👇",
        "screenshot_received": "✅ *Скриншот получен!*\n\n⏳ Ваша оплата на проверке\n🕐 Обычно до *30 минут*\n\n━━━━━━━━━━━━━━━\n🔔 Вы получите уведомление как только доступ откроется.",
        "access_granted": "🎉 *Поздравляем! Доступ открыт!*\n\n━━━━━━━━━━━━━━━\n📘 Предмет *{subject}* теперь доступен!\n\n✨ Удачи в учёбе!",
        "access_denied": "❌ *Оплата не подтверждена*\n\n━━━━━━━━━━━━━━━\nПожалуйста, свяжитесь с администратором.",
        "no_subjects": (
            "💎 *Мои курсы*\n\n"
            "━━━━━━━━━━━━━━━\n"
            "У вас пока нет активных курсов.\n\n"
            "*Что входит в каждый курс:*\n\n"
            "✏️ MCQ Тесты — тренируй и закрепляй\n"
            "⚡ True / False — быстрая проверка знаний\n"
            "📖 Теории — весь материал по предмету\n"
            "🃏 Флэшкарты — повторяй термины эффективно\n"
            "🎬 Видео — визуальное объяснение тем\n"
            "🤖 ИИ-преподаватель — задай любой вопрос\n"
            "📊 Прогресс — следи за своим ростом\n\n"
            "━━━━━━━━━━━━━━━\n"
            "👇 Выберите предмет и начните подготовку"
        ),
        "subject_menu": "📘 *{subject}*\n\n━━━━━━━━━━━━━━━\n_Выберите режим обучения:_",
        "study_materials": "📖 Теории",
        "flashcards": "🃏 Флэшкарты",
        "quiz": "✏️ Тест MCQ",
        "progress": "📊 Прогресс",
        "back": "← Назад",
        "quiz_start": "🧠 *{subject}*\n\n━━━━━━━━━━━━━━━\n📌 Вопрос *{num}* из *{total}*\n\n{question}",
        "correct": "✅ *Правильно!*\n\n💡 {explanation}",
        "wrong": "❌ *Неверно*\n\n✔️ Правильный ответ:\n*{correct}*\n\n💡 {explanation}",
        "quiz_done": "🏁 *Тест завершён!*\n\n━━━━━━━━━━━━━━━\n📊 Результат: *{score}/{total}*\n\n{grade}\n\n━━━━━━━━━━━━━━━",
        "flashcard_front": "🃏 *Флэшкарта {num} / {total}*\n\n━━━━━━━━━━━━━━━\n❓ *{term}*",
        "flashcard_back": "🃏 *Флэшкарта {num} / {total}*\n\n━━━━━━━━━━━━━━━\n❓ *{term}*\n\n💡 *Ответ:*\n{definition}",
        "show_answer": "👁 Показать ответ",
        "next_card": "➡️ Следующая",
        "prev_card": "⬅️ Предыдущая",
        "finish_flashcards": "✅ Завершить",
        "flashcards_done": "🎉 *Флэшкарты пройдены!*\n\n━━━━━━━━━━━━━━━\n💪 Отличная работа! Удачи на экзамене!",
        "help_text": "💬 *Поддержка*\n\n━━━━━━━━━━━━━━━\n📩 По вопросам оплаты и доступа:\n👤 Напишите администратору: @user\n\n⏰ Бот работает 24/7\n✅ Доступ открывается в течение 30 минут после оплаты",
        "already_has_access": "✅ У вас уже есть доступ к этому предмету!",
        "restart_quiz": "🔄 Пройти снова",
        "back_to_subject": "📘 К предмету",
        "grade_excellent": "🌟 *Отлично!* Вы готовы к экзамену!",
        "grade_good": "👍 *Хороший результат!* Повторите слабые темы.",
        "grade_ok": "📚 *Неплохо!* Ещё немного практики.",
        "grade_bad": "💪 *Не сдавайтесь!* Изучите материал и попробуйте снова.",
        "trial_question": "🎯 *Пробный тест: {subject}*\n\n━━━━━━━━━━━━━━━\n📌 Вопрос *{num}* из *3*\n\n{question}",
        "trial_done": "🏁 *Пробный тест завершён!*\n\n━━━━━━━━━━━━━━━\n📊 Ваш результат: *{score} / 3*\n\n━━━━━━━━━━━━━━━\n💎 *Полная версия включает:*\n✏️ 20 вопросов MCQ\n📖 Полный конспект\n🃏 Флэшкарты\n📊 История и прогресс\n🤖 ИИ-преподаватель\n\n👇 Купите доступ прямо сейчас!",
        "buy_now": "💳 Купить полный доступ",
        "progress_text": "📊 *Прогресс — {subject}*\n\n━━━━━━━━━━━━━━━\n✏️ Тестов пройдено: *{tests}*\n📈 Средний балл: *{avg}%*\n🏆 Лучший результат: *{best}%*\n🃏 Флэшкарт изучено: *{cards}*",
        "no_progress": "📊 *Прогресс пока пуст*\n\n━━━━━━━━━━━━━━━\nПройдите первый тест чтобы увидеть статистику! ✏️",
        "promo_enter": "🎁 *Промокод*\n\n━━━━━━━━━━━━━━━\nВведите ваш промокод:",
        "promo_valid": "🎉 *Промокод активирован!*\n\n━━━━━━━━━━━━━━━\n💸 Скидка: *{discount}%*\n💰 Цена со скидкой: *{price:,} сум*",
        "promo_invalid": "❌ *Промокод не найден*\n\nПопробуйте другой код или нажмите Назад.",
        "enter_promo": "🎁 У меня есть промокод",
        "stats_title": "📈 *Статистика — BMU Study Hub*\n\n━━━━━━━━━━━━━━━\n👥 Студентов: *{users}*\n💰 Оплат: *{paid}*\n💵 Выручка: *{revenue:,} сум*\n\n━━━━━━━━━━━━━━━\n📘 По предметам:",
        # AI Chat
        "ai_chat": "🤖 ИИ-преподаватель",
        "ai_chat_intro": "🤖 *ИИ-преподаватель*\n_Предмет: {subject}_\n\n━━━━━━━━━━━━━━━\nЗадайте любой вопрос — я объясню, приведу примеры и помогу разобраться!\n\n💬 _Введите вопрос:_",
        "ai_thinking": "🤔 _Думаю над ответом..._",
        "ai_clear": "🗑 Очистить историю",
        "ai_history_cleared": "✅ История чата очищена.",
        "ai_unavailable": "⚠️ ИИ-чат временно недоступен.",
        # Quiz history
        "quiz_history": "📋 История тестов",
        "quiz_history_empty": "📋 *История тестов пуста*\n\n━━━━━━━━━━━━━━━\nПройдите первый тест прямо сейчас! ✏️",
        "quiz_history_title": "📋 *История тестов*\n_{subject}_\n\n━━━━━━━━━━━━━━━\n",
        "quiz_history_all": "📋 *Все тесты*\n\n━━━━━━━━━━━━━━━\n",
        # Bookmarks
        "bookmarks": "🔖 Закладки",
        "bookmark_saved": "🔖 Сохранено в закладки!",
        "bookmark_exists": "✅ Уже в закладках.",
        "bookmarks_empty": "🔖 *Закладок пока нет*\n\n━━━━━━━━━━━━━━━\nВо время теста нажимайте 🔖 чтобы сохранить сложный вопрос.",
        "bookmarks_title": "🔖 *Мои закладки*\n\n━━━━━━━━━━━━━━━\n",
        "bookmark_delete": "🗑 Удалить",
        "bookmark_deleted": "✅ Закладка удалена.",
        # Language change
        "change_lang": "🌐 Язык",
        # Cheatsheet
        "cheatsheet": "📝 Шпаргалка",
        "cheatsheet_title": "📝 *Шпаргалка*\n_{subject}_\n\n━━━━━━━━━━━━━━━\n",
        # Glossary
        "glossary": "📖 Глоссарий",
        # XP / Streak / Leaderboard
        "leaderboard": "🏆 Лидерборд",
        "my_rank": "⚡ Мой рейтинг",
        "xp_earned": "⚡ +{xp} XP заработано!",
        "level_up": "🎉 *Новый уровень!* Вы достигли уровня *{level}*!",
        "streak_bonus": "🔥 Бонус за серию +{bonus} XP!",
        "leaderboard_title": "🏆 *Лидерборд*\n_BMU Study Hub_\n\n━━━━━━━━━━━━━━━\n",
        "my_stats": "⚡ *Мои достижения*\n\n━━━━━━━━━━━━━━━\n🏅 Уровень: *{level}* {badge}\n⚡ XP: *{xp}*\n🔥 Серия: *{streak}* дней\n\n{progress_bar}\n_До следующего уровня: *{xp_needed}* XP_",
        "glossary_intro": "📖 *Глоссарий*\n_{subject}_\n\n━━━━━━━━━━━━━━━\nВведите термин для поиска:",
        "glossary_not_found": "❌ Термин не найден. Попробуйте другое слово.",
        # True/False
        "true_false": "✅❌ True / False",
        "tf_question": "⚡ *True / False*\n_{subject}_\n\n━━━━━━━━━━━━━━━\n📌 Вопрос *{num}* из *{total}*\n\n_{statement}_",
        "tf_correct": "✅ *Верно!*\n\n💡 {explanation}",
        "tf_wrong": "❌ *Неверно!*\n\nПравильный ответ: *{correct}*\n💡 {explanation}",
        "tf_done": "🏁 *True/False завершён!*\n\n━━━━━━━━━━━━━━━\n📊 Результат: *{score}/{total}*\n{grade}",
        "tf_true": "✅ Верно",
        "tf_false": "❌ Неверно",
        # Exam plan
        "exam_plan": "📅 План подготовки",
        "exam_date_ask": "📅 *Предэкзаменационный режим*\n_{subject}_\n\n━━━━━━━━━━━━━━━\nВведите дату экзамена в формате:\n*ДД.ММ.ГГГГ*\n\n_Например: 25.06.2025_",
        "exam_date_invalid": "❌ Неверный формат. Введите дату как *ДД.ММ.ГГГГ*\n\nПример: *25.06.2025*",
        "exam_date_past": "❌ Дата уже прошла. Введите будущую дату.",
        "exam_plan_title": "📅 *План подготовки к экзамену*\n_{subject}_\n\n━━━━━━━━━━━━━━━\n📆 Экзамен: *{date}*\n⏳ Дней осталось: *{days}*\n\n",
        "exam_plan_generating": "⏳ Составляю план...",
        "exam_plan_exists": "📅 *Ваш план подготовки*\n_{subject}_\n━━━━━━━━━━━━━━━\n📆 Экзамен: *{date}*\n⏳ Осталось дней: *{days}*\n\n{plan}",
        "exam_plan_new": "🔄 Новый план",
        # Videos
        "videos": "🎬 Видео",
        "videos_title": "🎬 *Видео по предмету*\n_{subject}_\n\n━━━━━━━━━━━━━━━\n",
        # Comparison
        "quiz_comparison": "📈 Прогресс +{delta}% по сравнению с прошлым разом!",
        "quiz_regression": "📉 В прошлый раз было лучше на {delta}%. Не сдавайся!",
        "quiz_same": "➡️ Такой же результат как в прошлый раз.",
        # Bundle
        "bundle": "🎓 Пакеты предметов",
        "bundle_text": "🎓 *Пакет «Все предметы»*\n\n━━━━━━━━━━━━━━━\n📚 Включает все {count} предмета\n\n💰 Обычная цена: *{full_price:,} сум*\n🔥 Цена пакета: *{bundle_price:,} сум*\n💸 Экономия: *{save:,} сум* (скидка 20%!)\n\n━━━━━━━━━━━━━━━\n🏦 Переведите на карту:\n`{card}`\n\n📸 После оплаты отправьте скриншот 👇",
        "bundle_already": "✅ У вас уже есть доступ ко всем предметам!",
        "bundle_choose": "🎓 *Пакеты предметов*\n\n━━━━━━━━━━━━━━━\nВыберите пакет:\n\n📦 *2 предмета* — скидка *10%*\n📦 *4 предмета* — скидка *20%*",
        "bundle2_text": "📦 *Пакет 2 предмета (-10%)*\n\n━━━━━━━━━━━━━━━\nВыберите 2 предмета:\n\n💰 Обычная цена: *{full_price:,} сум*\n🔥 Цена пакета: *{bundle_price:,} сум*\n💸 Экономия: *{save:,} сум*\n\n━━━━━━━━━━━━━━━\n🏦 Переведите на карту:\n`{card}`\n\n📸 После оплаты отправьте скриншот 👇",
        "bundle4_text": "📦 *Пакет 4 предмета (-20%)*\n\n━━━━━━━━━━━━━━━\n📚 Все {count} предмета\n\n💰 Обычная цена: *{full_price:,} сум*\n🔥 Цена пакета: *{bundle_price:,} сум*\n💸 Экономия: *{save:,} сум*\n\n━━━━━━━━━━━━━━━\n🏦 Переведите на карту:\n`{card}`\n\n📸 После оплаты отправьте скриншот 👇",
        "bundle_select_2": "Выберите 2 предмета (нажмите на каждый):",
        "bundle_selected": "✅ Выбрано: {subjects}",
        "bundle_need_more": "❗ Выберите ещё {n} предмет(а)",
        # AI Humanizer
        # AI Detector
    },
    "en": {
        "welcome": "✨ *Welcome to BMU Study Hub!*\n\n🎓 Smart exam preparation\n📚 Notes · Tests · Flashcards · AI\n\n━━━━━━━━━━━━━━━\n🌐 Choose your language:",
        # Onboarding
        "onboarding_skip": "Skip →",
        "onboarding_next": "Next →",
        "onboarding_start": "Let's go →",
        "onboarding_1": (
            "👋 *Hey, {name}!*\n\n"
            "━━━━━━━━━━━━━━━\n"
            "Welcome to *BMU Study Hub* —\n"
            "your personal exam preparation assistant.\n\n"
            "Let me show you around in 20 seconds 👇\n\n"
            "_1 of 3_"
        ),
        "onboarding_2": (
            "🎓 *What's inside:*\n\n"
            "━━━━━━━━━━━━━━━\n"
            "✏️ MCQ Tests and ⚡ True/False\n"
            "📖 Theories for every topic\n"
            "🃏 Flashcards for memorisation\n"
            "🎬 Video explanations\n"
            "🤖 AI Tutor available 24/7\n"
            "📊 Progress and statistics\n\n"
            "━━━━━━━━━━━━━━━\n"
            "🆓 *Free:* AI Humanizer · AI Detector · Demo Test\n\n"
            "_2 of 3_"
        ),
        "onboarding_3": (
            "🚀 *Ready to start?*\n\n"
            "━━━━━━━━━━━━━━━\n"
            "Try it right now — free,\n"
            "no registration or payment needed 👇\n\n"
            "_3 of 3_"
        ),
        "main_menu": "🎓 *BMU Study Hub*\n_British Management University_\n\n━━━━━━━━━━━━━━━\n\nWhat shall we study today?",
        "my_subjects": "💎 My Courses",
        "buy_access": "💳 Buy Access",
        "trial_quiz": "🆓 Demo Test",
        "help": "💬 Support",
        "choose_subject_buy": "🛒 *Buy Access*\n\n━━━━━━━━━━━━━━━\nChoose a subject:",
        "choose_subject_study": (
            "💎 *My Courses*\n\n"
            "━━━━━━━━━━━━━━━\n"
            "✏️ MCQ  ⚡ True/False  📖 Theories\n"
            "🃏 Flashcards  🎬 Videos\n"
            "🤖 AI Tutor  📊 Progress\n\n"
            "━━━━━━━━━━━━━━━\n"
            "Choose a subject:"
        ),
        "choose_trial_subject": "🎯 *Free Trial*\n\n━━━━━━━━━━━━━━━\nChoose a subject\n_no payment needed_",
        "trial_choose_type": "🎯 *Free Trial: {subject}*\n\n━━━━━━━━━━━━━━━\nWhat would you like to try?",
        "trial_type_mcq": "✏️ MCQ Test (3 questions)",
        "trial_type_tf": "⚡ True / False (5 questions)",
        "trial_tf_done": "🏁 *Free Trial True/False Complete!*\n\n━━━━━━━━━━━━━━━\n📊 Your score: *{score} / {total}*\n\n━━━━━━━━━━━━━━━\n💎 *Full version includes:*\n✏️ 20 MCQ questions\n⚡ Full True/False\n📖 Theories\n🃏 Flashcards\n📊 History & progress\n🤖 AI Tutor\n\n👇 Buy access now!",
        "admin_profile_not_found": "❌ Student with ID `{user_id}` not found.",
        "admin_profile_text": "👤 *Student Profile*\n\n━━━━━━━━━━━━━━━\n🔹 Name: *{first_name}*\n🔹 Username: *{username}*\n🆔 ID: `{user_id}`\n🌐 Language: *{lang}*\n📅 Registered: *{created_at}*\n\n━━━━━━━━━━━━━━━\n📚 *Subjects:* {subjects}\n\n📊 *Activity:*\n✏️ Tests taken: *{tests}*\n📈 Average score: *{avg}%*\n⚡ XP: *{xp}*\n🏅 Level: *{level}*\n🔥 Streak: *{streak}* days\n📆 Last activity: *{last_activity}*",
        "admin_giveaccess_usage": "Usage: /giveaccess USER_ID SUBJECT_KEY\nExample: /giveaccess 123456789 f1\nFor all subjects: /giveaccess 123456789 all",
        "admin_giveaccess_done": "✅ Access to *{subject}* granted to student `{user_id}`",
        "admin_giveaccess_all_done": "✅ Access to *all subjects* granted to student `{user_id}`",
        "payment_instruction": "💳 *Purchase Access*\n\n📘 Subject: *{subject}*\n💰 Price: *{price:,} UZS*\n\n━━━━━━━━━━━━━━━\n🏦 Transfer to card:\n`{card}`\n\n━━━━━━━━━━━━━━━\n📸 After payment, send a screenshot 👇",
        "screenshot_received": "✅ *Screenshot received!*\n\n⏳ Your payment is under review\n🕐 Usually within *30 minutes*\n\n━━━━━━━━━━━━━━━\n🔔 You'll get a notification once access is granted.",
        "access_granted": "🎉 *Congratulations! Access Granted!*\n\n━━━━━━━━━━━━━━━\n📘 *{subject}* is now available!\n\n✨ Good luck with your studies!",
        "access_denied": "❌ *Payment Not Confirmed*\n\n━━━━━━━━━━━━━━━\nPlease contact the administrator.",
        "no_subjects": (
            "💎 *My Courses*\n\n"
            "━━━━━━━━━━━━━━━\n"
            "You don't have any active courses yet.\n\n"
            "*What's included in every course:*\n\n"
            "✏️ MCQ Tests — practise and consolidate\n"
            "⚡ True / False — quick knowledge checks\n"
            "📖 Theories — full study material\n"
            "🃏 Flashcards — revise terms effectively\n"
            "🎬 Videos — visual topic explanations\n"
            "🤖 AI Tutor — ask anything, get answered\n"
            "📊 Progress — track your growth\n\n"
            "━━━━━━━━━━━━━━━\n"
            "👇 Choose a subject and start preparing"
        ),
        "subject_menu": "📘 *{subject}*\n\n━━━━━━━━━━━━━━━\n_Choose a study mode:_",
        "study_materials": "📖 Theories",
        "flashcards": "🃏 Flashcards",
        "quiz": "✏️ Practice Test",
        "progress": "📊 Progress",
        "back": "← Back",
        "quiz_start": "🧠 *{subject}*\n\n━━━━━━━━━━━━━━━\n📌 Question *{num}* of *{total}*\n\n{question}",
        "correct": "✅ *Correct!*\n\n💡 {explanation}",
        "wrong": "❌ *Wrong*\n\n✔️ Correct answer:\n*{correct}*\n\n💡 {explanation}",
        "quiz_done": "🏁 *Quiz Complete!*\n\n━━━━━━━━━━━━━━━\n📊 Score: *{score}/{total}*\n\n{grade}\n\n━━━━━━━━━━━━━━━",
        "flashcard_front": "🃏 *Flashcard {num} / {total}*\n\n━━━━━━━━━━━━━━━\n❓ *{term}*",
        "flashcard_back": "🃏 *Flashcard {num} / {total}*\n\n━━━━━━━━━━━━━━━\n❓ *{term}*\n\n💡 *Answer:*\n{definition}",
        "show_answer": "👁 Show Answer",
        "next_card": "➡️ Next",
        "prev_card": "⬅️ Previous",
        "finish_flashcards": "✅ Finish",
        "flashcards_done": "🎉 *Flashcards Complete!*\n\n━━━━━━━━━━━━━━━\n💪 Great work! Good luck on your exam!",
        "help_text": "💬 *Support*\n\n━━━━━━━━━━━━━━━\n📩 For payment & access issues:\n👤 Contact the admin: @user\n\n⏰ Bot runs 24/7\n✅ Access granted within 30 minutes of payment",
        "already_has_access": "✅ You already have access to this subject!",
        "restart_quiz": "🔄 Try Again",
        "back_to_subject": "📘 Back to Subject",
        "grade_excellent": "🌟 *Excellent!* You're ready for the exam!",
        "grade_good": "👍 *Good result!* Review your weak areas.",
        "grade_ok": "📚 *Not bad!* A bit more practice needed.",
        "grade_bad": "💪 *Don't give up!* Study the material and try again.",
        "trial_question": "🎯 *Free Trial: {subject}*\n\n━━━━━━━━━━━━━━━\n📌 Question *{num}* of *3*\n\n{question}",
        "trial_done": "🏁 *Trial Complete!*\n\n━━━━━━━━━━━━━━━\n📊 Your score: *{score} / 3*\n\n━━━━━━━━━━━━━━━\n💎 *Full version includes:*\n✏️ 20 MCQ questions\n📖 Full study notes\n🃏 Flashcards\n📊 History & progress\n🤖 AI Tutor\n\n👇 Buy access now!",
        "buy_now": "💳 Buy Full Access",
        "progress_text": "📊 *Progress — {subject}*\n\n━━━━━━━━━━━━━━━\n✏️ Tests taken: *{tests}*\n📈 Average score: *{avg}%*\n🏆 Best result: *{best}%*\n🃏 Flashcards studied: *{cards}*",
        "no_progress": "📊 *No progress yet*\n\n━━━━━━━━━━━━━━━\nTake your first test to see stats! ✏️",
        "promo_enter": "🎁 *Promo Code*\n\n━━━━━━━━━━━━━━━\nEnter your promo code:",
        "promo_valid": "🎉 *Promo Code Applied!*\n\n━━━━━━━━━━━━━━━\n💸 Discount: *{discount}%*\n💰 New price: *{price:,} UZS*",
        "promo_invalid": "❌ *Promo code not found*\n\nTry another code or press Back.",
        "enter_promo": "🎁 I have a promo code",
        "stats_title": "📈 *Statistics — BMU Study Hub*\n\n━━━━━━━━━━━━━━━\n👥 Students: *{users}*\n💰 Paid accesses: *{paid}*\n💵 Revenue: *{revenue:,} UZS*\n\n━━━━━━━━━━━━━━━\n📘 By subject:",
        # AI Chat
        "ai_chat": "🤖 AI Tutor",
        "ai_chat_intro": "🤖 *AI Tutor*\n_{subject}_\n\n━━━━━━━━━━━━━━━\nAsk any question — I'll explain clearly with examples!\n\n💬 _Enter your question:_",
        "ai_thinking": "🤔 _Thinking..._",
        "ai_clear": "🗑 Clear history",
        "ai_history_cleared": "✅ Chat history cleared.",
        "ai_unavailable": "⚠️ AI chat is temporarily unavailable.",
        # Quiz history
        "quiz_history": "📋 Test History",
        "quiz_history_empty": "📋 *No test history yet*\n\n━━━━━━━━━━━━━━━\nTake your first test now! ✏️",
        "quiz_history_title": "📋 *Test History*\n_{subject}_\n\n━━━━━━━━━━━━━━━\n",
        "quiz_history_all": "📋 *All Tests*\n\n━━━━━━━━━━━━━━━\n",
        # Bookmarks
        "bookmarks": "🔖 Bookmarks",
        "bookmark_saved": "🔖 Saved to bookmarks!",
        "bookmark_exists": "✅ Already bookmarked.",
        "bookmarks_empty": "🔖 *No bookmarks yet*\n\n━━━━━━━━━━━━━━━\nDuring a quiz, press 🔖 to save tricky questions.",
        "bookmarks_title": "🔖 *My Bookmarks*\n\n━━━━━━━━━━━━━━━\n",
        "bookmark_delete": "🗑 Delete",
        "bookmark_deleted": "✅ Bookmark deleted.",
        # Language change
        "change_lang": "🌐 Language",
        # Cheatsheet
        "cheatsheet": "📝 Cheat Sheet",
        "cheatsheet_title": "📝 *Cheat Sheet*\n_{subject}_\n\n━━━━━━━━━━━━━━━\n",
        # Glossary
        "glossary": "📖 Glossary",
        # XP / Streak / Leaderboard
        "leaderboard": "🏆 Leaderboard",
        "my_rank": "⚡ My Rank",
        "xp_earned": "⚡ +{xp} XP earned!",
        "level_up": "🎉 *Level Up!* You reached level *{level}*!",
        "streak_bonus": "🔥 Streak bonus +{bonus} XP!",
        "leaderboard_title": "🏆 *Leaderboard*\n_BMU Study Hub_\n\n━━━━━━━━━━━━━━━\n",
        "my_stats": "⚡ *My Achievements*\n\n━━━━━━━━━━━━━━━\n🏅 Level: *{level}* {badge}\n⚡ XP: *{xp}*\n🔥 Streak: *{streak}* days\n\n{progress_bar}\n_To next level: *{xp_needed}* XP_",
        "glossary_intro": "📖 *Glossary*\n_{subject}_\n\n━━━━━━━━━━━━━━━\nEnter a term to search:",
        "glossary_not_found": "❌ Term not found. Try another word.",
        # True/False
        "true_false": "✅❌ True / False",
        "tf_question": "⚡ *True / False*\n_{subject}_\n\n━━━━━━━━━━━━━━━\n📌 Statement *{num}* of *{total}*\n\n_{statement}_",
        "tf_correct": "✅ *Correct!*\n\n💡 {explanation}",
        "tf_wrong": "❌ *Wrong!*\n\nCorrect answer: *{correct}*\n💡 {explanation}",
        "tf_done": "🏁 *True/False Complete!*\n\n━━━━━━━━━━━━━━━\n📊 Score: *{score}/{total}*\n{grade}",
        "tf_true": "✅ True",
        "tf_false": "❌ False",
        # Exam plan
        "exam_plan": "📅 Study Plan",
        "exam_date_ask": "📅 *Exam Preparation Mode*\n_{subject}_\n\n━━━━━━━━━━━━━━━\nEnter your exam date:\n*DD.MM.YYYY*\n\n_Example: 25.06.2025_",
        "exam_date_invalid": "❌ Invalid format. Enter date as *DD.MM.YYYY*\n\nExample: *25.06.2025*",
        "exam_date_past": "❌ That date is in the past. Enter a future date.",
        "exam_plan_title": "📅 *Exam Study Plan*\n_{subject}_\n\n━━━━━━━━━━━━━━━\n📆 Exam: *{date}*\n⏳ Days left: *{days}*\n\n",
        "exam_plan_generating": "⏳ Generating your plan...",
        "exam_plan_exists": "📅 *Your Study Plan*\n_{subject}_\n━━━━━━━━━━━━━━━\n📆 Exam: *{date}*\n⏳ Days left: *{days}*\n\n{plan}",
        "exam_plan_new": "🔄 New Plan",
        # Videos
        "videos": "🎬 Videos",
        "videos_title": "🎬 *Video Lessons*\n_{subject}_\n\n━━━━━━━━━━━━━━━\n",
        # Comparison
        "quiz_comparison": "📈 Progress +{delta}% compared to last time!",
        "quiz_regression": "📉 Last time was {delta}% better. Keep going!",
        "quiz_same": "➡️ Same result as last time.",
        # Bundle
        "bundle": "🎓 Subject Bundles",
        "bundle_text": "🎓 *All Subjects Bundle*\n\n━━━━━━━━━━━━━━━\n📚 Includes all {count} subjects\n\n💰 Regular price: *{full_price:,} UZS*\n🔥 Bundle price: *{bundle_price:,} UZS*\n💸 You save: *{save:,} UZS* (20% off!)\n\n━━━━━━━━━━━━━━━\n🏦 Transfer to card:\n`{card}`\n\n📸 After payment, send a screenshot 👇",
        "bundle_already": "✅ You already have access to all subjects!",
        "bundle_choose": "🎓 *Subject Bundles*\n\n━━━━━━━━━━━━━━━\nChoose a bundle:\n\n📦 *2 subjects* — *10%* discount\n📦 *4 subjects* — *20%* discount",
        "bundle2_text": "📦 *2-Subject Bundle (-10%)*\n\n━━━━━━━━━━━━━━━\nChoose 2 subjects:\n\n💰 Regular price: *{full_price:,} UZS*\n🔥 Bundle price: *{bundle_price:,} UZS*\n💸 You save: *{save:,} UZS*\n\n━━━━━━━━━━━━━━━\n🏦 Transfer to card:\n`{card}`\n\n📸 After payment, send a screenshot 👇",
        "bundle4_text": "📦 *4-Subject Bundle (-20%)*\n\n━━━━━━━━━━━━━━━\n📚 All {count} subjects\n\n💰 Regular price: *{full_price:,} UZS*\n🔥 Bundle price: *{bundle_price:,} UZS*\n💸 You save: *{save:,} UZS*\n\n━━━━━━━━━━━━━━━\n🏦 Transfer to card:\n`{card}`\n\n📸 After payment, send a screenshot 👇",
        "bundle_select_2": "Select 2 subjects (tap each one):",
        "bundle_selected": "✅ Selected: {subjects}",
        "bundle_need_more": "❗ Select {n} more subject(s)",
        # AI Humanizer
        # AI Detector
    }
}

def t(user_id, key, **kwargs):
    lang = db.get_user_lang(user_id) or "en"
    text = TEXTS[lang].get(key, key)
    return text.format(**kwargs) if kwargs else text


# ── /start ────────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Если пользователь уже есть в БД — сразу в меню
    existing_lang = db.get_user_lang(user.id)
    if existing_lang:
        await show_main_menu(update.message, user.id)
        return MAIN_MENU
    # Новый пользователь — выбор языка
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

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bug 8: /cancel — exits any session and returns to main menu."""
    user_id = update.effective_user.id
    context.user_data.clear()
    lang = db.get_user_lang(user_id) or "en"
    msg = "🏠 Вы вернулись в главное меню." if lang == "ru" else "🏠 Returned to main menu."
    await update.message.reply_text(msg)
    await show_main_menu(update.message, user_id)
    return MAIN_MENU

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split("_")[1]
    user = query.from_user
    db.upsert_user(user.id, user.username or "", user.first_name or "", lang)

    # Notify admin about new registration
    try:
        stats = db.get_stats()
        total = stats["users"]
        username_str = f"@{user.username}" if user.username else "без username"
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"🆕 *Новый студент!*\n\n"
                f"👤 Имя: *{user.first_name}*\n"
                f"🔗 Username: {username_str}\n"
                f"🆔 ID: `{user.id}`\n"
                f"🌐 Язык: *{lang}*\n\n"
                f"👥 Всего студентов: *{total}*"
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Failed to notify admin about new user: {e}", exc_info=True)

    # Запускаем онбординг
    name = user.first_name or ("друг" if lang == "ru" else "friend")
    context.user_data["onboarding_name"] = name
    text = TEXTS[lang]["onboarding_1"].format(name=name)
    keyboard = [
        [InlineKeyboardButton(TEXTS[lang]["onboarding_next"], callback_data="onboard_2"),
         InlineKeyboardButton(TEXTS[lang]["onboarding_skip"], callback_data="onboard_skip")]
    ]
    await query.message.edit_text(text, parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup(keyboard))
    return ONBOARDING

async def onboarding_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = db.get_user_lang(user_id) or "ru"
    action = query.data

    if action == "onboard_2":
        text = TEXTS[lang]["onboarding_2"]
        keyboard = [
            [InlineKeyboardButton(TEXTS[lang]["onboarding_next"], callback_data="onboard_3"),
             InlineKeyboardButton(TEXTS[lang]["onboarding_skip"], callback_data="onboard_skip")]
        ]
        await query.message.edit_text(text, parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(keyboard))
        return ONBOARDING

    elif action == "onboard_3":
        text = TEXTS[lang]["onboarding_3"]
        keyboard = [
                [InlineKeyboardButton(t(user_id, "trial_quiz"), callback_data="menu_trial")],
            [InlineKeyboardButton(TEXTS[lang]["onboarding_start"], callback_data="onboard_skip")],
        ]
        await query.message.edit_text(text, parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(keyboard))
        return ONBOARDING

    elif action == "onboard_skip":
        await show_main_menu(query.message, user_id, edit=True)
        return MAIN_MENU

    # Если нажал кнопку действия прямо из онбординга
    return MAIN_MENU



async def show_main_menu(message, user_id, edit=False):
    keyboard = [
        [InlineKeyboardButton(t(user_id, "trial_quiz"), callback_data="menu_trial"),
         InlineKeyboardButton(t(user_id, "leaderboard"), callback_data="menu_leaderboard")],
        [InlineKeyboardButton(t(user_id, "my_subjects"), callback_data="menu_my_subjects")],
        [InlineKeyboardButton(t(user_id, "buy_access"), callback_data="menu_buy_access"),
         InlineKeyboardButton(t(user_id, "bundle"), callback_data="menu_bundle")],
        [InlineKeyboardButton(t(user_id, "bookmarks"), callback_data="menu_bookmarks"),
         InlineKeyboardButton(t(user_id, "change_lang"), callback_data="menu_change_lang")],
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

def _safe(text):
    """Escape special Markdown chars in user-provided strings."""
    for ch in ["*", "_", "`", "["]:
        text = text.replace(ch, "\\" + ch)
    return text

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    users = db.get_all_users_with_subjects()
    if not users:
        await update.message.reply_text("Нет студентов.")
        return
    text = "👥 *Список студентов:*\n\n"
    for u in users[:30]:
        name = _safe(u["first_name"] or "—")
        username = f"@{_safe(u['username'])}" if u["username"] else "без username"
        subjects = ", ".join(u["subjects"]) if u["subjects"] else "нет"
        text += f"• {name} ({username}) — {subjects}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def admin_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if not args:
        await update.message.reply_text("Использование: /profile USER_ID\nПример: /profile 123456789")
        return
    try:
        target_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ USER_ID должен быть числом.")
        return
    profile = db.get_student_profile(target_id)
    if not profile:
        await update.message.reply_text(f"❌ Студент с ID `{target_id}` не найден.", parse_mode="Markdown")
        return
    subjects = ", ".join(profile["subjects"]) if profile["subjects"] else ("нет" if (db.get_user_lang(ADMIN_ID) or "ru") == "ru" else "none")
    username = f"@{_safe(profile['username'])}" if profile["username"] else "—"
    first_name = _safe(profile["first_name"] or "—")
    last_act = str(profile["last_activity"]) if profile["last_activity"] else "—"
    created = str(profile["created_at"])[:10] if profile["created_at"] else "—"
    text = (
        f"👤 *Профиль студента*\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔹 Имя: *{first_name}*\n"
        f"🔹 Username: *{username}*\n"
        f"🆔 ID: `{profile['user_id']}`\n"
        f"🌐 Язык: *{profile['lang']}*\n"
        f"📅 Регистрация: *{created}*\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📚 *Предметы:* {subjects}\n\n"
        f"📊 *Активность:*\n"
        f"✏️ Тестов пройдено: *{profile['tests']}*\n"
        f"📈 Средний балл: *{profile['avg_score']}%*\n"
        f"⚡ XP: *{profile['xp']}*\n"
        f"🏅 Уровень: *{profile['level']}*\n"
        f"🔥 Серия: *{profile['streak']}* дней\n"
        f"📆 Последняя активность: *{last_act}*"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def admin_giveaccess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if len(args) != 2:
        await update.message.reply_text(
            "Использование: /giveaccess USER_ID SUBJECT_KEY\n"
            "Пример: /giveaccess 123456789 f1\n"
            "Все предметы: /giveaccess 123456789 all",
            parse_mode="Markdown"
        )
        return
    try:
        target_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ USER_ID должен быть числом.")
        return
    subject_arg = args[1].lower()
    if subject_arg == "all":
        for key in SUBJECTS:
            db.grant_access(target_id, key)
        await update.message.reply_text(
            f"✅ *Доступ ко всем предметам* выдан студенту `{target_id}`", parse_mode="Markdown"
        )
        try:
            lang = db.get_user_lang(target_id) or "ru"
            msg = "🎉 *Доступ открыт!*\n\nАдминистратор открыл вам доступ ко всем предметам!\n\n▶️ Нажмите /start" if lang == "ru" else "🎉 *Access Granted!*\n\nAdmin has granted you access to all subjects!\n\n▶️ Press /start"
            await context.bot.send_message(target_id, msg, parse_mode="Markdown")
        except Exception:
            pass
    elif subject_arg in SUBJECTS:
        db.grant_access(target_id, subject_arg)
        subject_name = SUBJECTS[subject_arg]["name"]
        await update.message.reply_text(
            f"✅ Доступ к *{subject_name}* выдан студенту `{target_id}`", parse_mode="Markdown"
        )
        try:
            lang = db.get_user_lang(target_id) or "ru"
            msg = f"🎉 *Доступ открыт!*\n\nАдминистратор открыл вам доступ к *{subject_name}*!\n\n▶️ Нажмите /start" if lang == "ru" else f"🎉 *Access Granted!*\n\nAdmin has granted you access to *{subject_name}*!\n\n▶️ Press /start"
            await context.bot.send_message(target_id, msg, parse_mode="Markdown")
        except Exception:
            pass
    else:
        keys_list = ", ".join(SUBJECTS.keys())
        await update.message.reply_text(
            f"❌ Предмет `{subject_arg}` не найден.\nДоступные ключи: `{keys_list}`\nИли используйте `all`",
            parse_mode="Markdown"
        )



async def admin_revokeaccess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if len(args) != 2:
        await update.message.reply_text(
            "Использование: /revokeaccess USER_ID SUBJECT_KEY\n"
            "Пример: `/revokeaccess 123456789 f3`\n"
            "Все предметы: `/revokeaccess 123456789 all`",
            parse_mode="Markdown"
        )
        return
    try:
        target_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ USER_ID должен быть числом.")
        return
    subject_arg = args[1].lower()
    if subject_arg == "all":
        for key in SUBJECTS:
            db.revoke_access(target_id, key)
        await update.message.reply_text(
            f"✅ Все предметы убраны у студента `{target_id}`", parse_mode="Markdown"
        )
    elif subject_arg in SUBJECTS:
        removed = db.revoke_access(target_id, subject_arg)
        if removed:
            await update.message.reply_text(
                f"✅ Предмет *{SUBJECTS[subject_arg]['name']}* убран у `{target_id}`",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"❌ У студента `{target_id}` не было доступа к *{SUBJECTS[subject_arg]['name']}*",
                parse_mode="Markdown"
            )
    else:
        keys_list = ", ".join(f"`{k}`" for k in SUBJECTS.keys())
        await update.message.reply_text(
            f"❌ Неизвестный предмет: `{subject_arg}`\nДоступные: {keys_list}",
            parse_mode="Markdown"
        )


async def add_promo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if len(args) < 2 or len(args) > 3:
        await update.message.reply_text(
            "Использование: /addpromo КОД СКИДКА [КОЛИЧЕСТВО]\n\n"
            "Примеры:\n"
            "`/addpromo FRIEND50 50` — без ограничений\n"
            "`/addpromo PROMO20 20 10` — максимум 10 использований",
            parse_mode="Markdown"
        )
        return
    code = args[0].upper()
    try:
        discount = int(args[1])
        max_uses = int(args[2]) if len(args) == 3 else None
    except ValueError:
        await update.message.reply_text("❌ Скидка и количество должны быть числами.")
        return
    db.add_promo(code, discount, max_uses)
    uses_text = f"🔢 Лимит: *{max_uses}* использований" if max_uses else "♾ Без ограничений"
    await update.message.reply_text(
        f"✅ Промокод создан!\n\n"
        f"🎁 Код: `{code}`\n"
        f"💸 Скидка: *{discount}%*\n"
        f"{uses_text}",
        parse_mode="Markdown"
    )


async def delete_promo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if len(args) != 1:
        await update.message.reply_text(
            "Использование: /deletepromo КОД\nПример: `/deletepromo FRIEND50`",
            parse_mode="Markdown"
        )
        return
    code = args[0].upper()
    deleted = db.delete_promo(code)
    if deleted:
        await update.message.reply_text(f"✅ Промокод `{code}` удалён.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Промокод `{code}` не найден.", parse_mode="Markdown")


async def list_promos_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    promos = db.get_all_promos()
    if not promos:
        await update.message.reply_text("📋 Активных промокодов нет.")
        return
    text = "📋 *Список промокодов:*\n\n"
    for p in promos:
        uses = f"{p['used_count']}/{p['max_uses']}" if p['max_uses'] else f"{p['used_count']}/∞"
        text += f"• `{p['code']}` — *{p['discount']}%* · использовано: {uses}\n"
    await update.message.reply_text(text, parse_mode="Markdown")


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
        buttons = [[InlineKeyboardButton(f"🎯 {info['name']}", callback_data=f"trial_pick_{key}")] for key, info in SUBJECTS.items()]
        buttons.append([InlineKeyboardButton(t(user_id, "back"), callback_data="back_main")])
        await query.message.edit_text(t(user_id, "choose_trial_subject"), parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(buttons))
        return CHOOSING_SUBJECT

    elif action == "menu_bundle":
        lang = db.get_user_lang(user_id) or "en"
        keyboard = [
            [InlineKeyboardButton("📦 2 предмета (-10%)" if lang == "ru" else "📦 2 subjects (-10%)", callback_data="bundle2_start")],
            [InlineKeyboardButton("📦 4 предмета (-20%)" if lang == "ru" else "📦 4 subjects (-20%)", callback_data="bundle4_start")],
            [InlineKeyboardButton(t(user_id, "back"), callback_data="back_main")],
        ]
        await query.message.edit_text(t(user_id, "bundle_choose"), parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(keyboard))
        return MAIN_MENU

    elif action == "bundle2_start":
        context.user_data["bundle_type"] = 2
        context.user_data["bundle_selected"] = []
        await show_bundle_subject_select(query.message, user_id, context, edit=True)
        return CHOOSING_SUBJECT

    elif action == "bundle4_start":
        context.user_data["bundle_type"] = 4
        context.user_data["bundle_selected"] = []
        await show_bundle_subject_select(query.message, user_id, context, edit=True)
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

    elif action in ("lang_ru", "lang_en"):
        new_lang = action.split("_")[1]
        user = query.from_user
        db.upsert_user(user.id, user.username or "", user.first_name or "", new_lang)
        confirm = "✅ Язык изменён на *Русский*" if new_lang == "ru" else "✅ Language changed to *English*"
        back_label = "← Назад" if new_lang == "ru" else "← Back"
        keyboard = [[InlineKeyboardButton(back_label, callback_data="back_main")]]
        await query.message.edit_text(confirm, parse_mode="Markdown",
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

    elif action.startswith("study_"):
        subject_key = action.split("_", 1)[1]
        context.user_data["current_subject"] = subject_key
        try:
            await show_subject_menu(query.message, user_id, subject_key, edit=True)
        except Exception:
            await show_subject_menu(query.message, user_id, subject_key, edit=False)
        return SUBJECT_MENU


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
                buttons.append([InlineKeyboardButton(f"✅ {info['name']}", callback_data=f"already_{key}")])
            else:
                buttons.append([InlineKeyboardButton(f"🛒 {info['name']}", callback_data=f"buy_{key}")])
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

    if data.startswith("trial_pick_"):
        subject_key = data.split("trial_pick_")[1]
        subject_name = SUBJECTS[subject_key]["name"]
        keyboard = [
            [InlineKeyboardButton(t(user_id, "trial_type_mcq"), callback_data=f"trial_{subject_key}")],
            [InlineKeyboardButton(t(user_id, "trial_type_tf"), callback_data=f"trial_tf_{subject_key}")],
            [InlineKeyboardButton(t(user_id, "back"), callback_data="back_main")],
        ]
        await query.message.edit_text(
            t(user_id, "trial_choose_type", subject=subject_name),
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CHOOSING_SUBJECT

    if data.startswith("trial_tf_"):
        subject_key = data.split("trial_tf_")[1]
        if db.has_used_trial(user_id, subject_key):
            lang = db.get_user_lang(user_id) or "en"
            msg = "❌ Вы уже использовали пробный режим для этого предмета." if lang == "ru" else "❌ You have already used the free trial for this subject."
            await query.answer(msg, show_alert=True)
            return CHOOSING_SUBJECT
        all_tf = get_true_false(subject_key)
        if not all_tf:
            await query.answer("Нет вопросов" if (db.get_user_lang(user_id) or "en") == "ru" else "No questions", show_alert=True)
            return CHOOSING_SUBJECT
        questions = random.sample(all_tf, min(5, len(all_tf)))
        context.user_data["tf_questions"] = questions
        context.user_data["tf_index"] = 0
        context.user_data["tf_score"] = 0
        context.user_data["tf_subject"] = subject_key
        context.user_data["tf_is_trial"] = True
        db.mark_trial_used(user_id, subject_key)
        await show_tf_question(query.message, user_id, context, edit=True)
        return TF_SESSION

    if data.startswith("bsel_"):
        subject_key = data.split("bsel_")[1]
        bundle_type = context.user_data.get("bundle_type", 2)
        selected = context.user_data.get("bundle_selected", [])
        owned = db.get_user_subjects(user_id)
        if subject_key in owned:
            await query.answer("✅ У вас уже есть этот предмет" if (db.get_user_lang(user_id) or "en") == "ru" else "✅ You already own this subject", show_alert=False)
            return CHOOSING_SUBJECT
        if subject_key in selected:
            selected.remove(subject_key)
        else:
            if len(selected) < bundle_type:
                selected.append(subject_key)
            else:
                lang = db.get_user_lang(user_id) or "en"
                msg = f"Уже выбрано {bundle_type} предметов" if lang == "ru" else f"Already selected {bundle_type} subjects"
                await query.answer(msg, show_alert=False)
                return CHOOSING_SUBJECT
        context.user_data["bundle_selected"] = selected
        await show_bundle_subject_select(query.message, user_id, context, edit=True)
        return CHOOSING_SUBJECT

    if data == "bundle_confirm":
        selected = context.user_data.get("bundle_selected", [])
        bundle_type = context.user_data.get("bundle_type", 2)
        discount = 10 if bundle_type == 2 else 20
        full_price = PRICE_PER_SUBJECT * bundle_type
        bundle_price = int(full_price * (1 - discount / 100))
        save = full_price - bundle_price
        lang = db.get_user_lang(user_id) or "en"
        subject_names = ", ".join(SUBJECTS[k]["name"] for k in selected)
        if bundle_type == 2:
            text = t(user_id, "bundle2_text", full_price=full_price, bundle_price=bundle_price, save=save, card=CARD_NUMBER)
        else:
            text = t(user_id, "bundle4_text", count=bundle_type, full_price=full_price, bundle_price=bundle_price, save=save, card=CARD_NUMBER)
        text += f"\n\n📚 *{subject_names}*"
        context.user_data["pending_subject"] = f"bundle_{'-'.join(selected)}"
        context.user_data["promo_discount"] = 0
        keyboard = [[InlineKeyboardButton(t(user_id, "back"), callback_data="back_main")]]
        await query.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        return PAYMENT_SCREENSHOT

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
        if photo_url:
            try:
                await query.message.reply_photo(
                    photo=photo_url,
                    caption=text,
                    parse_mode="Markdown",
                    reply_markup=markup
                )
            except Exception as e:
                logger.error(f"send photo failed: {e}")
                await query.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)
        else:
            await query.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)
        return PAYMENT_SCREENSHOT

    if data.startswith("promo_"):
        subject_key = data.split("_", 1)[1]
        context.user_data["pending_subject"] = subject_key
        context.user_data["awaiting_promo"] = True
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
         InlineKeyboardButton(t(user_id, "quiz"), callback_data=f"quiz_{subject_key}")],
        [InlineKeyboardButton(t(user_id, "true_false"), callback_data=f"tf_{subject_key}"),
         InlineKeyboardButton(t(user_id, "quiz_history"), callback_data=f"history_{subject_key}")],
        [InlineKeyboardButton(t(user_id, "ai_chat"), callback_data=f"aichat_{subject_key}"),
         InlineKeyboardButton(t(user_id, "videos"), callback_data=f"videos_{subject_key}")],
        [InlineKeyboardButton(t(user_id, "progress"), callback_data=f"progress_{subject_key}"),
         InlineKeyboardButton(t(user_id, "back"), callback_data="back_main")],
    ]
    text = t(user_id, "subject_menu", subject=info["name"])
    markup = InlineKeyboardMarkup(keyboard)
    if edit:
        await message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await message.reply_text(text, parse_mode="Markdown", reply_markup=markup)


async def show_bundle_subject_select(message, user_id, context, edit=False):
    bundle_type = context.user_data.get("bundle_type", 2)
    selected = context.user_data.get("bundle_selected", [])
    lang = db.get_user_lang(user_id) or "en"
    owned = db.get_user_subjects(user_id)
    buttons = []
    for key, info in SUBJECTS.items():
        if key in owned:
            label = f"✅ {info['name']}"
        elif key in selected:
            label = f"☑️ {info['name']}"
        else:
            label = f"📘 {info['name']}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"bsel_{key}")])

    need = bundle_type - len(selected)
    if lang == "ru":
        header = f"📦 Выберите *{bundle_type}* предмета\n✅ Выбрано: {len(selected)}/{bundle_type}"
        confirm_label = "✅ Подтвердить выбор"
        back_label = "← Назад"
    else:
        header = f"📦 Select *{bundle_type}* subjects\n✅ Selected: {len(selected)}/{bundle_type}"
        confirm_label = "✅ Confirm selection"
        back_label = "← Back"

    if len(selected) == bundle_type:
        buttons.append([InlineKeyboardButton(confirm_label, callback_data="bundle_confirm")])
    buttons.append([InlineKeyboardButton(back_label, callback_data="back_main")])

    markup = InlineKeyboardMarkup(buttons)
    if edit:
        await message.edit_text(header, parse_mode="Markdown", reply_markup=markup)
    else:
        await message.reply_text(header, parse_mode="Markdown", reply_markup=markup)


# ── PAYMENT ───────────────────────────────────────────────────────────────────

async def receive_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = update.effective_user


    # Handle promo code text input
    if update.message.text and not update.message.photo and context.user_data.get("awaiting_promo"):
        context.user_data["awaiting_promo"] = False
        promo_code = update.message.text.strip().upper()
        discount = db.check_promo(promo_code)
        subject_key = context.user_data.get("pending_subject")
        if discount and subject_key:
            context.user_data["promo_discount"] = discount
            context.user_data["pending_promo_code"] = promo_code
            discounted_price = int(PRICE_PER_SUBJECT * (1 - discount / 100))
            info = SUBJECTS[subject_key]
            text = t(user_id, "promo_valid", discount=discount, price=discounted_price)
            text += "\n\n" + t(user_id, "payment_instruction",
                               subject=info["name"], price=discounted_price, card=CARD_NUMBER)
            keyboard = [[InlineKeyboardButton(t(user_id, "back"), callback_data=f"buy_{subject_key}")]]
            await update.message.reply_text(text, parse_mode="Markdown",
                                            reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            context.user_data["awaiting_promo"] = True
            keyboard = [[InlineKeyboardButton(t(user_id, "back"), callback_data=f"buy_{subject_key}" if subject_key else "back_main")]]
            await update.message.reply_text(t(user_id, "promo_invalid"), parse_mode="Markdown",
                                            reply_markup=InlineKeyboardMarkup(keyboard))
        return PAYMENT_SCREENSHOT

    subject_key = context.user_data.get("pending_subject")
    if not subject_key:
        await show_main_menu(update.message, user_id)
        return MAIN_MENU

    discount = context.user_data.get("promo_discount", 0)
    if subject_key == "bundle":
        count = len(SUBJECTS)
        full_price = PRICE_PER_SUBJECT * count
        final_price = int(full_price * 0.8)
        subject_display = "🎓 Пакет ВСЕ ПРЕДМЕТЫ"
    elif subject_key and subject_key.startswith("bundle_"):
        keys = subject_key.replace("bundle_", "").split("-")
        bundle_type = len(keys)
        discount_pct = 10 if bundle_type == 2 else 20
        full_price = PRICE_PER_SUBJECT * bundle_type
        final_price = int(full_price * (1 - discount_pct / 100))
        names = ", ".join(SUBJECTS[k]["name"] for k in keys if k in SUBJECTS)
        subject_display = f"📦 Пакет: {names}"
    else:
        final_price = int(PRICE_PER_SUBJECT * (1 - discount / 100))
        info = SUBJECTS[subject_key]
        subject_display = info["name"]
    db.add_pending_payment(user_id, subject_key)

    # Increment promo usage counter when screenshot is submitted
    if discount and context.user_data.get("pending_promo_code"):
        db.use_promo(context.user_data["pending_promo_code"])
        context.user_data.pop("pending_promo_code", None)

    approve_cb = f"approve_{user_id}_{subject_key}"
    deny_cb = f"deny_{user_id}_{subject_key}"
    admin_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить", callback_data=approve_cb),
         InlineKeyboardButton("❌ Отклонить", callback_data=deny_cb)]
    ])
    name = (f"{user.first_name or ''} {user.last_name or ''}").strip()
    name = name.replace("_", r"\_").replace("*", r"\*").replace("`", r"\`").replace("[", r"\[")
    username_raw = f"@{user.username}" if user.username else "без username"
    username_safe = username_raw.replace("_", r"\_").replace("*", r"\*").replace("`", r"\`")
    promo_text = f"\n🎁 Промокод: скидка {discount}%" if discount else ""
    admin_text = (f"💰 *Новая оплата*\n\n"
                  f"👤 {name} ({username_safe})\n"
                  f"🆔 `{user_id}`\n"
                  f"📘 Предмет: *{subject_display}*\n"
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
        else:
            # Fallback: student sent text instead of photo
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_text + "\n\n⚠️ Студент не прислал фото — прислал текст.",
                parse_mode="Markdown",
                reply_markup=admin_keyboard
            )
    except Exception as e:
        logger.error(f"Failed to notify admin about payment: {e}", exc_info=True)

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

    if query.from_user.id != ADMIN_ID:
        await query.answer()
        return

    # Guard against double-click: use message_id + data as key
    action_key = f"{query.message.message_id}_{query.data}"
    if action_key in _processed_admin_actions:
        try:
            await query.answer("⚠️ Уже обработано.", show_alert=True)
        except Exception:
            pass
        return
    _processed_admin_actions.add(action_key)
    # NOTE: do NOT call query.answer() here — we'll answer with the alert after processing

    parts = query.data.split("_")
    action = parts[0]
    student_id = int(parts[1])
    subject_key = "_".join(parts[2:])

    if action == "approve":
        if subject_key == "bundle":
            for key in SUBJECTS:
                db.grant_access(student_id, key)
            db.remove_pending(student_id, subject_key)
            student_lang = db.get_user_lang(student_id) or "en"
            msg = "🎉 *Доступ ко всем предметам открыт!*\n\nТеперь вам доступны все предметы в разделе «Мои предметы»." if student_lang == "ru" else "🎉 *Full Access Granted!*\n\nAll subjects are now available in 'My Subjects'."
            admin_alert = f"✅ Доступ выдан!\n🆔 ID: {student_id}\n📚 Все предметы"
        elif subject_key.startswith("bundle_"):
            keys = subject_key.replace("bundle_", "").split("-")
            for key in keys:
                if key in SUBJECTS:
                    db.grant_access(student_id, key)
            db.remove_pending(student_id, subject_key)
            student_lang = db.get_user_lang(student_id) or "en"
            names = ", ".join(SUBJECTS[k]["name"] for k in keys if k in SUBJECTS)
            msg = f"🎉 *Доступ открыт!*\n\n📚 {names}" if student_lang == "ru" else f"🎉 *Access Granted!*\n\n📚 {names}"
            admin_alert = f"✅ Доступ выдан!\n🆔 ID: {student_id}\n📦 {names}"
        else:
            info = SUBJECTS[subject_key]
            db.grant_access(student_id, subject_key)
            db.remove_pending(student_id, subject_key)
            student_lang = db.get_user_lang(student_id) or "en"
            msg = TEXTS[student_lang]["access_granted"].format(subject=info["name"])
            admin_alert = f"✅ Доступ выдан!\n🆔 ID: {student_id}\n📘 {info['name']}"
        start_hint = "\n\n▶️ Нажмите /start чтобы открыть предмет" if student_lang == "ru" else "\n\n▶️ Press /start to access your subject"
        try:
            await context.bot.send_message(student_id, msg + start_hint, parse_mode="Markdown")
        except Exception:
            pass
        try:
            await query.answer(admin_alert, show_alert=True)
        except Exception:
            pass
        try:
            if query.message.caption is not None:
                await query.message.edit_caption(
                    query.message.caption + "\n\n✅ *Доступ выдан*", parse_mode="Markdown",
                    reply_markup=None
                )
            else:
                await query.message.edit_text(
                    query.message.text + "\n\n✅ *Доступ выдан*", parse_mode="Markdown",
                    reply_markup=None
                )
        except Exception as e:
            logger.error(f"admin_action edit error: {e}")
    elif action == "deny":
        subject_key = "_".join(parts[2:])
        db.remove_pending(student_id, subject_key)
        student_lang = db.get_user_lang(student_id) or "en"
        msg = TEXTS[student_lang]["access_denied"]
        subject_display = SUBJECTS[subject_key]["name"] if subject_key in SUBJECTS else subject_key
        try:
            await context.bot.send_message(student_id, msg, parse_mode="Markdown")
        except Exception:
            pass
        try:
            await query.answer(f"❌ Оплата отклонена!\n🆔 ID: {student_id}\n📘 {subject_display}", show_alert=True)
        except Exception:
            pass
        try:
            if query.message.caption is not None:
                await query.message.edit_caption(
                    query.message.caption + "\n\n❌ *Отклонено*", parse_mode="Markdown",
                    reply_markup=None
                )
            else:
                await query.message.edit_text(
                    query.message.text + "\n\n❌ *Отклонено*", parse_mode="Markdown",
                    reply_markup=None
                )
        except Exception as e:
            logger.error(f"admin_action edit error: {e}")


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
        await send_materials(query.message, user_id, subject_key, index=0, edit=True)
        return SUBJECT_MENU

    if data == "chapter_noop":
        await query.answer()
        return SUBJECT_MENU

    if data.startswith("chapter_"):
        parts = data.split("_")
        index = int(parts[-1])
        subject_key = "_".join(parts[1:-1])
        await send_materials(query.message, user_id, subject_key, index=index, edit=True)
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

    if data.startswith("tf_"):
        subject_key = data.split("tf_")[1]
        questions = get_true_false(subject_key)
        if not questions:
            await query.answer("Нет вопросов" if (db.get_user_lang(user_id) or "en") == "ru" else "No questions", show_alert=True)
            return SUBJECT_MENU
        shuffled = random.sample(questions, min(10, len(questions)))
        context.user_data["tf_questions"] = shuffled
        context.user_data["tf_index"] = 0
        context.user_data["tf_score"] = 0
        context.user_data["tf_subject"] = subject_key
        await show_tf_question(query.message, user_id, context, edit=True)
        return TF_SESSION

    if data.startswith("videos_"):
        subject_key = data.split("videos_")[1]
        videos = get_videos(subject_key)
        text = t(user_id, "videos_title", subject=SUBJECTS[subject_key]["name"])
        for v in videos:
            text += f"▶️ [{v['title']}]({v['url']})\n"
        keyboard = [[InlineKeyboardButton(t(user_id, "back"), callback_data=f"back_subject_{subject_key}")]]
        await query.message.edit_text(text, parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(keyboard),
                                      disable_web_page_preview=True)
        return SUBJECT_MENU



    if data.startswith("examplan_"):
        subject_key = data.split("examplan_")[1]
        # Check if plan already exists
        existing = db.get_exam_plan(user_id, subject_key)
        if existing:
            from datetime import date
            try:
                exam_dt = datetime.strptime(existing["exam_date"], "%d.%m.%Y").date()
                days_left = (exam_dt - date.today()).days
                if days_left > 0:
                    text = t(user_id, "exam_plan_exists",
                             subject=SUBJECTS[subject_key]["name"],
                             date=existing["exam_date"],
                             days=days_left,
                             plan=existing["plan_text"])
                    keyboard = [
                        [InlineKeyboardButton(t(user_id, "exam_plan_new"), callback_data=f"examplan_new_{subject_key}")],
                        [InlineKeyboardButton(t(user_id, "back"), callback_data=f"back_subject_{subject_key}")]
                    ]
                    await query.message.edit_text(text, parse_mode="Markdown",
                                                  reply_markup=InlineKeyboardMarkup(keyboard))
                    return SUBJECT_MENU
            except Exception:
                pass
        context.user_data["examplan_subject"] = subject_key
        context.user_data["awaiting_exam_date"] = True
        keyboard = [[InlineKeyboardButton(t(user_id, "back"), callback_data=f"back_subject_{subject_key}")]]
        await query.message.edit_text(
            t(user_id, "exam_date_ask", subject=SUBJECTS[subject_key]["name"]),
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return EXAM_DATE_INPUT

    if data.startswith("examplan_new_"):
        subject_key = data.split("examplan_new_")[1]
        context.user_data["examplan_subject"] = subject_key
        context.user_data["awaiting_exam_date"] = True
        keyboard = [[InlineKeyboardButton(t(user_id, "back"), callback_data=f"back_subject_{subject_key}")]]
        await query.message.edit_text(
            t(user_id, "exam_date_ask", subject=SUBJECTS[subject_key]["name"]),
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return EXAM_DATE_INPUT

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


async def send_materials(message, user_id, subject_key, index=0, edit=True):
    info = get_subject_info(subject_key)
    chapters = info.get("chapters", [])
    total = len(chapters)
    if not chapters:
        await message.edit_text("📭 Материалы пока не добавлены.", parse_mode="Markdown")
        return

    chapter = chapters[index]
    text = (
        f"📘 *{info['name']}*\n"
        f"{'─' * 30}\n"
        f"📄 *{index + 1}/{total}. {chapter['title']}*\n\n"
        f"{chapter['content']}"
    )

    nav_row = []
    if index > 0:
        nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"chapter_{subject_key}_{index - 1}"))
    nav_row.append(InlineKeyboardButton(f"{index + 1} / {total}", callback_data="chapter_noop"))
    if index < total - 1:
        nav_row.append(InlineKeyboardButton("➡️", callback_data=f"chapter_{subject_key}_{index + 1}"))

    keyboard = [nav_row, [InlineKeyboardButton(t(user_id, "back"), callback_data=f"back_subject_{subject_key}")]]
    markup = InlineKeyboardMarkup(keyboard)

    if edit:
        await message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await message.reply_text(text, parse_mode="Markdown", reply_markup=markup)


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
        text = t(user_id, "flashcard_back", num=index+1, total=total, term=card["term"], definition=card["definition"])
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
        # Safety check — prevent IndexError on last question
        if index >= total:
            return QUIZ_SESSION
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
            # Compare with previous result
            last_two = db.get_last_two_results(user_id, subject_key)
            comparison_text = ""
            if len(last_two) >= 2:
                curr_pct = int(last_two[0][0] / last_two[0][1] * 100)
                prev_pct = int(last_two[1][0] / last_two[1][1] * 100)
                delta = abs(curr_pct - prev_pct)
                lang = db.get_user_lang(user_id) or "en"
                if curr_pct > prev_pct:
                    comparison_text = "\n" + t(user_id, "quiz_comparison", delta=delta)
                elif curr_pct < prev_pct:
                    comparison_text = "\n" + t(user_id, "quiz_regression", delta=delta)
                else:
                    comparison_text = "\n" + t(user_id, "quiz_same")
            # XP reward
            xp_gain = max(10, int(score / total * 50))
            xp_result = db.add_xp(user_id, xp_gain)
            xp_notification = f"\n\n⚡ *+{xp_gain} XP*"
            if xp_result.get("leveled_up"):
                xp_notification += f"\n🎉 *Новый уровень {xp_result['level']}!*" if (db.get_user_lang(user_id) or "en") == "ru" else f"\n🎉 *Level up! Level {xp_result['level']}!*"
            done_text = (
                result_text + "\n\n" +
                t(user_id, "quiz_done", score=score, total=total, grade=grade) +
                comparison_text +
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
            next_row = [InlineKeyboardButton("➡️ " + ("Следующий вопрос" if (db.get_user_lang(user_id) or "en") == "ru" else "Next Question"), callback_data="quiz_next")]
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
            lang_trial = db.get_user_lang(user_id) or "en"
            keyboard = [[InlineKeyboardButton("➡️ " + ("Следующий вопрос" if lang_trial == "ru" else "Next Question"), callback_data="trial_next")]]
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
        client = genai_client.Client(api_key=os.environ["GEMINI_API_KEY"])

        # Build conversation contents from history + current message
        contents = []
        for m in history:
            role = "user" if m["role"] == "user" else "model"
            contents.append(genai_types.Content(role=role, parts=[genai_types.Part(text=m["content"])]))
        contents.append(genai_types.Content(role="user", parts=[genai_types.Part(text=text)]))

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=genai_types.GenerateContentConfig(system_instruction=system_prompt),
        )
        ai_reply = response.text
        db.save_ai_message(user_id, subject_key, "assistant", ai_reply)

        keyboard = [
            [InlineKeyboardButton(t(user_id, "ai_clear"), callback_data=f"ai_clear_{subject_key}")],
            [InlineKeyboardButton(t(user_id, "back"), callback_data=f"back_subject_{subject_key}")]
        ]
        await thinking_msg.delete()
        reply_text = f"🤖 {ai_reply}"
        try:
            await update.message.reply_text(reply_text, parse_mode="Markdown",
                                            reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            # Fallback: send without markdown if formatting causes error
            await update.message.reply_text(reply_text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"AI chat error: {e}")
        try:
            await thinking_msg.delete()
        except Exception:
            pass
        keyboard = [
            [InlineKeyboardButton(t(user_id, "ai_clear"), callback_data=f"ai_clear_{subject_key}")],
            [InlineKeyboardButton(t(user_id, "back"), callback_data=f"back_subject_{subject_key}")]
        ]
        err_text = "⚠️ Ошибка ИИ. Попробуйте позже." if lang == "ru" else "⚠️ AI error. Try again later."
        await update.message.reply_text(err_text, reply_markup=InlineKeyboardMarkup(keyboard))

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



# ── TRUE / FALSE ──────────────────────────────────────────────────────────────

async def show_tf_question(message, user_id, context, edit=False):
    questions = context.user_data["tf_questions"]
    index = context.user_data["tf_index"]
    subject_key = context.user_data["tf_subject"]
    is_trial = context.user_data.get("tf_is_trial", False)
    total = len(questions)
    q = questions[index]
    text = t(user_id, "tf_question", subject=SUBJECTS[subject_key]["name"],
             num=index+1, total=total, statement=q["statement"])
    back_cb = "back_main" if is_trial else f"back_subject_{subject_key}"
    keyboard = [
        [InlineKeyboardButton(t(user_id, "tf_true"), callback_data="tf_ans_true"),
         InlineKeyboardButton(t(user_id, "tf_false"), callback_data="tf_ans_false")],
        [InlineKeyboardButton(t(user_id, "back"), callback_data=back_cb)]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    if edit:
        await message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await message.reply_text(text, parse_mode="Markdown", reply_markup=markup)

def _generate_exam_plan(subject_key, days_left, lang):
    """Generate a study plan based on days until exam."""
    topics = {
        "f1": ["Business Organisations & Stakeholders", "Corporate Governance", "Organisational Structure",
               "Motivation Theories", "Leadership & Management", "Recruitment & HR", "PESTEL & Porter's 5 Forces",
               "Information Systems", "Ethics & Sustainability"],
        "f3": ["Double Entry & Accounting Equation", "Ledger Accounts & Trial Balance", "Accruals & Prepayments",
               "Depreciation Methods", "Bad Debts & Provisions", "Financial Statements (P&L, Balance Sheet)",
               "Cash Flow Statements", "Consolidation & Goodwill", "Ratio Analysis"],
        "fm": ["Financial Markets Overview", "Money & Capital Markets", "Bond Valuation & Duration",
               "Equity & Share Valuation", "Risk & Return", "CAPM & Beta", "Derivatives Introduction",
               "Financial Intermediaries", "Regulation"],
        "macro": ["GDP & Measurement", "Economic Growth", "Inflation Types & Causes",
                  "Unemployment Types", "Fiscal Policy", "Monetary Policy & QE",
                  "International Trade & Comparative Advantage", "Balance of Payments", "Phillips Curve"],
    }
    subject_topics = topics.get(subject_key, ["Topic 1", "Topic 2", "Topic 3"])

    if lang == "ru":
        if days_left <= 3:
            plan = "⚡ *Экспресс-план (мало времени!)*\n\n"
            plan += "📌 День 1: Шпаргалки + флэшкарты по всем темам\n"
            plan += "📌 День 2: Тест MCQ + True/False — все предметы\n"
            if days_left == 3:
                plan += "📌 День 3: Повтор слабых тем + отдых\n"
        elif days_left <= 7:
            plan = "📅 *Недельный план*\n\n"
            per_day = max(1, len(subject_topics) // days_left)
            for i in range(days_left):
                start = i * per_day
                day_topics = subject_topics[start:start + per_day]
                if day_topics:
                    plan += f"📌 День {i+1}: {', '.join(day_topics)}\n"
                else:
                    plan += f"📌 День {i+1}: Повтор + тест\n"
        elif days_left <= 30:
            plan = "📅 *Двухнедельный план*\n\n"
            week1 = subject_topics[:len(subject_topics)//2]
            week2 = subject_topics[len(subject_topics)//2:]
            plan += f"🗓 *Неделя 1:* {', '.join(week1)}\n"
            plan += f"🗓 *Неделя 2:* {', '.join(week2)}\n"
            plan += f"🗓 *Финальные дни:* Тесты + повтор ошибок\n"
        else:
            plan = "📅 *Долгосрочный план*\n\n"
            chunk = max(1, len(subject_topics) // 4)
            plan += f"📚 *Месяц 1:* {', '.join(subject_topics[:chunk])}\n"
            plan += f"📚 *Месяц 2:* {', '.join(subject_topics[chunk:chunk*2])}\n"
            plan += f"📚 *Месяц 3:* {', '.join(subject_topics[chunk*2:chunk*3])}\n"
            plan += f"📚 *Финал:* Тесты, флэшкарты, повтор слабых тем\n"
        plan += "\n💡 *Совет:* Каждый день проходи тест и флэшкарты!\n"
        plan += "🎯 Используй ИИ-преподавателя для сложных тем."
    else:
        if days_left <= 3:
            plan = "⚡ *Express Plan (limited time!)*\n\n"
            plan += "📌 Day 1: Cheat sheets + flashcards on all topics\n"
            plan += "📌 Day 2: MCQ test + True/False — full review\n"
            if days_left == 3:
                plan += "📌 Day 3: Revise weak areas + rest\n"
        elif days_left <= 7:
            plan = "📅 *One-Week Plan*\n\n"
            per_day = max(1, len(subject_topics) // days_left)
            for i in range(days_left):
                start = i * per_day
                day_topics = subject_topics[start:start + per_day]
                if day_topics:
                    plan += f"📌 Day {i+1}: {', '.join(day_topics)}\n"
                else:
                    plan += f"📌 Day {i+1}: Revision + practice test\n"
        elif days_left <= 30:
            plan = "📅 *Two-Week Plan*\n\n"
            week1 = subject_topics[:len(subject_topics)//2]
            week2 = subject_topics[len(subject_topics)//2:]
            plan += f"🗓 *Week 1:* {', '.join(week1)}\n"
            plan += f"🗓 *Week 2:* {', '.join(week2)}\n"
            plan += f"🗓 *Final Days:* Practice tests + review mistakes\n"
        else:
            plan = "📅 *Long-Term Plan*\n\n"
            chunk = max(1, len(subject_topics) // 4)
            plan += f"📚 *Month 1:* {', '.join(subject_topics[:chunk])}\n"
            plan += f"📚 *Month 2:* {', '.join(subject_topics[chunk:chunk*2])}\n"
            plan += f"📚 *Month 3:* {', '.join(subject_topics[chunk*2:chunk*3])}\n"
            plan += f"📚 *Final:* Practice tests, flashcards, weak area review\n"
        plan += "\n💡 *Tip:* Do a quiz and flashcards every day!\n"
        plan += "🎯 Use the AI Tutor for difficult topics."
    return plan


async def tf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    if data in ("tf_ans_true", "tf_ans_false"):
        questions = context.user_data["tf_questions"]
        index = context.user_data["tf_index"]
        subject_key = context.user_data["tf_subject"]
        total = len(questions)
        q = questions[index]
        user_answer = (data == "tf_ans_true")
        is_correct = (user_answer == q["answer"])
        if is_correct:
            context.user_data["tf_score"] += 1
            result_text = t(user_id, "tf_correct", explanation=q["explanation"])
        else:
            correct_str = ("✅ Верно" if q["answer"] else "❌ Неверно") if (db.get_user_lang(user_id) or "en") == "ru" else ("✅ True" if q["answer"] else "❌ False")
            result_text = t(user_id, "tf_wrong", correct=correct_str, explanation=q["explanation"])
        next_index = index + 1
        context.user_data["tf_index"] = next_index
        if next_index >= total:
            score = context.user_data["tf_score"]
            pct = int(score / total * 100)
            if pct >= 90: grade = t(user_id, "grade_excellent")
            elif pct >= 70: grade = t(user_id, "grade_good")
            elif pct >= 50: grade = t(user_id, "grade_ok")
            else: grade = t(user_id, "grade_bad")
            is_trial = context.user_data.get("tf_is_trial", False)
            was_trial = is_trial
            if is_trial:
                context.user_data["tf_is_trial"] = False
                done = result_text + "\n\n" + t(user_id, "trial_tf_done", score=score, total=total)
                keyboard = [
                    [InlineKeyboardButton(t(user_id, "buy_now"), callback_data=f"buy_{subject_key}")],
                    [InlineKeyboardButton(t(user_id, "back"), callback_data="back_main")],
                ]
            else:
                xp_gain = max(5, int(score / total * 30))
                db.add_xp(user_id, xp_gain)
                done = result_text + "\n\n" + t(user_id, "tf_done", score=score, total=total, grade=grade)
                done += f"\n\n⚡ *+{xp_gain} XP*"
                keyboard = [
                    [InlineKeyboardButton(t(user_id, "restart_quiz"), callback_data=f"tf_{subject_key}")],
                    [InlineKeyboardButton(t(user_id, "back_to_subject"), callback_data=f"back_subject_{subject_key}")],
                ]
            await query.message.edit_text(done, parse_mode="Markdown",
                                          reply_markup=InlineKeyboardMarkup(keyboard))
            return CHOOSING_SUBJECT if was_trial else SUBJECT_MENU
        else:
            lang = db.get_user_lang(user_id) or "en"
            next_btn = "➡️ Следующий" if lang == "ru" else "➡️ Next"
            keyboard = [[InlineKeyboardButton(next_btn, callback_data="tf_next")]]
            await query.message.edit_text(result_text, parse_mode="Markdown",
                                          reply_markup=InlineKeyboardMarkup(keyboard))
            return TF_SESSION

    if data == "tf_next":
        await show_tf_question(query.message, user_id, context, edit=True)
        return TF_SESSION

    if data.startswith("tf_"):
        # Restart TF for subject
        subject_key = data.split("tf_")[1]
        questions = get_true_false(subject_key)
        shuffled = random.sample(questions, min(10, len(questions)))
        context.user_data["tf_questions"] = shuffled
        context.user_data["tf_index"] = 0
        context.user_data["tf_score"] = 0
        context.user_data["tf_subject"] = subject_key
        await show_tf_question(query.message, user_id, context, edit=True)
        return TF_SESSION

    return TF_SESSION


async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        user_id = update.effective_user.id

        # Handle exam date input
        if context.user_data.get("awaiting_exam_date"):
            subject_key = context.user_data.get("examplan_subject")
            date_str = update.message.text.strip()
            context.user_data["awaiting_exam_date"] = False
            from datetime import date
            try:
                exam_dt = datetime.strptime(date_str, "%d.%m.%Y").date()
                if exam_dt <= date.today():
                    keyboard = [[InlineKeyboardButton(t(user_id, "back"), callback_data=f"back_subject_{subject_key}")]]
                    await update.message.reply_text(t(user_id, "exam_date_past"), parse_mode="Markdown",
                                                   reply_markup=InlineKeyboardMarkup(keyboard))
                    return EXAM_DATE_INPUT
                days_left = (exam_dt - date.today()).days
                # Generate plan based on days
                wait_msg = await update.message.reply_text(t(user_id, "exam_plan_generating"))
                subject_name = SUBJECTS[subject_key]["name"]
                lang = db.get_user_lang(user_id) or "en"
                plan = _generate_exam_plan(subject_key, days_left, lang)
                db.save_exam_plan(user_id, subject_key, date_str, plan)
                await wait_msg.delete()
                text = t(user_id, "exam_plan_title", subject=subject_name, date=date_str, days=days_left) + plan
                keyboard = [
                    [InlineKeyboardButton(t(user_id, "exam_plan_new"), callback_data=f"examplan_new_{subject_key}")],
                    [InlineKeyboardButton(t(user_id, "back"), callback_data=f"back_subject_{subject_key}")]
                ]
                await update.message.reply_text(text, parse_mode="Markdown",
                                               reply_markup=InlineKeyboardMarkup(keyboard))
                return SUBJECT_MENU
            except ValueError:
                keyboard = [[InlineKeyboardButton(t(user_id, "back"), callback_data=f"back_subject_{subject_key}")]]
                await update.message.reply_text(t(user_id, "exam_date_invalid"), parse_mode="Markdown",
                                               reply_markup=InlineKeyboardMarkup(keyboard))
                context.user_data["awaiting_exam_date"] = True
                return EXAM_DATE_INPUT

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

    # Regex string to exclude admin approve/deny callbacks from ConversationHandler
    _not_admin_cb = r"^(?!(approve|deny)_)"

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_LANG: [CallbackQueryHandler(set_language, pattern="^lang_")],
            ONBOARDING: [CallbackQueryHandler(onboarding_handler, pattern="^onboard_"),
                         CallbackQueryHandler(main_menu_handler, pattern=_not_admin_cb)],
            MAIN_MENU: [CallbackQueryHandler(main_menu_handler, pattern=_not_admin_cb)],
            CHOOSING_SUBJECT: [CallbackQueryHandler(subject_handler, pattern=_not_admin_cb)],
            PAYMENT_SCREENSHOT: [
                MessageHandler(filters.PHOTO | filters.Document.ALL | (filters.TEXT & ~filters.COMMAND), receive_screenshot),
                CallbackQueryHandler(subject_handler, pattern=_not_admin_cb),
            ],
            SUBJECT_MENU: [CallbackQueryHandler(subject_menu_handler, pattern=_not_admin_cb)],
            QUIZ_SESSION: [CallbackQueryHandler(quiz_handler, pattern=_not_admin_cb)],
            FLASHCARD_SESSION: [CallbackQueryHandler(flashcard_handler, pattern=_not_admin_cb)],
            TRIAL_SESSION: [CallbackQueryHandler(trial_handler, pattern=_not_admin_cb)],
            AI_CHAT_SESSION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ai_chat_message_handler),
                CallbackQueryHandler(subject_menu_handler, pattern=_not_admin_cb),
            ],
            BOOKMARKS_SESSION: [CallbackQueryHandler(bookmarks_handler, pattern=_not_admin_cb)],
            TF_SESSION: [CallbackQueryHandler(tf_handler, pattern=_not_admin_cb)],
            EXAM_DATE_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, fallback),
                CallbackQueryHandler(subject_menu_handler, pattern=_not_admin_cb),
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("cancel", cancel),
            CommandHandler("stats", admin_stats),
            CommandHandler("users", admin_users),
            CommandHandler("profile", admin_profile),
            CommandHandler("giveaccess", admin_giveaccess),
            CommandHandler("revokeaccess", admin_revokeaccess),
            CommandHandler("addpromo", add_promo_cmd),
            CommandHandler("deletepromo", delete_promo_cmd),
            CommandHandler("listpromos", list_promos_cmd),
            MessageHandler(filters.ALL, fallback)
        ],
        allow_reentry=True,
    )

    app.add_handler(CallbackQueryHandler(admin_action, pattern="^(approve|deny)_"), group=-1)
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("users", admin_users))
    app.add_handler(CommandHandler("addpromo", add_promo_cmd))
    app.add_handler(CommandHandler("deletepromo", delete_promo_cmd))
    app.add_handler(CommandHandler("listpromos", list_promos_cmd))
    app.add_handler(CommandHandler("profile", admin_profile))
    app.add_handler(CommandHandler("giveaccess", admin_giveaccess))
    app.add_handler(CommandHandler("revokeaccess", admin_revokeaccess))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(conv)
    app.run_polling(drop_pending_updates=True, close_loop=False)

if __name__ == "__main__":
    main()
