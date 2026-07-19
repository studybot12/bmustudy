# ─── SUBJECTS REGISTRY ────────────────────────────────────────────────────────

SUBJECTS = {}

# ─── STUDY MATERIALS ──────────────────────────────────────────────────────────

MATERIALS = {}

# ─── FLASHCARDS ───────────────────────────────────────────────────────────────

FLASHCARDS = {}

# ─── QUIZ QUESTIONS ───────────────────────────────────────────────────────────

QUIZ_QUESTIONS = {}

# ─── CHEAT SHEETS ─────────────────────────────────────────────────────────────

CHEATSHEETS = {}

# ─── GLOSSARY ─────────────────────────────────────────────────────────────────

GLOSSARY = {}

# ─── TRUE / FALSE QUESTIONS ───────────────────────────────────────────────────

TRUE_FALSE = {}

# ─── VIDEO LINKS ──────────────────────────────────────────────────────────────

VIDEOS = {}


# ─── API FUNCTIONS ────────────────────────────────────────────────────────────

def get_subject_info(subject_key):
    return MATERIALS.get(subject_key, {})

def get_flashcards(subject_key):
    return FLASHCARDS.get(subject_key, [])

def get_quiz_questions(subject_key):
    return QUIZ_QUESTIONS.get(subject_key, [])

def get_cheatsheet(subject_key):
    return CHEATSHEETS.get(subject_key, "")

def get_glossary(subject_key):
    return GLOSSARY.get(subject_key, [])

def get_true_false(subject_key):
    return TRUE_FALSE.get(subject_key, [])

def get_videos(subject_key):
    return VIDEOS.get(subject_key, [])
