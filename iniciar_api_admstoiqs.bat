@echo off
setlocal

set "ROOT=%~dp0"
cd /d "%ROOT%"

echo [ADMStoIQS API] Ativando ambiente virtual...
call "%ROOT%.venv\Scripts\activate.bat"

echo [ADMStoIQS API] Iniciando em http://127.0.0.1:8000
python -m backend.scripts.run_api

echo.
echo [ADMStoIQS API] Processo encerrado.
pause
endlocal
