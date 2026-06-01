@echo off
cd /d %~dp0
if not exist venv (
    py -3 -m venv venv
)
call venv\Scripts\activate.bat
python -m pip install -r requirements.txt
if not exist .env copy .env.example .env
python manage.py migrate
echo.
echo Acesse neste computador: http://127.0.0.1:8000/
echo Para celular/outro computador na mesma rede, veja seu IPv4 com: ipconfig
echo Exemplo: http://192.168.1.50:8000/
echo.
python manage.py runserver 0.0.0.0:8000
pause
