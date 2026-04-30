from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os, hmac, hashlib, json, time
from database import db
from content import SUBJECTS, get_subject_info, get_flashcards, get_quiz_questions
from config import ADMIN_ID, PRICE_PER_SUBJECT

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

def verify_telegram_init_data(init_data: str) -> dict:
    try:
        parsed = dict(x.split("=", 1) for x in init_data.split("&"))
        hash_val = parsed.pop("hash", "")
        data_check = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        expected = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, hash_val):
            raise ValueError("Invalid hash")
        user_data = json.loads(parsed.get("user", "{}"))
        return user_data
    except Exception:
        return {}

def get_user(init_data: str = Header(None, alias="x-init-data")):
    if not init_data:
        raise HTTPException(status_code=401, detail="No init data")
    user = verify_telegram_init_data(init_data)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid init data")
    return user

@app.get("/api/me")
def get_me(init_data: str = Header(None, alias="x-init-data")):
    user = get_user(init_data)
    user_id = user["id"]
    db.upsert_user(user_id, user.get("username",""), user.get("first_name",""), user.get("language_code","en"))
    subjects = db.get_user_subjects(user_id)
    lang = db.get_user_lang(user_id)
    return {
        "id": user_id,
        "first_name": user.get("first_name",""),
        "username": user.get("username",""),
        "lang": lang,
        "subjects": subjects,
        "is_admin": user_id == ADMIN_ID,
    }

@app.get("/api/subjects")
def get_subjects(init_data: str = Header(None, alias="x-init-data")):
    user = get_user(init_data)
    user_id = user["id"]
    unlocked = db.get_user_subjects(user_id)
    result = []
    for key, info in SUBJECTS.items():
        result.append({
            "key": key,
            "name": info["name"],
            "unlocked": key in unlocked,
            "price": PRICE_PER_SUBJECT,
        })
    return result

@app.get("/api/subjects/{subject_key}/materials")
def get_materials(subject_key: str, init_data: str = Header(None, alias="x-init-data")):
    user = get_user(init_data)
    user_id = user["id"]
    if not db.has_access(user_id, subject_key):
        raise HTTPException(status_code=403, detail="No access")
    info = get_subject_info(subject_key)
    return info

@app.get("/api/subjects/{subject_key}/flashcards")
def get_cards(subject_key: str, init_data: str = Header(None, alias="x-init-data")):
    user = get_user(init_data)
    user_id = user["id"]
    if not db.has_access(user_id, subject_key):
        raise HTTPException(status_code=403, detail="No access")
    db.increment_cards(user_id, subject_key)
    return get_flashcards(subject_key)

@app.get("/api/subjects/{subject_key}/quiz")
def get_quiz(subject_key: str, trial: bool = False, init_data: str = Header(None, alias="x-init-data")):
    user = get_user(init_data)
    user_id = user["id"]
    if not trial and not db.has_access(user_id, subject_key):
        raise HTTPException(status_code=403, detail="No access")
    import random
    questions = get_quiz_questions(subject_key)
    count = 3 if trial else 20
    sample = random.sample(questions, min(count, len(questions)))
    return sample

class QuizResult(BaseModel):
    subject_key: str
    score: int
    total: int

@app.post("/api/quiz/result")
def save_result(result: QuizResult, init_data: str = Header(None, alias="x-init-data")):
    user = get_user(init_data)
    db.save_quiz_result(user["id"], result.subject_key, result.score, result.total)
    return {"ok": True}

@app.get("/api/progress")
def get_progress_all(init_data: str = Header(None, alias="x-init-data")):
    user = get_user(init_data)
    user_id = user["id"]
    subjects = db.get_user_subjects(user_id)
    result = {}
    for key in subjects:
        result[key] = db.get_progress(user_id, key)
    return result

class PromoCheck(BaseModel):
    code: str

@app.post("/api/promo/check")
def check_promo(body: PromoCheck, init_data: str = Header(None, alias="x-init-data")):
    get_user(init_data)
    discount = db.check_promo(body.code.upper())
    if not discount:
        raise HTTPException(status_code=404, detail="Invalid promo code")
    return {"discount": discount}

@app.get("/api/stats")
def stats(init_data: str = Header(None, alias="x-init-data")):
    user = get_user(init_data)
    if user["id"] != ADMIN_ID:
        raise HTTPException(status_code=403)
    return db.get_stats()

@app.get("/")
def root():
    return {"status": "BMU Study Hub API running"}
