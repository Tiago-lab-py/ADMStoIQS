@echo off
setlocal

set "ROOT=%~dp0"
set "FRONTEND_PORT=5173"
set "FRONTEND_URL=http://127.0.0.1:%FRONTEND_PORT%/ADMStoIQS.html"

cd /d "%ROOT%"

if not exist "%ROOT%.venv\Scripts\activate.bat" (
    echo [ADMStoIQS] Ambiente virtual nao encontrado em "%ROOT%.venv".
    echo [ADMStoIQS] Crie ou restaure o .venv antes de iniciar.
    pause
    exit /b 1
)

if not exist "%ROOT%tools\nodejs\npm.cmd" (
    echo [ADMStoIQS] tools\nodejs\npm.cmd nao encontrado.
    pause
    exit /b 1
)

echo [ADMStoIQS] Iniciando API em http://127.0.0.1:8000 ...
start "ADMStoIQS API" "%ROOT%iniciar_api_admstoiqs.bat"

echo [ADMStoIQS] Iniciando frontend em %FRONTEND_URL% ...
start "ADMStoIQS Frontend" "%ROOT%iniciar_frontend_admstoiqs.bat"

timeout /t 5 /nobreak >nul
start "" "%FRONTEND_URL%"

echo [ADMStoIQS] Pronto. Se o navegador abrir antes do Vite concluir, aguarde alguns segundos e atualize a pagina.
endlocal
