import asyncio
import logging
import os
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from database import db
from config import ADMIN_ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _safe(text):
    """Escape special Markdown chars in user-provided strings."""
    for ch in ["*", "_", "`", "["]:
        text = text.replace(ch, "\\" + ch)
    return text


# ── /start ────────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.username, user.first_name, "ru")
    await update.message.reply_text(
        f"👋 Привет, *{user.first_name}*!\n\nБот запущен.",
        parse_mode="Markdown"
    )


# ── ADMIN: /stats ──────────────────────────────────────────────────────────────

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    stats = db.get_stats()
    text = (
        f"📈 *Статистика*\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👥 Студентов: *{stats['users']}*"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ── ADMIN: /users ──────────────────────────────────────────────────────────────

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    users = db.get_all_users_with_subjects()
    if not users:
        await update.message.reply_text("Нет пользователей.")
        return
    await update.message.reply_text(f"👥 *Всего: {len(users)}*", parse_mode="Markdown")
    chunk = ""
    for u in users:
        name = _safe(u["first_name"] or "—")
        username = f"@{_safe(u['username'])}" if u["username"] else "без username"
        line = f"• {name} ({username}) — ID: `{u['user_id']}`\n"
        if len(chunk) + len(line) > 3800:
            await update.message.reply_text(chunk, parse_mode="Markdown")
            chunk = ""
        chunk += line
    if chunk:
        await update.message.reply_text(chunk, parse_mode="Markdown")


# ── ADMIN: /profile ────────────────────────────────────────────────────────────

async def admin_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if not args:
        await update.message.reply_text("Использование: /profile USER_ID")
        return
    try:
        target_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ USER_ID должен быть числом.")
        return
    profile = db.get_student_profile(target_id)
    if not profile:
        await update.message.reply_text(f"❌ Пользователь `{target_id}` не найден.", parse_mode="Markdown")
        return
    username = f"@{_safe(profile['username'])}" if profile["username"] else "—"
    first_name = _safe(profile["first_name"] or "—")
    created = str(profile["created_at"])[:10] if profile["created_at"] else "—"
    text = (
        f"👤 *Профиль*\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔹 Имя: *{first_name}*\n"
        f"🔹 Username: *{username}*\n"
        f"🆔 ID: `{profile['user_id']}`\n"
        f"🌐 Язык: *{profile['lang']}*\n"
        f"📅 Регистрация: *{created}*"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ── ADMIN: /broadcast ─────────────────────────────────────────────────────────
#
#  Использование:
#    /broadcast Текст сообщения
#
#  Поддерживает Markdown. Отправляет всем пользователям в базе.

async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text(
            "📢 *Рассылка*\n\n"
            "Использование:\n`/broadcast Текст сообщения`\n\n"
            "Пример:\n`/broadcast 🎉 Привет всем! Это важное объявление.`",
            parse_mode="Markdown"
        )
        return

    text = " ".join(context.args)
    users = db.get_all_users_with_subjects()
    if not users:
        await update.message.reply_text("❌ Нет пользователей для рассылки.")
        return

    progress_msg = await update.message.reply_text(f"📤 Начинаю рассылку... (0/{len(users)})")
    sent = 0
    failed = 0
    for i, user in enumerate(users):
        try:
            await context.bot.send_message(
                chat_id=user["user_id"],
                text=text,
                parse_mode="Markdown"
            )
            sent += 1
        except Exception:
            failed += 1
        if (i + 1) % 10 == 0:
            try:
                await progress_msg.edit_text(f"📤 Рассылка... ({i+1}/{len(users)})")
            except Exception:
                pass
        await asyncio.sleep(0.05)

    await progress_msg.edit_text(
        f"✅ *Рассылка завершена!*\n\n"
        f"📨 Отправлено: *{sent}*\n"
        f"❌ Не доставлено: *{failed}*\n"
        f"👥 Всего: *{len(users)}*",
        parse_mode="Markdown"
    )


# ── FALLBACK ───────────────────────────────────────────────────────────────────

async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Используйте /start")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN не задан!")
    db.init()

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("users", admin_users))
    app.add_handler(CommandHandler("profile", admin_profile))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(MessageHandler(filters.ALL, fallback))

    app.run_polling(drop_pending_updates=True, close_loop=False)


if __name__ == "__main__":
    main()
