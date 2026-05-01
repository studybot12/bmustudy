import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "studybot.db")

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
        """)
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

    def add_promo(self, code, discount):
        with self._con() as con:
            con.execute("INSERT OR REPLACE INTO promo_codes (code, discount) VALUES (?, ?)",
                        (code, discount))

    def check_promo(self, code):
        with self._con() as con:
            row = con.execute("SELECT discount FROM promo_codes WHERE code=?", (code,)).fetchone()
            return row[0] if row else None

    def get_stats(self):
        with self._con() as con:
            users = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            paid = con.execute("SELECT COUNT(*) FROM access").fetchone()[0]
            by_subject = {}
            rows = con.execute("SELECT subject_key, COUNT(*) FROM access GROUP BY subject_key").fetchall()
            for r in rows:
                by_subject[r[0]] = r[1]
            return {"users": users, "paid": paid, "by_subject": by_subject}

    def get_all_users_with_subjects(self):
        with self._con() as con:
            users = con.execute("SELECT user_id, username, first_name FROM users").fetchall()
            result = []
            for u in users:
                subjects = [r[0] for r in con.execute(
                    "SELECT subject_key FROM access WHERE user_id=?", (u[0],)).fetchall()]
                result.append({"user_id": u[0], "username": u[1], "first_name": u[2], "subjects": subjects})
            return result

db = Database()
