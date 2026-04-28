import os
import json
import hmac
import hashlib
import logging
from urllib.parse import unquote, parse_qs
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
import telebot

from database import db
from content import SUBJECTS, get_subject_info, get_flashcards, get_quiz_questions
from config import ADMIN_ID, CARD_NUMBER, PRICE_PER_SUBJECT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins="*")

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
bot = telebot.TeleBot(BOT_TOKEN) if BOT_TOKEN else None


# ── Telegram WebApp auth ──────────────────────────────────────────────────────

def verify_telegram_init_data(init_data: str) -> dict | None:
    """Verify Telegram WebApp initData and return parsed user dict or None."""
    try:
        parsed = parse_qs(init_data, keep_blank_values=True)
        hash_val = parsed.get("hash", [None])[0]
        if not hash_val:
            return None

        # Build check string (all fields except hash, sorted alphabetically)
        data_check_lines = []
        for key, values in sorted(parsed.items()):
            if key == "hash":
                continue
            data_check_lines.append(f"{key}={values[0]}")
        data_check_string = "\n".join(data_check_lines)

        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(expected_hash, hash_val):
            return None

        user_str = parsed.get("user", [None])[0]
        if not user_str:
            return None
        return json.loads(unquote(user_str))
    except Exception as e:
        logger.error(f"init_data verification error: {e}")
        return None


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        init_data = request.headers.get("X-Telegram-Init-Data", "")
        # In dev mode without real Telegram, allow mock user
        if not BOT_TOKEN or os.environ.get("DEV_MODE") == "1":
            request.tg_user = {"id": 891692774, "first_name": "Dev", "username": "devuser", "language_code": "en"}
            return f(*args, **kwargs)
        user = verify_telegram_init_data(init_data)
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
        request.tg_user = user
        return f(*args, **kwargs)
    return decorated


def get_user_lang(user_id):
    return db.get_user_lang(user_id) or "en"


# ── Auth / User ───────────────────────────────────────────────────────────────

@app.route("/api/auth/init", methods=["POST"])
@require_auth
def auth_init():
    u = request.tg_user
    lang = u.get("language_code", "en")
    if lang not in ("ru", "en"):
        lang = "en"
    db.upsert_user(u["id"], u.get("username"), u.get("first_name"), lang)
    subjects_access = db.get_user_subjects(u["id"])
    return jsonify({
        "user_id": u["id"],
        "first_name": u.get("first_name", ""),
        "username": u.get("username", ""),
        "lang": get_user_lang(u["id"]),
        "subjects": subjects_access,
        "is_admin": u["id"] == ADMIN_ID,
    })


@app.route("/api/user/lang", methods=["POST"])
@require_auth
def set_lang():
    lang = request.json.get("lang", "en")
    if lang not in ("ru", "en"):
        return jsonify({"error": "Invalid lang"}), 400
    db.upsert_user(request.tg_user["id"], request.tg_user.get("username"),
                   request.tg_user.get("first_name"), lang)
    return jsonify({"ok": True})


# ── Subjects ─────────────────────────────────────────────────────────────────

@app.route("/api/subjects", methods=["GET"])
@require_auth
def list_subjects():
    user_id = request.tg_user["id"]
    owned = db.get_user_subjects(user_id)
    result = []
    for key, info in SUBJECTS.items():
        result.append({
            "key": key,
            "name": info["name"],
            "owned": key in owned,
            "price": PRICE_PER_SUBJECT,
        })
    return jsonify(result)


@app.route("/api/subjects/<subject_key>/materials", methods=["GET"])
@require_auth
def get_materials(subject_key):
    user_id = request.tg_user["id"]
    if not db.has_access(user_id, subject_key):
        return jsonify({"error": "No access"}), 403
    info = get_subject_info(subject_key)
    return jsonify(info)


@app.route("/api/subjects/<subject_key>/flashcards", methods=["GET"])
@require_auth
def subject_flashcards(subject_key):
    user_id = request.tg_user["id"]
    if not db.has_access(user_id, subject_key):
        return jsonify({"error": "No access"}), 403
    cards = get_flashcards(subject_key)
    return jsonify(cards)


@app.route("/api/subjects/<subject_key>/quiz", methods=["GET"])
@require_auth
def subject_quiz(subject_key):
    user_id = request.tg_user["id"]
    if not db.has_access(user_id, subject_key):
        return jsonify({"error": "No access"}), 403
    import random
    questions = get_quiz_questions(subject_key)
    sample = random.sample(questions, min(20, len(questions)))
    # Strip explanations for quiz delivery
    safe = [{"question": q["question"], "options": q["options"], "correct": q["correct"]} for q in sample]
    return jsonify(safe)


