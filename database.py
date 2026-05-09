import sqlite3
import os
from datetime import date, timedelta

# On Railway: mount a Volume at /data → data persists across deploys.
# Locally: falls back to ./studybot.db in the project folder.
_DEFAULT_DB = "/data/studybot.db" if os.path.isdir("/data") else "studybot.db"
DB_PATH = os.environ.get("DB_PATH", _DEFAULT_DB)

os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)

def _migrate(con):
    """Add new columns to existing databases without data loss."""
    migrations = [
        "ALTER TABLE promo_codes ADD COLUMN max_uses INTEGER DEFAULT NULL",
        "ALTER TABLE promo_codes ADD COLUMN used_count INTEGER DEFAULT 0",
    ]
    for sql in migrations:
        try:
            con.execute(sql)
        except Exception:
            pass  # column already exists

class Database:
    def init(self):
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                lang TEXT DEFAULT 'en',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS access (
                user_id INTEGER,
                subject_key TEXT,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, subject_key)
            );
            CREATE TABLE IF NOT EXISTS pending_payments (
                user_id INTEGER,
                subject_key TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, subject_key)
            );
            CREATE TABLE IF NOT EXISTS quiz_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subject_key TEXT,
                score INTEGER,
                total INTEGER,
                taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS flashcard_progress (
                user_id INTEGER,
                subject_key TEXT,
                cards_viewed INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, subject_key)
            );
            CREATE TABLE IF NOT EXISTS trial_used (
                user_id INTEGER,
                subject_key TEXT,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, subject_key)
            );
            CREATE TABLE IF NOT EXISTS promo_codes (
                code TEXT PRIMARY KEY,
                discount INTEGER,
                max_uses INTEGER DEFAULT NULL,
                used_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subject_key TEXT,
                question_text TEXT,
                correct_answer TEXT,
                explanation TEXT,
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS ai_chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subject_key TEXT,
                role TEXT,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS exam_plans (
                user_id INTEGER,
                subject_key TEXT,
                exam_date TEXT,
                plan_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, subject_key)
            );
            CREATE TABLE IF NOT EXISTS user_xp (
                user_id INTEGER PRIMARY KEY,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                streak INTEGER DEFAULT 0,
                last_activity DATE
            );
        """)
        _migrate(con)
        con.commit()
        con.close()

    def _con(self):
        return sqlite3.connect(DB_PATH)

    # ── Used by bot ──────────────────────────────────────────────────────────

    def upsert_user(self, user_id, username, first_name, lang):
        with self._con() as con:
            con.execute("""
                INSERT INTO users (user_id, username, first_name, lang)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET username=excluded.username,
                first_name=excluded.first_name, lang=excluded.lang
            """, (user_id, username, first_name, lang))

    def get_user_lang(self, user_id):
        with self._con() as con:
            row = con.execute("SELECT lang FROM users WHERE user_id=?", (user_id,)).fetchone()
            return row[0] if row else None

    def get_user_subjects(self, user_id):
        with self._con() as con:
            rows = con.execute("SELECT subject_key FROM access WHERE user_id=?", (user_id,)).fetchall()
            return [r[0] for r in rows]

    def grant_access(self, user_id, subject_key):
        with self._con() as con:
            con.execute("INSERT OR IGNORE INTO access (user_id, subject_key) VALUES (?, ?)",
                        (user_id, subject_key))

    def revoke_access(self, user_id, subject_key):
        with self._con() as con:
            changes = con.execute(
                "DELETE FROM access WHERE user_id=? AND subject_key=?",
                (user_id, subject_key)
            ).rowcount
            return changes > 0

    def add_pending_payment(self, user_id, subject_key):
        with self._con() as con:
            con.execute("INSERT OR REPLACE INTO pending_payments (user_id, subject_key) VALUES (?, ?)",
                        (user_id, subject_key))

    def remove_pending(self, user_id, subject_key):
        with self._con() as con:
            con.execute("DELETE FROM pending_payments WHERE user_id=? AND subject_key=?",
                        (user_id, subject_key))

    def has_access(self, user_id, subject_key):
        with self._con() as con:
            row = con.execute("SELECT 1 FROM access WHERE user_id=? AND subject_key=?",
                              (user_id, subject_key)).fetchone()
            return row is not None

    def save_quiz_result(self, user_id, subject_key, score, total):
        with self._con() as con:
            con.execute("INSERT INTO quiz_results (user_id, subject_key, score, total) VALUES (?, ?, ?, ?)",
                        (user_id, subject_key, score, total))

    def get_progress(self, user_id, subject_key):
        """Progress for a single subject (used by bot)."""
        with self._con() as con:
            rows = con.execute("""
                SELECT score, total FROM quiz_results
                WHERE user_id=? AND subject_key=?
            """, (user_id, subject_key)).fetchall()
            if not rows:
                return {"tests": 0, "avg": 0, "best": 0, "cards": 0}
            tests = len(rows)
            avg = int(sum(r[0]/r[1]*100 for r in rows) / tests)
            best = int(max(r[0]/r[1]*100 for r in rows))
            cards_row = con.execute("""
                SELECT cards_viewed FROM flashcard_progress
                WHERE user_id=? AND subject_key=?
            """, (user_id, subject_key)).fetchone()
            cards = cards_row[0] if cards_row else 0
            return {"tests": tests, "avg": avg, "best": best, "cards": cards}

    # ── Used by Mini App API ─────────────────────────────────────────────────

    def ensure_user(self, user_id, username="", first_name=""):
        """Register user if not exists (called from Mini App)."""
        with self._con() as con:
            con.execute("""
                INSERT INTO users (user_id, username, first_name, lang)
                VALUES (?, ?, ?, 'en')
                ON CONFLICT(user_id) DO UPDATE SET
                    username=excluded.username,
                    first_name=excluded.first_name
            """, (user_id, username or "", first_name or ""))

    def get_all_progress(self, user_id):
        """Progress for all subjects (used by Mini App /api/progress)."""
        with self._con() as con:
            rows = con.execute("""
                SELECT subject_key, score, total FROM quiz_results
                WHERE user_id=?
            """, (user_id,)).fetchall()

            by_subject = {}
            for subject_key, score, total in rows:
                if subject_key not in by_subject:
                    by_subject[subject_key] = []
                by_subject[subject_key].append((score, total))

            result = {}
            for key, entries in by_subject.items():
                tests = len(entries)
                avg = int(sum(s/t*100 for s, t in entries) / tests)
                best = int(max(s/t*100 for s, t in entries))
                cards_row = con.execute("""
                    SELECT cards_viewed FROM flashcard_progress
                    WHERE user_id=? AND subject_key=?
                """, (user_id, key)).fetchone()
                cards = cards_row[0] if cards_row else 0
                result[key] = {"tests": tests, "avg": avg, "best": best, "cards": cards}

            return result

    # ── Promo & admin ────────────────────────────────────────────────────────

    def increment_cards(self, user_id, subject_key):
        with self._con() as con:
            con.execute("""
                INSERT INTO flashcard_progress (user_id, subject_key, cards_viewed)
                VALUES (?, ?, 1)
                ON CONFLICT(user_id, subject_key) DO UPDATE SET
                cards_viewed = cards_viewed + 1
            """, (user_id, subject_key))

    def has_used_trial(self, user_id, subject_key):
        with self._con() as con:
            row = con.execute(
                "SELECT 1 FROM trial_used WHERE user_id=? AND subject_key=?",
                (user_id, subject_key)
            ).fetchone()
            return row is not None

    def mark_trial_used(self, user_id, subject_key):
        with self._con() as con:
            con.execute(
                "INSERT OR IGNORE INTO trial_used (user_id, subject_key) VALUES (?, ?)",
                (user_id, subject_key)
            )

    # ── Bookmarks ────────────────────────────────────────────────────────────

    def add_bookmark(self, user_id, subject_key, question_text, correct_answer, explanation):
        with self._con() as con:
            con.execute("""
                INSERT INTO bookmarks (user_id, subject_key, question_text, correct_answer, explanation)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, subject_key, question_text, correct_answer, explanation))

    def get_bookmarks(self, user_id, subject_key=None):
        with self._con() as con:
            if subject_key:
                rows = con.execute("""
                    SELECT id, subject_key, question_text, correct_answer, explanation, saved_at
                    FROM bookmarks WHERE user_id=? AND subject_key=? ORDER BY saved_at DESC
                """, (user_id, subject_key)).fetchall()
            else:
                rows = con.execute("""
                    SELECT id, subject_key, question_text, correct_answer, explanation, saved_at
                    FROM bookmarks WHERE user_id=? ORDER BY saved_at DESC LIMIT 20
                """, (user_id,)).fetchall()
            return [{"id": r[0], "subject_key": r[1], "question": r[2],
                     "answer": r[3], "explanation": r[4], "saved_at": r[5]} for r in rows]

    def delete_bookmark(self, bookmark_id, user_id):
        with self._con() as con:
            con.execute("DELETE FROM bookmarks WHERE id=? AND user_id=?", (bookmark_id, user_id))

    def bookmark_exists(self, user_id, question_text):
        with self._con() as con:
            row = con.execute(
                "SELECT 1 FROM bookmarks WHERE user_id=? AND question_text=?",
                (user_id, question_text)
            ).fetchone()
            return row is not None

    # ── AI Chat History ──────────────────────────────────────────────────────

    def save_ai_message(self, user_id, subject_key, role, message):
        with self._con() as con:
            con.execute("""
                INSERT INTO ai_chat_history (user_id, subject_key, role, message)
                VALUES (?, ?, ?, ?)
            """, (user_id, subject_key, role, message))

    def get_ai_history(self, user_id, subject_key, limit=10):
        with self._con() as con:
            rows = con.execute("""
                SELECT role, message FROM ai_chat_history
                WHERE user_id=? AND subject_key=?
                ORDER BY created_at DESC LIMIT ?
            """, (user_id, subject_key, limit)).fetchall()
            return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    def clear_ai_history(self, user_id, subject_key):
        with self._con() as con:
            con.execute("DELETE FROM ai_chat_history WHERE user_id=? AND subject_key=?",
                        (user_id, subject_key))

    # ── Quiz History with dates ──────────────────────────────────────────────

    def get_quiz_history(self, user_id, subject_key=None, limit=10):
        with self._con() as con:
            if subject_key:
                rows = con.execute("""
                    SELECT subject_key, score, total, taken_at FROM quiz_results
                    WHERE user_id=? AND subject_key=?
                    ORDER BY taken_at DESC LIMIT ?
                """, (user_id, subject_key, limit)).fetchall()
            else:
                rows = con.execute("""
                    SELECT subject_key, score, total, taken_at FROM quiz_results
                    WHERE user_id=?
                    ORDER BY taken_at DESC LIMIT ?
                """, (user_id, limit)).fetchall()
            return [{"subject_key": r[0], "score": r[1], "total": r[2], "taken_at": r[3]} for r in rows]

    def add_promo(self, code, discount, max_uses=None):
        with self._con() as con:
            con.execute(
                "INSERT OR REPLACE INTO promo_codes (code, discount, max_uses, used_count) VALUES (?, ?, ?, 0)",
                (code, discount, max_uses)
            )

    def check_promo(self, code):
        with self._con() as con:
            row = con.execute(
                "SELECT discount, max_uses, used_count FROM promo_codes WHERE code=?", (code,)
            ).fetchone()
            if not row:
                return None
            discount, max_uses, used_count = row
            if max_uses is not None and used_count >= max_uses:
                return None
            return discount

    def use_promo(self, code):
        with self._con() as con:
            con.execute(
                "UPDATE promo_codes SET used_count = used_count + 1 WHERE code=?", (code,)
            )

    def delete_promo(self, code):
        with self._con() as con:
            changes = con.execute(
                "DELETE FROM promo_codes WHERE code=?", (code,)
            ).rowcount
            return changes > 0

    def get_all_promos(self):
        with self._con() as con:
            rows = con.execute(
                "SELECT code, discount, max_uses, used_count, created_at FROM promo_codes ORDER BY created_at DESC"
            ).fetchall()
            return [
                {"code": r[0], "discount": r[1], "max_uses": r[2], "used_count": r[3], "created_at": r[4]}
                for r in rows
            ]

    def get_stats(self):
        with self._con() as con:
            users = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            paid = con.execute("SELECT COUNT(DISTINCT user_id) FROM access").fetchone()[0]
            revenue_row = con.execute("SELECT COUNT(DISTINCT user_id) FROM pending_payments").fetchone()
            revenue = 0  # Actual revenue tracking requires payment records; approximate here
            by_subject = {}
            rows = con.execute("SELECT subject_key, COUNT(*) FROM access GROUP BY subject_key").fetchall()
            for r in rows:
                by_subject[r[0]] = r[1]
            return {"users": users, "paid": paid, "revenue": revenue, "by_subject": by_subject}

    def get_student_profile(self, user_id):
        """Full profile for admin: user info + subjects + xp + activity."""
        with self._con() as con:
            user = con.execute(
                "SELECT user_id, username, first_name, lang, created_at FROM users WHERE user_id=?",
                (user_id,)
            ).fetchone()
            if not user:
                return None
            subjects = [r[0] for r in con.execute(
                "SELECT subject_key FROM access WHERE user_id=?", (user_id,)).fetchall()]
            quiz_rows = con.execute(
                "SELECT score, total FROM quiz_results WHERE user_id=?", (user_id,)).fetchall()
            tests = len(quiz_rows)
            avg = int(sum(r[0]/r[1]*100 for r in quiz_rows)/tests) if tests else 0
            try:
                xp_row = con.execute(
                    "SELECT xp, level, streak, last_activity FROM user_xp WHERE user_id=?", (user_id,)
                ).fetchone()
            except Exception:
                xp_row = None
            return {
                "user_id": user[0],
                "username": user[1],
                "first_name": user[2],
                "lang": user[3],
                "created_at": user[4],
                "subjects": subjects,
                "tests": tests,
                "avg_score": avg,
                "xp": xp_row[0] if xp_row else 0,
                "level": xp_row[1] if xp_row else 1,
                "streak": xp_row[2] if xp_row else 0,
                "last_activity": xp_row[3] if xp_row else None,
            }

    def get_all_users_with_subjects(self):
        with self._con() as con:
            users = con.execute("SELECT user_id, username, first_name FROM users").fetchall()
            all_access = con.execute("SELECT user_id, subject_key FROM access").fetchall()
            access_map = {}
            for user_id, subject_key in all_access:
                access_map.setdefault(user_id, []).append(subject_key)
            result = []
            for u in users:
                result.append({"user_id": u[0], "username": u[1], "first_name": u[2], "subjects": access_map.get(u[0], [])})
            return result

    # ── XP / Streak / Leaderboard ─────────────────────────────────────────────
 
    def get_or_create_xp(self, user_id):
        with self._con() as con:
            row = con.execute(
                "SELECT xp, level, streak, last_activity FROM user_xp WHERE user_id=?",
                (user_id,)
            ).fetchone()
            if not row:
                today = date.today()
                con.execute(
                    "INSERT OR IGNORE INTO user_xp (user_id, xp, level, streak, last_activity) VALUES (?, 0, 1, 0, ?)",
                    (user_id, today)
                )
                return {"xp": 0, "level": 1, "streak": 0, "last_activity": str(today)}
            return {"xp": row[0], "level": row[1], "streak": row[2], "last_activity": row[3]}
 
    def add_xp(self, user_id, amount):
        today = date.today()
        with self._con() as con:
            row = con.execute(
                "SELECT xp, level, streak, last_activity FROM user_xp WHERE user_id=?",
                (user_id,)
            ).fetchone()
            if not row:
                con.execute(
                    "INSERT OR IGNORE INTO user_xp (user_id, xp, level, streak, last_activity) VALUES (?, ?, 1, 1, ?)",
                    (user_id, amount, today)
                )
                return {"xp": amount, "level": 1, "streak": 1, "leveled_up": False, "bonus": 0}
 
            xp, level, streak, last_act = row
            bonus = 0
            if last_act:
                try:
                    last_date = date.fromisoformat(str(last_act))
                    if last_date == today:
                        new_streak = streak
                    elif last_date == today - timedelta(days=1):
                        new_streak = streak + 1
                        if new_streak >= 7:
                            bonus = 50
                        elif new_streak >= 3:
                            bonus = 20
                    else:
                        new_streak = 1
                except Exception:
                    new_streak = 1
            else:
                new_streak = 1
 
            total_xp = xp + amount + bonus
            thresholds = [0, 100, 250, 500, 1000, 2000, 5000, 10000]
            new_level = 1
            for i, th in enumerate(thresholds):
                if total_xp >= th:
                    new_level = i + 1
            new_level = min(new_level, 8)
            leveled_up = new_level > level
 
            con.execute(
                "UPDATE user_xp SET xp=?, level=?, streak=?, last_activity=? WHERE user_id=?",
                (total_xp, new_level, new_streak, today, user_id)
            )
            return {"xp": total_xp, "level": new_level, "streak": new_streak,
                    "leveled_up": leveled_up, "bonus": bonus}
 
    def get_leaderboard(self, limit=10):
        with self._con() as con:
            rows = con.execute("""
                SELECT u.user_id, u.first_name, u.username, x.xp, x.level, x.streak
                FROM users u JOIN user_xp x ON u.user_id = x.user_id
                ORDER BY x.xp DESC LIMIT ?
            """, (limit,)).fetchall()
            return [{"user_id": r[0], "first_name": r[1], "username": r[2],
                     "xp": r[3], "level": r[4], "streak": r[5]} for r in rows]
 
    # ── Exam Plan ─────────────────────────────────────────────────────────────

    def save_exam_plan(self, user_id, subject_key, exam_date, plan_text):
        with self._con() as con:
            con.execute("""
                INSERT OR REPLACE INTO exam_plans (user_id, subject_key, exam_date, plan_text)
                VALUES (?, ?, ?, ?)
            """, (user_id, subject_key, exam_date, plan_text))

    def get_exam_plan(self, user_id, subject_key):
        with self._con() as con:
            row = con.execute(
                "SELECT exam_date, plan_text FROM exam_plans WHERE user_id=? AND subject_key=?",
                (user_id, subject_key)
            ).fetchone()
            return {"exam_date": row[0], "plan_text": row[1]} if row else None

    # ── Last quiz comparison ───────────────────────────────────────────────────

    def get_last_two_results(self, user_id, subject_key):
        with self._con() as con:
            rows = con.execute("""
                SELECT score, total FROM quiz_results
                WHERE user_id=? AND subject_key=?
                ORDER BY taken_at DESC LIMIT 2
            """, (user_id, subject_key)).fetchall()
            return rows  # [(latest_score, latest_total), (prev_score, prev_total)]

db = Database()
