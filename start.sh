#!/bin/bash
# Start both the FastAPI server and the Telegram bot in parallel
uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000} &
python bot.py
