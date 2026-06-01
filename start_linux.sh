#!/usr/bin/env bash
cd "$(dirname "$0")"
if [ ! -d venv ]; then
  python3 -m venv venv
fi
source venv/bin/activate
python3 -m pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
python3 manage.py migrate
python3 manage.py runserver 127.0.0.1:8000
