import os
import sys

# Flat repo — all files are in root
from app import app

if __name__ == "__main__":
    from database import db
    db.init()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
