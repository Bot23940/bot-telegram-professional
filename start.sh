#!/bin/bash

# Démarrer le backend FastAPI en arrière-plan
python -m uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8000} --log-level warning &

# Attendre que le backend démarre
sleep 5

# Démarrer le bot Telegram (au premier plan pour que Render ne tue pas le processus)
python -u bot/bot.py
