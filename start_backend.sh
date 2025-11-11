#!/bin/bash

# Démarrer uniquement le backend FastAPI
python -m uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8000}
