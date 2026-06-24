@echo off
setlocal

set "ROOT=%~dp0"
set "FRONTEND_PORT=5173"
set "PATH=%ROOT%tools\nodejs;%PATH%"

cd /d "%ROOT%frontend"

echo [ADMStoIQS Frontend] Ativando ambiente virtual...
call "%ROOT%.venv\Scripts\activate.bat"

echo [ADMStoIQS Frontend] Iniciando em http://127.0.0.1:%FRONTEND_PORT%/ADMStoIQS.html
call "%ROOT%tools\nodejs\npm.cmd" run dev -- --host 127.0.0.1 --port %FRONTEND_PORT%

echo.
echo [ADMStoIQS Frontend] Processo encerrado.
pause
endlocal
