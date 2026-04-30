import os
import json
import urllib.parse
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from database import db
from content import SUBJECTS, get_subject_info, get_flashcards, get_quiz_questions

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth ──────────────────────────────────────────────────────────────────────

def parse_init_data(init_data: str) -> dict:
    """Parse Telegram WebApp initData and return user dict."""
    if not init_data:
        return {}
    try:
        parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        user_str = parsed.get("user", "{}")
        return json.loads(user_str)
    except Exception:
        return {}

def get_user(x_init_data: str) -> dict:
    user = parse_init_data(x_init_data)
    if not user or "id" not in user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    # Auto-register user
    db.ensure_user(user["id"], user.get("username", ""), user.get("first_name", ""))
    return user

# ── API routes ────────────────────────────────────────────────────────────────

@app.get("/api/me")
def me(x_init_data: str = Header(default="")):
    user = get_user(x_init_data)
    return user

@app.get("/api/subjects")
def subjects(x_init_data: str = Header(default="")):
    user = get_user(x_init_data)
    user_id = user["id"]
    result = []
    for key, subj in SUBJECTS.items():
        result.append({
            "key": key,
            "name": subj["name"],
            "price": subj.get("price", 50000),
            "unlocked": db.has_access(user_id, key),
        })
    return result

@app.get("/api/subjects/{key}/quiz")
def quiz(key: str, trial: bool = False, x_init_data: str = Header(default="")):
    user = get_user(x_init_data)
    if key not in SUBJECTS:
        raise HTTPException(status_code=404, detail="Subject not found")
    questions = get_quiz_questions(key)
    if trial:
        questions = questions[:3]
    return questions

@app.get("/api/subjects/{key}/flashcards")
def flashcards(key: str, x_init_data: str = Header(default="")):
    user = get_user(x_init_data)
    if key not in SUBJECTS:
        raise HTTPException(status_code=404, detail="Subject not found")
    return get_flashcards(key)

@app.get("/api/subjects/{key}/materials")
def materials(key: str, x_init_data: str = Header(default="")):
    user = get_user(x_init_data)
    info = get_subject_info(key)
    if not info:
        raise HTTPException(status_code=404, detail="Subject not found")
    return {"chapters": info.get("chapters", [])}

@app.get("/api/progress")
def progress(x_init_data: str = Header(default="")):
    user = get_user(x_init_data)
    return db.get_all_progress(user["id"])

class QuizResult(BaseModel):
    subject_key: str
    score: int
    total: int

@app.post("/api/quiz/result")
def save_result(body: QuizResult, x_init_data: str = Header(default="")):
    user = get_user(x_init_data)
    db.save_quiz_result(user["id"], body.subject_key, body.score, body.total)
    return {"ok": True}

class PromoCheck(BaseModel):
    code: str

@app.post("/api/promo/check")
def check_promo(body: PromoCheck, x_init_data: str = Header(default="")):
    user = get_user(x_init_data)
    discount = db.check_promo(body.code.strip().upper())
    if discount is None:
        raise HTTPException(status_code=400, detail="Invalid promo code")
    return {"discount": discount}

@app.get("/health")
def health():
    return {"status": "ok"}

# ── Static files (Mini App HTML) ──────────────────────────────────────────────
# Place your index.html inside a "static/" folder
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
