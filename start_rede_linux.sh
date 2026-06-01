#!/usr/bin/env bash
cd "$(dirname "$0")"
if [ ! -d venv ]; then
  python3 -m venv venv
fi
source venv/bin/activate
python3 -m pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
python3 manage.py migrate
IP=$(hostname -I | awk '{print $1}')
[ -z "$IP" ] && IP="SEU-IP-LOCAL"
echo ""
echo "Acesse neste computador: http://127.0.0.1:8000/"
echo "Acesse no celular ou outro computador na MESMA rede: http://$IP:8000/"
echo ""
python3 manage.py runserver 0.0.0.0:8000