@app.route("/api/subjects/<subject_key>/quiz/answer", methods=["POST"])
@require_auth
def check_answer(subject_key):
    user_id = request.tg_user["id"]
    if not db.has_access(user_id, subject_key):
        return jsonify({"error": "No access"}), 403
    data = request.json
    questions = get_quiz_questions(subject_key)
    q_index = data.get("question_index", 0)
    answer_index = data.get("answer_index", -1)
    if q_index >= len(questions):
        return jsonify({"error": "Invalid question index"}), 400
    q = questions[q_index]
    correct = q["correct"]
    is_correct = answer_index == correct
    return jsonify({
        "correct": is_correct,
        "correct_index": correct,
        "explanation": q.get("explanation", ""),
    })


@app.route("/api/subjects/<subject_key>/quiz/submit", methods=["POST"])
@require_auth
def submit_quiz(subject_key):
    user_id = request.tg_user["id"]
    if not db.has_access(user_id, subject_key):
        return jsonify({"error": "No access"}), 403
    data = request.json
    score = data.get("score", 0)
    total = data.get("total", 0)
    db.save_quiz_result(user_id, subject_key, score, total)
    return jsonify({"ok": True})


@app.route("/api/subjects/<subject_key>/flashcards/viewed", methods=["POST"])
@require_auth
def mark_card_viewed(subject_key):
    user_id = request.tg_user["id"]
    if not db.has_access(user_id, subject_key):
        return jsonify({"error": "No access"}), 403
    db.increment_cards(user_id, subject_key)
    return jsonify({"ok": True})


@app.route("/api/subjects/<subject_key>/progress", methods=["GET"])
@require_auth
def subject_progress(subject_key):
    user_id = request.tg_user["id"]
    if not db.has_access(user_id, subject_key):
        return jsonify({"error": "No access"}), 403
    prog = db.get_progress(user_id, subject_key)
    return jsonify(prog)


# ── Trial Quiz ────────────────────────────────────────────────────────────────

@app.route("/api/trial/<subject_key>", methods=["GET"])
@require_auth
def trial_quiz(subject_key):
    import random
    if subject_key not in SUBJECTS:
        return jsonify({"error": "Unknown subject"}), 404
    questions = get_quiz_questions(subject_key)
    sample = random.sample(questions, min(3, len(questions)))
    safe = [{"question": q["question"], "options": q["options"], "correct": q["correct"]} for q in sample]
    return jsonify(safe)


# ── Payment ───────────────────────────────────────────────────────────────────

