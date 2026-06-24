@echo off
cd /d D:\ADMStoIQS
call D:\ADMStoIQS\.venv\Scripts\activate.bat

python -m backend.scripts.orquestrar_apuracao --anomes 202605 >> D:\ADMStoIQS\data\logs\orquestrador_agendado.log 2>&1

exit /b %ERRORLEVEL%