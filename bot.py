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
from content import SUBJECTS, get_subject_info, get_flashcards, get_quiz_questions, get_cheatsheet, get_glossary, get_true_false, get_videos
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
 AI_CHAT_SESSION, BOOKMARKS_SESSION, TF_SESSION, EXAM_DATE_INPUT) = range(12)

FREE_QUESTIONS = 3
QUIZ_QUESTIONS_COUNT = 20

TEXTS = {
    "ru": {
        "welcome": "✨ *Добро пожаловать в BMU Study Hub!*\n\n🎓 Умная подготовка к экзаменам\n📚 Конспекты · Тесты · Флэшкарты · ИИ\n\n━━━━━━━━━━━━━━━\n🌐 Выберите язык:",
        "main_menu": "🎓 *BMU Study Hub*\n_British Management University_\n\n━━━━━━━━━━━━━━━\n\nЧто будем делать сегодня?",
        "my_subjects": "📚 Мои предметы",
        "buy_access": "💳 Купить доступ",
        "trial_quiz": "🎯 Попробовать бесплатно",
        "help": "💬 Поддержка",
        "choose_subject_buy": "🛒 *Купить доступ*\n\n━━━━━━━━━━━━━━━\nВыберите предмет:",
        "choose_subject_study": "📚 *Мои предметы*\n\n━━━━━━━━━━━━━━━\nВыберите предмет для изучения:",
        "choose_trial_subject": "🎯 *Пробный тест — бесплатно*\n\n━━━━━━━━━━━━━━━\nВыберите предмет\n_3 вопроса · без оплаты_",
        "payment_instruction": "💳 *Оплата доступа*\n\n📘 Предмет: *{subject}*\n💰 Стоимость: *{price:,} сум*\n\n━━━━━━━━━━━━━━━\n🏦 Переведите на карту:\n`{card}`\n\n━━━━━━━━━━━━━━━\n📸 После оплаты отправьте скриншот перевода 👇",
        "screenshot_received": "✅ *Скриншот получен!*\n\n⏳ Ваша оплата на проверке\n🕐 Обычно до *30 минут*\n\n━━━━━━━━━━━━━━━\n🔔 Вы получите уведомление как только доступ откроется.",
        "access_granted": "🎉 *Поздравляем! Доступ открыт!*\n\n━━━━━━━━━━━━━━━\n📘 Предмет *{subject}* теперь доступен!\n\n✨ Удачи в учёбе!",
        "access_denied": "❌ *Оплата не подтверждена*\n\n━━━━━━━━━━━━━━━\nПожалуйста, свяжитесь с администратором.",
        "no_subjects": "📭 *Предметов пока нет*\n\n━━━━━━━━━━━━━━━\nПриобретите доступ чтобы начать учиться 👇",
        "subject_menu": "📘 *{subject}*\n\n━━━━━━━━━━━━━━━\n_Выберите режим обучения:_",
        "study_materials": "📖 Конспект",
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
        "help_text": "💬 *Поддержка*\n\n━━━━━━━━━━━━━━━\n📩 По вопросам оплаты и доступа:\nОбратитесь к администратору\n\n⏰ Бот работает 24/7\n✅ Доступ открывается в течение 30 минут после оплаты",
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
        "bundle": "🎓 Все предметы (-20%)",
        "bundle_text": "🎓 *Пакет «Все предметы»*\n\n━━━━━━━━━━━━━━━\n📚 Включает все {count} предмета\n\n💰 Обычная цена: *{full_price:,} сум*\n🔥 Цена пакета: *{bundle_price:,} сум*\n💸 Экономия: *{save:,} сум* (скидка 20%!)\n\n━━━━━━━━━━━━━━━\n🏦 Переведите на карту:\n`{card}`\n\n📸 После оплаты отправьте скриншот 👇",
        "bundle_already": "✅ У вас уже есть доступ ко всем предметам!",
    },
    "en": {
        "welcome": "✨ *Welcome to BMU Study Hub!*\n\n🎓 Smart exam preparation\n📚 Notes · Tests · Flashcards · AI\n\n━━━━━━━━━━━━━━━\n🌐 Choose your language:",
        "main_menu": "🎓 *BMU Study Hub*\n_British Management University_\n\n━━━━━━━━━━━━━━━\n\nWhat shall we study today?",
        "my_subjects": "📚 My Subjects",
        "buy_access": "💳 Buy Access",
        "trial_quiz": "🎯 Try for Free",
        "help": "💬 Support",
        "choose_subject_buy": "🛒 *Buy Access*\n\n━━━━━━━━━━━━━━━\nChoose a subject:",
        "choose_subject_study": "📚 *My Subjects*\n\n━━━━━━━━━━━━━━━\nChoose a subject to study:",
        "choose_trial_subject": "🎯 *Free Trial*\n\n━━━━━━━━━━━━━━━\nChoose a subject\n_3 questions · no payment needed_",
        "payment_instruction": "💳 *Purchase Access*\n\n📘 Subject: *{subject}*\n💰 Price: *{price:,} UZS*\n\n━━━━━━━━━━━━━━━\n🏦 Transfer to card:\n`{card}`\n\n━━━━━━━━━━━━━━━\n📸 After payment, send a screenshot 👇",
        "screenshot_received": "✅ *Screenshot received!*\n\n⏳ Your payment is under review\n🕐 Usually within *30 minutes*\n\n━━━━━━━━━━━━━━━\n🔔 You'll get a notification once access is granted.",
        "access_granted": "🎉 *Congratulations! Access Granted!*\n\n━━━━━━━━━━━━━━━\n📘 *{subject}* is now available!\n\n✨ Good luck with your studies!",
        "access_denied": "❌ *Payment Not Confirmed*\n\n━━━━━━━━━━━━━━━\nPlease contact the administrator.",
        "no_subjects": "📭 *No subjects yet*\n\n━━━━━━━━━━━━━━━\nPurchase access to start learning 👇",
        "subject_menu": "📘 *{subject}*\n\n━━━━━━━━━━━━━━━\n_Choose a study mode:_",
        "study_materials": "📖 Study Notes",
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
        "help_text": "💬 *Support*\n\n━━━━━━━━━━━━━━━\n📩 For payment & access issues:\nContact the administrator\n\n⏰ Bot runs 24/7\n✅ Access granted within 30 minutes of payment",
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
        "bundle": "🎓 All Subjects (-20%)",
        "bundle_text": "🎓 *All Subjects Bundle*\n\n━━━━━━━━━━━━━━━\n📚 Includes all {count} subjects\n\n💰 Regular price: *{full_price:,} UZS*\n🔥 Bundle price: *{bundle_price:,} UZS*\n💸 You save: *{save:,} UZS* (20% off!)\n\n━━━━━━━━━━━━━━━\n🏦 Transfer to card:\n`{card}`\n\n📸 After payment, send a screenshot 👇",
        "bundle_already": "✅ You already have access to all subjects!",
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
        [InlineKeyboardButton(t(user_id, "buy_access"), callback_data="menu_buy_access"),
         InlineKeyboardButton(t(user_id, "bundle"), callback_data="menu_bundle")],
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

    elif action == "menu_bundle":
        subjects = db.get_user_subjects(user_id)
        all_keys = list(SUBJECTS.keys())
        if all(k in subjects for k in all_keys):
            await query.answer(t(user_id, "bundle_already"), show_alert=True)
            return MAIN_MENU
        count = len(all_keys)
        full_price = PRICE_PER_SUBJECT * count
        bundle_price = int(full_price * 0.8)
        save = full_price - bundle_price
        text = t(user_id, "bundle_text", count=count, full_price=full_price,
                 bundle_price=bundle_price, save=save, card=CARD_NUMBER)
        context.user_data["pending_subject"] = "bundle"
        context.user_data["promo_discount"] = 0
        keyboard = [[InlineKeyboardButton(t(user_id, "back"), callback_data="back_main")]]
        await query.message.edit_text(text, parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(keyboard))
        return PAYMENT_SCREENSHOT

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
         InlineKeyboardButton(t(user_id, "true_false"), callback_data=f"tf_{subject_key}")],
        [InlineKeyboardButton(t(user_id, "quiz_history"), callback_data=f"history_{subject_key}"),
         InlineKeyboardButton(t(user_id, "exam_plan"), callback_data=f"examplan_{subject_key}")],
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
    if subject_key == "bundle":
        count = len(SUBJECTS)
        full_price = PRICE_PER_SUBJECT * count
        final_price = int(full_price * 0.8)
        subject_display = "🎓 Пакет ВСЕ ПРЕДМЕТЫ"
    else:
        final_price = int(PRICE_PER_SUBJECT * (1 - discount / 100))
        info = SUBJECTS[subject_key]
        subject_display = info["name"]
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

    if action == "approve":
        if subject_key == "bundle":
            for key in SUBJECTS:
                db.grant_access(student_id, key)
            db.remove_pending(student_id, subject_key)
            student_lang = db.get_user_lang(student_id) or "en"
            msg = "🎉 *Доступ ко всем предметам открыт!*\n\nТеперь вам доступны все предметы в разделе «Мои предметы»." if student_lang == "ru" else "🎉 *Full Access Granted!*\n\nAll subjects are now available in 'My Subjects'."
        else:
            info = SUBJECTS[subject_key]
            db.grant_access(student_id, subject_key)
            db.remove_pending(student_id, subject_key)
            student_lang = db.get_user_lang(student_id) or "en"
            msg = TEXTS[student_lang]["access_granted"].format(subject=info["name"])
        start_hint = "\n\n▶️ Нажмите /start чтобы открыть предмет" if student_lang == "ru" else "\n\n▶️ Press /start to access your subject"
        try:
            await context.bot.send_message(student_id, msg + start_hint, parse_mode="Markdown")
        except:
            pass
        await query.message.edit_caption(
            query.message.caption + "\n\n✅ *Доступ выдан*", parse_mode="Markdown"
        )
    elif action == "deny":
        subject_key = parts[2]
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
            await query.answer()
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



# ── TRUE / FALSE ──────────────────────────────────────────────────────────────

async def show_tf_question(message, user_id, context, edit=False):
    questions = context.user_data["tf_questions"]
    index = context.user_data["tf_index"]
    subject_key = context.user_data["tf_subject"]
    total = len(questions)
    q = questions[index]
    text = t(user_id, "tf_question", subject=SUBJECTS[subject_key]["name"],
             num=index+1, total=total, statement=q["statement"])
    keyboard = [
        [InlineKeyboardButton(t(user_id, "tf_true"), callback_data="tf_ans_true"),
         InlineKeyboardButton(t(user_id, "tf_false"), callback_data="tf_ans_false")],
        [InlineKeyboardButton(t(user_id, "back"), callback_data=f"back_subject_{subject_key}")]
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
            return SUBJECT_MENU
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
            TF_SESSION: [CallbackQueryHandler(tf_handler)],
            EXAM_DATE_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, fallback),
                CallbackQueryHandler(subject_menu_handler),
            ],
        },
        fallbacks=[CommandHandler("start", start), MessageHandler(filters.ALL, fallback)],
        allow_reentry=True,
    )

    app.add_handler(CallbackQueryHandler(admin_action, pattern="^(approve|deny)_"))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("users", admin_users))
    app.add_handler(CommandHandler("addpromo", add_promo_cmd))
    app.add_handler(conv)
    app.run_polling(drop_pending_updates=True, close_loop=False)

if __name__ == "__main__":
    main()
