#!/usr/bin/env bash
set -euo pipefail
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
npm install
test -f .env || cp .env.example .env
echo "Setup complete. Run 'npm run dev' and 'cd backend && ../.venv/bin/python -m uvicorn app.main:app --reload --port 8000' in two terminals."