@app.route("/api/payment/request", methods=["POST"])
@require_auth
def request_payment():
    user_id = request.tg_user["id"]
    data = request.json
    subject_key = data.get("subject_key")
    promo_code = data.get("promo_code", "").strip()

    if subject_key not in SUBJECTS:
        return jsonify({"error": "Unknown subject"}), 400
    if db.has_access(user_id, subject_key):
        return jsonify({"error": "already_owned"}), 400

    price = PRICE_PER_SUBJECT
    discount = 0
    if promo_code:
        d = db.check_promo(promo_code)
        if d:
            discount = d
            price = int(price * (100 - d) / 100)
        else:
            return jsonify({"error": "invalid_promo"}), 400

    db.add_pending_payment(user_id, subject_key)

    # Notify admin
    if bot:
        try:
            u = request.tg_user
            name = u.get("first_name", "")
            uname = f"@{u.get('username')}" if u.get("username") else f"ID:{user_id}"
            subject_name = SUBJECTS[subject_key]["name"]
            msg = (f"💰 *New Payment Request*\n\n"
                   f"Student: {name} ({uname})\n"
                   f"Subject: *{subject_name}*\n"
                   f"Amount: *{price:,} UZS*\n"
                   f"Discount: {discount}%\n\n"
                   f"User ID: `{user_id}`\n"
                   f"Subject key: `{subject_key}`")
            keyboard = telebot.types.InlineKeyboardMarkup()
            keyboard.add(
                telebot.types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}_{subject_key}"),
                telebot.types.InlineKeyboardButton("❌ Deny", callback_data=f"deny_{user_id}_{subject_key}")
            )
            bot.send_message(ADMIN_ID, msg, parse_mode="Markdown", reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")

    return jsonify({
        "ok": True,
        "card": CARD_NUMBER,
        "price": price,
        "discount": discount,
    })


@app.route("/api/payment/screenshot", methods=["POST"])
@require_auth
def upload_screenshot():
    """Receive base64 screenshot and forward to admin."""
    user_id = request.tg_user["id"]
    data = request.json
    subject_key = data.get("subject_key")
    screenshot_b64 = data.get("screenshot")  # base64 string

    if not screenshot_b64 or not subject_key:
        return jsonify({"error": "Missing data"}), 400

    if bot and screenshot_b64:
        try:
            import base64
            img_bytes = base64.b64decode(screenshot_b64.split(",")[-1])
            u = request.tg_user
            name = u.get("first_name", "")
            uname = f"@{u.get('username')}" if u.get("username") else f"ID:{user_id}"
            subject_name = SUBJECTS.get(subject_key, {}).get("name", subject_key)
            caption = (f"📸 *Payment Screenshot*\n"
                       f"Student: {name} ({uname})\n"
                       f"Subject: *{subject_name}*\n"
                       f"User ID: `{user_id}` | Key: `{subject_key}`")
            keyboard = telebot.types.InlineKeyboardMarkup()
            keyboard.add(
                telebot.types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}_{subject_key}"),
                telebot.types.InlineKeyboardButton("❌ Deny", callback_data=f"deny_{user_id}_{subject_key}")
            )
            bot.send_photo(ADMIN_ID, img_bytes, caption=caption, parse_mode="Markdown", reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Failed to send screenshot: {e}")

    return jsonify({"ok": True})


@app.route("/api/promo/check", methods=["POST"])
@require_auth
def check_promo():
    code = request.json.get("code", "").strip()
    discount = db.check_promo(code)
    if discount:
        price = int(PRICE_PER_SUBJECT * (100 - discount) / 100)
        return jsonify({"valid": True, "discount": discount, "price": price})
    return jsonify({"valid": False})


# ── Admin ─────────────────────────────────────────────────────────────────────

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.tg_user["id"] != ADMIN_ID:
            return jsonify({"error": "Forbidden"}), 403
        return f(*args, **kwargs)
    return decorated


@app.route("/api/admin/stats", methods=["GET"])
@require_auth
@require_admin
def admin_stats():
    stats = db.get_stats()
    revenue = stats["paid"] * PRICE_PER_SUBJECT
    return jsonify({**stats, "revenue": revenue, "price_per_subject": PRICE_PER_SUBJECT})


@app.route("/api/admin/users", methods=["GET"])
@require_auth
@require_admin
def admin_users():
    users = db.get_all_users_with_subjects()
    return jsonify(users)


@app.route("/api/admin/grant", methods=["POST"])
@require_auth
@require_admin
def admin_grant():
    data = request.json
    user_id = data.get("user_id")
    subject_key = data.get("subject_key")
    db.grant_access(user_id, subject_key)
    db.remove_pending(user_id, subject_key)
    if bot:
        try:
            subject_name = SUBJECTS.get(subject_key, {}).get("name", subject_key)
            bot.send_message(user_id, f"🎉 *Access Granted!*\n\n*{subject_name}* is now available.", parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to notify user: {e}")
    return jsonify({"ok": True})


@app.route("/api/admin/deny", methods=["POST"])
@require_auth
@require_admin
def admin_deny():
    data = request.json
    user_id = data.get("user_id")
    subject_key = data.get("subject_key")
    db.remove_pending(user_id, subject_key)
    if bot:
        try:
            bot.send_message(user_id, "❌ Your payment was not confirmed. Please contact the admin.")
        except Exception as e:
            logger.error(f"Failed to notify user: {e}")
    return jsonify({"ok": True})


@app.route("/api/admin/promo", methods=["POST"])
@require_auth
@require_admin
def admin_add_promo():
    data = request.json
    code = data.get("code", "").strip().upper()
    discount = int(data.get("discount", 0))
    if not code or not (1 <= discount <= 100):
        return jsonify({"error": "Invalid data"}), 400
    db.add_promo(code, discount)
    return jsonify({"ok": True})


@app.route("/api/admin/subjects", methods=["GET"])
@require_auth
@require_admin
def admin_subjects():
    return jsonify([{"key": k, "name": v["name"]} for k, v in SUBJECTS.items()])


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    db.init()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
