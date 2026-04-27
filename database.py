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
        """)
        con.commit()
        con.close()

    def _con(self):
        return sqlite3.connect(DB_PATH)

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
            con.execute("""
                INSERT OR IGNORE INTO access (user_id, subject_key) VALUES (?, ?)
            """, (user_id, subject_key))

    def add_pending_payment(self, user_id, subject_key):
        with self._con() as con:
            con.execute("""
                INSERT OR REPLACE INTO pending_payments (user_id, subject_key) VALUES (?, ?)
            """, (user_id, subject_key))

    def remove_pending(self, user_id, subject_key):
        with self._con() as con:
            con.execute("DELETE FROM pending_payments WHERE user_id=? AND subject_key=?",
                        (user_id, subject_key))

    def has_access(self, user_id, subject_key):
        with self._con() as con:
            row = con.execute("SELECT 1 FROM access WHERE user_id=? AND subject_key=?",
                              (user_id, subject_key)).fetchone()
            return row is not None

db = Database()
