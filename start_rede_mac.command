#!/bin/bash
cd "$(dirname "$0")"
if [ ! -d venv ]; then
  python3 -m venv venv
fi
source venv/bin/activate
python3 -m pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
python3 manage.py migrate
IP=$(ipconfig getifaddr en0)
if [ -z "$IP" ]; then IP=$(ipconfig getifaddr en1); fi
if [ -z "$IP" ]; then IP="SEU-IP-LOCAL"; fi
echo ""
echo "Acesse neste computador: http://127.0.0.1:8000/"
echo "Acesse no celular ou outro computador na MESMA rede Wi-Fi: http://$IP:8000/"
echo ""
python3 manage.py runserver 0.0.0.0:8000
