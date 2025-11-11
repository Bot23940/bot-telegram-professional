#!/bin/bash

# Démarrer le bot Telegram en arrière-plan
python -u bot/bot.py &

# Attendre un peu
sleep 3

# Démarrer le backend FastAPI au premier plan (pour que Render détecte le port)
exec python -m uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8000} --log-level warning
